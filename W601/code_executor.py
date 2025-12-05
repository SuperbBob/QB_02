"""
Code Executor Module
Safely executes generated Python code and captures results
Based on reference: execute_python.py (Jupyter kernel approach)
"""
import sys
import io
import json
import traceback
import base64
import logging
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import signal
import config

# Try to import Jupyter kernel for better execution
try:
    from jupyter_client.manager import start_new_kernel
    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False

logger = logging.getLogger(f'excel_agent.{__name__}')


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")


class JupyterCodeExecutor:
    """Execute code using Jupyter kernel for better isolation and output capture"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        
    def execute(self, code: str, df: pd.DataFrame, df_name: str = "df") -> Dict[str, Any]:
        """Execute code with Jupyter kernel"""
        result = {
            "success": False,
            "output": "",
            "result": None,
            "figure": None,
            "error": None,
            "used_columns": []
        }
        
        kernel_manager = None
        client = None
        
        try:
            # Start kernel
            kernel_manager, client = start_new_kernel()
            
            # First, inject the DataFrame
            # Save df to a temp file and load it
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
                df.to_pickle(tmp.name)
                tmp_path = tmp.name
            
            setup_code = f'''
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.simplefilter(action='ignore', category=Warning)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)

{df_name} = pd.read_pickle("{tmp_path}")
'''
            self._run_code(setup_code, client)
            
            # Execute the actual code
            output = self._run_code(code, client)
            
            # Get analysis_result if defined
            result_code = '''
import json
import base64
import io

_result_dict = {}

if 'analysis_result' in dir():
    ar = analysis_result
    if isinstance(ar, pd.DataFrame):
        _result_dict['analysis_result'] = {
            'type': 'dataframe',
            'data': ar.head(100).to_dict(orient='records'),
            'columns': list(ar.columns),
            'shape': list(ar.shape)
        }
    elif isinstance(ar, pd.Series):
        _result_dict['analysis_result'] = {
            'type': 'series',
            'data': ar.head(100).to_dict(),
            'name': str(ar.name)
        }
    elif isinstance(ar, (int, float)):
        _result_dict['analysis_result'] = {'type': 'number', 'value': float(ar)}
    else:
        _result_dict['analysis_result'] = {'type': 'other', 'value': str(ar)}

if 'used_columns' in dir():
    _result_dict['used_columns'] = used_columns

if plt.get_fignums():
    fig = plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    _result_dict['figure'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close('all')

print("__RESULT_JSON__" + json.dumps(_result_dict))
'''
            result_output = self._run_code(result_code, client)
            
            # Parse result
            if "__RESULT_JSON__" in result_output:
                try:
                    json_str = result_output.split("__RESULT_JSON__")[1].strip()
                    # Clean up JSON string - take only until first newline or end
                    if '\n' in json_str:
                        json_str = json_str.split('\n')[0]
                    # Find the JSON object boundaries
                    if json_str.startswith('{'):
                        depth = 0
                        end_idx = 0
                        for i, c in enumerate(json_str):
                            if c == '{':
                                depth += 1
                            elif c == '}':
                                depth -= 1
                                if depth == 0:
                                    end_idx = i + 1
                                    break
                        json_str = json_str[:end_idx]
                    
                    result_data = json.loads(json_str)
                    
                    if 'analysis_result' in result_data:
                        result["result"] = result_data['analysis_result']
                    if 'used_columns' in result_data:
                        result["used_columns"] = result_data['used_columns']
                    if 'figure' in result_data:
                        result["figure"] = f"data:image/png;base64,{result_data['figure']}"
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse error: {je}, raw: {result_output[:200]}")
                    # Continue without parsed result
            
            result["output"] = output
            result["success"] = True
            
            # Clean up temp file
            import os
            os.unlink(tmp_path)
            
        except Exception as e:
            logger.error(f"Jupyter execution error: {e}")
            result["error"] = str(e)
            
        finally:
            if client:
                try:
                    client.stop_channels()
                except:
                    pass
            if kernel_manager:
                try:
                    kernel_manager.shutdown_kernel()
                except:
                    pass
                    
        return result
    
    def _run_code(self, code: str, client) -> str:
        """Execute code and get output"""
        try:
            client.execute(code)
            output = []
            
            while True:
                try:
                    msg = client.get_iopub_msg(timeout=self.timeout)
                    msg_type = msg['header']['msg_type']
                    content = msg['content']
                    
                    if msg_type == 'stream':
                        output.append(content['text'])
                    elif msg_type == 'execute_result':
                        if 'text/plain' in content.get('data', {}):
                            output.append(content['data']['text/plain'])
                    elif msg_type == 'error':
                        return "ERROR:\n" + '\n'.join(content['traceback'])
                    elif msg_type == 'status' and content['execution_state'] == 'idle':
                        break
                        
                except Exception as e:
                    logger.error(f"Error getting output: {e}")
                    break
                    
            return '\n'.join(output) if output else ""
            
        except Exception as e:
            return f"Exception: {str(e)}"


class SimpleCodeExecutor:
    """Fallback executor using exec() when Jupyter is not available"""
    
    def __init__(self, timeout: int = None):
        self.timeout = timeout or config.MAX_CODE_EXECUTION_TIME
        
    def execute(self, code: str, df: pd.DataFrame, df_name: str = "df") -> Dict[str, Any]:
        """Execute code with exec()"""
        result = {
            "success": False,
            "output": "",
            "result": None,
            "figure": None,
            "error": None,
            "used_columns": []
        }
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        namespace = {
            df_name: df.copy(),
            'pd': pd,
            'np': np,
            'plt': plt,
            'matplotlib': matplotlib,
            '__builtins__': self._get_safe_builtins()
        }
        
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout)
            
            plt.close('all')
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)
            
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            result["output"] = stdout_capture.getvalue()
            result["success"] = True
            
            if 'analysis_result' in namespace:
                result["result"] = self._serialize_result(namespace['analysis_result'])
            
            if 'used_columns' in namespace:
                result["used_columns"] = namespace['used_columns']
            
            # Capture any matplotlib figures
            if plt.get_fignums():
                result["figure"] = self._capture_figure(namespace.get('figure'))
            elif 'figure' in namespace:
                result["figure"] = self._capture_figure(namespace.get('figure'))
            elif 'fig' in namespace:
                result["figure"] = self._capture_figure(namespace.get('fig'))
                
        except TimeoutError:
            result["error"] = f"代码执行超时（{self.timeout}秒）"
        except Exception as e:
            result["error"] = f"执行错误: {str(e)}\n{traceback.format_exc()}"
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            plt.close('all')
            
        return result
    
    def _get_safe_builtins(self) -> Dict:
        """Get a restricted set of builtins"""
        return {
            'abs': abs, 'all': all, 'any': any, 'bool': bool,
            'dict': dict, 'enumerate': enumerate, 'filter': filter,
            'float': float, 'format': format, 'frozenset': frozenset,
            'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
            'iter': iter, 'len': len, 'list': list, 'map': map,
            'max': max, 'min': min, 'next': next, 'print': print,
            'range': range, 'repr': repr, 'reversed': reversed,
            'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
            'str': str, 'sum': sum, 'tuple': tuple, 'type': type,
            'zip': zip, 'True': True, 'False': False, 'None': None,
            '__import__': self._safe_import
        }
    
    def _safe_import(self, name, *args, **kwargs):
        """Restricted import"""
        allowed = {
            'pandas', 'numpy', 'matplotlib', 'matplotlib.pyplot',
            'datetime', 'math', 'statistics', 're', 'json',
            'collections', 'itertools', 'functools', 'plotly',
            'plotly.graph_objects', 'plotly.express'
        }
        if name in allowed or name.startswith('matplotlib') or name.startswith('plotly'):
            return __import__(name, *args, **kwargs)
        raise ImportError(f"Import of '{name}' is not allowed")
    
    def _serialize_result(self, result: Any) -> Any:
        """Serialize analysis result for JSON response"""
        if isinstance(result, pd.DataFrame):
            return {
                "type": "dataframe",
                "data": result.head(100).to_dict(orient='records'),
                "columns": list(result.columns),
                "shape": list(result.shape),
                "dtypes": {col: str(dtype) for col, dtype in result.dtypes.items()}
            }
        elif isinstance(result, pd.Series):
            return {
                "type": "series",
                "data": result.head(100).to_dict(),
                "name": result.name,
                "dtype": str(result.dtype)
            }
        elif isinstance(result, (np.integer, np.floating)):
            return {"type": "number", "value": float(result)}
        elif isinstance(result, np.ndarray):
            return {"type": "array", "data": result.tolist()[:100]}
        elif isinstance(result, dict):
            return {"type": "dict", "data": self._convert_numpy_types(result)}
        else:
            return {"type": "other", "value": str(result)}
    
    def _convert_numpy_types(self, obj: Any) -> Any:
        """Convert numpy types to Python native types"""
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(v) for v in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return obj
    
    def _capture_figure(self, figure=None) -> Optional[str]:
        """Capture matplotlib figure as base64"""
        try:
            # Try to get the current figure if none provided
            if figure is None:
                if plt.get_fignums():
                    figure = plt.gcf()
                else:
                    return None
            
            # Check if it's a matplotlib figure
            if not hasattr(figure, 'savefig'):
                # Maybe it's a tuple (figure, axes) from plt.subplots
                if isinstance(figure, tuple) and len(figure) > 0:
                    figure = figure[0]
                else:
                    return None
            
            # Don't require axes - some figures are valid without them
            buffer = io.BytesIO()
            figure.savefig(buffer, format='png', dpi=100, bbox_inches='tight',
                          facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            if buffer.getbuffer().nbytes == 0:
                return None
                
            image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            buffer.close()
            
            return f"data:image/png;base64,{image_base64}"
        except Exception as e:
            logger.error(f"Figure capture error: {e}")
            return None


class CodeExecutor:
    """Main code executor - uses Jupyter if available, falls back to exec()"""
    
    def __init__(self, timeout: int = None):
        self.timeout = timeout or config.MAX_CODE_EXECUTION_TIME
        self._simple_executor = SimpleCodeExecutor(self.timeout)
        
        if JUPYTER_AVAILABLE:
            logger.info("Using Jupyter kernel for code execution")
            self._jupyter_executor = JupyterCodeExecutor(self.timeout)
            self._use_jupyter = True
        else:
            logger.info("Jupyter not available, using simple executor")
            self._jupyter_executor = None
            self._use_jupyter = False
    
    def execute(self, code: str, df: pd.DataFrame, df_name: str = "df") -> Dict[str, Any]:
        """Execute code and return results, with fallback"""
        # Try Jupyter first if available
        if self._use_jupyter and self._jupyter_executor:
            try:
                result = self._jupyter_executor.execute(code, df, df_name)
                if result["success"]:
                    return result
                # If Jupyter failed, fall back to simple executor
                logger.warning(f"Jupyter execution failed: {result.get('error')}, falling back to simple executor")
            except Exception as e:
                logger.warning(f"Jupyter executor error: {e}, falling back to simple executor")
        
        # Fallback to simple executor
        return self._simple_executor.execute(code, df, df_name)


class ResultFormatter:
    """Format execution results for display"""
    
    @staticmethod
    def format_for_display(result: Dict[str, Any]) -> Dict[str, Any]:
        """Format execution result for frontend display"""
        formatted = {
            "success": result["success"],
            "message": "",
            "data": None,
            "visualization": None,
            "used_columns": result.get("used_columns", []),
            "output": result.get("output", "")
        }
        
        if not result["success"]:
            formatted["message"] = f"执行失败: {result.get('error', '未知错误')}"
            return formatted
            
        formatted["message"] = "分析完成"
        
        if result.get("result"):
            res = result["result"]
            if res["type"] == "dataframe":
                formatted["data"] = {
                    "type": "table",
                    "headers": res["columns"],
                    "rows": res["data"],
                    "total_rows": res["shape"][0],
                    "total_columns": res["shape"][1]
                }
            elif res["type"] == "series":
                formatted["data"] = {
                    "type": "series",
                    "name": res["name"],
                    "values": res["data"]
                }
            elif res["type"] == "number":
                formatted["data"] = {
                    "type": "number",
                    "value": res["value"]
                }
            elif res["type"] == "dict":
                formatted["data"] = {
                    "type": "summary",
                    "content": res["data"]
                }
            else:
                formatted["data"] = {
                    "type": "text",
                    "content": str(res.get("value", res))
                }
        
        if result.get("figure"):
            formatted["visualization"] = result["figure"]
            
        return formatted
    
    @staticmethod
    def format_columns_used(columns: list) -> str:
        """Format used columns as readable string"""
        if not columns:
            return "未指定使用的数据列"
        return f"本次分析使用列：{', '.join(columns)}"
