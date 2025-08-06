from cx_Freeze import setup, Executable
import sys

# 基础设置
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# 包含的包
packages = [
    "tkinter", 
    "aiohttp", 
    "asyncio", 
    "sqlite3", 
    "requests",
    "urllib.parse",
    "json",
    "time",
    "random",
    "threading",
    "platform",
    "subprocess",
    "os",
    "re"
]

# 包含的文件
include_files = [
    "cary.json",
    "alibaba_supplier_crawler.py"
]

# 排除的模块
excludes = [
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "cv2"
]

setup(
    name="阿里巴巴供应商爬虫",
    version="1.0.0",
    description="阿里巴巴供应商数据爬取和执照提取工具",
    author="AI Assistant",
    options={
        "build_exe": {
            "packages": packages,
            "include_files": include_files,
            "excludes": excludes,
            "include_msvcrt": True,
            "optimize": 2
        }
    },
    executables=[
        Executable(
            "alibaba_crawler_gui.py",
            base=base,
            target_name="阿里巴巴供应商爬虫.exe",
            icon=None  # 可以添加图标文件路径
        )
    ]
) 