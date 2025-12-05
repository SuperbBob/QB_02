"""
Natural Language Parser Module
Uses LLM to understand user queries and extract analysis intents
Also handles Excel structure detection for complex headers
Based on reference: prompt.py
"""
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
import config


class AnalysisIntent:
    """Represents parsed analysis intent from user query"""
    
    def __init__(
        self,
        operation: str,
        target_columns: List[str] = None,
        group_by: Optional[List[str]] = None,
        filter_conditions: Optional[Dict] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        aggregations: Optional[List[str]] = None,
        visualization: Optional[str] = None,
        description: str = ""
    ):
        self.operation = operation
        self.target_columns = target_columns or []
        self.group_by = group_by or []
        self.filter_conditions = filter_conditions or {}
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.aggregations = aggregations or []
        self.visualization = visualization
        self.description = description
        
    def to_dict(self) -> Dict:
        return {
            "operation": self.operation,
            "target_columns": self.target_columns,
            "group_by": self.group_by,
            "filter_conditions": self.filter_conditions,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "aggregations": self.aggregations,
            "visualization": self.visualization,
            "description": self.description
        }


class NLPParser:
    """Parse natural language queries into structured analysis intents"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        ) if config.OPENAI_API_KEY else None
        
        self.system_prompt = """你是一个专业的数据分析助手。你的任务是理解用户的自然语言问题，并提取分析意图。

请根据用户的问题，返回JSON格式的分析意图，包含以下字段：
- operation: 操作类型 (sum/average/count/trend/compare/filter/group/pivot/correlation/distribution/sort)
- target_columns: 需要分析的目标列名列表（数值列）
- group_by: 分组列名列表（维度列，如果需要）
- filter_conditions: 筛选条件字典 {"列名": {"operator": "=/>/</>=/<=/contains", "value": "值"}}
- sort_by: 排序列名（如果需要）
- sort_order: 排序方向 (asc/desc)
- aggregations: 聚合函数列表 (sum/mean/count/max/min)
- visualization: 推荐的可视化类型 (bar/line/pie/scatter/table/heatmap)
- description: 对分析任务的简要描述

常见分析意图映射：
- "趋势分析"、"变化"、"走势" -> operation: "trend", visualization: "line"
- "各地区"、"分组统计"、"按...分" -> operation: "group", visualization: "bar"
- "求和"、"总计"、"合计" -> aggregations: ["sum"]
- "平均值"、"均值" -> aggregations: ["mean"]
- "计数"、"数量"、"多少" -> aggregations: ["count"], operation: "count"
- "排名"、"排序"、"Top"、"最高"、"最低" -> operation: "sort"
- "对比"、"比较" -> operation: "compare", visualization: "bar"
- "占比"、"分布"、"比例" -> operation: "distribution", visualization: "pie"

重要：从可用数据列中选择最匹配用户问题的列名，确保列名与数据中的列名完全匹配。

请确保返回的是有效的JSON格式。"""

    def parse_query(self, query: str, file_context: str) -> AnalysisIntent:
        """Parse user query with file context"""
        if not self.client:
            return self._rule_based_parse(query, file_context)
            
        user_prompt = f"""知识库中的文件信息：
{file_context}

用户问题：{query}

