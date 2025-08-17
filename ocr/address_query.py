#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地址查询模块
基于高德地图API实现地址解析，结合本地area数据库查询邮编功能
"""

import sqlite3
import re
import os
from typing import Dict, List, Optional, Tuple
from .amap_address_query import AmapAddressQuery

class AddressQuery:
    def __init__(self, db_path: str = None, amap_api_key: str = None):
        """
        初始化地址查询器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
            amap_api_key: 高德地图API密钥，如果为None则尝试从配置文件读取
        """
        if db_path is None:
            # 默认数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'area.db')
        
        self.db_path = db_path
        
        # 初始化高德地图API
        self.amap_query = None
        if amap_api_key:
            self.amap_query = AmapAddressQuery(amap_api_key)
        else:
            # 尝试从配置文件读取API密钥
            try:
                config_path = os.path.join(os.path.dirname(__file__), 'amap_config.json')
                if os.path.exists(config_path):
                    import json
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        api_key = config.get('api_key')
                        if api_key:
                            self.amap_query = AmapAddressQuery(api_key)
            except Exception as e:
                print(f"读取高德API配置失败: {e}")
        
        # 初始化数据库表结构（如果需要）
        self._init_database()
    
    def _get_connection(self):
        """
        获取数据库连接（每次使用时创建新连接，解决线程安全问题）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn
    
    def _init_database(self):
        """
        初始化数据库表结构
        """
        try:
            conn = self._get_connection()
            
            # 检查表是否存在，如果不存在则创建
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS area (
                    id INTEGER PRIMARY KEY,
                    parent_id INTEGER,
                    name TEXT,
                    province TEXT,
                    city TEXT,
                    county TEXT,
                    postcode TEXT,
                    parent_path TEXT,
                    level INTEGER,
                    full_path TEXT
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON area(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_province ON area(province)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_city ON area(city)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_county ON area(county)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_postcode ON area(postcode)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_path ON area(full_path)")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
    
    def import_from_sql(self, sql_file_path: str):
        """
        从SQL文件导入数据
        
        Args:
            sql_file_path: SQL文件路径
        """
        try:
            conn = self._get_connection()
            
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 提取INSERT语句
            insert_pattern = r"INSERT INTO `area` VALUES \(([^)]+)\);"
            matches = re.findall(insert_pattern, sql_content)
            
            cursor = conn.cursor()
            imported_count = 0
            
            for match in matches:
                try:
                    # 正确解析VALUES中的数据，处理单引号包围的值
                    values = []
                    current_field = ""
                    in_quotes = False
                    i = 0
                    
                    while i < len(match):
                        char = match[i]
                        if char == "'" and not in_quotes:
                            in_quotes = True
                        elif char == "'" and in_quotes:
                            in_quotes = False
                        elif char == "," and not in_quotes:
                            field = current_field.strip()
                            if field.lower() == 'null':
                                values.append(None)
                            elif field.startswith("'") and field.endswith("'"):
                                values.append(field[1:-1])
                            else:
                                try:
                                    values.append(int(field))
                                except ValueError:
                                    values.append(field.strip("'"))
                            current_field = ""
                            i += 1
                            continue
                        
                        if char != "," or in_quotes:
                            current_field += char
                        i += 1
                    
                    # 处理最后一个字段
                    if current_field:
                        field = current_field.strip()
                        if field.lower() == 'null':
                            values.append(None)
                        elif field.startswith("'") and field.endswith("'"):
                            values.append(field[1:-1])
                        else:
                            try:
                                values.append(int(field))
                            except ValueError:
                                values.append(field.strip("'"))
                    
                    # 确保有正确数量的字段
                    if len(values) == 10:
                        # 插入数据
                        cursor.execute("""
                            INSERT OR REPLACE INTO area 
                            (id, parent_id, name, province, city, county, postcode, parent_path, level, full_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, values)
                        imported_count += 1
                    else:
                        print(f"跳过无效记录，字段数量: {len(values)}, 数据: {values[:3]}...")
                        
                except Exception as e:
                    print(f"处理记录时出错: {e}, 数据: {match[:100]}...")
                    continue
            
            conn.commit()
            conn.close()
            print(f"成功导入 {imported_count} 条记录")
            return imported_count > 0
            
        except Exception as e:
            print(f"导入SQL文件失败: {e}")
            return False
    
    def parse_address(self, address: str) -> Dict[str, str]:
        """
        解析地址字符串，优先使用高德API获取省市区信息，然后从本地数据库查询邮编
        
        Args:
            address: 地址字符串
            
        Returns:
            dict: 包含province, city, county, postcode等信息的字典
        """
        result = {
            'province': '',
            'city': '',
            'county': '',
            'detail': address,
            'postcode': ''
        }
        
        # 优先使用高德API解析地址
        if self.amap_query:
            try:
                amap_result = self.amap_query.parse_address(address)
                if amap_result and amap_result.get('status') == '1':
                    geocodes = amap_result.get('geocodes', [])
                    if geocodes:
                        geocode = geocodes[0]
                        addressComponent = geocode.get('addressComponent', {})
                        
                        # 提取省市区信息
                        result['province'] = addressComponent.get('province', '')
                        result['city'] = addressComponent.get('city', '')
                        result['county'] = addressComponent.get('district', '')
                        
                        # 根据获取到的省市区信息从本地数据库查询邮编
                        if result['province'] and result['city'] and result['county']:
                            postcode = self._get_postcode_from_db(result['province'], result['city'], result['county'])
                            if postcode:
                                result['postcode'] = postcode
                        
                        print(f"高德API解析成功: {result['province']} {result['city']} {result['county']} - 邮编: {result['postcode']}")
                        return result
                    else:
                        print(f"高德API返回结果为空: {amap_result}")
                else:
                    print(f"高德API解析失败: {amap_result}")
            except Exception as e:
                print(f"调用高德API时出错: {e}")
        
        # 如果高德API不可用或解析失败，使用本地数据库解析（保留原有逻辑作为备用）
        print("使用本地数据库进行地址解析...")
        return self._parse_address_local(address)
    
    def _get_postcode_from_db(self, province: str, city: str, county: str) -> Optional[str]:
        """
        根据省市区信息从本地数据库查询邮编
        优先级：district -> city -> province
        
        Args:
            province: 省份
            city: 城市
            county: 区县
            
        Returns:
            str: 邮编，如果未找到返回None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 策略1：优先使用district(县区)查询
            if county:
                # 精确匹配district
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name = ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (county,))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
                
                # 模糊匹配district
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name LIKE ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (f"%{county}%",))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
            
            # 策略2：如果district没找到，使用city查询
            if city:
                # 精确匹配city
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name = ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (city,))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
                
                # 模糊匹配city
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name LIKE ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (f"%{city}%",))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
            
            # 策略3：如果city也没找到，使用province查询
            if province:
                # 精确匹配province
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name = ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (province,))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
                
                # 模糊匹配province
                cursor.execute("""
                    SELECT postcode FROM area 
                    WHERE name LIKE ? AND postcode IS NOT NULL AND postcode != ''
                    ORDER BY level DESC LIMIT 1
                """, (f"%{province}%",))
                
                result = cursor.fetchone()
                if result:
                    conn.close()
                    return result['postcode']
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"查询邮编时出错: {e}")
            return None
    
    def _parse_address_local(self, address: str) -> Dict[str, str]:
        """
        使用本地数据库解析地址（原有逻辑）
        
        Args:
            address: 地址字符串
            
        Returns:
            dict: 包含province, city, county等信息的字典
        """
        result = {
            'province': '',
            'city': '',
            'county': '',
            'detail': address,
            'postcode': ''
        }
        
        # 清理地址字符串
        clean_address = address.strip()
        # 保存原始地址用于特殊匹配（如自贸区），同时创建清理版本用于常规解析
        parsing_address = clean_address
        # 对于非自贸区地址，移除括号内容以避免干扰
        if '自由贸易试验区' not in clean_address:
            parsing_address = re.sub(r'\([^)]*\)', '', clean_address).strip()
        
        # 预处理：从数据库中查询可能的县级市或县，但需要更智能的匹配
        # 只有在地址中同时包含省市信息或者是独特的县级市名称时才优先识别
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 先检查是否有明确的省市县组合
            cursor.execute("""
                SELECT name, province, city, county, full_path
                FROM area 
                WHERE (name LIKE '%市' OR name LIKE '%县' OR name LIKE '%区') 
                AND LENGTH(name) >= 2
                ORDER BY LENGTH(full_path) DESC, LENGTH(name) DESC
            """)
            
            county_results = cursor.fetchall()
            for row in county_results:
                county_name = row['name']
                province_name = row['province']
                city_name = row['city']
                
                # 优先匹配：地址中包含区域名，并且同时包含对应的省或市信息
                if (county_name in parsing_address and 
                    (province_name.replace('省', '').replace('市', '').replace('自治区', '') in parsing_address or
                     city_name.replace('市', '').replace('区', '') in parsing_address)):
                    
                    # 检查是否为直辖市的区（在数据库中，直辖市的区存储为city）
                    if (province_name in ['北京市', '上海市', '天津市', '重庆市'] and 
                        county_name.endswith('区') and row['county'] is None):
                        # 对于直辖市，区已经是city
                        result['province'] = province_name
                        result['city'] = city_name  # city_name就是区名
                        result['county'] = ''
                    elif row['county'] is not None and row['county'] != '':
                        # 非直辖市的正常处理（有county的情况）
                        result['province'] = province_name
                        result['city'] = city_name
                        result['county'] = row['county']
                    else:
                        # 其他情况（可能是地级市）
                        result['province'] = province_name
                        result['city'] = city_name
                        result['county'] = ''
                    
                    conn.close()
                    return result
            
            # 如果上面没有匹配到，再尝试匹配一些独特的县名（避免重名冲突）
            cursor.execute("""
                SELECT name, province, city, county, COUNT(*) as name_count
                FROM area 
                WHERE (name LIKE '%县' OR (name LIKE '%市' AND county IS NOT NULL)) 
                AND county IS NOT NULL AND county != ''
                AND LENGTH(name) >= 2
                GROUP BY name
                HAVING name_count = 1
                ORDER BY LENGTH(name) DESC
            """)
            
            unique_counties = cursor.fetchall()
            for row in unique_counties:
                county_name = row['name']
                if county_name in parsing_address:
                    result['province'] = row['province']
                    result['city'] = row['city']
                    result['county'] = row['county']
                    conn.close()
                    return result
            
            conn.close()
                    
        except Exception as e:
            print(f"查询县级市/县区信息时出错: {e}")
        
        # 从数据库获取所有省级行政区信息
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT province 
                FROM area 
                WHERE province IS NOT NULL AND province != ''
            """)
            
            all_provinces = [row['province'] for row in cursor.fetchall()]
            conn.close()
            municipalities = [p.replace('市', '') for p in all_provinces if p.endswith('市') and len(p) <= 4]
            autonomous_regions = {p.split('自治区')[0]: p for p in all_provinces if '自治区' in p}
        except Exception as e:
            print(f"查询省级行政区信息时出错: {e}")
            # 备用硬编码数据
            municipalities = ['北京', '上海', '天津', '重庆']
            autonomous_regions = {
                '内蒙古': '内蒙古自治区',
                '广西': '广西壮族自治区', 
                '西藏': '西藏自治区',
                '宁夏': '宁夏回族自治区',
                '新疆': '新疆维吾尔自治区'
            }
        
        # 1. 匹配省级行政区
        province_patterns = [
            r'([^省市区县]{2,}省)',  # XX省
            r'([\u4e00-\u9fa5]{2,}自治区)',  # XX自治区
            r'(香港特别行政区|澳门特别行政区)',  # 特别行政区
            r'中国\(([^)]+)\)自由贸易试验区',  # 自贸区，如"中国(上海)自由贸易试验区"
        ]
        
        for i, pattern in enumerate(province_patterns):
            match = re.search(pattern, parsing_address)
            if match:
                if i == 3:  # 自贸区模式
                    # 提取括号内的省份名称，如"上海"转换为"上海市"
                    province_name = match.group(1)
                    if province_name in municipalities:
                        result['province'] = province_name + '市'
                    else:
                        # 如果不是直辖市，尝试添加"省"
                        result['province'] = province_name + '省'
                else:
                    result['province'] = match.group(1)
                break
        
        # 处理直辖市
        if not result['province']:
            for municipality in municipalities:
                if municipality in parsing_address:
                    result['province'] = municipality + '市'
                    break
        
        # 处理自治区的特殊情况
        if not result['province']:
            for region, full_name in autonomous_regions.items():
                if region in parsing_address:
                    result['province'] = full_name
                    break
        
        # 2. 匹配市级行政区（优先在已知省份范围内匹配）
        city_patterns = [
            r'([\u4e00-\u9fa5]{2,8}市)',  # 匹配2-8个汉字+"市"
            r'([\u4e00-\u9fa5]{2,8}地区)',  # 匹配2-8个汉字+"地区"
            r'([\u4e00-\u9fa5]{2,8}州)',   # 匹配2-8个汉字+"州"
            r'([\u4e00-\u9fa5]{2,8}盟)'    # 匹配2-8个汉字+"盟"
        ]
        
        # 对于直辖市，区应该被识别为city
        municipalities = ['北京市', '上海市', '天津市', '重庆市']
        if result['province'] in municipalities:
            city_patterns.append(r'([\u4e00-\u9fa5]{2,8}区)')  # 对直辖市添加"区"的匹配
        
        # 如果已有省份信息，优先在该省份范围内查找城市
        if result['province']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                for pattern in city_patterns:
                    matches = re.findall(pattern, parsing_address)
                    for match in matches:
                        # 过滤掉明显不是城市名的匹配
                        if len(match) < 2 or any(char.isdigit() for char in match):
                            continue
                        if '路' in match or '街' in match or '号' in match or '楼' in match:
                            continue
                        
                        # 在数据库中验证该城市是否属于当前省份
                        cursor.execute("""
                            SELECT DISTINCT city FROM area 
                            WHERE province = ? AND city = ?
                        """, (result['province'], match))
                        if cursor.fetchone():
                            result['city'] = match
                            conn.close()
                            break
                    if result['city']:
                        break
                
                if not result['city']:
                    conn.close()
            except Exception as e:
                print(f"在省份范围内查询城市时出错: {e}")
        
        # 如果没有省份信息或在省份范围内未找到城市，进行全局匹配
        if not result['city']:
            # 重新构建city_patterns，包含对直辖市区的匹配
            global_city_patterns = [
                r'([\u4e00-\u9fa5]{2,8}市)',  # 匹配2-8个汉字+"市"
                r'([\u4e00-\u9fa5]{2,8}地区)',  # 匹配2-8个汉字+"地区"
                r'([\u4e00-\u9fa5]{2,8}州)',   # 匹配2-8个汉字+"州"
                r'([\u4e00-\u9fa5]{2,8}盟)',    # 匹配2-8个汉字+"盟"
                r'([\u4e00-\u9fa5]{2,8}区)'     # 匹配2-8个汉字+"区"（可能是直辖市的区）
            ]
            
            for pattern in global_city_patterns:
                matches = re.findall(pattern, parsing_address)
                if matches:
                    # 过滤掉省级匹配，选择最合适的市级匹配
                    for match in matches:
                        # 过滤掉明显不是城市名的匹配
                        if len(match) < 2 or any(char.isdigit() for char in match):
                            continue
                        if '路' in match or '街' in match or '号' in match or '楼' in match:
                            continue
                            
                        province_base = result['province'].replace('市', '').replace('自治区', '').replace('省', '') if result['province'] else ''
                        # 修复逻辑：当province_base为空时，不应该阻止匹配
                        if match != result['province'] and (not province_base or province_base not in match):
                            # 如果匹配的是"区"，需要验证是否为直辖市的区
                            if match.endswith('区'):
                                # 检查是否为直辖市的区
                                try:
                                    conn = self._get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        SELECT DISTINCT province FROM area 
                                        WHERE city = ? AND province IN ('北京市', '上海市', '天津市', '重庆市')
                                    """, (match,))
                                    municipality_result = cursor.fetchone()
                                    if municipality_result:
                                        result['city'] = match
                                        if not result['province']:
                                            result['province'] = municipality_result[0]
                                        conn.close()
                                        break
                                    conn.close()
                                except Exception as e:
                                    print(f"验证直辖市区时出错: {e}")
                            else:
                                result['city'] = match
                                break
                    if result['city']:
                        break
        
        # 如果没有找到市级，但有省份，尝试从数据库查找
        if not result['city'] and result['province']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                # 从地址中提取可能的市级名称，并在数据库中验证
                for pattern in city_patterns:
                    matches = re.findall(pattern, parsing_address)
                    for match in matches:
                        cursor.execute("""
                            SELECT DISTINCT city FROM area 
                            WHERE province = ? AND city = ?
                        """, (result['province'], match))
                        if cursor.fetchone():
                            result['city'] = match
                            conn.close()
                            break
                    if result['city']:
                        break
                
                if not result['city']:
                    conn.close()
            except Exception as e:
                print(f"查询市级信息时出错: {e}")
        
        # 3. 如果没有找到省份但找到了城市，通过数据库查询省份
        if not result['province'] and result['city']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                # 先尝试精确匹配城市名
                cursor.execute("""
                    SELECT DISTINCT province FROM area 
                    WHERE city = ?
                    ORDER BY level ASC LIMIT 1
                """, (result['city'],))
                province_result = cursor.fetchone()
                
                # 如果精确匹配失败，尝试更精确的模糊匹配（只匹配完整的城市名）
                if not province_result:
                    city_name = result['city'].replace('市', '')
                    cursor.execute("""
                        SELECT DISTINCT province FROM area 
                        WHERE city = ? OR city = ?
                        ORDER BY level ASC LIMIT 1
                    """, (city_name, city_name + '市'))
                    province_result = cursor.fetchone()
                
                if province_result:
                    result['province'] = province_result[0]
                
                conn.close()
            except Exception as e:
                print(f"查询省份信息时出错: {e}")
        
        # 4. 如果仍然没有省份，尝试通过数据库查询城市对应的省份
        if not result['province'] and result['city']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT province 
                    FROM area 
                    WHERE city = ? AND province IS NOT NULL AND province != ''
                    LIMIT 1
                """, (result['city'],))
                
                province_result = cursor.fetchone()
                if province_result:
                    result['province'] = province_result['province']
                
                conn.close()
            except Exception as e:
                print(f"查询城市对应省份时出错: {e}")
        
        # 5. 如果仍然没有省份，尝试从地址中提取可能的省份信息
        if not result['province']:
            # 尝试从地址中查找省份关键词
            province_keywords = ['省', '自治区', '特别行政区']
            for keyword in province_keywords:
                if keyword in parsing_address:
                        # 查找包含关键词的可能省份
                        pattern = rf'([^\s，,。.]{2,8}{keyword})'
                        matches = re.findall(pattern, parsing_address)
                        for match in matches:
                            try:
                                conn = self._get_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    SELECT DISTINCT province FROM area 
                                    WHERE province LIKE ? 
                                    ORDER BY level ASC LIMIT 1
                                """, (f"%{match}%",))
                                province_result = cursor.fetchone()
                                if province_result:
                                    result['province'] = province_result[0]
                                    conn.close()
                                    break
                                conn.close()
                            except Exception as e:
                                print(f"查询省份信息时出错: {e}")
                        if result['province']:
                            break
        
        # 6. 如果仍然没有省份，尝试通过县区反查省份和城市
        if not result['province'] and result['county']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT province, city FROM area 
                    WHERE name = ? OR county = ?
                    ORDER BY level ASC LIMIT 1
                """, (result['county'], result['county']))
                province_city_result = cursor.fetchone()
                if province_city_result:
                    result['province'] = province_city_result[0]
                    if not result['city'] and province_city_result[1]:
                        result['city'] = province_city_result[1]
                
                conn.close()
            except Exception as e:
                print(f"通过县区查询省份城市信息时出错: {e}")
        
        # 7. 最后的兜底策略：如果有城市但没有省份，尝试通过地址中的关键词推断
        if not result['province'] and parsing_address:
            # 常见省份简称映射
            province_abbr = {
                '京': '北京市', '津': '天津市', '沪': '上海市', '渝': '重庆市',
                '冀': '河北省', '晋': '山西省', '蒙': '内蒙古自治区', '辽': '辽宁省',
                '吉': '吉林省', '黑': '黑龙江省', '苏': '江苏省', '浙': '浙江省',
                '皖': '安徽省', '闽': '福建省', '赣': '江西省', '鲁': '山东省',
                '豫': '河南省', '鄂': '湖北省', '湘': '湖南省', '粤': '广东省',
                '桂': '广西壮族自治区', '琼': '海南省', '川': '四川省', '蜀': '四川省',
                '贵': '贵州省', '云': '云南省', '藏': '西藏自治区', '陕': '陕西省',
                '甘': '甘肃省', '青': '青海省', '宁': '宁夏回族自治区', '新': '新疆维吾尔自治区'
            }
            
            for abbr, full_name in province_abbr.items():
                if abbr in parsing_address:
                    result['province'] = full_name
                    break
        
        # 4. 匹配县区级行政区（优先在已知省市范围内匹配）
        county_patterns = [
            r'([^省市区县]{1,}自治县)',  # XX自治县（优先匹配）
            r'([^省市区县]{1,}自治旗)',  # XX自治旗（优先匹配）
            r'([^省市区县]{2,}市)',  # XX市（县级市）
            r'([^省市区县]{2,}县)',  # XX县
            r'([^省市区县]{2,}旗)',  # XX旗
        ]
        
        # 对于非直辖市，才匹配区作为县级行政区
        if result['province'] not in ['北京市', '上海市', '天津市', '重庆市']:
            county_patterns.append(r'([^省市区县]{2,}区)')  # XX区（降低优先级，避免匹配到园区等）
        
        # 如果已有省份和城市信息，优先在该范围内查找县区
        if result['province'] and result['city']:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                for pattern in county_patterns:
                    matches = re.findall(pattern, parsing_address)
                    for match in reversed(matches):  # 选择最后一个匹配，通常是最具体的行政区
                        # 排除园区、开发区、工业区等非正式行政区
                        if ('园区' in match or '开发区' in match or '工业区' in match or 
                            '经济区' in match or '高新区' in match or '保税区' in match):
                            continue
                        
                        # 在数据库中验证该县区是否属于当前省市
                        cursor.execute("""
                            SELECT county FROM area 
                            WHERE province = ? AND city = ? AND (county = ? OR name = ?)
                        """, (result['province'], result['city'], match, match))
                        if cursor.fetchone():
                            result['county'] = match
                            conn.close()
                            break
                    if result['county']:
                        break
                
                if not result['county']:
                    conn.close()
            except Exception as e:
                print(f"在省市范围内查询县区时出错: {e}")
        
        # 如果没有省市信息或在省市范围内未找到县区，进行全局匹配
        if not result['county']:
            # 重新构建county_patterns，对于直辖市排除区的匹配
            global_county_patterns = [
                r'([^省市区县]{1,}自治县)',  # XX自治县（优先匹配）
                r'([^省市区县]{1,}自治旗)',  # XX自治旗（优先匹配）
                r'([^省市区县]{2,}市)',  # XX市（县级市）
                r'([^省市区县]{2,}县)',  # XX县
                r'([^省市区县]{2,}旗)',  # XX旗
            ]
            
            # 对于非直辖市，才匹配区作为县级行政区
            if result['province'] not in ['北京市', '上海市', '天津市', '重庆市']:
                global_county_patterns.append(r'([^省市区县]{2,}区)')  # XX区
            
            for pattern in global_county_patterns:
                matches = re.findall(pattern, parsing_address)
                if matches:
                    # 选择最后一个匹配，通常是最具体的行政区
                    for match in reversed(matches):
                        # 确保不与省市重复，并且排除园区、开发区等非行政区
                        province_base = result['province'].replace('市', '').replace('自治区', '').replace('省', '') if result['province'] else ''
                        city_base = result['city'].replace('市', '').replace('地区', '').replace('州', '').replace('盟', '').replace('区', '') if result['city'] else ''
                        
                        # 排除园区、开发区、工业区等非正式行政区
                        if ('园区' in match or '开发区' in match or '工业区' in match or 
                            '经济区' in match or '高新区' in match or '保税区' in match):
                            continue
                        
                        # 对于县级市，需要特殊处理：不能与地级市相同
                        if (match not in (result['province'] or '') and 
                            match != result['city'] and  # 县级市不能与地级市相同
                            (not province_base or province_base not in match) and
                            (not city_base or city_base not in match)):
                            
                            # 如果是市级单位，需要在数据库中验证是否为县级市
                            if match.endswith('市'):
                                try:
                                    conn = self._get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        SELECT county FROM area 
                                        WHERE province = ? AND city = ? AND county = ?
                                    """, (result['province'], result['city'], match))
                                    if cursor.fetchone():
                                        result['county'] = match
                                        conn.close()
                                        break
                                    conn.close()
                                except Exception as e:
                                    print(f"验证县级市时出错: {e}")
                            else:
                                result['county'] = match
                                break
                    if result['county']:  # 如果找到了县区，跳出外层循环
                        break
        
        # 4.1 如果找到了县区但没有省份和城市，通过县区反查省份和城市
        if result['county'] and (not result['province'] or not result['city']):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT province, city FROM area 
                    WHERE name = ? OR county = ?
                    ORDER BY level ASC LIMIT 1
                """, (result['county'], result['county']))
                province_city_result = cursor.fetchone()
                if province_city_result:
                    if not result['province'] and province_city_result[0]:
                        result['province'] = province_city_result[0]
                    if not result['city'] and province_city_result[1]:
                        result['city'] = province_city_result[1]
                
                conn.close()
            except Exception as e:
                print(f"通过县区查询省份城市信息时出错: {e}")
        
        # 5. 如果没有找到县区，但有镇级单位，尝试通过数据库查找对应的县区
        if not result['county']:
            # 查找镇级单位
            town_match = re.search(r'([^省市区县]{2,}镇)', parsing_address)
            if town_match:
                town_name = town_match.group(1)
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    # 查找包含该镇的县区
                    cursor.execute("""
                        SELECT DISTINCT county FROM area 
                        WHERE full_path LIKE ? AND county IS NOT NULL AND county != ''
                        ORDER BY level DESC LIMIT 1
                    """, (f"%{town_name}%",))
                    county_result = cursor.fetchone()
                    if county_result:
                        result['county'] = county_result[0]
                    
                    conn.close()
                except Exception as e:
                    print(f"查询镇级对应县区时出错: {e}")
        
        return result
    
    def query_by_address(self, address: str) -> List[Dict]:
        """
        根据地址查询邮编和区域信息
        
        Args:
            address: 地址字符串
            
        Returns:
            list: 匹配的区域信息列表
        """
        # 解析地址
        parsed = self.parse_address(address)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        results = []
        
        try:
            # 策略1: 精确匹配省市区
            if parsed['province'] and parsed['city'] and parsed['county']:
                query = """
                    SELECT id, name, province, city, county, postcode, level, full_path
                    FROM area 
                    WHERE province LIKE ? AND name LIKE ?
                    ORDER BY level DESC LIMIT 10
                """
                cursor.execute(query, (f"%{parsed['province']}%", f"%{parsed['county']}%"))
                results.extend(cursor.fetchall())
            
            # 策略2: 匹配省市
            if not results and parsed['province'] and parsed['city']:
                query = """
                    SELECT id, name, province, city, county, postcode, level, full_path
                    FROM area 
                    WHERE province LIKE ? AND name LIKE ?
                    ORDER BY level DESC LIMIT 10
                """
                cursor.execute(query, (f"%{parsed['province']}%", f"%{parsed['city']}%"))
                results.extend(cursor.fetchall())
            
            # 策略3: 只匹配省
            if not results and parsed['province']:
                query = """
                    SELECT id, name, province, city, county, postcode, level, full_path
                    FROM area 
                    WHERE province LIKE ?
                    ORDER BY level ASC LIMIT 10
                """
                cursor.execute(query, (f"%{parsed['province']}%",))
                results.extend(cursor.fetchall())
            
            # 策略4: 模糊匹配地址中的关键词
            if not results:
                keywords = []
                for part in [parsed['province'], parsed['city'], parsed['county']]:
                    if part:
                        # 去掉常见的行政区划后缀
                        clean_part = re.sub(r'(省|市|区|县|自治区|自治州|地区)$', '', part)
                        if clean_part:
                            keywords.append(clean_part)
                
                if keywords:
                    for keyword in keywords:
                        query = """
                            SELECT id, name, province, city, county, postcode, level, full_path
                            FROM area 
                            WHERE name LIKE ? OR full_path LIKE ?
                            ORDER BY level DESC LIMIT 5
                        """
                        cursor.execute(query, (f"%{keyword}%", f"%{keyword}%"))
                        results.extend(cursor.fetchall())
                        if results:
                            break
            
            # 如果仍然没有结果，使用原始地址进行模糊匹配
            if not results:
                query = """
                    SELECT id, name, province, city, county, postcode, level, full_path
                    FROM area 
                    WHERE name LIKE ? OR full_path LIKE ?
                    ORDER BY level DESC LIMIT 10
                """
                cursor.execute(query, (f"%{address}%", f"%{address}%"))
                results.extend(cursor.fetchall())
            
            # 转换结果格式
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'province': row['province'] or '',
                    'city': row['city'] or '',
                    'county': row['county'] or '',
                    'postcode': row['postcode'] or '',
                    'level': row['level'],
                    'full_path': row['full_path'] or ''
                })
                
        except Exception as e:
            print(f"查询失败: {e}")
        finally:
            conn.close()
        
        return formatted_results[:20]  # 限制返回结果数量
    
    def query_single_address(self, address: str) -> Optional[Dict]:
        """
        查询单个地址，返回最佳匹配结果
        
        Args:
            address: 地址字符串
            
        Returns:
            dict: 最佳匹配的区域信息，如果未找到返回None
        """
        results = self.query_by_address(address)
        
        if results:
            return results[0]  # 返回第一个（最佳匹配）结果
        
        return None
    
    def get_postcode(self, address: str) -> Optional[str]:
        """
        获取地址对应的邮编
        
        Args:
            address: 地址字符串
            
        Returns:
            str: 邮编，如果未找到返回None
        """
        results = self.query_by_address(address)
        
        # 优先返回最具体的邮编（level最高的）
        for result in results:
            if result['postcode']:
                return result['postcode']
        
        return None
    
    def get_region_info(self, address: str) -> Dict[str, str]:
        """
        获取地址对应的省市区信息
        
        Args:
            address: 地址字符串
            
        Returns:
            dict: 包含province, city, county, postcode的字典
        """
        results = self.query_by_address(address)
        
        if not results:
            return {
                'province': '',
                'city': '',
                'county': '',
                'postcode': ''
            }
        
        # 选择最匹配的结果（level最高的）
        best_match = results[0]
        
        return {
            'province': best_match['province'],
            'city': best_match['city'],
            'county': best_match['county'],
            'postcode': best_match['postcode']
        }
    
    def close(self):
        """
        关闭数据库连接（保留方法以保持兼容性）
        """
        pass
    
    def __del__(self):
        """
        析构函数（保留方法以保持兼容性）
        """
        pass

# 便捷函数
def query_address(address: str, db_path: str = None) -> Dict[str, str]:
    """
    便捷函数：查询地址对应的省市区和邮编
    
    Args:
        address: 地址字符串
        db_path: 数据库路径（可选）
        
    Returns:
        dict: 包含province, city, county, postcode的字典
    """
    query_engine = AddressQuery(db_path)
    try:
        return query_engine.get_region_info(address)
    finally:
        query_engine.close()

def get_postcode(address: str, db_path: str = None) -> Optional[str]:
    """
    便捷函数：获取地址对应的邮编
    
    Args:
        address: 地址字符串
        db_path: 数据库路径（可选）
        
    Returns:
        str: 邮编，如果未找到返回None
    """
    query_engine = AddressQuery(db_path)
    try:
        return query_engine.get_postcode(address)
    finally:
        query_engine.close()

# 示例用法
if __name__ == "__main__":
    # 创建查询器实例
    query_engine = AddressQuery()
    
    # 从SQL文件导入数据（首次运行时需要）
    sql_file = os.path.join(os.path.dirname(__file__), 'area.sql')
    if os.path.exists(sql_file):
        print("正在导入数据...")
        query_engine.import_from_sql(sql_file)
    
    # 测试地址查询
    test_addresses = [
        "北京市朝阳区建国门外大街1号",
        "上海市浦东新区陆家嘴金融贸易区",
        "广东省深圳市南山区科技园",
        "浙江省杭州市西湖区文三路",
        "四川省成都市锦江区春熙路"
    ]
    
    for address in test_addresses:
        print(f"\n地址: {address}")
        
        # 查询详细信息
        results = query_engine.query_by_address(address)
        if results:
            print(f"匹配结果数: {len(results)}")
            for i, result in enumerate(results[:3]):  # 只显示前3个结果
                print(f"  {i+1}. {result['full_path']} - 邮编: {result['postcode']}")
        
        # 获取最佳匹配的邮编
        postcode = query_engine.get_postcode(address)
        print(f"邮编: {postcode}")
        
        # 获取省市区信息
        region_info = query_engine.get_region_info(address)
        print(f"省市区: {region_info['province']} {region_info['city']} {region_info['county']}")
    
    # 关闭连接
    query_engine.close()