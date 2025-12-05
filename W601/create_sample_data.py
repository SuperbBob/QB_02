"""
Create sample Excel data for testing
Run this script to generate sample Excel files in the knowledge_base directory
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Create knowledge_base directory
kb_dir = Path(__file__).parent / "knowledge_base"
kb_dir.mkdir(exist_ok=True)


def create_sales_data():
    """Create sample sales data"""
    np.random.seed(42)
    
    regions = ['华东', '华南', '华北', '华中', '西南', '西北']
    products = ['产品A', '产品B', '产品C', '产品D', '产品E']
    
    data = []
    start_date = datetime(2024, 1, 1)
    
    for i in range(500):
        data.append({
            '日期': start_date + timedelta(days=np.random.randint(0, 365)),
            '地区': np.random.choice(regions),
            '产品': np.random.choice(products),
            '销售额': np.random.randint(1000, 50000),
            '销售数量': np.random.randint(10, 500),
            '客户名称': f'客户{np.random.randint(1, 100):03d}',
            '销售员': f'销售员{np.random.randint(1, 20):02d}'
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('日期')
    
    output_path = kb_dir / "销售数据.xlsx"
    df.to_excel(output_path, index=False, sheet_name='销售记录')
    print(f"Created: {output_path}")
    return df


def create_employee_data():
    """Create sample employee data"""
    np.random.seed(123)
    
    departments = ['技术部', '销售部', '市场部', '人力资源', '财务部', '运营部']
    positions = ['初级', '中级', '高级', '经理', '总监']
    
    data = []
    for i in range(100):
        hire_date = datetime(2020, 1, 1) + timedelta(days=np.random.randint(0, 1500))
        data.append({
            '员工ID': f'EMP{i+1:04d}',
            '姓名': f'员工{i+1}',
            '部门': np.random.choice(departments),
            '职位': np.random.choice(positions),
            '入职日期': hire_date,
            '基本工资': np.random.randint(8000, 50000),
            '绩效奖金': np.random.randint(0, 10000),
            '年龄': np.random.randint(22, 55)
        })
    
    df = pd.DataFrame(data)
    
    output_path = kb_dir / "员工信息.xlsx"
    df.to_excel(output_path, index=False, sheet_name='员工列表')
    print(f"Created: {output_path}")
    return df


def create_order_data():
    """Create sample order data"""
    np.random.seed(456)
    
    categories = ['电子产品', '服装', '食品', '家居', '图书']
    statuses = ['已完成', '处理中', '已发货', '已取消']
    
    data = []
    for i in range(300):
        order_date = datetime(2024, 1, 1) + timedelta(days=np.random.randint(0, 300))
        data.append({
            '订单号': f'ORD{i+1:06d}',
            '订单日期': order_date,
            '客户ID': f'C{np.random.randint(1, 200):04d}',
            '产品类别': np.random.choice(categories),
            '订单金额': round(np.random.uniform(50, 5000), 2),
            '订单数量': np.random.randint(1, 20),
            '订单状态': np.random.choice(statuses),
            '配送城市': np.random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安'])
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('订单日期')
    
    output_path = kb_dir / "订单数据.xlsx"
    df.to_excel(output_path, index=False, sheet_name='订单明细')
    print(f"Created: {output_path}")
    return df


if __name__ == "__main__":
    print("Creating sample Excel files...")
    print("-" * 40)
    
    create_sales_data()
    create_employee_data()
    create_order_data()
    
    print("-" * 40)
    print("Sample data created successfully!")
    print(f"Files saved in: {kb_dir}")

