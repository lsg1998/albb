#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地址查询模块
基于本地area数据库实现地址解析和邮编查询功能
"""

import sqlite3
import re
import os
from typing import Dict, List, Optional, Tuple

class AddressQuery:
    def __init__(self, db_path: str = None):
        """
        初始化地址查询器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 默认数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'area.db')
        
        self.db_path = db_path
        self.conn = None
        
        # 初始化数据库连接
        self._init_database()
    
    def _init_database(self):
        """
        初始化数据库连接和表结构
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            
            # 检查表是否存在，如果不存在则创建
            cursor = self.conn.cursor()
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
            
            self.conn.commit()
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            self.conn = None
    
    def import_from_sql(self, sql_file_path: str):
        """
        从SQL文件导入数据
        
        Args:
            sql_file_path: SQL文件路径
        """
        if not self.conn:
            print("数据库连接未建立")
            return False
        
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 提取INSERT语句
            insert_pattern = r"INSERT INTO `area` VALUES \(([^)]+)\);"
            matches = re.findall(insert_pattern, sql_content)
            
            cursor = self.conn.cursor()
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
            
            self.conn.commit()
            print(f"成功导入 {imported_count} 条记录")
            return imported_count > 0
            
        except Exception as e:
            print(f"导入SQL文件失败: {e}")
            return False
    
    def parse_address(self, address: str) -> Dict[str, str]:
        """
        解析地址字符串，提取省市区信息
        
        Args:
            address: 地址字符串
            
        Returns:
            dict: 包含province, city, county等信息的字典
        """
        result = {
            'province': '',
            'city': '',
            'county': '',
            'detail': address
        }
        
        # 清理地址字符串，移除括号内容以避免干扰
        clean_address = address.strip()
        # 先保存原始地址，然后清理括号内容用于解析
        parsing_address = re.sub(r'\([^)]*\)', '', clean_address).strip()
        
        # 定义直辖市
        municipalities = ['北京', '上海', '天津', '重庆']
        
        # 定义自治区
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
            r'([^省市区县]{2,}自治区)',  # XX自治区
            r'(香港特别行政区|澳门特别行政区)',  # 特别行政区
        ]
        
        for pattern in province_patterns:
            match = re.search(pattern, parsing_address)
            if match:
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
        
        # 2. 匹配市级行政区
        city_patterns = [
            r'([\u4e00-\u9fa5]{2,8}市)',  # 匹配2-8个汉字+"市"
            r'([\u4e00-\u9fa5]{2,8}地区)',  # 匹配2-8个汉字+"地区"
            r'([\u4e00-\u9fa5]{2,8}州)',   # 匹配2-8个汉字+"州"
            r'([\u4e00-\u9fa5]{2,8}盟)'    # 匹配2-8个汉字+"盟"
        ]
        
        for pattern in city_patterns:
            matches = re.findall(pattern, parsing_address)
            if matches:
                # 过滤掉省级匹配，选择最合适的市级匹配
                for match in matches:
                    # 过滤掉明显不是城市名的匹配
                    if len(match) < 2 or any(char.isdigit() for char in match):
                        continue
                    if '路' in match or '街' in match or '号' in match or '楼' in match:
                        continue
                        
                    province_base = result['province'].replace('市', '').replace('自治区', '').replace('省', '')
                    # 修复逻辑：当province_base为空时，不应该阻止匹配
                    if match != result['province'] and (not province_base or province_base not in match):
                        result['city'] = match
                        break
        
        # 如果没有找到市级，但有省份，尝试从数据库查找
        if not result['city'] and result['province'] and self.conn:
            try:
                cursor = self.conn.cursor()
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
                            break
                    if result['city']:
                        break
            except Exception as e:
                print(f"查询市级信息时出错: {e}")
        
        # 3. 如果没有找到省份但找到了城市，通过数据库查询省份
        if not result['province'] and result['city'] and self.conn:
            try:
                cursor = self.conn.cursor()
                # 先尝试精确匹配城市名
                cursor.execute("""
                    SELECT DISTINCT province FROM area 
                    WHERE city = ?
                    ORDER BY level ASC LIMIT 1
                """, (result['city'],))
                province_result = cursor.fetchone()
                
                # 如果精确匹配失败，尝试模糊匹配
                if not province_result:
                    city_name = result['city'].replace('市', '').replace('地区', '').replace('州', '').replace('盟', '')
                    cursor.execute("""
                        SELECT DISTINCT province FROM area 
                        WHERE name LIKE ? OR city LIKE ?
                        ORDER BY level ASC LIMIT 1
                    """, (f"%{city_name}%", f"%{city_name}%"))
                    province_result = cursor.fetchone()
                
                if province_result:
                    result['province'] = province_result[0]
            except Exception as e:
                print(f"查询省份信息时出错: {e}")
        
        # 4. 如果仍然没有省份，尝试通过常见城市映射来推断省份
        if not result['province'] and result['city']:
            # 常见地级市到省份的映射
            city_to_province = {
                '成都市': '四川省', '绵阳市': '四川省', '德阳市': '四川省',
                '东莞市': '广东省', '佛山市': '广东省', '中山市': '广东省', '珠海市': '广东省',
                '苏州市': '江苏省', '无锡市': '江苏省', '常州市': '江苏省', '南通市': '江苏省',
                '宜兴市': '江苏省', '兴化市': '江苏省', '江阴市': '江苏省',
                '温州市': '浙江省', '嘉兴市': '浙江省', '湖州市': '浙江省', '绍兴市': '浙江省',
                '金华市': '浙江省', '衢州市': '浙江省', '舟山市': '浙江省', '台州市': '浙江省',
                '丽水市': '浙江省', '温岭市': '浙江省',
                '合肥市': '安徽省', '芜湖市': '安徽省', '蚌埠市': '安徽省', '淮南市': '安徽省',
                '马鞍山市': '安徽省', '淮北市': '安徽省', '铜陵市': '安徽省', '安庆市': '安徽省',
                '黄山市': '安徽省', '滁州市': '安徽省', '阜阳市': '安徽省', '宿州市': '安徽省',
                '六安市': '安徽省', '亳州市': '安徽省', '池州市': '安徽省', '宣城市': '安徽省',
                '济南市': '山东省', '青岛市': '山东省', '淄博市': '山东省', '枣庄市': '山东省',
                '东营市': '山东省', '烟台市': '山东省', '潍坊市': '山东省', '济宁市': '山东省',
                '泰安市': '山东省', '威海市': '山东省', '日照市': '山东省', '滨州市': '山东省',
                '德州市': '山东省', '聊城市': '山东省', '临沂市': '山东省', '菏泽市': '山东省',
                '郑州市': '河南省', '开封市': '河南省', '洛阳市': '河南省', '平顶山市': '河南省',
                '安阳市': '河南省', '鹤壁市': '河南省', '新乡市': '河南省', '焦作市': '河南省',
                '濮阳市': '河南省', '许昌市': '河南省', '漯河市': '河南省', '三门峡市': '河南省',
                '南阳市': '河南省', '商丘市': '河南省', '信阳市': '河南省', '周口市': '河南省',
                '驻马店市': '河南省',
                '广州市': '广东省', '深圳市': '广东省', '汕头市': '广东省', '韶关市': '广东省',
                '河源市': '广东省', '梅州市': '广东省', '惠州市': '广东省', '汕尾市': '广东省',
                '江门市': '广东省', '阳江市': '广东省', '湛江市': '广东省', '茂名市': '广东省',
                '肇庆市': '广东省', '清远市': '广东省', '潮州市': '广东省', '揭阳市': '广东省',
                '云浮市': '广东省'
            }
            
            if result['city'] in city_to_province:
                result['province'] = city_to_province[result['city']]
        
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
                        if self.conn:
                            try:
                                cursor = self.conn.cursor()
                                cursor.execute("""
                                    SELECT DISTINCT province FROM area 
                                    WHERE province LIKE ? 
                                    ORDER BY level ASC LIMIT 1
                                """, (f"%{match}%",))
                                province_result = cursor.fetchone()
                                if province_result:
                                    result['province'] = province_result[0]
                                    break
                            except Exception as e:
                                print(f"查询省份信息时出错: {e}")
                    if result['province']:
                        break
        
        # 6. 如果仍然没有省份，尝试通过县区反查省份
        if not result['province'] and result['county'] and self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT province FROM area 
                    WHERE name = ? OR county = ?
                    ORDER BY level ASC LIMIT 1
                """, (result['county'], result['county']))
                province_result = cursor.fetchone()
                if province_result:
                    result['province'] = province_result[0]
            except Exception as e:
                print(f"通过县区查询省份信息时出错: {e}")
        
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
        
        # 4. 匹配县区级行政区（优化精度）
        county_patterns = [
            r'([^省市区县]{1,}自治县)',  # XX自治县（优先匹配）
            r'([^省市区县]{1,}自治旗)',  # XX自治旗（优先匹配）
            r'([^省市区县]{2,}市)',  # XX市（县级市）
            r'([^省市区县]{2,}县)',  # XX县
            r'([^省市区县]{2,}旗)',  # XX旗
            r'([^省市区县]{2,}区)',  # XX区（降低优先级，避免匹配到园区等）
        ]
        
        for pattern in county_patterns:
            matches = re.findall(pattern, parsing_address)
            if matches:
                # 选择最后一个匹配，通常是最具体的行政区
                for match in reversed(matches):
                    # 确保不与省市重复，并且排除园区、开发区等非行政区
                    province_base = result['province'].replace('市', '').replace('自治区', '').replace('省', '')
                    city_base = result['city'].replace('市', '').replace('地区', '').replace('州', '').replace('盟', '')
                    
                    # 排除园区、开发区、工业区等非正式行政区
                    if ('园区' in match or '开发区' in match or '工业区' in match or 
                        '经济区' in match or '高新区' in match or '保税区' in match):
                        continue
                    
                    # 对于县级市，需要特殊处理：不能与地级市相同
                    if (match not in result['province'] and 
                        match != result['city'] and  # 县级市不能与地级市相同
                        (not province_base or province_base not in match) and
                        (not city_base or city_base not in match)):
                        
                        # 如果是市级单位，需要在数据库中验证是否为县级市
                        if match.endswith('市') and self.conn:
                            try:
                                cursor = self.conn.cursor()
                                cursor.execute("""
                                    SELECT county FROM area 
                                    WHERE province = ? AND city = ? AND county = ?
                                """, (result['province'], result['city'], match))
                                if cursor.fetchone():
                                    result['county'] = match
                                    break
                            except Exception as e:
                                print(f"验证县级市时出错: {e}")
                        else:
                            result['county'] = match
                            break
                if result['county']:  # 如果找到了县区，跳出外层循环
                    break
        
        # 5. 如果没有找到县区，但有镇级单位，尝试通过数据库查找对应的县区
        if not result['county'] and self.conn:
            # 查找镇级单位
            town_match = re.search(r'([^省市区县]{2,}镇)', parsing_address)
            if town_match:
                town_name = town_match.group(1)
                try:
                    cursor = self.conn.cursor()
                    # 查找包含该镇的县区
                    cursor.execute("""
                        SELECT DISTINCT county FROM area 
                        WHERE full_path LIKE ? AND county IS NOT NULL AND county != ''
                        ORDER BY level DESC LIMIT 1
                    """, (f"%{town_name}%",))
                    county_result = cursor.fetchone()
                    if county_result:
                        result['county'] = county_result[0]
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
        if not self.conn:
            return []
        
        # 解析地址
        parsed = self.parse_address(address)
        
        cursor = self.conn.cursor()
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
        关闭数据库连接
        """
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __del__(self):
        """
        析构函数，确保数据库连接被关闭
        """
        self.close()

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