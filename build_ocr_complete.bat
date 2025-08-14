@echo off
chcp 65001
echo ========================================
echo 打包完整版OCR识别工具
echo ========================================
echo.

echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo 检查OCR依赖包...
python -c "import alibabacloud_ocr_api20210707; print('✅ alibabacloud_ocr_api20210707 已安装')"
python -c "import alibabacloud_credentials; print('✅ alibabacloud_credentials 已安装')"
python -c "import alibabacloud_tea_openapi; print('✅ alibabacloud_tea_openapi 已安装')"
python -c "import alibabacloud_tea_util; print('✅ alibabacloud_tea_util 已安装')"
python -c "import PIL; print('✅ PIL/Pillow已安装')"
python -c "import tkinter; print('✅ tkinter已安装')"

echo.
echo 开始打包完整版OCR工具...
echo.

venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name "营业执照OCR识别工具_完整版" --hidden-import tkinter --hidden-import PIL --hidden-import PIL.Image --hidden-import PIL.ImageTk --hidden-import json --hidden-import os --hidden-import datetime --hidden-import threading --hidden-import requests --hidden-import base64 --hidden-import alibabacloud_ocr_api20210707 --hidden-import alibabacloud_credentials --hidden-import alibabacloud_tea_openapi --hidden-import alibabacloud_tea_util --hidden-import alibabacloud_ocr_api20210707.client --hidden-import alibabacloud_ocr_api20210707.models --hidden-import alibabacloud_credentials.client --hidden-import alibabacloud_tea_openapi.models --hidden-import alibabacloud_tea_util.models --hidden-import alibabacloud_tea_util.client --hidden-import darabonba_core --hidden-import alibabacloud_tea --hidden-import cryptography --hidden-import cffi --hidden-import pycparser --collect-all PIL --collect-all tkinter --collect-all alibabacloud_ocr_api20210707 --collect-all alibabacloud_credentials --collect-all alibabacloud_tea_openapi --collect-all alibabacloud_tea_util ocr_license_complete.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包成功！
    echo.
    if exist "dist\营业执照OCR识别工具_完整版.exe" (
        echo 📦 可执行文件: dist\营业执照OCR识别工具_完整版.exe
        for %%A in ("dist\营业执照OCR识别工具_完整版.exe") do echo 📏 文件大小: %%~zA 字节
        echo.
        echo 🎉 完整版OCR工具打包完成！
        echo 📁 可执行文件位置: dist\营业执照OCR识别工具_完整版.exe
        echo 📋 使用说明:
        echo 1. 双击运行 营业执照OCR识别工具_完整版.exe
        echo 2. 配置阿里云OCR服务
        echo 3. 选择图片文件进行识别
        echo 4. 查看识别结果
        echo.
        echo 🔧 功能说明:
        echo - 阿里云OCR：使用阿里云OCR服务进行真实识别
    ) else (
        echo ❌ 可执行文件生成失败
    )
) else (
    echo ❌ 打包失败
)

echo.
pause