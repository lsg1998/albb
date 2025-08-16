#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度云营业执照OCR识别接口
纯粹的接口实现，仅接收URL作为输入
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr.ocr_baidu_api import BaiduLicenseOCRAPI

def recognize_license(image_url):
    """
    营业执照OCR识别接口
    
    Args:
        image_url (str): 图片URL地址
        
    Returns:
        dict: 识别结果，包含以下字段：
            - success (bool): 识别是否成功
            - error (str): 错误信息（如果失败）
            - data (dict): 识别结果数据，包含：
                - RequestId: 请求ID
                - Data: 营业执照信息
                    - 注册号: 统一社会信用代码
                    - 公司名称: 企业名称
                    - 发证日期: 成立日期
                    - 到期日期: 有效期
                    - 注册资本: 注册资本
                    - 国家/地区: 国家地区
                    - 注册地址: 注册地址
                    - 省份: 省份信息
                    - 城市: 城市信息
                    - 区县: 区县信息
                    - 邮编: 邮政编码
                    - 成立年份: 成立年份
                    - 法律形式: 企业类型
                    - 法定代表人: 法定代表人
    """
    api = BaiduLicenseOCRAPI()
    return api.recognize_license_from_url(image_url)