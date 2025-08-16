#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR营业执照识别API包

提供阿里云和百度云的营业执照OCR识别功能
"""



# 导入百度云OCR API
try:
    from .ocr_baidu_api import BaiduLicenseOCRAPI
    from .ocr_baidu_api import recognize_license_from_url as baidu_recognize_url
    from .ocr_baidu_api import recognize_license_from_file as baidu_recognize_file
    BAIDU_AVAILABLE = True
except ImportError:
    BAIDU_AVAILABLE = False
    print("百度云OCR API不可用，请安装相关依赖")

# 版本信息
__version__ = "1.0.0"
__author__ = "OCR API Team"

# 导出的公共接口
__all__ = [
    # 阿里云相关
    'AliyunOCRAPI',
    'aliyun_recognize_url',
    'aliyun_recognize_file',
    
    # 百度云相关
    'BaiduLicenseOCRAPI',
    'baidu_recognize_url',
    'baidu_recognize_file',
    
    # 可用性标志
    'ALIYUN_AVAILABLE',
    'BAIDU_AVAILABLE'
]

# 便捷函数：自动选择可用的OCR服务
def recognize_license_from_url(image_url, provider='auto', **kwargs):
    """
    从URL识别营业执照（自动选择可用的服务提供商）
    
    Args:
        image_url: 图片URL
        provider: 服务提供商 ('auto', 'aliyun', 'baidu')
        **kwargs: 其他参数
        
    Returns:
        dict: 识别结果
    """
    if provider == 'aliyun' or (provider == 'auto' and ALIYUN_AVAILABLE):
        if ALIYUN_AVAILABLE:
            return aliyun_recognize_url(image_url, **kwargs)
        else:
            return {
                "success": False,
                "error": "阿里云OCR API不可用",
                "data": None
            }
    
    elif provider == 'baidu' or (provider == 'auto' and BAIDU_AVAILABLE):
        if BAIDU_AVAILABLE:
            return baidu_recognize_url(image_url, **kwargs)
        else:
            return {
                "success": False,
                "error": "百度云OCR API不可用",
                "data": None
            }
    
    else:
        return {
            "success": False,
            "error": "没有可用的OCR服务",
            "data": None
        }

def recognize_license_from_file(file_path, provider='auto', **kwargs):
    """
    从本地文件识别营业执照（自动选择可用的服务提供商）
    
    Args:
        file_path: 本地文件路径
        provider: 服务提供商 ('auto', 'aliyun', 'baidu')
        **kwargs: 其他参数
        
    Returns:
        dict: 识别结果
    """
    if provider == 'aliyun' or (provider == 'auto' and ALIYUN_AVAILABLE):
        if ALIYUN_AVAILABLE:
            return aliyun_recognize_file(file_path, **kwargs)
        else:
            return {
                "success": False,
                "error": "阿里云OCR API不可用",
                "data": None
            }
    
    elif provider == 'baidu' or (provider == 'auto' and BAIDU_AVAILABLE):
        if BAIDU_AVAILABLE:
            return baidu_recognize_file(file_path, **kwargs)
        else:
            return {
                "success": False,
                "error": "百度云OCR API不可用",
                "data": None
            }
    
    else:
        return {
            "success": False,
            "error": "没有可用的OCR服务",
            "data": None
        }

# 获取可用的服务提供商列表
def get_available_providers():
    """
    获取可用的OCR服务提供商列表
    
    Returns:
        list: 可用的服务提供商列表
    """
    providers = []
    if ALIYUN_AVAILABLE:
        providers.append('aliyun')
    if BAIDU_AVAILABLE:
        providers.append('baidu')
    return providers

# 打印可用性信息
def print_availability():
    """
    打印OCR服务可用性信息
    """
    print(f"OCR API 可用性状态:")
    print(f"  阿里云OCR: {'✓ 可用' if ALIYUN_AVAILABLE else '✗ 不可用'}")
    print(f"  百度云OCR: {'✓ 可用' if BAIDU_AVAILABLE else '✗ 不可用'}")
    
    available = get_available_providers()
    if available:
        print(f"  可用服务: {', '.join(available)}")
    else:
        print(f"  ⚠️  没有可用的OCR服务")