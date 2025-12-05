"""
Excel Agent - Main FastAPI Application
Natural language powered Excel data analysis
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

import config
from excel_processor import ExcelProcessor, KnowledgeBase
from nlp_parser import NLPParser, AnalysisIntent, FileSelector
from code_generator import CodeGenerator
from code_executor import CodeExecutor, ResultFormatter
from voice_handler import VoiceHandler, WebSocketVoiceSession


# Global instances
knowledge_base: KnowledgeBase = None
nlp_parser: NLPParser = None
code_generator: CodeGenerator = None
code_executor: CodeExecutor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global knowledge_base, nlp_parser, code_generator, code_executor
    
    # Initialize components
    knowledge_base = KnowledgeBase(str(config.KNOWLEDGE_BASE_DIR))
    nlp_parser = NLPParser()
    code_generator = CodeGenerator()
    code_executor = CodeExecutor()
    
    # Scan for existing files
    count = knowledge_base.scan_directory()
    print(f"Loaded {count} files from knowledge base")
    
    yield
    
    # Cleanup
    print("Shutting down Excel Agent")


app = FastAPI(
    title="Excel智能分析Agent",
    description="基于自然语言的Excel数据分析系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


# Pydantic models
class AnalysisRequest(BaseModel):
    query: str
    file_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    code: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    visualization: Optional[str] = None
    used_columns: List[str] = []
    selected_file: Optional[str] = None


class FileInfo(BaseModel):
    file_id: str
    file_name: str
    sheets: List[Dict[str, Any]]


# REST API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    return get_frontend_html()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "files_loaded": len(knowledge_base.files) if knowledge_base else 0,
        "openai_configured": bool(config.OPENAI_API_KEY)
    }


@app.get("/api/files", response_model=List[FileInfo])
async def list_files():
    """List all files in knowledge base"""
    files = []
    for file_id, summary in knowledge_base.index.items():
        files.append(FileInfo(
            file_id=file_id,
            file_name=summary["file_name"],
            sheets=summary["sheets"]
        ))
    return files


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload an Excel file to the knowledge base"""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持: {', '.join(config.SUPPORTED_EXTENSIONS)}"
        )
    
    # Save file
    file_path = config.KNOWLEDGE_BASE_DIR / file.filename
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Add to knowledge base
        if knowledge_base.add_file(str(file_path)):
            return {"success": True, "message": f"文件 {file.filename} 上传成功"}
        else:
            raise HTTPException(status_code=500, detail="文件处理失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """Analyze data based on natural language query"""
    query = request.query.strip()
    
    if not query:
        return AnalysisResponse(
            success=False,
            message="请输入分析问题"
        )
    
    if not knowledge_base.files:
        return AnalysisResponse(
            success=False,
            message="知识库为空，请先上传Excel文件"
        )
    
    try:
        # Get file context
        file_context = knowledge_base.get_all_summaries()
        
        # Parse query to get analysis intent
        intent = nlp_parser.parse_query(query, file_context)
        
        # Select target file
        file_id = request.file_id
        if not file_id:
            file_id = nlp_parser.select_target_file(
                query, intent, knowledge_base.index
            )
        
        if not file_id or file_id not in knowledge_base.files:
            file_id = list(knowledge_base.files.keys())[0]
            
        # Get file processor and data
        processor = knowledge_base.get_file_by_id(file_id)
        file_info = knowledge_base.index[file_id]
        
        # Process sheets and get DataFrame
        processed_sheets = processor.process_all_sheets()
        first_sheet = list(processed_sheets.keys())[0]
        df = processed_sheets[first_sheet]
        
        # Generate analysis code
        code, used_columns = code_generator.generate_code(
            query, intent, file_info, "df"
        )
        
        # Execute code
        exec_result = code_executor.execute(code, df, "df")
        
        # Format result
        formatted = ResultFormatter.format_for_display(exec_result)
        
        return AnalysisResponse(
            success=formatted["success"],
            message=formatted["message"],
            code=code,
            result=formatted.get("data"),
            visualization=formatted.get("visualization"),
            used_columns=exec_result.get("used_columns", used_columns),
            selected_file=file_info["file_name"]
        )
        
    except Exception as e:
        import traceback
        return AnalysisResponse(
            success=False,
            message=f"分析失败: {str(e)}",
            code=None
        )


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file from knowledge base"""
    if file_id not in knowledge_base.files:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        # Get file path and delete
        file_info = knowledge_base.index[file_id]
        file_path = Path(file_info["file_path"])
        if file_path.exists():
            file_path.unlink()
            
        # Remove from knowledge base
        del knowledge_base.files[file_id]
        del knowledge_base.index[file_id]
        
        return {"success": True, "message": "文件已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for voice input
@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for voice input"""
    await websocket.accept()
    
    async def on_transcription(text: str):
        """Callback when voice is transcribed"""
        if text:
            # Send transcription to client
            await websocket.send_json({
                "type": "transcription",
                "text": text
            })
            
            # Optionally auto-analyze
            # result = await analyze(AnalysisRequest(query=text))
            # await websocket.send_json({
            #     "type": "analysis_result",
            #     "data": result.dict()
            # })
    
    session = WebSocketVoiceSession(websocket, on_transcription)
    
    try:
        while True:
            data = await websocket.receive_text()
            await session.handle_message(data)
            
    except WebSocketDisconnect:
        print("Voice WebSocket disconnected")
    except Exception as e:
        print(f"Voice WebSocket error: {e}")


# WebSocket for real-time analysis updates
@app.websocket("/ws/analysis")
async def analysis_websocket(websocket: WebSocket):
    """WebSocket for real-time analysis progress updates"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "analyze":
                query = data.get("query", "")
                file_id = data.get("file_id")
                
                # Send progress updates
                await websocket.send_json({
                    "type": "progress",
                    "step": "parsing",
                    "message": "正在解析问题..."
                })
                
                # Perform analysis
                request = AnalysisRequest(query=query, file_id=file_id)
                result = await analyze(request)
                
                await websocket.send_json({
                    "type": "progress",
                    "step": "complete",
                    "message": "分析完成"
                })
                
                await websocket.send_json({
                    "type": "result",
                    "data": result.dict()
                })
                
    except WebSocketDisconnect:
        print("Analysis WebSocket disconnected")
    except Exception as e:
        print(f"Analysis WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


def get_frontend_html() -> str:
    """Return the frontend HTML"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Excel智能分析Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e14;
            --bg-secondary: #1a1f2e;
            --bg-tertiary: #252b3d;
            --accent-cyan: #00d9ff;
            --accent-purple: #b362ff;
            --accent-green: #39ff85;
            --accent-orange: #ff9f43;
            --text-primary: #e6e6e6;
            --text-secondary: #8892a2;
            --border-color: #2d3548;
            --shadow-glow: 0 0 30px rgba(0, 217, 255, 0.15);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Noto Sans SC', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at 20% 0%, rgba(0, 217, 255, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 100%, rgba(179, 98, 255, 0.08) 0%, transparent 50%);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
            position: relative;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 24px;
            margin-top: 30px;
        }
        
        .panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow-glow);
        }
        
        .panel-title {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .panel-title::before {
            content: '';
            width: 4px;
            height: 20px;
            background: linear-gradient(180deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 2px;
        }
        
        /* File Upload Area */
        .upload-area {
            border: 2px dashed var(--border-color);
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            border-color: var(--accent-cyan);
            background: rgba(0, 217, 255, 0.05);
        }
        
        .upload-area.dragover {
            border-color: var(--accent-green);
            background: rgba(57, 255, 133, 0.1);
        }
        
        .upload-icon {
            font-size: 3rem;
            margin-bottom: 10px;
        }
        
        /* File List */
        .file-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .file-item:hover {
            transform: translateX(5px);
            border-left: 3px solid var(--accent-cyan);
        }
        
        .file-item.selected {
            border-left: 3px solid var(--accent-green);
            background: rgba(57, 255, 133, 0.1);
        }
        
        .file-name {
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .delete-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 5px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .delete-btn:hover {
            color: #ff6b6b;
            background: rgba(255, 107, 107, 0.1);
        }
        
        /* Query Input */
        .query-section {
            margin-bottom: 24px;
        }
        
        .query-input-wrapper {
            position: relative;
            display: flex;
            gap: 12px;
        }
        
        .query-input {
            flex: 1;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 20px;
            color: var(--text-primary);
            font-size: 1rem;
            font-family: inherit;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .query-input:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 20px rgba(0, 217, 255, 0.2);
        }
        
        .voice-btn {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-cyan));
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .voice-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 0 30px rgba(179, 98, 255, 0.4);
        }
        
        .voice-btn.recording {
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7); }
            50% { box-shadow: 0 0 0 15px rgba(255, 107, 107, 0); }
        }
        
        .analyze-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border: none;
            border-radius: 12px;
            padding: 16px 32px;
            color: white;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .analyze-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 217, 255, 0.3);
        }
        
        .analyze-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Results Section */
        .results-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 24px;
        }
        
        .result-panel {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 20px;
            max-height: 500px;
            overflow: auto;
        }
        
        .result-panel.full-width {
            grid-column: 1 / -1;
        }
        
        .result-title {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* Code Display */
        .code-block {
            background: #1e1e2e;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
        }
        
        /* Data Table */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        
        .data-table th {
            background: var(--bg-secondary);
            padding: 12px;
            text-align: left;
            font-weight: 500;
            color: var(--accent-cyan);
            border-bottom: 2px solid var(--border-color);
        }
        
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .data-table tr:hover {
            background: rgba(0, 217, 255, 0.05);
        }
        
        /* Visualization */
        .viz-container img {
            max-width: 100%;
            border-radius: 8px;
        }
        
        /* Used Columns Badge */
        .columns-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(57, 255, 133, 0.1);
            border: 1px solid var(--accent-green);
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 0.85rem;
            margin-top: 16px;
        }
        
        .columns-badge span {
            color: var(--accent-green);
        }
        
        /* Loading State */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border-color);
            border-top-color: var(--accent-cyan);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 24px;
            box-shadow: var(--shadow-glow);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        
        .toast.success { border-color: var(--accent-green); }
        .toast.error { border-color: #ff6b6b; }
        
        @keyframes slideIn {
            from { transform: translateX(100px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
        
        /* Responsive */
        @media (max-width: 1024px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .results-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-indicator.online { background: var(--accent-green); }
        .status-indicator.offline { background: #ff6b6b; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Excel智能分析Agent</h1>
            <p class="subtitle">使用自然语言分析您的Excel数据 · 支持语音输入</p>
        </header>
        
        <div class="main-grid">
            <!-- Sidebar -->
            <aside>
                <div class="panel">
                    <h3 class="panel-title">📁 知识库文件</h3>
                    
                    <div class="upload-area" id="uploadArea">
                        <div class="upload-icon">📤</div>
                        <p>拖拽文件到此处或点击上传</p>
                        <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 8px;">
                            支持 .xlsx, .xls, .csv
                        </p>
                        <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" hidden>
                    </div>
                    
                    <div class="file-list" id="fileList">
                        <div class="empty-state">暂无文件</div>
                    </div>
                </div>
                
                <div class="panel" style="margin-top: 20px;">
                    <h3 class="panel-title">📊 系统状态</h3>
                    <p><span class="status-indicator" id="statusIndicator"></span>
                       <span id="statusText">检查中...</span></p>
                    <p style="margin-top: 10px; font-size: 0.85rem; color: var(--text-secondary);">
                        已加载文件: <span id="fileCount">0</span>
                    </p>
                </div>
            </aside>
            
            <!-- Main Content -->
            <main>
                <div class="panel">
                    <h3 class="panel-title">💬 智能分析</h3>
                    
                    <div class="query-section">
                        <div class="query-input-wrapper">
                            <input type="text" 
                                   class="query-input" 
                                   id="queryInput" 
                                   placeholder="输入您的分析问题，例如：帮我分析各地区的销售趋势..."
                                   autocomplete="off">
                            <button class="voice-btn" id="voiceBtn" title="语音输入">
                                🎤
                            </button>
                        </div>
                        <div style="margin-top: 16px; display: flex; gap: 12px;">
                            <button class="analyze-btn" id="analyzeBtn">
                                🚀 开始分析
                            </button>
                        </div>
                    </div>
                    
                    <div id="resultsContainer" style="display: none;">
                        <div class="results-grid">
                            <!-- Generated Code -->
                            <div class="result-panel">
                                <div class="result-title">
                                    <span>📝</span> 生成的代码
                                </div>
                                <pre class="code-block"><code id="codeDisplay" class="language-python"></code></pre>
                            </div>
                            
                            <!-- Visualization -->
                            <div class="result-panel">
                                <div class="result-title">
                                    <span>📈</span> 可视化结果
                                </div>
                                <div class="viz-container" id="vizContainer">
                                    <div class="empty-state">暂无图表</div>
                                </div>
                            </div>
                            
                            <!-- Data Result -->
                            <div class="result-panel full-width">
                                <div class="result-title">
                                    <span>📋</span> 分析结果
                                </div>
                                <div id="dataContainer">
                                    <div class="empty-state">等待分析...</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Used Columns -->
                        <div class="columns-badge" id="columnsUsed" style="display: none;">
                            <span>📊 使用的数据列:</span>
                            <span id="columnsList"></span>
                        </div>
                    </div>
                    
                    <div class="loading" id="loadingIndicator" style="display: none;">
                        <div class="spinner"></div>
                        <span style="margin-left: 16px;">正在分析中...</span>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
    <script>
        // State
        let selectedFileId = null;
        let isRecording = false;
        let voiceWs = null;
        let mediaRecorder = null;
        
        // Elements
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const queryInput = document.getElementById('queryInput');
        const voiceBtn = document.getElementById('voiceBtn');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const resultsContainer = document.getElementById('resultsContainer');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const codeDisplay = document.getElementById('codeDisplay');
        const vizContainer = document.getElementById('vizContainer');
        const dataContainer = document.getElementById('dataContainer');
        const columnsUsed = document.getElementById('columnsUsed');
        const columnsList = document.getElementById('columnsList');
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const fileCount = document.getElementById('fileCount');
        
        // Initialize
        async function init() {
            await checkHealth();
            await loadFiles();
            setupEventListeners();
            initVoiceWebSocket();
        }
        
        async function checkHealth() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                statusIndicator.classList.add('online');
                statusText.textContent = data.openai_configured ? 'AI已就绪' : '基础模式';
                fileCount.textContent = data.files_loaded;
            } catch (e) {
                statusIndicator.classList.add('offline');
                statusText.textContent = '连接失败';
            }
        }
        
        async function loadFiles() {
            try {
                const res = await fetch('/api/files');
                const files = await res.json();
                renderFileList(files);
                fileCount.textContent = files.length;
            } catch (e) {
                console.error('Failed to load files:', e);
            }
        }
        
        function renderFileList(files) {
            if (files.length === 0) {
                fileList.innerHTML = '<div class="empty-state">暂无文件</div>';
                return;
            }
            
            fileList.innerHTML = files.map(file => `
                <div class="file-item ${file.file_id === selectedFileId ? 'selected' : ''}" 
                     data-id="${file.file_id}">
                    <span class="file-name" title="${file.file_name}">
                        📄 ${file.file_name}
                    </span>
                    <button class="delete-btn" onclick="event.stopPropagation(); deleteFile('${file.file_id}')" title="删除文件">❌</button>
                </div>
            `).join('');
            
            // Add event listeners for file selection
            fileList.querySelectorAll('.file-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    // Only select if not clicking delete button
                    if (!e.target.classList.contains('delete-btn')) {
                        selectFile(item.dataset.id);
                    }
                });
            });
        }
        
        function selectFile(fileId) {
            selectedFileId = fileId;
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.toggle('selected', item.dataset.id === fileId);
            });
        }
        
        async function deleteFile(fileId) {
            if (!fileId) {
                showToast('文件ID无效', 'error');
                return;
            }
            
            if (!confirm('确定要删除此文件吗？')) return;
            
            try {
                const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
                const data = await res.json();
                
                if (res.ok) {
                    showToast('✅ 文件已删除', 'success');
                    if (selectedFileId === fileId) {
                        selectedFileId = null;
                    }
                    await loadFiles();
                } else {
                    showToast('删除失败: ' + (data.detail || '未知错误'), 'error');
                }
            } catch (e) {
                console.error('Delete error:', e);
                showToast('删除失败: ' + e.message, 'error');
            }
        }
        
        function setupEventListeners() {
            // File upload
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            uploadArea.addEventListener('drop', handleFileDrop);
            fileInput.addEventListener('change', handleFileSelect);
            
            // Query
            analyzeBtn.addEventListener('click', analyze);
            queryInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') analyze();
            });
            
            // Voice
            voiceBtn.addEventListener('click', toggleVoiceRecording);
        }
        
        async function handleFileDrop(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                await uploadFile(files[0]);
            }
        }
        
        async function handleFileSelect(e) {
            if (e.target.files.length > 0) {
                await uploadFile(e.target.files[0]);
            }
        }
        
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                analyzeBtn.disabled = true;
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await res.json();
                if (res.ok) {
                    showToast('文件上传成功', 'success');
                    await loadFiles();
                } else {
                    showToast(data.detail || '上传失败', 'error');
                }
            } catch (e) {
                showToast('上传失败: ' + e.message, 'error');
            } finally {
                analyzeBtn.disabled = false;
                fileInput.value = '';
            }
        }
        
        async function analyze() {
            const query = queryInput.value.trim();
            if (!query) {
                showToast('请输入分析问题', 'error');
                return;
            }
            
            loadingIndicator.style.display = 'flex';
            resultsContainer.style.display = 'none';
            analyzeBtn.disabled = true;
            
            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        file_id: selectedFileId
                    })
                });
                
                const data = await res.json();
                displayResults(data);
            } catch (e) {
                showToast('分析失败: ' + e.message, 'error');
            } finally {
                loadingIndicator.style.display = 'none';
                analyzeBtn.disabled = false;
            }
        }
        
        function displayResults(data) {
            resultsContainer.style.display = 'block';
            
            // Display code
            if (data.code) {
                codeDisplay.textContent = data.code;
                Prism.highlightElement(codeDisplay);
            }
            
            // Display visualization
            if (data.visualization) {
                vizContainer.innerHTML = `<img src="${data.visualization}" alt="分析图表">`;
            } else {
                vizContainer.innerHTML = '<div class="empty-state">暂无图表</div>';
            }
            
            // Display data result
            if (data.result) {
                dataContainer.innerHTML = formatDataResult(data.result);
            } else if (data.message) {
                dataContainer.innerHTML = `<p>${data.message}</p>`;
            }
            
            // Display used columns
            if (data.used_columns && data.used_columns.length > 0) {
                columnsUsed.style.display = 'inline-flex';
                columnsList.textContent = data.used_columns.join(', ');
            } else {
                columnsUsed.style.display = 'none';
            }
            
            if (data.selected_file) {
                showToast(`分析文件: ${data.selected_file}`, 'success');
            }
        }
        
        function formatDataResult(result) {
            if (result.type === 'table' && result.rows) {
                let html = '<div style="overflow-x: auto;"><table class="data-table"><thead><tr>';
                result.headers.forEach(h => html += `<th>${h}</th>`);
                html += '</tr></thead><tbody>';
                result.rows.slice(0, 50).forEach(row => {
                    html += '<tr>';
                    result.headers.forEach(h => html += `<td>${row[h] ?? ''}</td>`);
                    html += '</tr>';
                });
                html += '</tbody></table></div>';
                if (result.total_rows > 50) {
                    html += `<p style="margin-top: 10px; color: var(--text-secondary);">显示前50行，共${result.total_rows}行</p>`;
                }
                return html;
            } else if (result.type === 'number') {
                return `<div style="font-size: 2rem; color: var(--accent-cyan);">${result.value}</div>`;
            } else if (result.type === 'summary') {
                return `<pre>${JSON.stringify(result.content, null, 2)}</pre>`;
            }
            return `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        }
        
        // Voice Recording using Web Speech API
        let recognition = null;
        
        function initVoiceRecognition() {
            // Check for Web Speech API support
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!SpeechRecognition) {
                console.log('Web Speech API not supported');
                voiceBtn.style.display = 'none';
                return;
            }
            
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'zh-CN'; // Chinese language
            
            recognition.onstart = () => {
                isRecording = true;
                voiceBtn.classList.add('recording');
                voiceBtn.innerHTML = '⏹️';
                showToast('🎤 正在聆听...请说话', 'success');
            };
            
            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                // Show interim results in real-time
                if (interimTranscript) {
                    queryInput.value = interimTranscript;
                    queryInput.style.color = 'var(--text-secondary)';
                }
                
                // Set final result
                if (finalTranscript) {
                    queryInput.value = finalTranscript;
                    queryInput.style.color = 'var(--text-primary)';
                    showToast('✅ 语音识别完成', 'success');
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                let errorMsg = '语音识别错误';
                
                switch (event.error) {
                    case 'no-speech':
                        errorMsg = '未检测到语音，请再试一次';
                        break;
                    case 'audio-capture':
                        errorMsg = '无法访问麦克风';
                        break;
                    case 'not-allowed':
                        errorMsg = '请允许使用麦克风';
                        break;
                    case 'network':
                        errorMsg = '网络错误，请检查连接';
                        break;
                }
                
                showToast(errorMsg, 'error');
                stopRecording();
            };
            
            recognition.onend = () => {
                if (isRecording) {
                    // Auto-restart if still recording
                    try {
                        recognition.start();
                    } catch (e) {
                        stopRecording();
                    }
                }
            };
        }
        
        // Initialize voice on page load
        function initVoiceWebSocket() {
            initVoiceRecognition();
        }
        
        async function toggleVoiceRecording() {
            if (!recognition) {
                showToast('您的浏览器不支持语音输入', 'error');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                await startRecording();
            }
        }
        
        async function startRecording() {
            if (!recognition) {
                showToast('语音识别不可用', 'error');
                return;
            }
            
            try {
                // Request microphone permission first
                await navigator.mediaDevices.getUserMedia({ audio: true });
                
                recognition.start();
            } catch (e) {
                console.error('Start recording error:', e);
                showToast('无法访问麦克风，请检查权限', 'error');
            }
        }
        
        function stopRecording() {
            if (recognition) {
                try {
                    recognition.stop();
                } catch (e) {
                    // Ignore errors when stopping
                }
            }
            
            isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '🎤';
            queryInput.style.color = 'var(--text-primary)';
        }
        
        // Toast notification
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideIn 0.3s ease reverse';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        // Initialize app
        init();
    </script>
</body>
</html>'''


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )

