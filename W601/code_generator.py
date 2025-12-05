"""
Code Generator Module
Generates Python code for data analysis based on parsed intents
Based on reference: prompt.py (Excel data processing rules)
"""
import json
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
import config
from nlp_parser import AnalysisIntent


# Excel Data Processing Rules (from prompt.py)
EXCEL_PROCESSING_RULES = '''
**Excel数据处理规则集**
1. 基础代码结构要求：
    1.1 必要的导入和设置：
        ```python
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
```
    1.2 输出格式要求：
        - 只需要输出代码即可，无需额外的解释
        - 输出的代码不要包含任何 Markdown 或代码块标记，仅提供纯文本的 Python 代码
        - 禁止输出"```python" 或者"```"
        - 所有生成的结果都必须通过"print"打印到控制台

2. 数据查询与处理要求：
    2.1 多行数据处理：
        - 生成代码前需要先根据数据结构判断用户想要查询的数据是处于"某范围内"还是"某个具体值"
        - 对结果集排序时，必须显式指定`ascending=False`（倒序）或`True`（升序），避免依赖默认排序
    2.2 关键字段处理：
        - 时间字段必须用`pd.to_datetime(..., errors='coerce').dt.normalize()`统一转换，并提取年月日等分量进行比较
        - 对于标识符类字段，建议使用 .astype(str) 进行字符串类型转换
        - 数值字段必须用`pd.to_numeric(..., errors='coerce')`转换，避免字符串比较数值
        - 为了确保可以执行数值计算，请用"pd.to_numeric(data, errors='coerce')"将数据转换为数值类型
    2.3 数据清洗和处理：
        - "DataFrame.fillna"方法在使用"method"参数时已过时被官方弃用，使用ffill()或bfill()代替
        - 列名中可能出现的下划线、多个空格等特殊字符需保持结构不变
    2.4 输出规范：
        - 批量输出时逐行格式化打印

3. 代码健壮性要求：
    3.1 异常处理：
        - 代码需要包含异常处理机制，必须用try-except包裹数据处理逻辑
        - 捕获KeyError等常见异常并给出友好提示
        - 打印异常时需包含具体错误信息
    3.2 数据校验：
        - 读取数据后立即检查df.empty，避免操作空DataFrame
        - 对关键筛选字段先确认存在性

4. 命名规范：
    4.1 变量和函数命名：
        - 避免使用符号如#，因为它是注释符号
        - 避免使用中文字符命名变量
        - 使用有意义的英文变量名，如filtered_df、result_data等

5. 问题拆解原则：
    5.1 分析用户需求：
        - 先解析用户问题的关键维度
        - 将自然语言描述转化为对应的pandas操作链
    5.2 防御性编程：
        - 假设原始数据可能存在缺失值、类型混乱或特殊字符
'''


class CodeGenerator:
    """Generate Python code for data analysis"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        ) if config.OPENAI_API_KEY else None
        
        self.system_prompt = f"""你是一个Python数据分析代码生成专家。

根据用户的分析需求，生成完整、可执行的Python代码。

{EXCEL_PROCESSING_RULES}

额外要求：
1. 在代码开头声明使用的列：used_columns = ["列名1", "列名2", ...]
2. 分析结果保存到 `analysis_result` 变量（DataFrame、Series或数值）
3. 如果生成图表，保存到 `figure` 变量
4. 使用matplotlib进行可视化，设置中文字体支持
5. 图表需要有标题、轴标签

输出格式：只返回Python代码，不要包含markdown格式标记。"""

    def generate_code(
        self, 
        query: str,
        intent: AnalysisIntent,
        file_info: Dict[str, Any],
        df_variable: str = "df",
        html_name: str = None
    ) -> Tuple[str, List[str]]:
        """
        Generate Python analysis code
        Returns: (code_string, used_columns)
        """
        if self.client:
            return self._llm_generate(query, intent, file_info, df_variable, html_name)
        else:
            return self._template_generate(intent, file_info, df_variable)
    
    def _llm_generate(
        self, 
        query: str,
        intent: AnalysisIntent,
        file_info: Dict[str, Any],
        df_variable: str,
        html_name: str = None
    ) -> Tuple[str, List[str]]:
        """Generate code using LLM"""
        
        columns_desc = self._format_columns_info(file_info)
        
        # Add Plotly chart generation hint if visualization needed
        chart_hint = ""
        if intent.visualization and html_name:
            chart_hint = f'''
如果需要生成图表，可以使用plotly生成可交互的图表：
- import plotly.graph_objects as go
- 使用 go.Figure 创建图表
- mode参数值为"lines+markers+text"（如果适用）
- fig.update_layout的title（需要居中展示）、xaxis_title、yaxis_title不得缺失
- X轴的数据需要从小到大进行排序后再绘制图表
- 如果使用plotly，将figure设为fig对象
'''
        
        prompt = f"""用户需求：{query}

分析意图：
- 操作类型：{intent.operation}
- 目标列：{intent.target_columns}
- 分组列：{intent.group_by}
- 筛选条件：{intent.filter_conditions}
- 排序：{intent.sort_by} ({intent.sort_order})
- 聚合方式：{intent.aggregations}
- 可视化：{intent.visualization}