请分析用户的问题，从可用的列名中选择匹配的列，提取分析意图并返回JSON格式的结果。"""

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return AnalysisIntent(**result)
            
        except Exception as e:
            print(f"LLM parsing error: {e}")
            return self._rule_based_parse(query, file_context)
    
    def _rule_based_parse(self, query: str, file_context: str = "") -> AnalysisIntent:
        """Fallback rule-based parsing when LLM is unavailable"""
        query_lower = query.lower()
        
        # Detect operation type
        operation = "general"
        visualization = "table"
        aggregations = []
        
        if any(kw in query_lower for kw in ["趋势", "trend", "变化", "走势", "月度", "年度"]):
            operation = "trend"
            visualization = "line"
        elif any(kw in query_lower for kw in ["对比", "比较", "compare", "vs"]):
            operation = "compare"
            visualization = "bar"
        elif any(kw in query_lower for kw in ["占比", "分布", "distribution", "比例", "构成"]):
            operation = "distribution"
            visualization = "pie"
        elif any(kw in query_lower for kw in ["排名", "排序", "top", "最高", "最低", "前"]):
            operation = "sort"
            visualization = "bar"
        elif any(kw in query_lower for kw in ["分组", "各", "每个", "group", "按"]):
            operation = "group"
            visualization = "bar"
        elif any(kw in query_lower for kw in ["计数", "count", "数量", "多少个"]):
            operation = "count"
            aggregations.append("count")
            
        if any(kw in query_lower for kw in ["求和", "总计", "sum", "合计", "总额"]):
            aggregations.append("sum")
        if any(kw in query_lower for kw in ["平均", "average", "mean", "均值"]):
            aggregations.append("mean")
        if any(kw in query_lower for kw in ["计数", "数量", "count", "多少"]):
            if "count" not in aggregations:
                aggregations.append("count")
        if any(kw in query_lower for kw in ["最大", "max", "最高"]):
            aggregations.append("max")
        if any(kw in query_lower for kw in ["最小", "min", "最低"]):
            aggregations.append("min")
        
        # Extract potential column names from context
        target_columns = []
        group_by = []
        
        # Try to extract columns from file_context
        columns_mentioned = self._extract_columns_from_context(file_context, query)
        
        return AnalysisIntent(
            operation=operation,
            target_columns=columns_mentioned.get("numeric", []),
            group_by=columns_mentioned.get("dimension", []),
            aggregations=aggregations if aggregations else ["sum"],
            visualization=visualization,
            description=query
        )
    
    def _extract_columns_from_context(self, file_context: str, query: str) -> Dict[str, List[str]]:
        """Extract column names from file context that match query keywords"""
        result = {"numeric": [], "dimension": []}
        
        # Common data keywords mapping
        keyword_mapping = {
            # Chinese keywords
            '销售': ['销售额', '销售', '销售量', '销售数量'],
            '地区': ['地区', '区域', '省份', '城市'],
            '日期': ['日期', '时间', '月份', '年份'],
            '金额': ['金额', '销售额', '收入', '成本'],
            '数量': ['数量', '销售数量', '订单数'],
            '产品': ['产品', '商品', '品类', '类别'],
            '客户': ['客户', '客户名称', '顾客'],
            '部门': ['部门', '团队', '组'],
            '员工': ['员工', '姓名', '销售员'],
            # English keywords
            'sales': ['sales', 'revenue', 'amount'],
            'region': ['region', 'area', 'city'],
            'date': ['date', 'time', 'month', 'year'],
            'product': ['product', 'item', 'category'],
            'customer': ['customer', 'client'],
        }
        
        query_lower = query.lower()
        
        # Find matching columns
        for keyword, possible_cols in keyword_mapping.items():
            if keyword in query_lower:
                for col in possible_cols:
                    if col in file_context.lower():
                        # Try to find exact column name from context
                        for line in file_context.split('\n'):
                            if col.lower() in line.lower() and '-' in line:
                                # Extract column name
                                parts = line.strip().split('-')
                                if len(parts) >= 1:
                                    col_name = parts[0].strip().lstrip('- ')
                                    if '(' in col_name:
                                        col_name = col_name.split('(')[0].strip()
                                    
                                    # Classify as numeric or dimension
                                    if any(t in line.lower() for t in ['int', 'float', '金额', '数量', '额']):
                                        if col_name not in result["numeric"]:
                                            result["numeric"].append(col_name)
                                    else:
                                        if col_name not in result["dimension"]:
                                            result["dimension"].append(col_name)
        
        return result
    
    def select_target_file(
        self, 
        query: str, 
        intent: AnalysisIntent, 
        file_summaries: Dict[str, Any]
    ) -> Optional[str]:
        """Select the most appropriate file for the analysis"""
        if not file_summaries:
            return None
            
        if not self.client:
            return list(file_summaries.keys())[0]
            
        summaries_text = json.dumps(file_summaries, ensure_ascii=False, indent=2)
        
        prompt = f"""根据用户的分析需求，从以下文件中选择最合适的文件：

用户问题：{query}
分析意图：{json.dumps(intent.to_dict(), ensure_ascii=False)}

可用文件：
{summaries_text}

