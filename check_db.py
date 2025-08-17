#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_database():
    try:
        print("正在连接数据库...")
        conn = sqlite3.connect('./suppliers.db')
        cursor = conn.cursor()
        
        # 获取所有表名
        print("正在查询表名...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"数据库中共有 {len(tables)} 个表:")
        for i, table in enumerate(tables, 1):
            table_name = table[0]
            print(f"{i}. {table_name}")
            
            try:
                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   记录数: {count}")
                
                # 如果是license_info表，检查地址相关字段
                if table_name == 'license_info':
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    print(f"   字段: {column_names}")
                    
                    # 检查是否有地址相关字段
                    address_fields = [col for col in column_names if 'address' in col.lower() or 'province' in col.lower() or 'city' in col.lower()]
                    if address_fields:
                        print(f"   地址相关字段: {address_fields}")
                        
                        # 检查未解析的地址记录
                        if 'registered_address' in column_names:
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE (province IS NULL OR province = '') AND (city IS NULL OR city = '') AND registered_address IS NOT NULL AND registered_address != ''")
                            unresolved_count = cursor.fetchone()[0]
                            print(f"   未解析地址记录数: {unresolved_count}")
                            
                            if unresolved_count > 0:
                                cursor.execute(f"SELECT id, registered_address FROM {table_name} WHERE (province IS NULL OR province = '') AND (city IS NULL OR city = '') AND registered_address IS NOT NULL AND registered_address != '' LIMIT 3")
                                sample_records = cursor.fetchall()
                                print(f"   示例未解析记录:")
                                for record in sample_records:
                                    print(f"     ID: {record[0]}, 地址: {record[1][:50]}...")
                
            except Exception as table_error:
                print(f"   查询表 {table_name} 时出错: {table_error}")
            
            print()
        
        conn.close()
        print("数据库检查完成")
        
    except Exception as e:
        print(f"检查数据库时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()