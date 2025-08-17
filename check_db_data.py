import sqlite3
import os

# 数据库文件路径
db_path = r'd:\phpstudy_pro\WWW\xm\alibaba\alibaba_supplier_data.db'

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

try:
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看company_registration表结构
    print("=== company_registration表结构 ===")
    cursor.execute("PRAGMA table_info(company_registration)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[1]} ({col[2]})")
    
    print("\n=== company_registration表数据 ===")
    # 查看前10条记录
    cursor.execute("SELECT * FROM company_registration LIMIT 10")
    rows = cursor.fetchall()
    
    if not rows:
        print("表中没有数据")
    else:
        # 打印列名
        column_names = [description[0] for description in cursor.description]
        print("|".join(column_names))
        print("-" * 100)
        
        # 打印数据
        for row in rows:
            print("|".join(str(cell) if cell is not None else "NULL" for cell in row))
    
    # 统计总记录数
    cursor.execute("SELECT COUNT(*) FROM company_registration")
    count = cursor.fetchone()[0]
    print(f"\n总记录数: {count}")
    
    # 查看地址解析相关字段的统计
    print("\n=== 地址解析字段统计 ===")
    cursor.execute("SELECT COUNT(*) as total, COUNT(province) as has_province, COUNT(city) as has_city, COUNT(district) as has_district FROM company_registration")
    stats = cursor.fetchone()
    print(f"总记录: {stats[0]}")
    print(f"有省份: {stats[1]}")
    print(f"有城市: {stats[2]}")
    print(f"有区县: {stats[3]}")
    
    conn.close()
    
except Exception as e:
    print(f"查询数据库时出错: {e}")