可用数据（DataFrame变量名为 `{df_variable}`）：
{columns_desc}
{chart_hint}
请生成完整的Python分析代码。记住：
1. 在代码开头声明 used_columns 列表，列出实际使用的列名
2. 分析结果存入 analysis_result 变量
3. 图表存入 figure 变量（如果有）
4. 使用中文注释说明每个步骤
5. 添加数据类型转换和错误处理
6. 数值列用 pd.to_numeric(..., errors='coerce') 转换
7. 日期列用 pd.to_datetime(..., errors='coerce') 转换"""

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            code = response.choices[0].message.content
            code = self._clean_code(code)
            used_columns = self._extract_used_columns(code)
            
            return code, used_columns
            
        except Exception as e:
            print(f"Code generation error: {e}")
            return self._template_generate(intent, file_info, df_variable)
    
    def _template_generate(
        self,
        intent: AnalysisIntent,
        file_info: Dict[str, Any],
        df_variable: str
    ) -> Tuple[str, List[str]]:
        """Generate code using templates when LLM unavailable"""
        
        columns = self._get_column_names(file_info)
        numeric_cols = self._get_numeric_columns(file_info)
        non_numeric_cols = [c for c in columns if c not in numeric_cols]
        
        # Preferred column patterns for Chinese/English data
        value_keywords = ['销售额', '金额', '收入', '总额', '净额', 'amount', 'revenue', 'sales', 'total', 'price']
        category_keywords = ['城市', '地区', '产品', '类别', '渠道', '部门', 'city', 'region', 'product', 'category', 'channel']
        
        # Find best target column (prefer value-related columns)
        target_col = None
        for kw in value_keywords:
            for col in numeric_cols:
                if kw in col.lower():
                    target_col = col
                    break
            if target_col:
                break
        if not target_col:
            target_col = numeric_cols[0] if numeric_cols else (columns[0] if columns else "value")
        
        # Find best group column (prefer categorical columns, avoid dates)
        group_col = None
        for kw in category_keywords:
            for col in non_numeric_cols:
                if kw in col.lower() and '日期' not in col and 'date' not in col.lower():
                    group_col = col
                    break
            if group_col:
                break
        if not group_col:
            # Filter out date columns
            categorical_cols = [c for c in non_numeric_cols if '日期' not in c and 'date' not in c.lower() and '时间' not in c]
            group_col = categorical_cols[0] if categorical_cols else (non_numeric_cols[0] if non_numeric_cols else (columns[0] if columns else "category"))
        
        # Use intent columns if available AND not empty AND exist
        if intent.target_columns and intent.target_columns[0] and intent.target_columns[0].strip():
            if intent.target_columns[0] in columns:
                target_col = intent.target_columns[0]
        if intent.group_by and intent.group_by[0] and intent.group_by[0].strip():
            if intent.group_by[0] in columns:
                group_col = intent.group_by[0]
            
        used_columns = [target_col]
        if group_col != target_col:
            used_columns.append(group_col)
            
        templates = {
            "sum": self._sum_template,
            "average": self._average_template,
            "trend": self._trend_template,
            "group": self._group_template,
            "distribution": self._distribution_template,
            "compare": self._compare_template,
            "sort": self._sort_template,
            "filter": self._filter_template,
            "count": self._count_template,
            "general": self._general_template
        }
        
        template_func = templates.get(intent.operation, self._general_template)
        code = template_func(df_variable, target_col, group_col, intent)
        
        return code, used_columns
    
    def _format_columns_info(self, file_info: Dict[str, Any]) -> str:
        """Format column information for LLM prompt"""
        lines = []
        for sheet in file_info.get('sheets', []):
            lines.append(f"工作表: {sheet['sheet_name']} ({sheet['row_count']}行)")
            for col in sheet.get('columns', []):
                samples = str(col.get('sample_values', []))[:50]
                lines.append(f"  - {col['name']} ({col['dtype']}): 示例={samples}")
        return "\n".join(lines)
    
    def _get_column_names(self, file_info: Dict[str, Any]) -> List[str]:
        """Extract column names from file info"""
        columns = []
        for sheet in file_info.get('sheets', []):
            for col in sheet.get('columns', []):
                columns.append(col['name'])
        return columns
    
    def _get_numeric_columns(self, file_info: Dict[str, Any]) -> List[str]:
        """Extract numeric column names"""
        numeric = []
        for sheet in file_info.get('sheets', []):
            for col in sheet.get('columns', []):
                if 'int' in col['dtype'] or 'float' in col['dtype']:
                    numeric.append(col['name'])
        return numeric
    
    def _clean_code(self, code: str) -> str:
        """Remove markdown formatting from code"""
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()
    
    def _extract_used_columns(self, code: str) -> List[str]:
        """Extract used_columns from generated code"""
        import re
        match = re.search(r'used_columns\s*=\s*\[(.*?)\]', code, re.DOTALL)
        if match:
            cols_str = match.group(1)
            cols = re.findall(r'["\']([^"\']+)["\']', cols_str)
            return cols
        return []
    
    def _get_matplotlib_chinese_setup(self) -> str:
        """Return matplotlib Chinese font setup code with professional styling"""
        return '''import matplotlib.pyplot as plt
import matplotlib
from matplotlib import cm

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Heiti TC', 'STHeiti', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 专业图表样式
plt.rcParams['figure.facecolor'] = '#f8f9fa'
plt.rcParams['axes.facecolor'] = '#ffffff'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.labelcolor'] = '#333333'
plt.rcParams['xtick.color'] = '#666666'
plt.rcParams['ytick.color'] = '#666666'
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'

# 专业配色方案
COLORS = ['#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B', '#EECA3B', '#B279A2', '#FF9DA6']
'''

    # Template methods with improved data handling
    def _sum_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 数据求和分析
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

# 动态选择列
all_cols = {df_var}.columns.tolist()
numeric_cols = {df_var}.select_dtypes(include=[np.number]).columns.tolist()
non_numeric_cols = [c for c in all_cols if c not in numeric_cols]

# 选择目标列和分组列
target_col = "{target}" if "{target}" in all_cols else (numeric_cols[0] if numeric_cols else all_cols[0])
group_col = "{group}" if "{group}" in all_cols else (non_numeric_cols[0] if non_numeric_cols else all_cols[0])

used_columns = [target_col, group_col]
print(f"使用列: 数值列={{target_col}}, 分组列={{group_col}}")

# 检查数据
if {df_var}.empty:
    print("警告: 数据为空")
    analysis_result = pd.DataFrame()
else:
    # 数据类型转换
    {df_var}[target_col] = pd.to_numeric({df_var}[target_col], errors='coerce')
    
    # 分组求和
    analysis_result = {df_var}.groupby(group_col)[target_col].sum().reset_index()
    analysis_result.columns = [group_col, f"{{target_col}}_总计"]
    analysis_result = analysis_result.sort_values(f"{{target_col}}_总计", ascending=False)
    
    print("\\n=== 分组求和结果 ===")
    print(analysis_result.to_string(index=False))
    print(f"\\n总计: {{analysis_result[f'{{target_col}}_总计'].sum():,.2f}}")
    
    # 可视化
    figure, ax = plt.subplots(figsize=(12, 7))
    figure.patch.set_facecolor('#f8f9fa')
    
    x_labels = analysis_result[group_col].astype(str)
    x_pos = range(len(x_labels))
    values = analysis_result[f"{{target_col}}_总计"]
    
    # 渐变色柱状图
    colors = [COLORS[i % len(COLORS)] for i in range(len(x_labels))]
    bars = ax.bar(x_pos, values, color=colors, edgecolor='white', linewidth=1.5, width=0.7)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=11)
    ax.set_xlabel(group_col, fontsize=12, fontweight='bold')
    ax.set_ylabel(target_col, fontsize=12, fontweight='bold')
    ax.set_title(f"📊 {{target_col}}统计分析 - 按{{group_col}}分组", fontsize=14, fontweight='bold', pad=20)
    
    # 移除顶部和右侧边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加数值标签
    max_val = max(values)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_val*0.02, 
                f'{{val:,.0f}}', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#333')
    
    # 添加总计线
    avg_val = values.mean()
    ax.axhline(y=avg_val, color='#E45756', linestyle='--', linewidth=2, alpha=0.7, label=f'平均值: {{avg_val:,.0f}}')
    ax.legend(loc='upper right', framealpha=0.9)
    
    plt.tight_layout(pad=2.0)
'''
    
    def _average_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 平均值分析
used_columns = ["{target}", "{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    {df_var}["{target}"] = pd.to_numeric({df_var}["{target}"], errors='coerce')
    
    analysis_result = {df_var}.groupby("{group}")["{target}"].mean().reset_index()
    analysis_result.columns = ["{group}", "{target}_平均"]
    analysis_result = analysis_result.sort_values("{target}_平均", ascending=False)
    
    print("=== 平均值分析结果 ===")
    print(analysis_result.to_string(index=False))
    print(f"\\n总体平均: {{{df_var}['{target}'].mean():,.2f}}")
    
    figure, ax = plt.subplots(figsize=(10, 6))
    ax.bar(analysis_result["{group}"], analysis_result["{target}_平均"], color='steelblue')
    ax.axhline(y={df_var}["{target}"].mean(), color='red', linestyle='--', label='总体平均')
    ax.set_xlabel("{group}")
    ax.set_ylabel("{target} 平均值")
    ax.set_title("{target}平均值分析 - 按{group}")
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _trend_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 趋势分析
used_columns = ["{target}", "{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    {df_var}["{target}"] = pd.to_numeric({df_var}["{target}"], errors='coerce')
    
    # 尝试转换为日期类型
    if {df_var}["{group}"].dtype == 'object':
        {df_var}["{group}"] = pd.to_datetime({df_var}["{group}"], errors='coerce')
    
    # 按时间分组聚合
    if pd.api.types.is_datetime64_any_dtype({df_var}["{group}"]):
        analysis_result = {df_var}.groupby({df_var}["{group}"].dt.to_period('M'))["{target}"].sum().reset_index()
        analysis_result["{group}"] = analysis_result["{group}"].astype(str)
    else:
        analysis_result = {df_var}.groupby("{group}")["{target}"].sum().reset_index()
    
    analysis_result = analysis_result.sort_values("{group}", ascending=True)
    
    print("=== 趋势分析结果 ===")
    print(analysis_result.to_string(index=False))
    
    figure, ax = plt.subplots(figsize=(12, 6))
    ax.plot(analysis_result["{group}"], analysis_result["{target}"], marker='o', linewidth=2, markersize=6)
    ax.fill_between(range(len(analysis_result)), analysis_result["{target}"], alpha=0.3)
    ax.set_xlabel("{group}")
    ax.set_ylabel("{target}")
    ax.set_title("{target}趋势分析")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _group_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 分组统计分析
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

# 动态选择列
all_cols = {df_var}.columns.tolist()
numeric_cols = {df_var}.select_dtypes(include=[np.number]).columns.tolist()
non_numeric_cols = [c for c in all_cols if c not in numeric_cols]

target_col = "{target}" if "{target}" in all_cols else (numeric_cols[0] if numeric_cols else all_cols[0])
group_col = "{group}" if "{group}" in all_cols else (non_numeric_cols[0] if non_numeric_cols else all_cols[0])

used_columns = [target_col, group_col]
print(f"使用列: 数值列={{target_col}}, 分组列={{group_col}}")

if {df_var}.empty:
    print("警告: 数据为空")
    analysis_result = pd.DataFrame()
else:
    {df_var}[target_col] = pd.to_numeric({df_var}[target_col], errors='coerce')
    
    analysis_result = {df_var}.groupby(group_col)[target_col].agg(['sum', 'mean', 'count', 'min', 'max']).reset_index()
    analysis_result.columns = [group_col, "总和", "平均", "计数", "最小", "最大"]
    analysis_result = analysis_result.sort_values("总和", ascending=False)
    
    print("\\n=== 分组统计结果 ===")
    print(analysis_result.to_string(index=False))
    
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    figure.patch.set_facecolor('#f8f9fa')
    
    x_labels = analysis_result[group_col].astype(str)
    x_pos = range(len(x_labels))
    
    # 总和柱状图 - 渐变色
    colors1 = [COLORS[i % len(COLORS)] for i in range(len(x_labels))]
    bars1 = axes[0].bar(x_pos, analysis_result["总和"], color=colors1, edgecolor='white', linewidth=1.2)
    axes[0].set_xticks(x_pos)
    axes[0].set_xticklabels(x_labels, rotation=45, ha='right')
    axes[0].set_title(f"📊 各{{group_col}}的{{target_col}}总和", fontsize=13, fontweight='bold', pad=15)
    axes[0].set_xlabel(group_col, fontsize=11)
    axes[0].set_ylabel("总和", fontsize=11)
    axes[0].spines['top'].set_visible(False)
    axes[0].spines['right'].set_visible(False)
    
    # 添加数值标签
    for bar, val in zip(bars1, analysis_result["总和"]):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(analysis_result["总和"])*0.02, 
                    f'{{val:,.0f}}', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#333')
    
    # 计数柱状图
    colors2 = ['#72B7B2'] * len(x_labels)
    bars2 = axes[1].bar(x_pos, analysis_result["计数"], color=colors2, edgecolor='white', linewidth=1.2)
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(x_labels, rotation=45, ha='right')
    axes[1].set_title(f"📈 各{{group_col}}的记录数", fontsize=13, fontweight='bold', pad=15)
    axes[1].set_xlabel(group_col, fontsize=11)
    axes[1].set_ylabel("记录数", fontsize=11)
    axes[1].spines['top'].set_visible(False)
    axes[1].spines['right'].set_visible(False)
    
    # 添加数值标签
    for bar, val in zip(bars2, analysis_result["计数"]):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(analysis_result["计数"])*0.02, 
                    f'{{int(val)}}', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#333')
    
    plt.tight_layout(pad=2.0)
'''

    def _distribution_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 分布分析
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

# 动态选择列
all_cols = {df_var}.columns.tolist()
numeric_cols = {df_var}.select_dtypes(include=[np.number]).columns.tolist()
non_numeric_cols = [c for c in all_cols if c not in numeric_cols]

target_col = "{target}" if "{target}" in all_cols else (numeric_cols[0] if numeric_cols else all_cols[0])
group_col = "{group}" if "{group}" in all_cols else (non_numeric_cols[0] if non_numeric_cols else all_cols[0])

used_columns = [target_col, group_col]
print(f"使用列: 数值列={{target_col}}, 分组列={{group_col}}")

if {df_var}.empty:
    print("警告: 数据为空")
    analysis_result = pd.DataFrame()
else:
    {df_var}[target_col] = pd.to_numeric({df_var}[target_col], errors='coerce')
    
    analysis_result = {df_var}.groupby(group_col)[target_col].sum().reset_index()
    analysis_result.columns = [group_col, "数值"]
    analysis_result["占比"] = (analysis_result["数值"] / analysis_result["数值"].sum() * 100).round(2)
    analysis_result = analysis_result.sort_values("数值", ascending=False)
    
    print("\\n=== 分布分析结果 ===")
    for _, row in analysis_result.iterrows():
        print(f"{{row[group_col]}}: {{row['数值']:,.0f}} ({{row['占比']}}%)")
    
    # 创建专业饼图
    figure, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
    figure.patch.set_facecolor('#f8f9fa')
    
    # 饼图
    colors = COLORS[:len(analysis_result)]
    explode = [0.02] * len(analysis_result)
    explode[0] = 0.08  # 突出最大项
    
    wedges, texts, autotexts = ax1.pie(
        analysis_result["数值"], 
        labels=analysis_result[group_col].astype(str),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        explode=explode,
        shadow=True,
        textprops={{'fontsize': 10}}
    )
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)
    ax1.set_title(f"🥧 {{target_col}}分布 - 按{{group_col}}", fontsize=14, fontweight='bold', pad=20)
    
    # 水平柱状图
    y_pos = range(len(analysis_result))
    ax2.barh(y_pos, analysis_result["数值"], color=colors, edgecolor='white', height=0.7)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(analysis_result[group_col].astype(str), fontsize=10)
    ax2.set_xlabel("数值", fontsize=11, fontweight='bold')
    ax2.set_title(f"📊 {{target_col}}对比", fontsize=14, fontweight='bold', pad=20)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.invert_yaxis()
    
    # 添加数值标签
    for i, (val, pct) in enumerate(zip(analysis_result["数值"], analysis_result["占比"])):
        ax2.text(val + max(analysis_result["数值"])*0.02, i, f'{{val:,.0f}} ({{pct}}%)', 
                va='center', fontsize=9, fontweight='bold', color='#333')
    
    plt.tight_layout(pad=2.0)
'''

    def _compare_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 对比分析
used_columns = ["{target}", "{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    {df_var}["{target}"] = pd.to_numeric({df_var}["{target}"], errors='coerce')
    
    analysis_result = {df_var}.groupby("{group}")["{target}"].sum().sort_values(ascending=False).reset_index()
    analysis_result.columns = ["{group}", "{target}"]
    
    print("=== 对比分析结果 ===")
    print(analysis_result.to_string(index=False))
    
    figure, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(analysis_result)))
    bars = ax.barh(analysis_result["{group}"], analysis_result["{target}"], color=colors)
    
    # 添加数值标签
    for bar, val in zip(bars, analysis_result["{target}"]):
        ax.text(val, bar.get_y() + bar.get_height()/2, f'{{val:,.0f}}', 
                va='center', ha='left', fontsize=9)
    
    ax.set_xlabel("{target}")
    ax.set_ylabel("{group}")
    ax.set_title("{group}对比分析 - {target}")
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _sort_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        ascending = intent.sort_order == "asc"
        return f'''# 排序分析 (Top N)
used_columns = ["{target}", "{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    {df_var}["{target}"] = pd.to_numeric({df_var}["{target}"], errors='coerce')
    
    # 排序并取Top 10
    analysis_result = {df_var}.sort_values("{target}", ascending={ascending}).head(10)
    
    print("=== Top 10 排名 ===")
    for i, (_, row) in enumerate(analysis_result.iterrows(), 1):
        print(f"{{i}}. {{row.get('{group}', 'N/A')}}: {{row['{target}']:,.2f}}")
    
    figure, ax = plt.subplots(figsize=(10, 6))
    y_pos = range(len(analysis_result))
    ax.barh(y_pos, analysis_result["{target}"].values, color='steelblue')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(analysis_result["{group}"].values if "{group}" in analysis_result.columns else analysis_result.index)
    ax.invert_yaxis()
    ax.set_xlabel("{target}")
    ax.set_title("Top 10 {target}排名")
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _filter_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 筛选分析
used_columns = ["{target}", "{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    {df_var}["{target}"] = pd.to_numeric({df_var}["{target}"], errors='coerce')
    
    # 筛选数据
    analysis_result = {df_var}.copy()
    
    print("=== 筛选结果 ===")
    print(f"筛选后数据量: {{len(analysis_result)}} 条")
    print(analysis_result.head(20).to_string(index=False))
    
    figure, ax = plt.subplots(figsize=(10, 6))
    if len(analysis_result) > 0:
        analysis_result["{target}"].hist(ax=ax, bins=20, color='steelblue', edgecolor='white')
    ax.set_xlabel("{target}")
    ax.set_ylabel("频数")
    ax.set_title("{target}分布直方图")
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _count_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 计数分析
used_columns = ["{group}"]

import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

try:
    if {df_var}.empty:
        raise ValueError("数据为空")
    
    analysis_result = {df_var}["{group}"].value_counts().reset_index()
    analysis_result.columns = ["{group}", "计数"]
    
    print("=== 计数统计结果 ===")
    print(analysis_result.to_string(index=False))
    print(f"\\n总计: {{analysis_result['计数'].sum()}}")
    
    figure, ax = plt.subplots(figsize=(10, 6))
    ax.bar(analysis_result["{group}"].astype(str), analysis_result["计数"], color='steelblue')
    ax.set_xlabel("{group}")
    ax.set_ylabel("计数")
    ax.set_title("{group}计数统计")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
except Exception as e:
    print(f"分析错误: {{e}}")
    analysis_result = None
'''

    def _general_template(self, df_var: str, target: str, group: str, intent: AnalysisIntent) -> str:
        return f'''# 数据概览分析
import pandas as pd
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=Warning)
{self._get_matplotlib_chinese_setup()}

# 获取所有列信息
all_cols = {df_var}.columns.tolist()
numeric_cols = {df_var}.select_dtypes(include=[np.number]).columns.tolist()
used_columns = all_cols[:5]  # 使用前5列作为示例

print("=== 数据概览 ===")
print(f"数据维度: {{{df_var}.shape[0]}} 行 x {{{df_var}.shape[1]}} 列")
print(f"\\n所有列名: {{all_cols}}")
print(f"数值列: {{numeric_cols}}")

print("\\n=== 数据预览 (前5行) ===")
print({df_var}.head().to_string())

print("\\n=== 数值列统计 ===")
if len(numeric_cols) > 0:
    print({df_var}[numeric_cols].describe().to_string())
else:
    print("没有数值列")

# 创建分析结果 DataFrame
analysis_result = {df_var}.describe().T.reset_index()
analysis_result.columns = ['列名'] + list(analysis_result.columns[1:])

print("\\n=== 统计摘要 ===")
summary = {{
    "总行数": len({df_var}),
    "总列数": len({df_var}.columns),
    "数值列数": len(numeric_cols),
    "缺失值总数": int({df_var}.isna().sum().sum())
}}
for k, v in summary.items():
    print(f"{{k}}: {{v}}")

# 可视化
figure, axes = plt.subplots(1, 2, figsize=(14, 5))

# 数据类型分布
type_counts = {df_var}.dtypes.value_counts()
axes[0].pie(type_counts.values, labels=type_counts.index.astype(str), autopct='%1.1f%%')
axes[0].set_title("数据类型分布")

# 缺失值情况或数值分布
missing = {df_var}.isna().sum()
missing = missing[missing > 0]
if len(missing) > 0:
    axes[1].barh(missing.index.astype(str), missing.values, color='coral')
    axes[1].set_title("缺失值统计")
    axes[1].set_xlabel("缺失数量")
elif len(numeric_cols) > 0:
    {df_var}[numeric_cols[0]].hist(ax=axes[1], bins=20, color='steelblue', edgecolor='white')
    axes[1].set_title(f"{{numeric_cols[0]}} 分布")
else:
    axes[1].text(0.5, 0.5, '数据完整', ha='center', va='center', fontsize=14)
    axes[1].set_title("数据质量")

plt.tight_layout()
print("\\n分析完成!")
'''
