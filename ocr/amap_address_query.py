import http.client
import json
import urllib.parse
import time
from typing import Dict, Optional

class AmapAddressQuery:
    """高德地图地址解析API封装类"""
    
    def __init__(self, api_key: str = ""):
        """
        初始化高德地图地址解析器
        
        Args:
            api_key: 高德地图API密钥
        """
        self.api_key = api_key
        self.base_url = "restapi.amap.com"
        self.api_path = "/v3/geocode/geo"
        
        # 频率控制：每秒最多3次请求
        self.max_requests_per_second = 3
        self.request_timestamps = []
    
    def parse_address(self, address: str) -> Optional[Dict[str, str]]:
        """
        解析地址信息
        
        Args:
            address: 要解析的地址字符串
            
        Returns:
            解析结果字典，包含province, city, district等字段
            如果解析失败返回None
        """
        if not address or not address.strip():
            return None
            
        if not self.api_key:
            print("警告: 未设置高德地图API密钥")
            return None
        
        # 频率控制：确保每秒不超过3次请求
        self._rate_limit()
        
        try:
            # URL编码地址
            encoded_address = urllib.parse.quote(address.strip())
            
            # 构建请求URL
            url_path = f"{self.api_path}?address={encoded_address}&key={self.api_key}"
            
            # 发送HTTP请求
            conn = http.client.HTTPSConnection(self.base_url)
            headers = {}
            conn.request("GET", url_path, "", headers)
            
            # 获取响应
            response = conn.getresponse()
            data = response.read()
            conn.close()
            
            # 解析JSON响应
            result = json.loads(data.decode("utf-8"))
            
            # 检查API响应状态
            if result.get("status") != "1":
                print(f"高德API错误: {result.get('info', '未知错误')}")
                return None
            
            # 检查是否有解析结果
            geocodes = result.get("geocodes", [])
            if not geocodes:
                print(f"地址解析失败: {address}")
                return None
            
            # 提取第一个解析结果
            geocode = geocodes[0]
            
            # 构建标准化结果
            parsed_result = {
                "province": geocode.get("province", ""),
                "city": geocode.get("city", ""),
                "district": geocode.get("district", ""),
                "county": geocode.get("district", ""),  # 兼容原有字段名
                "street": geocode.get("street", ""),
                "number": geocode.get("number", ""),
                "formatted_address": geocode.get("formatted_address", ""),
                "location": geocode.get("location", ""),
                "adcode": geocode.get("adcode", ""),
                "citycode": geocode.get("citycode", ""),
                "level": geocode.get("level", "")
            }
            
            return parsed_result
            
        except Exception as e:
            print(f"地址解析异常: {str(e)}")
            return None
    
    def batch_parse_addresses(self, addresses: list) -> Dict[str, Optional[Dict[str, str]]]:
        """
        批量解析地址
        
        Args:
            addresses: 地址列表
            
        Returns:
            字典，键为原地址，值为解析结果
        """
        results = {}
        
        for address in addresses:
            if address:
                results[address] = self.parse_address(address)
            else:
                results[address] = None
                
        return results
    
    def set_api_key(self, api_key: str):
        """
        设置API密钥
        
        Args:
            api_key: 高德地图API密钥
        """
        self.api_key = api_key
    
    def _rate_limit(self):
        """
        频率控制：确保每秒不超过3次请求
        """
        current_time = time.time()
        
        # 清理1秒前的请求记录
        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 1.0]
        
        # 如果当前1秒内已有3次或更多请求，则等待
        while len(self.request_timestamps) >= self.max_requests_per_second:
            # 计算需要等待的时间，等到最早的请求超过1秒
            oldest_request = self.request_timestamps[0]
            sleep_time = 1.0 - (current_time - oldest_request)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # 重新获取当前时间并清理过期记录
            current_time = time.time()
            self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 1.0]
        
        # 记录当前请求时间
        self.request_timestamps.append(current_time)

# 测试函数
def test_amap_address_query():
    """测试高德地图地址解析功能"""
    # 注意: 需要替换为实际的API密钥
    api_key = "YOUR_AMAP_API_KEY"
    
    amap_query = AmapAddressQuery(api_key)
    
    # 测试地址
    test_addresses = [
        "北京市朝阳区阜通东大街6号",
        "上海市浦东新区陆家嘴环路1000号",
        "广州市天河区珠江新城花城大道85号"
    ]
    
    print("高德地图地址解析测试:")
    print("=" * 50)
    
    for address in test_addresses:
        print(f"\n原地址: {address}")
        result = amap_query.parse_address(address)
        
        if result:
            print(f"省份: {result.get('province')}")
            print(f"城市: {result.get('city')}")
            print(f"区县: {result.get('district')}")
            print(f"街道: {result.get('street')}")
            print(f"门牌号: {result.get('number')}")
            print(f"标准地址: {result.get('formatted_address')}")
            print(f"坐标: {result.get('location')}")
        else:
            print("解析失败")

if __name__ == "__main__":
    test_amap_address_query()