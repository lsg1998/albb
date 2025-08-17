#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试地址查询功能，验证SQLite线程安全问题是否已解决
"""

import threading
import time
from address_query import AddressQuery

def test_address_query_in_thread(thread_id, addresses):
    """
    在线程中测试地址查询功能
    """
    print(f"线程 {thread_id} 开始测试")
    
    try:
        # 创建查询引擎实例
        query_engine = AddressQuery()
        
        for i, address in enumerate(addresses):
            print(f"线程 {thread_id} - 测试地址 {i+1}: {address}")
            
            # 测试解析地址
            result = query_engine.parse_address(address)
            print(f"线程 {thread_id} - 解析结果: {result}")
            
            # 测试查询地址
            query_results = query_engine.query_by_address(address)
            print(f"线程 {thread_id} - 查询结果数: {len(query_results) if query_results else 0}")
            
            # 测试获取邮编
            postcode = query_engine.get_postcode(address)
            print(f"线程 {thread_id} - 邮编: {postcode}")
            
            # 测试获取区域信息
            region_info = query_engine.get_region_info(address)
            print(f"线程 {thread_id} - 区域信息: {region_info}")
            
            print(f"线程 {thread_id} - 地址 {i+1} 测试完成\n")
            
            # 短暂休眠，模拟实际使用场景
            time.sleep(0.1)
            
        print(f"线程 {thread_id} 测试完成")
        
    except Exception as e:
        print(f"线程 {thread_id} 出现错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """
    主测试函数
    """
    print("开始多线程测试地址查询功能...")
    
    # 测试地址列表
    test_addresses = [
        "北京市朝阳区建国门外大街1号",
        "上海市浦东新区陆家嘴金融贸易区",
        "广东省深圳市南山区科技园",
        "浙江省杭州市西湖区文三路",
        "四川省成都市锦江区春熙路"
    ]
    
    # 创建多个线程
    threads = []
    num_threads = 3
    
    for i in range(num_threads):
        thread = threading.Thread(
            target=test_address_query_in_thread,
            args=(i+1, test_addresses)
        )
        threads.append(thread)
    
    # 启动所有线程
    for thread in threads:
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("\n所有线程测试完成！")

if __name__ == "__main__":
    main()