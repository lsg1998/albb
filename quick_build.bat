@echo off
chcp 65001
echo ========================================
echo 快速打包 - 虚拟环境版本
echo ========================================
echo.

echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo 检查PyInstaller...
python -c "import PyInstaller; print('PyInstaller可用')"
if %errorlevel% neq 0 (
    echo ❌ PyInstaller不可用，正在安装...
    pip install pyinstaller
)

echo.
echo 开始打包...
echo.

venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name "阿里巴巴供应商爬虫" --add-data "cary.json;." --add-data "alibaba_supplier_crawler.py;." --add-data "ocr;ocr" --hidden-import aiohttp --hidden-import asyncio --hidden-import sqlite3 --hidden-import tkinter --hidden-import requests --hidden-import urllib.parse --hidden-import json --hidden-import time --hidden-import random --hidden-import threading --hidden-import platform --hidden-import subprocess --hidden-import os --hidden-import re alibaba_crawler_gui.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包成功！
    echo.
    if exist "dist\阿里巴巴供应商爬虫.exe" (
        echo 📦 可执行文件: dist\阿里巴巴供应商爬虫.exe
        for %%A in ("dist\阿里巴巴供应商爬虫.exe") do echo 📏 文件大小: %%~zA 字节
        echo.
        echo 📄 复制必要文件...
        copy "cary.json" "dist\" >nul
        copy "gatewayService.json" "dist\" >nul
        echo ✅ 已复制 cary.json 到 dist\ 目录
        echo ✅ 已复制 gatewayService.json 到 dist\ 目录
        echo.
        echo 🎉 打包完成！
        echo 📁 可执行文件位置: dist\阿里巴巴供应商爬虫.exe
        echo 📋 使用说明:
        echo 1. 双击运行 阿里巴巴供应商爬虫.exe
        echo 2. 确保 cary.json 和 gatewayService.json 文件在同一目录
        echo 3. 首次运行会自动创建数据库文件
    ) else (
        echo ❌ 可执行文件生成失败
    )
) else (
    echo ❌ 打包失败
)

echo.
pause