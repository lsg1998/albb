#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度云营业执照OCR识别API - 简化版本
提供简单的接口形式，支持URL和本地文件输入
"""

import json
import os
import sys
import requests
import base64
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入地址查询模块
from ocr.address_query import AddressQuery

class BaiduLicenseOCRAPI:
    def __init__(self, api_key=None, secret_key=None):
        """
        初始化百度云OCR API
        
        Args:
            api_key: 百度云API Key
            secret_key: 百度云Secret Key
        """
        # 初始化地址查询器
        self.address_query = AddressQuery()
        
        # 百度云配置 - 优先使用传入参数，否则使用硬编码密钥
        if api_key and secret_key:
            self.api_key = api_key
            self.secret_key = secret_key
        else:
            # 使用硬编码的百度云密钥
            self.api_key = "9APTxTPcgrO0oyTMkzGQh1U1"
            self.secret_key = "ycnhyZjkP3ClmiAjfoGAQhtabM2uOEB4"
        
        self.access_token = None
        
        # 获取访问令牌
        self._get_access_token()
    
    def _get_access_token(self):
        """
        使用 API Key 和 Secret Key 生成访问令牌
        """
        try:
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            response = requests.post(url, params=params)
            result = response.json()
            
            if "access_token" in result:
                self.access_token = result["access_token"]
            else:
                print(f"获取访问令牌失败: {result}")
                
        except Exception as e:
            print(f"获取访问令牌异常: {e}")
    
    def _download_image_from_url(self, url):
        """
        从URL下载图片并转换为base64
        
        Args:
            url: 图片URL
            
        Returns:
            str: base64编码的图片数据
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            raise Exception(f"下载图片失败: {e}")
    
    def _read_local_image(self, file_path):
        """
        读取本地图片并转换为base64
        
        Args:
            file_path: 本地图片文件路径
            
        Returns:
            str: base64编码的图片数据
        """
        try:
            with open(file_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"读取本地图片失败: {e}")
    
    def recognize_license_from_url(self, image_url):
        """
        从URL识别营业执照
        
        Args:
            image_url: 图片URL地址
            
        Returns:
            dict: 识别结果，包含结构化的营业执照信息
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "访问令牌获取失败",
                "data": None
            }
        
        if not image_url or not image_url.startswith(('http://', 'https://')):
            return {
                "success": False,
                "error": "请提供有效的图片URL",
                "data": None
            }
        
        try:
            # 下载图片并转换为base64
            image_base64 = self._download_image_from_url(image_url)
            
            # 调用百度云OCR API
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/business_license?access_token={self.access_token}"
            
            payload = {
                'image': image_base64,
                'detect_quality': 'false',
                'fullwidth_shift': 'false'
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(url, headers=headers, data=payload)
            result = response.json()
            
            if 'words_result' in result:
                # 转换结果
                converted_result = self._convert_baidu_result(result)
                return {
                    "success": True,
                    "error": None,
                    "data": converted_result
                }
            else:
                return {
                    "success": False,
                    "error": f"OCR识别失败: {result.get('error_msg', '未知错误')}",
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR识别异常: {str(e)}",
                "data": None
            }
    
    def recognize_license_from_file(self, file_path):
        """
        从本地文件识别营业执照
        
        Args:
            file_path: 本地图片文件路径
            
        Returns:
            dict: 识别结果，包含结构化的营业执照信息
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "访问令牌获取失败",
                "data": None
            }
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "文件不存在",
                "data": None
            }
        
        try:
            # 读取本地图片并转换为base64
            image_base64 = self._read_local_image(file_path)
            
            # 调用百度云OCR API
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/business_license?access_token={self.access_token}"
            
            payload = {
                'image': image_base64,
                'detect_quality': 'false',
                'fullwidth_shift': 'false'
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(url, headers=headers, data=payload)
            result = response.json()
            
            if 'words_result' in result:
                # 转换结果
                converted_result = self._convert_baidu_result(result)
                return {
                    "success": True,
                    "error": None,
                    "data": converted_result
                }
            else:
                return {
                    "success": False,
                    "error": f"OCR识别失败: {result.get('error_msg', '未知错误')}",
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR识别异常: {str(e)}",
                "data": None
            }
    
    def _convert_baidu_result(self, baidu_result):
        """
        转换百度云OCR结果为标准格式
        
        Args:
            baidu_result: 百度云OCR原始结果
            
        Returns:
            dict: 标准化的识别结果
        """
        try:
            words_result = baidu_result.get('words_result', {})
            
            # 获取注册地址
            registered_address = words_result.get('地址', {}).get('words', '')
            
            # 解析地址获取省市区和邮编
            province = ''
            city = ''
            district = ''
            postal_code = ''
            
            if registered_address:
                try:
                    # 解析地址
                    parsed_address = self.address_query.parse_address(registered_address)
                    province = parsed_address.get('province', '')
                    city = parsed_address.get('city', '')
                    district = parsed_address.get('county', '')
                    
                    # 查询邮编
                    address_info = self.address_query.query_single_address(registered_address)
                    if address_info:
                        postal_code = address_info.get('postcode', '')
                except Exception as e:
                    print(f"地址解析失败: {str(e)}")
            
            # 构建标准化结果
            result = {
                "RequestId": baidu_result.get('log_id', ''),
                "Data": {
                    "注册号": words_result.get('社会信用代码', {}).get('words', ''),
                    "公司名称": words_result.get('单位名称', {}).get('words', ''),
                    "发证日期": words_result.get('成立日期', {}).get('words', ''),
                    "到期日期": words_result.get('有效期', {}).get('words', '长期'),
                    "注册资本": words_result.get('注册资本', {}).get('words', ''),
                    "国家/地区": "中国",
                    "注册地址": registered_address,
                    "省份": province,
                    "城市": city,
                    "区县": district,
                    "邮编": postal_code,
                    "成立年份": words_result.get('成立日期', {}).get('words', ''),
                    "法律形式": words_result.get('类型', {}).get('words', ''),
                    "法定代表人": words_result.get('法人', {}).get('words', '')
                }
                # "RawText": json.dumps(baidu_result, ensure_ascii=False, indent=2)  # 暂时注释
            }
            
            return result
            
        except Exception as e:
            return {
                "RequestId": "conversion-error",
                "Data": {},
                "Error": f"结果转换失败: {str(e)}"
                # "RawText": json.dumps(baidu_result, ensure_ascii=False, indent=2)  # 暂时注释
            }

# 便捷函数
def recognize_license_from_url(image_url, api_key=None, secret_key=None):
    """
    便捷函数：从URL识别营业执照
    
    Args:
        image_url: 图片URL地址
        api_key: 百度云API Key（可选）
        secret_key: 百度云Secret Key（可选）
        
    Returns:
        dict: 识别结果
    """
    api = BaiduLicenseOCRAPI(api_key, secret_key)
    return api.recognize_license_from_url(image_url)

def recognize_license_from_file(file_path, api_key=None, secret_key=None):
    """
    便捷函数：从本地文件识别营业执照
    
    Args:
        file_path: 本地图片文件路径
        api_key: 百度云API Key（可选）
        secret_key: 百度云Secret Key（可选）
        
    Returns:
        dict: 识别结果
    """
    api = BaiduLicenseOCRAPI(api_key, secret_key)
    return api.recognize_license_from_file(file_path)

# 示例用法
if __name__ == "__main__":
    # 示例1: 使用类的方式
    ocr_api = BaiduLicenseOCRAPI()
    
    # 从URL识别
    test_url = "https://sc04.alicdn.com/kf/H8799706075fd4458830df0d2ec760700m.jpg"
    result = ocr_api.recognize_license_from_url(test_url)
    
    if result["success"]:
        print("识别成功！")
        data = result["data"]["Data"]
        print(f"公司名称: {data['公司名称']}")
        print(f"统一社会信用代码: {data['注册号']}")
        print(f"法定代表人: {data['法定代表人']}")
        print(f"注册资本: {data['注册资本']}")
        print(f"注册地址: {data['注册地址']}")
    else:
        print(f"识别失败: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # 示例2: 使用便捷函数
    result2 = recognize_license_from_url(test_url)
    
    if result2["success"]:
        print("便捷函数识别成功！")
        print(json.dumps(result2["data"]["Data"], ensure_ascii=False, indent=2))
    else:
        print(f"便捷函数识别失败: {result2['error']}")