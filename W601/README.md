# 🤖 Excel智能分析Agent

一个基于自然语言的Excel数据分析系统，支持语音输入，能够自动解析用户问题、选择合适的数据文件、生成Python分析代码并执行。

## ✨ 功能特性

### 核心功能
- **自然语言理解**: 支持中英文问题输入，自动提取分析意图
- **智能文件选择**: 根据问题自动选择知识库中的相关Excel文件
- **代码自动生成**: 生成可执行的Python数据分析代码
- **数据追溯**: 明确显示分析使用的数据列
- **实时语音输入**: 支持WebSocket语音输入和实时转文字

### 分析能力
- 📊 **趋势分析**: 时间序列趋势、变化分析
- 📈 **分组统计**: 按维度分组的聚合计算
- 🎯 **排名分析**: Top N排序和对比
- 🥧 **分布分析**: 数据占比和分布
- 📉 **对比分析**: 多维度数据对比
- 🔢 **基础统计**: 求和、平均、计数等

### 可视化输出
- 柱状图 / 条形图
- 折线图 / 趋势图
- 饼图 / 环形图
- 散点图
- 数据表格

## 🏗️ 系统架构

```
W601/
├── app.py                 # FastAPI主应用 + 前端UI
├── config.py              # 配置管理
├── excel_processor.py     # Excel文件处理与预处理
├── nlp_parser.py          # 自然语言解析与意图提取
├── code_generator.py      # Python代码生成器
├── code_executor.py       # 安全代码执行器
├── voice_handler.py       # 语音输入处理
├── requirements.txt       # 依赖包
├── knowledge_base/        # Excel文件知识库目录
└── uploads/               # 文件上传临时目录
```

## 🚀 快速开始

### 环境要求
- Python 3.9+
- OpenAI API Key (可选，用于增强自然语言理解)

### 安装步骤

1. **克隆项目并进入目录**
```bash
cd W601
```

2. **创建虚拟环境 (推荐)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量 (可选)**

创建 `.env` 文件:
```env
# OpenAI配置 (可选，增强自然语言理解能力)
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

5. **启动服务**
```bash
python app.py
```

或使用uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

6. **访问应用**

打开浏览器访问: http://localhost:8000

## 📖 使用指南

### 上传文件
1. 点击上传区域或拖拽Excel文件到指定区域
2. 支持 `.xlsx`, `.xls`, `.csv` 格式
3. 文件将被添加到知识库中

### 文本输入分析
1. 在输入框中输入自然语言问题
2. 例如:
   - "帮我分析各地区的销售趋势"
   - "统计每个产品的总销售额"
   - "找出销售额最高的前10个客户"
   - "按月份分析订单数量变化"
3. 点击"开始分析"按钮

### 语音输入
1. 点击麦克风按钮开始录音
2. 说出您的分析问题
3. 再次点击停止录音
4. 系统自动将语音转为文字

### 查看结果
- **生成的代码**: 显示自动生成的Python分析代码
- **可视化结果**: 图表展示 (柱状图、折线图、饼图等)
- **分析结果**: 数据表格或统计摘要
- **使用的数据列**: 显示本次分析涉及的列名

## 🔧 API接口

### REST API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/files` | GET | 获取文件列表 |
| `/api/upload` | POST | 上传文件 |
| `/api/analyze` | POST | 执行分析 |
| `/api/files/{file_id}` | DELETE | 删除文件 |

### WebSocket

| 端点 | 描述 |
|------|------|
| `/ws/voice` | 语音输入WebSocket |
| `/ws/analysis` | 实时分析进度WebSocket |

### 分析请求示例

```python
import requests

response = requests.post("http://localhost:8000/api/analyze", json={
    "query": "分析各地区销售趋势",
    "file_id": None  # 可选，不指定则自动选择
})

result = response.json()
print(result["code"])           # 生成的代码
print(result["used_columns"])   # 使用的列
print(result["visualization"])  # Base64图表
```

## 🛡️ 安全特性

- **沙箱执行**: 生成的代码在受限环境中执行
- **超时控制**: 代码执行时间限制，防止无限循环
- **受限导入**: 仅允许数据分析相关的Python库
- **输入验证**: 文件类型和大小验证

## 📝 示例问题

```
1. 帮我分析各地区的销售趋势
2. 统计每个月的订单总金额
3. 找出销售额最高的10个产品
4. 分析客户的地区分布
5. 计算各产品类别的平均售价
6. 对比不同季度的收入情况
7. 展示销售额的月度变化趋势
8. 统计各部门的员工数量
```

## ⚙️ 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API密钥 |
| `OPENAI_MODEL` | gpt-4o-mini | 使用的模型 |
| `HOST` | 0.0.0.0 | 服务器主机 |
| `PORT` | 8000 | 服务器端口 |
| `MAX_CODE_EXECUTION_TIME` | 30 | 代码执行超时(秒) |

## 🔄 工作流程

```
用户输入 (文本/语音)
       ↓
  自然语言解析
       ↓
  提取分析意图
       ↓
  选择目标文件
       ↓
  生成Python代码
       ↓
  安全执行代码
       ↓
  格式化输出结果
       ↓
展示 (代码 + 图表 + 数据 + 使用的列)
```

## 🤝 技术栈

- **后端**: FastAPI, Python
- **LLM**: OpenAI GPT-4o-mini
- **数据处理**: Pandas, NumPy
- **可视化**: Matplotlib, Plotly
- **语音**: OpenAI Whisper, SpeechRecognition
- **前端**: 原生HTML/CSS/JavaScript

## 📜 License

MIT License