请返回JSON格式：{{"selected_file_id": "文件ID", "reason": "选择原因"}}"""

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个数据分析专家，帮助选择合适的数据文件。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("selected_file_id")
            
        except Exception as e:
            print(f"File selection error: {e}")
            return list(file_summaries.keys())[0]


class ExcelStructureAnalyzer:
    """
    Analyze Excel structure to detect headers and labels
    Based on reference: prompt.py drop_and_merge_excel function
    """
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        ) if config.OPENAI_API_KEY else None
        
        self.system_prompt = '''你是一个专业的结构化数据处理AI，具有以下核心能力：
1. 能精确识别Excel工作表中的多级表头结构（包括跨行合并的表头）
2. 能准确区分表单级说明文本（针对整个工作表的说明）和数据行内说明文本（如产品介绍等字段）
3. 严格遵守数据行不可误判为说明文本的原则
4. 对每个工作表进行独立分析，不受其他工作表影响
'''

    def analyze_structure(
        self, 
        excel_info: str, 
        merged_info: Dict[str, List]
    ) -> Dict[str, Dict]:
        """
        Analyze Excel structure to identify label rows and header rows
        
        Returns: {
            "sheet_name": {
                "labels": [row_numbers_to_drop],
                "header": [header_row_numbers]
            }
        }
        """
        if not self.client:
            return self._default_structure()
            
        prompt = f'''请根据以下数据精确分析每个工作表的结构，分别输出每个表单应该去掉哪几行说明性文本（不包含数据行内说明性文本），哪几行为多级表头：
1. 取消合并单元格后的Excel文件数据：
```
{excel_info}
```
2. 原始合并单元格信息（用于判断表头层级）：
```
{json.dumps(merged_info, ensure_ascii=False, indent=2)}
```
输出格式：
[
    {{
        "sheet_name1": {{
            "labels": [行号列表],    # 整个工作表的说明文本行（无则[]）
            "header": [行号列表]     # 多级表头行（至少包含1行）
        }}
    }}
]
注意:
    1. 每个表单，不可受其他表单的影响。
    2. 不一定每个表单都会有说明性文本，判断说明性文本的时候需要判断与表头之间的关系，避免误判数据行为说明性文本。
    3. 注意多级表头可能有表头跨多行的情况。
    4. labels列表与header列表中都不可以输出行号以外的值。
    5. sheet_name必须和源文件中的表单名保持一致。
    6. 严格遵守输出格式，仅输出结果即可。
'''

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            # Clean markdown formatting
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            result_list = json.loads(result_text)
            
            # Convert list format to dict format
            result_dict = {}
            for item in result_list:
                result_dict.update(item)
                
            return result_dict
            
        except Exception as e:
            print(f"Structure analysis error: {e}")
            return self._default_structure()
    
    def _default_structure(self) -> Dict[str, Dict]:
        """Return default structure when LLM is unavailable"""
        return {}


class FileSelector:
    """Intelligent file selection based on query and available files"""
    
    def __init__(self, nlp_parser: NLPParser):
        self.parser = nlp_parser
        
    def find_matching_columns(
        self, 
        query: str, 
        file_summaries: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Find columns that match the query keywords"""
        keywords = self._extract_keywords(query)
        
        matches = {}
        for file_id, summary in file_summaries.items():
            file_matches = []
            for sheet in summary.get('sheets', []):
                for col in sheet.get('columns', []):
                    col_name = col['name'].lower()
                    for kw in keywords:
                        if kw in col_name or col_name in kw:
                            file_matches.append(col['name'])
                            
            if file_matches:
                matches[file_id] = list(set(file_matches))
                
        return matches
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract potential column name keywords from query"""
        data_keywords = [
            '销售', '地区', '日期', '时间', '金额', '数量', '产品', '客户',
            '收入', '成本', '利润', '价格', '订单', '类别', '品牌', '部门',
            '员工', '姓名', '月份', '年份', '季度',
            'sales', 'region', 'date', 'amount', 'quantity', 'product',
            'customer', 'revenue', 'cost', 'profit', 'price', 'order',
            'category', 'brand', 'department', 'employee', 'month', 'year'
        ]
        
        found = []
        query_lower = query.lower()
        for kw in data_keywords:
            if kw in query_lower:
                found.append(kw)
                
        return found
