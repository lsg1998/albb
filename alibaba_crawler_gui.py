import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import sqlite3
import os
import json
import requests
import random
import aiohttp
from datetime import datetime
from alibaba_supplier_crawler import AlibabaSupplierCrawler

class AlibabaCrawlerGUI:
    def __init__(self):
        self.crawler = AlibabaSupplierCrawler()
        # 初始化数据库（确保代理表存在）
        self.crawler.init_database()
        # 从数据库加载当前活跃代理
        self.proxy = self.load_active_proxy()
        # OCR识别相关变量
        self.ocr_running = False
        self.ocr_thread = None
        self.setup_gui()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("阿里巴巴供应商爬虫 - 增强版")
        self.root.geometry("1000x700")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 数据库配置区域
        db_config_frame = ttk.LabelFrame(main_frame, text="数据库配置", padding="10")
        db_config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 数据库路径选择
        path_frame = ttk.Frame(db_config_frame)
        path_frame.pack(fill=tk.X)
        
        ttk.Label(path_frame, text="数据库路径:").pack(side=tk.LEFT, padx=(0, 5))
        self.db_path_var = tk.StringVar(value=self.crawler.db_path)
        self.db_path_entry = ttk.Entry(path_frame, textvariable=self.db_path_var, width=60)
        self.db_path_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self.browse_db_path).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(path_frame, text="应用", command=self.apply_db_path).pack(side=tk.LEFT)
        
        # 数据库状态显示
        self.db_status_label = ttk.Label(db_config_frame, text="")
        self.db_status_label.pack(anchor=tk.W, pady=(5, 0))
        self.update_db_status()
        
        # 创建选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 数据库列表页面 - 放在第一位
        db_list_frame = ttk.Frame(notebook)
        notebook.add(db_list_frame, text="数据库列表")
        
        # 爬取页面
        crawl_frame = ttk.Frame(notebook)
        notebook.add(crawl_frame, text="获取供应商")
        
        # 执照提取页面
        license_frame = ttk.Frame(notebook)
        notebook.add(license_frame, text="一键获取执照")
        
        # 营业执照识别页面
        ocr_frame = ttk.Frame(notebook)
        notebook.add(ocr_frame, text="营业执照识别")
        
        # 代理配置页面
        proxy_frame = ttk.Frame(notebook)
        notebook.add(proxy_frame, text="代理配置")
        
        # 设置数据库列表页面 - 先设置第一个标签页
        self.setup_db_list_page(db_list_frame)
        
        # 设置爬取页面
        self.setup_crawl_page(crawl_frame)
        
        # 设置执照提取页面
        self.setup_license_page(license_frame)
        
        # 设置营业执照识别页面
        self.setup_ocr_page(ocr_frame)
        
        # 设置代理配置页面
        self.setup_proxy_page(proxy_frame)
    
    def browse_db_path(self):
        """浏览数据库文件路径"""
        file_path = filedialog.askopenfilename(
            title="选择数据库文件",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")],
            initialdir=os.path.dirname(self.crawler.db_path) if os.path.dirname(self.crawler.db_path) else "."
        )
        if file_path:
            self.db_path_var.set(file_path)
    
    def apply_db_path(self):
        """应用新的数据库路径"""
        new_path = self.db_path_var.get().strip()
        if not new_path:
            messagebox.showwarning("警告", "请输入数据库路径")
            return
        
        # 检查文件是否存在，如果不存在询问是否创建
        if not os.path.exists(new_path):
            result = messagebox.askyesno(
                "数据库不存在", 
                f"数据库文件不存在：{new_path}\n\n是否创建新的数据库文件？"
            )
            if not result:
                return
        
        try:
            # 更新crawler的数据库路径
            old_path = self.crawler.db_path
            
            # 使用新的方法更改数据库路径并初始化
            self.crawler.change_database_path(new_path)
            
            # 更新状态显示
            self.update_db_status()
            
            # 刷新数据库列表页面
            self.refresh_db_list_page()
            
            messagebox.showinfo("成功", f"数据库路径已更新为：{new_path}")
            
        except Exception as e:
            # 如果出错，恢复原路径
            self.crawler.db_path = old_path
            self.db_path_var.set(old_path)
            messagebox.showerror("错误", f"切换数据库失败：{str(e)}")
    
    def update_db_status(self):
        """更新数据库状态显示"""
        db_path = self.crawler.db_path
        if os.path.exists(db_path):
            try:
                # 获取数据库统计信息
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查suppliers表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM suppliers")
                    total_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM suppliers WHERE license_extracted = 1")
                    extracted_count = cursor.fetchone()[0]
                    
                    status_text = f"状态: 已连接 | 总供应商: {total_count} | 已提取执照: {extracted_count} | 文件: {os.path.basename(db_path)}"
                else:
                    status_text = f"状态: 已连接 (空数据库) | 文件: {os.path.basename(db_path)}"
                
                conn.close()
                
            except Exception as e:
                status_text = f"状态: 连接错误 - {str(e)} | 文件: {os.path.basename(db_path)}"
        else:
            status_text = f"状态: 文件不存在 | 文件: {os.path.basename(db_path)}"
        
        self.db_status_label.config(text=status_text)
    
    def setup_crawl_page(self, parent):
        """设置爬取页面"""
        # 输入区域
        input_frame = ttk.LabelFrame(parent, text="爬取设置", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 搜索类型选择
        ttk.Label(input_frame, text="搜索类型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_type_var = tk.StringVar(value="keyword")
        search_type_frame = ttk.Frame(input_frame)
        search_type_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Radiobutton(search_type_frame, text="关键词搜索", variable=self.search_type_var, 
                       value="keyword", command=self.on_search_type_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(search_type_frame, text="分类搜索", variable=self.search_type_var, 
                       value="category", command=self.on_search_type_change).pack(side=tk.LEFT)
        
        # 关键词输入
        ttk.Label(input_frame, text="搜索关键词:").grid(row=1, column=0, sticky=tk.W, pady=5)
        keyword_frame = ttk.Frame(input_frame)
        keyword_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        self.keyword_entry = ttk.Entry(keyword_frame, width=40)
        self.keyword_entry.insert(0, "men's perfume")
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 快捷选择按钮
        ttk.Button(keyword_frame, text="快捷选择", command=self.show_category_selector).pack(side=tk.LEFT, padx=(5, 0))
        
        # 分类选择
        ttk.Label(input_frame, text="选择分类:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        self.category_combobox = ttk.Combobox(input_frame, textvariable=self.category_var, width=47, state="readonly")
        self.category_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 初始化分类选项
        self.load_categories()
        
        # 初始状态设置
        self.on_search_type_change()
        
        # 页面范围输入
        page_frame = ttk.Frame(input_frame)
        page_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(page_frame, text="页面范围:").pack(side=tk.LEFT)
        self.start_page_var = tk.StringVar(value="1")
        start_page_entry = ttk.Entry(page_frame, textvariable=self.start_page_var, width=8)
        start_page_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(page_frame, text="到").pack(side=tk.LEFT, padx=(5, 0))
        self.end_page_var = tk.StringVar(value="10")
        end_page_entry = ttk.Entry(page_frame, textvariable=self.end_page_var, width=8)
        end_page_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # 基础设置区域
        basic_frame = ttk.LabelFrame(input_frame, text="基础设置", padding="10")
        basic_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # 代理使用开关
        self.use_proxy_var = tk.BooleanVar(value=False)  # 默认关闭代理
        self.use_proxy_check = ttk.Checkbutton(basic_frame, text="使用代理", variable=self.use_proxy_var)
        self.use_proxy_check.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # 跳过重复数据开关
        self.skip_duplicates_var = tk.BooleanVar(value=True)
        self.skip_duplicates_check = ttk.Checkbutton(basic_frame, text="跳过重复数据", variable=self.skip_duplicates_var)
        self.skip_duplicates_check.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(20, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        self.start_crawl_btn = ttk.Button(button_frame, text="开始获取供应商", command=self.start_crawl)
        self.start_crawl_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_crawl_btn = ttk.Button(button_frame, text="一键爬取", command=self.show_batch_crawl_dialog)
        self.batch_crawl_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.batch_save_btn = ttk.Button(button_frame, text="批量入库", command=self.show_batch_save_dialog)
        self.batch_save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_crawl_btn = ttk.Button(button_frame, text="停止", command=self.stop_crawl, state=tk.DISABLED)
        self.stop_crawl_btn.pack(side=tk.LEFT)
        
        # 配置网格权重
        input_frame.columnconfigure(1, weight=1)
        basic_frame.columnconfigure(1, weight=1)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(parent, text="进度", padding="15")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack(anchor=tk.W)
        
        # 详细进度信息
        self.crawl_detail_label = ttk.Label(progress_frame, text="")
        self.crawl_detail_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 提取日志区域 - 替换原来的数据库列表
        log_frame = ttk.LabelFrame(parent, text="获取日志", padding="15")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 日志过滤区域
        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="过滤:").pack(side=tk.LEFT)
        self.crawl_log_filter_entry = ttk.Entry(filter_frame, width=30)
        self.crawl_log_filter_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(filter_frame, text="应用过滤", command=self.apply_crawl_log_filter).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="清除过滤", command=self.clear_crawl_log_filter).pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志控制按钮
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 日志级别设置
        ttk.Label(log_control_frame, text="日志级别:").pack(side=tk.LEFT)
        self.crawl_log_level_var = tk.StringVar(value="INFO")
        self.crawl_log_level_combobox = ttk.Combobox(log_control_frame, textvariable=self.crawl_log_level_var, width=10, state="readonly")
        self.crawl_log_level_combobox['values'] = ("DEBUG", "INFO", "WARNING", "ERROR")
        self.crawl_log_level_combobox.current(1)  # 默认选择INFO
        self.crawl_log_level_combobox.pack(side=tk.LEFT, padx=(5, 10))
        
        # 自动保存日志
        self.crawl_auto_save_log_var = tk.BooleanVar(value=True)
        self.crawl_auto_save_log_check = ttk.Checkbutton(log_control_frame, text="自动保存日志", variable=self.crawl_auto_save_log_var)
        self.crawl_auto_save_log_check.pack(side=tk.LEFT)
        
        # 保存和清空按钮
        ttk.Button(log_control_frame, text="保存日志", command=self.save_crawl_log).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(log_control_frame, text="清空日志", command=self.clear_crawl_log).pack(side=tk.RIGHT, padx=(0, 5))
        
        # 日志显示区域 - 修复滚动问题
        log_display_frame = ttk.Frame(log_frame)
        log_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.crawl_log_text = tk.Text(log_display_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_display_frame, orient=tk.VERTICAL, command=self.crawl_log_text.yview)
        self.crawl_log_text.configure(yscrollcommand=scrollbar.set)
        
        self.crawl_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 设置日志标签和颜色
        self.crawl_log_text.tag_configure("DEBUG", foreground="gray")
        self.crawl_log_text.tag_configure("INFO", foreground="black")
        self.crawl_log_text.tag_configure("WARNING", foreground="orange")
        self.crawl_log_text.tag_configure("ERROR", foreground="red")
        self.crawl_log_text.tag_configure("SUCCESS", foreground="green")
    
    def setup_license_page(self, parent):
        """设置执照提取页面"""
        # 控制区域
        control_frame = ttk.LabelFrame(parent, text="执照提取控制", padding="15")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 保存路径
        ttk.Label(control_frame, text="保存路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.save_path_var = tk.StringVar(value="./license_files")
        self.save_path_entry = ttk.Entry(control_frame, textvariable=self.save_path_var, width=50)
        self.save_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        self.browse_btn = ttk.Button(control_frame, text="浏览", command=self.browse_save_path)
        self.browse_btn.grid(row=0, column=2, padx=(10, 0))
        
        # 手动设置区域
        settings_frame = ttk.LabelFrame(control_frame, text="手动设置", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 线程数设置
        ttk.Label(settings_frame, text="并发线程数:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.thread_count_var = tk.StringVar(value="1")
        self.thread_count_entry = ttk.Entry(settings_frame, textvariable=self.thread_count_var, width=10)
        self.thread_count_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 批次间隔设置
        ttk.Label(settings_frame, text="批次间隔(秒):").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(20, 0))
        self.batch_delay_var = tk.StringVar(value="1.0")
        self.batch_delay_entry = ttk.Entry(settings_frame, textvariable=self.batch_delay_var, width=10)
        self.batch_delay_entry.grid(row=0, column=3, sticky=tk.W, pady=2, padx=(10, 0))
        
        # IP检测开关
        self.enable_ip_check_var = tk.BooleanVar(value=False)
        self.enable_ip_check_checkbox = ttk.Checkbutton(settings_frame, text="启用IP检测", variable=self.enable_ip_check_var)
        self.enable_ip_check_checkbox.grid(row=0, column=4, sticky=tk.W, pady=2, padx=(20, 0))
        
        # 日志级别设置
        ttk.Label(settings_frame, text="日志级别:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.log_level_var = tk.StringVar(value="INFO")
        self.log_level_combobox = ttk.Combobox(settings_frame, textvariable=self.log_level_var, width=10, state="readonly")
        self.log_level_combobox['values'] = ("DEBUG", "INFO", "WARNING", "ERROR")
        self.log_level_combobox.current(1)  # 默认选择INFO
        self.log_level_combobox.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 自动保存日志
        self.auto_save_log_var = tk.BooleanVar(value=True)
        self.auto_save_log_check = ttk.Checkbutton(settings_frame, text="自动保存日志", variable=self.auto_save_log_var)
        self.auto_save_log_check.grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=2, padx=(20, 0))
        
        # 配置网格权重
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        # 按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        self.extract_all_btn = ttk.Button(button_frame, text="一键获取所有执照", command=self.extract_all_licenses)
        self.extract_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_extract_btn = ttk.Button(button_frame, text="停止提取", command=self.stop_extract, state=tk.DISABLED)
        self.stop_extract_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_log_btn = ttk.Button(button_frame, text="保存日志", command=self.save_extract_log)
        self.save_log_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_log_btn = ttk.Button(button_frame, text="清空日志", command=self.clear_extract_log)
        self.clear_log_btn.pack(side=tk.LEFT)
        
        # 配置网格权重
        control_frame.columnconfigure(1, weight=1)
        
        # 提取进度
        extract_progress_frame = ttk.LabelFrame(parent, text="提取进度", padding="15")
        extract_progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.extract_progress = ttk.Progressbar(extract_progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.extract_progress.pack(fill=tk.X, pady=5)
        
        self.extract_status_label = ttk.Label(extract_progress_frame, text="就绪")
        self.extract_status_label.pack(anchor=tk.W)
        
        # 详细进度信息
        self.extract_detail_label = ttk.Label(extract_progress_frame, text="")
        self.extract_detail_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 提取日志
        extract_log_frame = ttk.LabelFrame(parent, text="提取日志", padding="15")
        extract_log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 日志过滤区域
        filter_frame = ttk.Frame(extract_log_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="过滤:").pack(side=tk.LEFT)
        self.log_filter_entry = ttk.Entry(filter_frame, width=30)
        self.log_filter_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(filter_frame, text="应用过滤", command=self.apply_log_filter).pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="清除过滤", command=self.clear_log_filter).pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志显示
        self.extract_log_text = tk.Text(extract_log_frame, height=15, wrap=tk.WORD)
        extract_scrollbar = ttk.Scrollbar(extract_log_frame, orient=tk.VERTICAL, command=self.extract_log_text.yview)
        self.extract_log_text.configure(yscrollcommand=extract_scrollbar.set)
        
        self.extract_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        extract_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 设置日志标签和颜色
        self.extract_log_text.tag_configure("DEBUG", foreground="gray")
        self.extract_log_text.tag_configure("INFO", foreground="black")
        self.extract_log_text.tag_configure("WARNING", foreground="orange")
        self.extract_log_text.tag_configure("ERROR", foreground="red")
        self.extract_log_text.tag_configure("SUCCESS", foreground="green")
    
    def setup_ocr_page(self, parent):
        """设置营业执照识别页面"""
        # OCR识别设置区域
        ocr_settings_frame = ttk.LabelFrame(parent, text="识别设置", padding="15")
        ocr_settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：识别数量和线程数设置
        settings_row1 = ttk.Frame(ocr_settings_frame)
        settings_row1.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_row1, text="识别数量:").pack(side=tk.LEFT)
        self.ocr_count_var = tk.StringVar(value="10")
        ocr_count_entry = ttk.Entry(settings_row1, textvariable=self.ocr_count_var, width=10)
        ocr_count_entry.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(settings_row1, text="OCR线程数:").pack(side=tk.LEFT)
        self.ocr_threads_var = tk.StringVar(value="3")
        ocr_threads_entry = ttk.Entry(settings_row1, textvariable=self.ocr_threads_var, width=10)
        ocr_threads_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # 按钮区域
        ocr_btn_frame = ttk.Frame(ocr_settings_frame)
        ocr_btn_frame.pack(fill=tk.X)
        
        self.ocr_recognize_btn = ttk.Button(ocr_btn_frame, text="一键识别营业执照", command=self.start_ocr_recognition)
        self.ocr_recognize_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_ocr_btn = ttk.Button(ocr_btn_frame, text="停止识别", command=self.stop_ocr_recognition, state=tk.DISABLED)
        self.stop_ocr_btn.pack(side=tk.LEFT)
        
        # 进度显示区域
        ocr_progress_frame = ttk.LabelFrame(parent, text="识别进度", padding="15")
        ocr_progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 进度条
        self.ocr_progress = ttk.Progressbar(ocr_progress_frame, mode='determinate')
        self.ocr_progress.pack(fill=tk.X, pady=(0, 5))
        
        # 状态标签
        self.ocr_status_label = ttk.Label(ocr_progress_frame, text="准备就绪")
        self.ocr_status_label.pack(anchor=tk.W)
        
        # 详细进度信息
        self.ocr_detail_label = ttk.Label(ocr_progress_frame, text="")
        self.ocr_detail_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 识别结果列表
        ocr_result_frame = ttk.LabelFrame(parent, text="识别结果列表", padding="15")
        ocr_result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 识别结果操作按钮
        ocr_result_btn_frame = ttk.Frame(ocr_result_frame)
        ocr_result_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(ocr_result_btn_frame, text="刷新列表", command=self.refresh_ocr_results).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(ocr_result_btn_frame, text="导出结果", command=self.export_ocr_results).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(ocr_result_btn_frame, text="批量导入缓存", command=self.batch_import_ocr_cache_to_db).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(ocr_result_btn_frame, text="清空结果", command=self.clear_ocr_results).pack(side=tk.LEFT)
        
        # 识别结果表格
        ocr_columns = ('序号', '公司名称', '统一社会信用代码', '法人', '公司地址', '省市区')
        self.ocr_result_tree = ttk.Treeview(ocr_result_frame, columns=ocr_columns, show='headings', height=8)
        
        # 设置列标题和宽度
        for col in ocr_columns:
            self.ocr_result_tree.heading(col, text=col)
            if col == '序号':
                self.ocr_result_tree.column(col, width=50, anchor=tk.CENTER)
            elif col == '公司名称':
                self.ocr_result_tree.column(col, width=200, anchor=tk.W)
            elif col == '统一社会信用代码':
                self.ocr_result_tree.column(col, width=150, anchor=tk.CENTER)
            elif col == '法人':
                self.ocr_result_tree.column(col, width=100, anchor=tk.CENTER)
            elif col == '公司地址':
                self.ocr_result_tree.column(col, width=250, anchor=tk.W)
            elif col == '省市区':
                self.ocr_result_tree.column(col, width=120, anchor=tk.CENTER)
            else:
                self.ocr_result_tree.column(col, width=100, anchor=tk.CENTER)
        
        # 添加滚动条
        ocr_result_scrollbar = ttk.Scrollbar(ocr_result_frame, orient=tk.VERTICAL, command=self.ocr_result_tree.yview)
        self.ocr_result_tree.configure(yscrollcommand=ocr_result_scrollbar.set)
        
        self.ocr_result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ocr_result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # OCR识别日志
        ocr_log_frame = ttk.LabelFrame(parent, text="识别日志", padding="15")
        ocr_log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 日志过滤区域
        ocr_filter_frame = ttk.Frame(ocr_log_frame)
        ocr_filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(ocr_filter_frame, text="过滤:").pack(side=tk.LEFT)
        self.ocr_log_filter_entry = ttk.Entry(ocr_filter_frame, width=30)
        self.ocr_log_filter_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(ocr_filter_frame, text="应用过滤", command=self.apply_ocr_log_filter).pack(side=tk.LEFT)
        ttk.Button(ocr_filter_frame, text="清除过滤", command=self.clear_ocr_log_filter).pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志显示
        self.ocr_log_text = tk.Text(ocr_log_frame, height=15, wrap=tk.WORD)
        ocr_log_scrollbar = ttk.Scrollbar(ocr_log_frame, orient=tk.VERTICAL, command=self.ocr_log_text.yview)
        self.ocr_log_text.configure(yscrollcommand=ocr_log_scrollbar.set)
        
        self.ocr_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ocr_log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 设置日志标签和颜色
        self.ocr_log_text.tag_configure("DEBUG", foreground="gray")
        self.ocr_log_text.tag_configure("INFO", foreground="black")
        self.ocr_log_text.tag_configure("WARNING", foreground="orange")
        self.ocr_log_text.tag_configure("ERROR", foreground="red")
        self.ocr_log_text.tag_configure("SUCCESS", foreground="green")
    
    def setup_proxy_page(self, parent):
        """设置代理配置页面"""
        # 当前代理信息
        current_proxy_frame = ttk.LabelFrame(parent, text="当前代理", padding="15")
        current_proxy_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_proxy_label = ttk.Label(current_proxy_frame, text="未设置代理")
        self.current_proxy_label.pack()
        
        # 代理配置
        proxy_config_frame = ttk.LabelFrame(parent, text="代理配置", padding="15")
        proxy_config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 主机
        ttk.Label(proxy_config_frame, text="主机:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_host_entry = ttk.Entry(proxy_config_frame, width=30)
        self.proxy_host_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 端口
        ttk.Label(proxy_config_frame, text="端口:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.proxy_port_entry = ttk.Entry(proxy_config_frame, width=30)
        self.proxy_port_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 用户名
        ttk.Label(proxy_config_frame, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.proxy_username_entry = ttk.Entry(proxy_config_frame, width=30)
        self.proxy_username_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 密码
        ttk.Label(proxy_config_frame, text="密码:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.proxy_password_entry = ttk.Entry(proxy_config_frame, width=30, show="*")
        self.proxy_password_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 按钮
        proxy_btn_frame = ttk.Frame(proxy_config_frame)
        proxy_btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(proxy_btn_frame, text="保存代理", command=self.save_proxy).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(proxy_btn_frame, text="测试连接", command=self.test_current_proxy).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(proxy_btn_frame, text="代理管理", command=self.switch_proxy).pack(side=tk.LEFT)
        
        # 配置网格权重
        proxy_config_frame.columnconfigure(1, weight=1)
        
        # 初始化代理配置
        self.load_proxy_config()
    
    def setup_db_list_page(self, parent):
        """设置数据库列表页面"""
        # 顶部控制区域
        control_frame = ttk.LabelFrame(parent, text="数据库操作", padding="15")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 统计信息Label
        self.db_list_stats_label = ttk.Label(control_frame, text="")
        self.db_list_stats_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 数据库操作按钮
        db_btn_frame = ttk.Frame(control_frame)
        db_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(db_btn_frame, text="刷新列表", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(db_btn_frame, text="清空数据库", command=self.clear_database).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(db_btn_frame, text="导出选中", command=self.export_selected_suppliers).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(db_btn_frame, text="导出全部", command=self.export_all_suppliers).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(db_btn_frame, text="自动识别本地文件", command=self.auto_recognize_local_files).pack(side=tk.LEFT, padx=(0, 10))
        
        # 搜索框
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_frame, text="搜索", command=self.search_suppliers).pack(side=tk.LEFT)
        
        # Tab切换
        tab_frame = ttk.Frame(control_frame)
        tab_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.db_list_tab_var = tk.StringVar(value="all")
        ttk.Radiobutton(tab_frame, text="全部", variable=self.db_list_tab_var, value="all", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="已成功", variable=self.db_list_tab_var, value="success", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="未提取", variable=self.db_list_tab_var, value="pending", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="已识别", variable=self.db_list_tab_var, value="recognized", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="已使用", variable=self.db_list_tab_var, value="used", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="未使用", variable=self.db_list_tab_var, value="unused", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="问题数据", variable=self.db_list_tab_var, value="problematic", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(tab_frame, text="识别错误", variable=self.db_list_tab_var, value="ocr_error", command=self.refresh_db_list_page).pack(side=tk.LEFT, padx=(0, 10))
        
        # 数据库列表
        list_frame = ttk.LabelFrame(parent, text="供应商列表", padding="15")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表
        columns = ('序号', '店铺名称', 'Action URL', '分类', '执照状态', '识别状态', '使用状态')
        self.db_list_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.db_list_tree.heading(col, text=col)
            self.db_list_tree.column(col, width=150)
        
        self.db_list_tree.column('店铺名称', width=250)
        self.db_list_tree.column('Action URL', width=350)
        self.db_list_tree.column('分类', width=150)
        self.db_list_tree.column('执照状态', width=100)
        self.db_list_tree.column('识别状态', width=100)
        self.db_list_tree.column('使用状态', width=100)
        
        self.db_list_tree.pack(fill=tk.BOTH, expand=True)
        
        # 分页控件
        pagination_frame = ttk.Frame(list_frame)
        pagination_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 分页信息和控件
        self.current_page = 1
        self.page_size = 100
        self.total_pages = 1
        
        # 左侧分页信息
        self.pagination_info_label = ttk.Label(pagination_frame, text="")
        self.pagination_info_label.pack(side=tk.LEFT)
        
        # 右侧分页控件
        pagination_controls = ttk.Frame(pagination_frame)
        pagination_controls.pack(side=tk.RIGHT)
        
        ttk.Button(pagination_controls, text="首页", command=self.go_to_first_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_controls, text="上一页", command=self.go_to_prev_page).pack(side=tk.LEFT, padx=(0, 5))
        
        # 页码输入框
        ttk.Label(pagination_controls, text="第").pack(side=tk.LEFT, padx=(5, 0))
        self.page_entry = ttk.Entry(pagination_controls, width=5)
        self.page_entry.pack(side=tk.LEFT, padx=(2, 2))
        self.page_entry.bind('<Return>', self.go_to_page)
        ttk.Label(pagination_controls, text="页").pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(pagination_controls, text="下一页", command=self.go_to_next_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_controls, text="末页", command=self.go_to_last_page).pack(side=tk.LEFT, padx=(0, 5))
        
        # 每页显示数量选择
        ttk.Label(pagination_controls, text="每页").pack(side=tk.LEFT, padx=(10, 2))
        self.page_size_var = tk.StringVar(value="100")
        page_size_combo = ttk.Combobox(pagination_controls, textvariable=self.page_size_var, values=["50", "100", "200", "500"], width=5, state="readonly")
        page_size_combo.pack(side=tk.LEFT, padx=(0, 2))
        page_size_combo.bind('<<ComboboxSelected>>', self.on_page_size_changed)
        ttk.Label(pagination_controls, text="条").pack(side=tk.LEFT)
        
        # 添加右键菜单
        self.db_list_context_menu = tk.Menu(self.root, tearoff=0)
        self.db_list_context_menu.add_command(label="编辑", command=self.edit_selected_supplier)
        self.db_list_context_menu.add_command(label="删除", command=self.delete_selected_supplier)
        self.db_list_context_menu.add_separator()
        self.db_list_context_menu.add_command(label="标记为已使用", command=self.mark_supplier_as_used)
        self.db_list_context_menu.add_command(label="标记为未使用", command=self.mark_supplier_as_unused)
        self.db_list_context_menu.add_command(label="已使用", command=self.show_used_suppliers)
        self.db_list_context_menu.add_separator()
        self.db_list_context_menu.add_command(label="重置失败次数", command=self.reset_extraction_failures)
        self.db_list_context_menu.add_command(label="取消跳过标记", command=self.unmark_skip_extraction)
        self.db_list_context_menu.add_command(label="标记为跳过", command=self.mark_skip_extraction)
        self.db_list_context_menu.add_separator()
        self.db_list_context_menu.add_command(label="识别执照", command=self.recognize_selected_db_list)
        self.db_list_context_menu.add_command(label="浏览文件", command=self.browse_selected_db_list)
        self.db_list_context_menu.add_command(label="导出选中", command=self.export_selected_suppliers)
        self.db_list_context_menu.add_separator()
        self.db_list_context_menu.add_command(label="刷新", command=self.refresh_db_list_page)
        
        # 绑定右键菜单
        self.db_list_tree.bind("<Button-3>", self.show_db_list_context_menu)
        
        # 绑定双击事件
        self.db_list_tree.bind("<Double-1>", self.on_db_list_double_click)
        
        # 添加滚动条
        db_list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.db_list_tree.yview)
        db_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.db_list_tree.configure(yscrollcommand=db_list_scrollbar.set)
        
        # 初始化时刷新列表
        self.refresh_db_list_page()
    
    def show_db_list_context_menu(self, event):
        """显示数据库列表右键菜单"""
        try:
            # 选中右键点击的项
            item = self.db_list_tree.identify_row(event.y)
            if item:
                self.db_list_tree.selection_set(item)
                self.db_list_context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass
    
    def mark_supplier_as_used(self):
        """标记选中的供应商为已使用"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            for item in selected_items:
                item_values = self.db_list_tree.item(item)['values']
                company_name = item_values[1].replace('...', '')  # 移除截断标记
                
                # 根据公司名称更新使用状态
                cursor.execute('UPDATE suppliers SET is_used = 1 WHERE company_name LIKE ?', (f'%{company_name}%',))
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                self.log_message(f"已标记 {updated_count} 个供应商为已使用")
                self.refresh_db_list_page()  # 刷新列表显示
            else:
                messagebox.showwarning("提示", "未找到匹配的供应商")
                
        except Exception as e:
            self.log_message(f"标记供应商为已使用失败: {e}")
            messagebox.showerror("错误", f"标记失败: {e}")
    
    def mark_supplier_as_unused(self):
        """标记选中的供应商为未使用"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            for item in selected_items:
                item_values = self.db_list_tree.item(item)['values']
                company_name = item_values[1].replace('...', '')  # 移除截断标记
                
                # 根据公司名称更新使用状态
                cursor.execute('UPDATE suppliers SET is_used = 0 WHERE company_name LIKE ?', (f'%{company_name}%',))
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                self.log_message(f"已标记 {updated_count} 个供应商为未使用")
                self.refresh_db_list_page()  # 刷新列表显示
            else:
                messagebox.showwarning("提示", "未找到匹配的供应商")
                
        except Exception as e:
            self.log_message(f"标记供应商为未使用失败: {e}")
            messagebox.showerror("错误", f"标记失败: {e}")
    
    def go_to_first_page(self):
        """跳转到首页"""
        self.current_page = 1
        self.refresh_db_list_page()
    
    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_db_list_page()
    
    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_db_list_page()
    
    def go_to_last_page(self):
        """跳转到末页"""
        self.current_page = self.total_pages
        self.refresh_db_list_page()
    
    def go_to_page(self, event=None):
        """跳转到指定页面"""
        try:
            page = int(self.page_entry.get())
            if 1 <= page <= self.total_pages:
                self.current_page = page
                self.refresh_db_list_page()
            else:
                messagebox.showwarning("警告", f"页码必须在1到{self.total_pages}之间")
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的页码")
    
    def on_page_size_changed(self, event=None):
        """页面大小改变时的处理"""
        try:
            self.page_size = int(self.page_size_var.get())
            self.current_page = 1  # 重置到第一页
            self.refresh_db_list_page()
        except ValueError:
            pass
    
    def update_pagination_info(self, total_count):
        """更新分页信息"""
        self.total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        
        # 确保当前页不超过总页数
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        # 更新页码输入框
        self.page_entry.delete(0, tk.END)
        self.page_entry.insert(0, str(self.current_page))
        
        # 更新分页信息标签
        start_index = (self.current_page - 1) * self.page_size + 1
        end_index = min(self.current_page * self.page_size, total_count)
        
        if total_count == 0:
            info_text = "暂无数据"
        else:
            info_text = f"显示 {start_index}-{end_index} 条，共 {total_count} 条记录，第 {self.current_page}/{self.total_pages} 页"
        
        self.pagination_info_label.config(text=info_text)
    
    def show_used_suppliers(self):
        """显示已使用的供应商"""
        # 切换到"已使用"标签页
        self.db_list_tab_var.set("used")
        # 重置到第一页
        self.current_page = 1
        # 刷新列表
        self.refresh_db_list_page()
    
    def reset_extraction_failures(self):
        """重置选中供应商的失败次数"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个或多个供应商")
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            for item in selected_items:
                item_values = self.db_list_tree.item(item)['values']
                company_name = item_values[1].replace('...', '')  # 移除截断标记
                
                # 重置失败次数
                cursor.execute('''
                    UPDATE suppliers 
                    SET extraction_failed_count = 0,
                        last_extraction_attempt = NULL
                    WHERE company_name = ?
                ''', (company_name,))
                
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                messagebox.showinfo("成功", f"已重置 {updated_count} 个供应商的失败次数")
                self.refresh_db_list_page()
            else:
                messagebox.showwarning("提示", "没有找到匹配的供应商")
                
        except Exception as e:
            messagebox.showerror("错误", f"重置失败次数时出错: {e}")
    
    def unmark_skip_extraction(self):
        """取消选中供应商的跳过标记"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个或多个供应商")
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            for item in selected_items:
                item_values = self.db_list_tree.item(item)['values']
                company_name = item_values[1].replace('...', '')  # 移除截断标记
                
                # 取消跳过标记并重置失败次数
                cursor.execute('''
                    UPDATE suppliers 
                    SET skip_extraction = 0,
                        extraction_failed_count = 0,
                        last_extraction_attempt = NULL
                    WHERE company_name = ?
                ''', (company_name,))
                
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                messagebox.showinfo("成功", f"已取消 {updated_count} 个供应商的跳过标记")
                self.refresh_db_list_page()
            else:
                messagebox.showwarning("提示", "没有找到匹配的供应商")
                
        except Exception as e:
            messagebox.showerror("错误", f"取消跳过标记时出错: {e}")
    
    def mark_skip_extraction(self):
        """手动标记选中供应商为跳过提取"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个或多个供应商")
            return
        
        # 确认操作
        if not messagebox.askyesno("确认", "确定要将选中的供应商标记为跳过提取吗？\n这将使它们不再出现在一键获取执照的处理列表中。"):
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            for item in selected_items:
                item_values = self.db_list_tree.item(item)['values']
                company_name = item_values[1].replace('...', '')  # 移除截断标记
                
                # 标记为跳过
                cursor.execute('''
                    UPDATE suppliers 
                    SET skip_extraction = 1,
                        last_extraction_attempt = CURRENT_TIMESTAMP
                    WHERE company_name = ?
                ''', (company_name,))
                
                if cursor.rowcount > 0:
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                messagebox.showinfo("成功", f"已标记 {updated_count} 个供应商为跳过提取")
                self.refresh_db_list_page()
            else:
                messagebox.showwarning("提示", "没有找到匹配的供应商")
                
        except Exception as e:
            messagebox.showerror("错误", f"标记跳过时出错: {e}")
    
    def load_active_proxy(self):
        """从数据库加载当前活跃的代理配置"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT host, port, username, password FROM proxies WHERE is_active = 1 LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'host': result[0],
                    'port': result[1],
                    'username': result[2],
                    'password': result[3]
                }
            else:
                # 如果没有活跃代理，返回默认配置
                return {
                    'host': '127.0.0.1',
                    'port': 7890,
                    'username': '',
                    'password': ''
                }
        except Exception as e:
            print(f"加载代理配置失败: {e}")
            return {
                'host': '127.0.0.1',
                'port': 7890,
                'username': '',
                'password': ''
            }
    
    def get_all_proxies(self):
        """获取所有代理配置"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, host, port, username, password, is_active FROM proxies ORDER BY id')
            results = cursor.fetchall()
            conn.close()
            
            proxies = []
            for row in results:
                proxies.append({
                    'id': row[0],
                    'name': row[1],
                    'host': row[2],
                    'port': row[3],
                    'username': row[4],
                    'password': row[5],
                    'is_active': row[6]
                })
            return proxies
        except Exception as e:
            print(f"获取代理列表失败: {e}")
            return []
    
    def save_proxy_to_db(self, name, host, port, username, password, set_active=False):
        """保存代理配置到数据库"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 如果设置为活跃，先将其他代理设为非活跃
            if set_active:
                cursor.execute('UPDATE proxies SET is_active = 0')
            
            # 插入新代理
            cursor.execute('''
                INSERT INTO proxies (name, host, port, username, password, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, host, port, username, password, set_active))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存代理配置失败: {e}")
            return False
    
    def set_active_proxy(self, proxy_id):
        """设置指定代理为活跃状态"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 将所有代理设为非活跃
            cursor.execute('UPDATE proxies SET is_active = 0')
            
            # 设置指定代理为活跃
            cursor.execute('UPDATE proxies SET is_active = 1 WHERE id = ?', (proxy_id,))
            
            conn.commit()
            conn.close()
            
            # 重新加载当前代理配置
            self.proxy = self.load_active_proxy()
            self.load_proxy_config()
            return True
        except Exception as e:
            print(f"切换代理失败: {e}")
            return False
    
    def delete_proxy(self, proxy_id):
        """删除代理配置"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM proxies WHERE id = ?', (proxy_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除代理失败: {e}")
            return False
    
    def load_proxy_config(self):
        """加载代理配置"""
        self.proxy_host_entry.delete(0, tk.END)
        self.proxy_host_entry.insert(0, self.proxy['host'])
        
        self.proxy_port_entry.delete(0, tk.END)
        self.proxy_port_entry.insert(0, str(self.proxy['port']))
        
        self.proxy_username_entry.delete(0, tk.END)
        self.proxy_username_entry.insert(0, self.proxy['username'])
        
        self.proxy_password_entry.delete(0, tk.END)
        self.proxy_password_entry.insert(0, self.proxy['password'])
        
        self.update_current_proxy_display()
    
    def update_current_proxy_display(self):
        """更新当前代理显示"""
        self.current_proxy_label.config(
            text=f"当前代理: {self.proxy['host']}:{self.proxy['port']} ({self.proxy['username']})"
        )
    
    def save_proxy(self):
        """保存代理配置"""
        host = self.proxy_host_entry.get().strip()
        port = self.proxy_port_entry.get().strip()
        username = self.proxy_username_entry.get().strip()
        password = self.proxy_password_entry.get().strip()
        
        if not all([host, port]):
            messagebox.showerror("错误", "请至少填写主机和端口")
            return
        
        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
        
        # 弹出对话框让用户输入代理名称
        name_dialog = tk.Toplevel(self.root)
        name_dialog.title("保存代理")
        name_dialog.geometry("300x150")
        name_dialog.transient(self.root)
        name_dialog.grab_set()
        
        # 居中显示
        name_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        ttk.Label(name_dialog, text="请输入代理名称:").pack(pady=10)
        name_entry = ttk.Entry(name_dialog, width=30)
        name_entry.pack(pady=5)
        name_entry.insert(0, f"{host}:{port}")
        name_entry.focus()
        
        button_frame = ttk.Frame(name_dialog)
        button_frame.pack(pady=10)
        
        def save_and_close():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("错误", "请输入代理名称")
                return
            
            # 询问是否设为当前活跃代理
            set_active = messagebox.askyesno("设置活跃代理", "是否将此代理设为当前活跃代理？")
            
            if self.save_proxy_to_db(name, host, port, username, password, set_active):
                if set_active:
                    # 更新当前代理配置
                    self.proxy = {
                        'host': host,
                        'port': port,
                        'username': username,
                        'password': password
                    }
                    self.load_proxy_config()
                
                messagebox.showinfo("成功", "代理配置已保存")
                name_dialog.destroy()
            else:
                messagebox.showerror("错误", "保存代理配置失败")
        
        ttk.Button(button_frame, text="保存", command=save_and_close).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=name_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        name_entry.bind('<Return>', lambda e: save_and_close())
    
    def test_current_proxy(self):
        """测试当前代理连接"""
        def test():
            try:
                import requests
                
                # 使用HTTP代理格式
                proxies = {
                    'http': f"http://{self.proxy['username']}:{self.proxy['password']}@{self.proxy['host']}:{self.proxy['port']}",
                    'https': f"http://{self.proxy['username']}:{self.proxy['password']}@{self.proxy['host']}:{self.proxy['port']}"
                }
                
                response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
                if response.status_code == 200:
                    ip_info = response.json()
                    messagebox.showinfo("成功", f"代理连接成功\n当前IP: {ip_info.get('origin', '未知')}")
                else:
                    messagebox.showerror("失败", "代理连接失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"代理测试失败: {e}")
        
        # 在新线程中测试
        import threading
        thread = threading.Thread(target=test)
        thread.daemon = True
        thread.start()
    
    def switch_proxy(self):
        """代理管理界面"""
        # 创建代理管理对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("代理管理")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="代理管理", font=("Arial", 14, "bold")).pack(pady=(0, 10))
        
        # 代理列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview显示代理列表
        columns = ('ID', '名称', '主机', '端口', '用户名', '状态')
        self.proxy_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列标题和宽度
        self.proxy_tree.heading('ID', text='ID')
        self.proxy_tree.heading('名称', text='名称')
        self.proxy_tree.heading('主机', text='主机')
        self.proxy_tree.heading('端口', text='端口')
        self.proxy_tree.heading('用户名', text='用户名')
        self.proxy_tree.heading('状态', text='状态')
        
        self.proxy_tree.column('ID', width=50)
        self.proxy_tree.column('名称', width=120)
        self.proxy_tree.column('主机', width=150)
        self.proxy_tree.column('端口', width=80)
        self.proxy_tree.column('用户名', width=120)
        self.proxy_tree.column('状态', width=80)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proxy_tree.yview)
        self.proxy_tree.configure(yscrollcommand=scrollbar.set)
        
        self.proxy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="刷新列表", command=self.refresh_proxy_list).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="设为活跃", command=self.activate_selected_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除代理", command=self.delete_selected_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # 保存对话框引用
        self.proxy_dialog = dialog
        
        # 加载代理列表
        self.refresh_proxy_list()
    
    def refresh_proxy_list(self):
        """刷新代理列表"""
        # 清空现有项目
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        
        # 获取所有代理
        proxies = self.get_all_proxies()
        
        # 添加到树形视图
        for proxy in proxies:
            status = "活跃" if proxy['is_active'] else "非活跃"
            self.proxy_tree.insert('', 'end', values=(
                proxy['id'],
                proxy['name'],
                proxy['host'],
                proxy['port'],
                proxy['username'],
                status
            ))
    
    def activate_selected_proxy(self):
        """激活选中的代理"""
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = self.proxy_tree.item(selection[0])
        proxy_id = item['values'][0]
        proxy_name = item['values'][1]
        
        if messagebox.askyesno("确认", f"确定要激活代理 '{proxy_name}' 吗？"):
            if self.set_active_proxy(proxy_id):
                messagebox.showinfo("成功", f"代理 '{proxy_name}' 已激活")
                self.refresh_proxy_list()
                self.update_current_proxy_display()
            else:
                messagebox.showerror("错误", "激活代理失败")
    
    def delete_selected_proxy(self):
        """删除选中的代理"""
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = self.proxy_tree.item(selection[0])
        proxy_id = item['values'][0]
        proxy_name = item['values'][1]
        is_active = item['values'][5] == "活跃"
        
        if is_active:
            messagebox.showwarning("警告", "不能删除当前活跃的代理")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除代理 '{proxy_name}' 吗？\n此操作不可撤销。"):
            if self.delete_proxy(proxy_id):
                messagebox.showinfo("成功", f"代理 '{proxy_name}' 已删除")
                self.refresh_proxy_list()
            else:
                messagebox.showerror("错误", "删除代理失败")
    

    
    def refresh_db_list(self):
        """刷新数据库列表"""
        try:
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 检查表结构，确保有必要的字段
            try:
                cursor.execute("PRAGMA table_info(suppliers)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # 如果缺少license_extracted字段，添加它
                if 'license_extracted' not in columns:
                    self.log_message("添加license_extracted字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN license_extracted BOOLEAN DEFAULT FALSE')
                    conn.commit()
                
                # 如果缺少category_id或category_name字段，添加它们
                if 'category_id' not in columns:
                    self.log_message("添加category_id字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN category_id TEXT')
                    conn.commit()
                
                if 'category_name' not in columns:
                    self.log_message("添加category_name字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN category_name TEXT')
                    conn.commit()
                
                # 如果缺少is_used字段，添加它
                if 'is_used' not in columns:
                    self.log_message("添加is_used字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN is_used BOOLEAN DEFAULT FALSE')
                    conn.commit()
            except Exception as e:
                self.log_message(f"检查表结构时出错: {e}")
            
            # 根据Tab选择查询条件
            tab_filter = self.db_list_tab_var.get()
            
            # 构建基本查询
            base_query = "SELECT id, company_name, action_url"
            
            # 根据表结构添加字段
            if 'license_extracted' in columns:
                base_query += ", license_extracted"
            else:
                base_query += ", 0 as license_extracted"
                
            if 'category_id' in columns:
                base_query += ", category_id"
            else:
                base_query += ", '' as category_id"
                
            if 'category_name' in columns:
                base_query += ", category_name"
            else:
                base_query += ", '' as category_name"
                
            if 'is_used' in columns:
                base_query += ", is_used"
            else:
                base_query += ", 0 as is_used"
            
            base_query += " FROM suppliers"
            
            # 添加过滤条件
            if tab_filter == "success":
                query = f"{base_query} WHERE license_extracted = 1 ORDER BY created_at DESC"
            elif tab_filter == "pending":
                query = f"{base_query} WHERE license_extracted = 0 OR license_extracted IS NULL ORDER BY created_at DESC"
            else:
                query = f"{base_query} ORDER BY created_at DESC"
            
            # 执行查询
            self.log_message(f"执行查询: {query}")
            cursor.execute(query)
            suppliers = cursor.fetchall()
            
            # 统计各种状态的数量（基于总数据，不是当前页）
            try:
                # 统计总数
                cursor.execute("SELECT COUNT(*) FROM suppliers")
                all_count = cursor.fetchone()[0]
                
                # 统计已成功数量
                cursor.execute("SELECT COUNT(*) FROM suppliers WHERE license_extracted = 1")
                success_count = cursor.fetchone()[0]
                
                # 统计未提取数量
                cursor.execute("SELECT COUNT(*) FROM suppliers WHERE license_extracted = 0 OR license_extracted IS NULL")
                fail_count = cursor.fetchone()[0]
                
                # 统计已使用数量
                cursor.execute("SELECT COUNT(*) FROM suppliers WHERE is_used = 1")
                used_count = cursor.fetchone()[0]
                
                # 统计未使用数量
                cursor.execute("SELECT COUNT(*) FROM suppliers WHERE is_used = 0 OR is_used IS NULL")
                unused_count = cursor.fetchone()[0]
                
                self.db_list_stats_label.config(text=f"总数: {all_count}，已成功: {success_count}，未提取: {fail_count}，已使用: {used_count}，未使用: {unused_count}")
            except Exception as e:
                self.log_message(f"统计数量时出错: {e}")
                self.db_list_stats_label.config(text=f"当前页显示: {len(suppliers)} 条记录")
            
            conn.close()
            
            self.log_message(f"数据库列表已刷新，共 {len(suppliers)} 个供应商")
            
        except Exception as e:
            self.log_message(f"刷新数据库列表失败: {e}")
            import traceback
            self.log_message(f"详细错误: {traceback.format_exc()}")
    
    def clear_database(self):
        """清空数据库"""
        try:
            # 确认对话框
            result = messagebox.askyesno("确认", "确定要清空数据库吗？此操作不可恢复！")
            if not result:
                return
            
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 清空所有表
            cursor.execute('DELETE FROM suppliers')
            cursor.execute('DELETE FROM licenses')
            cursor.execute('DELETE FROM license_info')
            
            conn.commit()
            conn.close()
            
            # 刷新列表
            self.refresh_db_list()
            
            self.log_message("数据库已清空")
            messagebox.showinfo("完成", "数据库已清空")
            
        except Exception as e:
            self.log_message(f"清空数据库失败: {e}")
            messagebox.showerror("错误", f"清空数据库失败: {e}")
    
    def browse_save_path(self):
        """浏览保存路径"""
        path = filedialog.askdirectory()
        if path:
            self.save_path_var.set(path)
    
    def browse_supplier_files(self):
        """浏览供应商文件"""
        try:
            # 获取当前选中的项目
            selected_item = self.db_list_tree.selection()
            if not selected_item:
                messagebox.showwarning("提示", "请先选择一个供应商")
                return
            
            # 获取供应商信息
            item_values = self.db_list_tree.item(selected_item[0])['values']
            company_name = item_values[1]  # 店铺名称
            
            # 从数据库获取供应商的保存路径
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT save_path FROM suppliers WHERE company_name = ?', (company_name,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                # 使用数据库中存储的保存路径
                folder_path = result[0]
                
                # 如果是相对路径，转换为绝对路径
                if not os.path.isabs(folder_path):
                    folder_path = os.path.abspath(folder_path)
                
                if os.path.exists(folder_path):
                    import subprocess
                    import platform
                    
                    if platform.system() == "Windows":
                        subprocess.run(['explorer', folder_path])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', folder_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', folder_path])
                    
                    self.log_message(f"已打开文件夹: {folder_path}")
                else:
                    messagebox.showinfo("提示", f"该供应商的文件还未保存到本地\n路径: {folder_path}")
            else:
                messagebox.showinfo("提示", "该供应商还没有保存路径信息")
                
        except Exception as e:
            self.log_message(f"浏览文件时出错: {e}")
            messagebox.showerror("错误", f"浏览文件失败: {e}")
    
    def start_crawl(self):
        """开始爬取"""
        search_type = self.search_type_var.get()
        start_page = self.start_page_var.get().strip()
        end_page = self.end_page_var.get().strip()
        
        try:
            start_page = int(start_page)
            end_page = int(end_page)
            if start_page <= 0 or end_page <= 0:
                messagebox.showerror("错误", "页面范围必须大于0")
                return
            if start_page > end_page:
                messagebox.showerror("错误", "起始页面不能大于结束页面")
                return
        except ValueError:
            messagebox.showerror("错误", "页面范围必须是数字")
            return
        
        # 页面爬取不使用并发设置
        
        # 获取当前代理
        proxy = None
        if self.use_proxy_var.get():
            proxy = self.proxy
        
        # 页面爬取使用默认设置
        
        self.start_crawl_btn.config(state=tk.DISABLED)
        self.stop_crawl_btn.config(state=tk.NORMAL)
        
        # 清空日志并添加开始信息
        self.crawl_log_text.delete("1.0", tk.END)
        
        # 获取跳过重复选项
        skip_duplicates = self.skip_duplicates_var.get()
        
        # 在新线程中运行爬虫
        def run_crawl():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if search_type == "keyword":
                    # 关键词搜索
                    keyword = self.keyword_entry.get().strip()
                    if not keyword:
                        self.root.after(0, lambda: messagebox.showerror("错误", "请输入搜索关键词"))
                        return
                    
                    self.root.after(0, lambda: self.log_crawl_message(f"开始获取供应商，关键词: {keyword}，页面范围: {start_page}-{end_page}", "INFO"))
                    
                    # 创建进度更新函数
                    def update_progress(current_page, total_pages, detail=""):
                        progress = ((current_page - start_page) / (total_pages - start_page + 1)) * 100
                        self.root.after(0, lambda p=progress, c=current_page, t=total_pages, d=detail: (
                            self.progress.configure(value=p), 
                            self.status_label.config(text=f"进度: {c}/{t} 页 ({p:.1f}%)"),
                            self.crawl_detail_label.config(text=d)
                        ))
                    
                    # 修改爬虫方法以支持进度回调
                    async def crawl_with_progress():
                        # 直接调用爬虫类的完整方法，处理整个页面范围
                        self.root.after(0, lambda: self.log_crawl_message(f"开始爬取关键词: {keyword}，页面范围: {start_page}-{end_page}", "INFO"))
                        
                        try:
                            # 记录代理信息
                            if proxy:
                                self.root.after(0, lambda: self.log_proxy_info(proxy['host'], proxy['port']))
                            
                            # 记录请求开始时间
                            start_time = datetime.now()
                            
                            # 创建日志回调函数
                            def log_callback(message, level="INFO"):
                                self.root.after(0, lambda m=message, l=level: self.log_crawl_message(m, l))
                            
                            # 直接调用爬虫类的完整方法
                            suppliers = await self.crawler.crawl_suppliers_range(keyword, start_page, end_page, proxy, skip_duplicates=skip_duplicates, log_callback=log_callback)
                            
                            # 计算请求耗时
                            duration = (datetime.now() - start_time).total_seconds()
                            
                            # 记录数据提取信息
                            self.root.after(0, lambda s=len(suppliers): self.log_data_extraction("供应商", s, f"关键词'{keyword}'"))
                            
                            # 记录每个供应商的详细信息
                            for supplier in suppliers:
                                company_name = supplier.get('company_name', 'Unknown')
                                action_url = supplier.get('action_url', '')
                                country_code = supplier.get('country_code', '')
                                
                                self.root.after(0, lambda n=company_name, u=action_url, c=country_code: 
                                    self.log_supplier_info(n, u, c))
                            
                            self.root.after(0, lambda s=len(suppliers): self.log_crawl_message(f"爬取完成，共获取到 {s} 个供应商", "SUCCESS"))
                            update_progress(end_page, end_page, f"爬取完成，获取到 {len(suppliers)} 个供应商")
                            
                            return suppliers
                            
                        except Exception as e:
                            error_msg = str(e)
                            self.root.after(0, lambda e=error_msg: self.log_error("爬取失败", e, f"关键词'{keyword}'"))
                            self.root.after(0, lambda e=error_msg: self.log_crawl_message(f"爬取失败: {e}", "ERROR"))
                            return []
                    
                    suppliers = loop.run_until_complete(crawl_with_progress())
                    
                else:
                    # 分类搜索
                    category_id = self.get_selected_category_id()
                    if not category_id:
                        self.root.after(0, lambda: messagebox.showerror("错误", "请选择分类"))
                        return
                    
                    # 获取保存路径
                    save_path = self.save_path_var.get().strip() if hasattr(self, 'save_path_var') else "./license_files"
                    
                    self.root.after(0, lambda: self.log_crawl_message(f"开始获取供应商，分类ID: {category_id}，页面范围: {start_page}-{end_page}", "INFO"))
                    
                    # 创建进度更新函数
                    def update_progress(current_page, total_pages, detail=""):
                        progress = ((current_page - start_page) / (total_pages - start_page + 1)) * 100
                        self.root.after(0, lambda p=progress, c=current_page, t=total_pages, d=detail: (
                            self.progress.configure(value=p), 
                            self.status_label.config(text=f"进度: {c}/{t} 页 ({p:.1f}%)"),
                            self.crawl_detail_label.config(text=d)
                        ))
                    
                    # 修改爬虫方法以支持进度回调
                    async def crawl_category_with_progress():
                        # 直接调用爬虫类的完整方法，处理整个页面范围
                        self.root.after(0, lambda: self.log_crawl_message(f"开始爬取分类: {category_id}，页面范围: {start_page}-{end_page}", "INFO"))
                        
                        try:
                            # 记录代理信息
                            if proxy:
                                self.root.after(0, lambda: self.log_proxy_info(proxy['host'], proxy['port']))
                            
                            # 记录请求开始时间
                            start_time = datetime.now()
                            
                            # 创建日志回调函数
                            def log_callback(message, level="INFO"):
                                self.root.after(0, lambda m=message, l=level: self.log_crawl_message(m, l))
                            
                            # 直接调用爬虫类的完整方法
                            suppliers = await self.crawler.crawl_suppliers_by_category(category_id, start_page, end_page, proxy, skip_duplicates=skip_duplicates, save_path=save_path, log_callback=log_callback)
                            
                            # 计算请求耗时
                            duration = (datetime.now() - start_time).total_seconds()
                            
                            # 记录数据提取信息
                            self.root.after(0, lambda s=len(suppliers): self.log_data_extraction("供应商", s, f"分类{category_id}"))
                            
                            # 记录每个供应商的详细信息
                            for supplier in suppliers:
                                company_name = supplier.get('company_name', 'Unknown')
                                action_url = supplier.get('action_url', '')
                                country_code = supplier.get('country_code', '')
                                
                                self.root.after(0, lambda n=company_name, u=action_url, c=country_code: 
                                    self.log_supplier_info(n, u, c))
                            
                            self.root.after(0, lambda s=len(suppliers): self.log_crawl_message(f"爬取完成，共获取到 {s} 个供应商", "SUCCESS"))
                            update_progress(end_page, end_page, f"爬取完成，获取到 {len(suppliers)} 个供应商")
                            
                            return suppliers
                            
                        except Exception as e:
                            error_msg = str(e)
                            self.root.after(0, lambda e=error_msg: self.log_error("爬取失败", e, f"分类{category_id}"))
                            self.root.after(0, lambda e=error_msg: self.log_crawl_message(f"爬取失败: {e}", "ERROR"))
                            return []
                    
                    suppliers = loop.run_until_complete(crawl_category_with_progress())
                
                self.root.after(0, lambda: self.crawl_finished(suppliers))
                
            except Exception as e:
                self.root.after(0, lambda: self.crawl_error(str(e)))
        
        threading.Thread(target=run_crawl, daemon=True).start()
    
    def stop_crawl(self):
        """停止爬取"""
        self.start_crawl_btn.config(state=tk.NORMAL)
        self.stop_crawl_btn.config(state=tk.DISABLED)
        self.log_message("爬取已停止")
    
    def crawl_finished(self, suppliers):
        """爬取完成"""
        self.start_crawl_btn.config(state=tk.NORMAL)
        self.stop_crawl_btn.config(state=tk.DISABLED)
        self.log_message(f"爬取完成，获取到 {len(suppliers)} 个供应商")
        
        # 刷新数据库列表
        self.refresh_db_list()
        
        messagebox.showinfo("完成", f"成功获取 {len(suppliers)} 个供应商")
    
    def crawl_error(self, error):
        """爬取错误"""
        self.start_crawl_btn.config(state=tk.NORMAL)
        self.stop_crawl_btn.config(state=tk.DISABLED)
        self.log_message(f"爬取失败: {error}")
        messagebox.showerror("错误", f"爬取失败: {error}")
    
    def extract_all_licenses(self):
        """一键获取所有执照"""
        # 检查保存路径
        save_path = self.save_path_var.get().strip()
        if not save_path:
            messagebox.showerror("错误", "请设置保存路径")
            return
        
        # 创建保存目录
        os.makedirs(save_path, exist_ok=True)
        
        # 获取并发设置
        try:
            thread_count = int(self.thread_count_var.get())
            if thread_count <= 0:
                messagebox.showerror("错误", "并发线程数必须大于0")
                return
            elif thread_count > 20:
                if not messagebox.askyesno("警告", f"设置了较高的并发线程数({thread_count})，可能会导致IP被封禁。是否继续？"):
                    return
        except ValueError:
            messagebox.showerror("错误", "并发线程数必须是整数")
            return
        
        # 获取批次间隔
        try:
            batch_delay = float(self.batch_delay_var.get())
            if batch_delay < 0:
                messagebox.showerror("错误", "批次间隔不能为负数")
                return
        except ValueError:
            messagebox.showerror("错误", "批次间隔必须是数字")
            return
        
        # 获取IP检测设置
        enable_ip_check = self.enable_ip_check_var.get()
        
        self.extract_all_btn.config(state=tk.DISABLED)
        self.stop_extract_btn.config(state=tk.NORMAL)
        
        # 清空日志并添加开始信息
        self.extract_log_text.delete("1.0", tk.END)
        self.log_extract_message(f"开始提取执照，保存路径: {save_path}", "INFO")
        self.log_extract_message(f"并发线程数: {thread_count}, 批次间隔: {batch_delay}秒, IP检测: {'启用' if enable_ip_check else '禁用'}", "INFO")
        
        # 在新线程中运行提取
        def run_extract():
            try:
                self.extract_licenses_with_retry(save_path, thread_count, batch_delay, enable_ip_check)
                self.root.after(0, lambda: self.extract_finished())
            except Exception as e:
                self.root.after(0, lambda: self.extract_error(str(e)))
        
        threading.Thread(target=run_extract, daemon=True).start()
    
    def extract_licenses_with_retry(self, save_path, thread_count=5, batch_delay=1.0, enable_ip_check=True):
        """提取执照（只提取未提取的供应商）"""
        # 获取所有未提取的供应商
        conn = sqlite3.connect(self.crawler.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT company_id, company_name, action_url 
                FROM suppliers 
                WHERE (license_extracted = 0 OR license_extracted IS NULL)
                  AND (skip_extraction = 0 OR skip_extraction IS NULL)
            ''')
            suppliers = cursor.fetchall()
        except Exception as e:
            # 兼容旧表结构
            self.log_extract_message(f"查询失败，尝试兼容查询: {e}", "WARNING")
            cursor.execute('SELECT company_id, company_name, action_url FROM suppliers')
            suppliers = cursor.fetchall()
        conn.close()
        
        if not suppliers:
            self.log_extract_message("没有找到未提取的供应商数据", "WARNING")
            return
        
        total_suppliers = len(suppliers)
        self.log_extract_message(f"找到 {total_suppliers} 个未提取的供应商", "INFO")
        
        # 使用异步并发处理
        def run_concurrent_extract():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 创建进度更新函数
                def update_progress(current, total, detail=""):
                    progress = (current / total) * 100
                    self.root.after(0, lambda p=progress, c=current, t=total: (
                        self.extract_progress.configure(value=p), 
                        self.extract_status_label.config(text=f"进度: {c}/{t} ({p:.1f}%)"),
                        self.extract_detail_label.config(text=detail)
                    ))
                
                # 重写crawler的extract_licenses_from_database方法以支持进度回调
                async def extract_with_progress():
                    try:
                        # 获取数据库中的所有未提取供应商
                        conn = sqlite3.connect(self.crawler.db_path)
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT company_id, company_name, action_url 
                            FROM suppliers 
                            WHERE (license_extracted = 0 OR license_extracted IS NULL)
                              AND (skip_extraction = 0 OR skip_extraction IS NULL)
                            ORDER BY created_at DESC
                        ''')
                        suppliers = cursor.fetchall()
                        conn.close()
                        
                        if not suppliers:
                            self.root.after(0, lambda: self.log_extract_message("没有未提取的供应商数据", "WARNING"))
                            return 0
                        
                        self.root.after(0, lambda: self.log_extract_message(f"从数据库获取到 {len(suppliers)} 个未提取供应商，使用{thread_count}个并发线程处理", "INFO"))
                        
                        # 创建异步会话
                        connector = aiohttp.TCPConnector(limit=thread_count * 4)  # 连接限制为线程数的4倍
                        timeout = aiohttp.ClientTimeout(total=15)
                        
                        processed_count = 0
                        success_count = 0
                        failed_count = 0
                        successfully_extracted_ids = []  # 记录成功提取的供应商ID
                        
                        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                            # 将供应商分成指定数量一组
                            batch_size = thread_count
                            for i in range(0, len(suppliers), batch_size):
                                batch = suppliers[i:i + batch_size]
                                batch_num = i//batch_size + 1
                                total_batches = (len(suppliers) + batch_size - 1)//batch_size
                                batch_info = f"处理批次 {batch_num}/{total_batches}: {len(batch)} 个供应商"
                                self.root.after(0, lambda m=batch_info: self.log_extract_message(m, "INFO"))
                                
                                # 更新进度
                                update_progress(i, len(suppliers), f"批次 {batch_num}/{total_batches}")
                                
                                # 创建并发任务
                                tasks = []
                                for company_id, company_name, action_url in batch:
                                    # 根据IP检测设置调用不同的方法
                                    if enable_ip_check:
                                        task = self.crawler.process_single_supplier(company_id, company_name, action_url, self.proxy, session)
                                    else:
                                        # 如果禁用IP检测，使用自定义的process_single_supplier_no_ip_check
                                        task = self.process_single_supplier_no_ip_check(company_id, company_name, action_url, self.proxy, session)
                                    tasks.append(task)
                                
                                # 并发执行，不等待所有任务完成
                                running_tasks = []
                                for task in tasks:
                                    running_tasks.append(asyncio.create_task(task))
                                
                                # 等待当前批次的任务完成（不阻塞下一批）
                                for idx, task in enumerate(running_tasks):
                                    try:
                                        result = await task
                                        processed_count += 1
                                        if result:
                                            success_count += 1
                                            # 记录成功提取的供应商ID
                                            company_id = batch[idx][0]  # batch中的第一个元素是company_id
                                            successfully_extracted_ids.append(company_id)
                                            company_name = batch[idx][1]  # 获取公司名称
                                            self.root.after(0, lambda cn=company_name: self.log_extract_message(f"✓ 成功处理: {cn} ({processed_count}/{len(suppliers)})", "SUCCESS"))
                                        else:
                                            failed_count += 1
                                            company_name = batch[idx][1]  # 获取公司名称
                                            self.root.after(0, lambda cn=company_name: self.log_extract_message(f"✗ 处理失败: {cn} ({processed_count}/{len(suppliers)}) - 可能原因: 页面无法访问或未找到执照信息", "ERROR"))
                                    except Exception as e:
                                        failed_count += 1
                                        company_name = batch[idx][1] if idx < len(batch) else "未知供应商"
                                        error_msg = str(e)
                                        self.root.after(0, lambda cn=company_name, m=error_msg: self.log_extract_message(f"✗ 处理异常: {cn} - 错误: {m}", "ERROR"))
                                
                                # 更新进度
                                current_processed = min(i + batch_size, len(suppliers))
                                update_progress(current_processed, len(suppliers), f"批次 {batch_num}/{total_batches} 完成")
                                
                                # 批次间延迟（使用手动设置）
                                if i + batch_size < len(suppliers):
                                    self.root.after(0, lambda d=batch_delay: self.log_extract_message(f"批次间等待 {d:.1f} 秒...", "DEBUG"))
                                    await asyncio.sleep(batch_delay)
                        
                        # 最终进度更新
                        update_progress(len(suppliers), len(suppliers), "处理完成")
                        
                        done_msg = f"执照图片提取完成，成功: {success_count}，失败: {failed_count}，总计: {processed_count}"
                        self.root.after(0, lambda m=done_msg: self.log_extract_message(m, "INFO"))
                        return successfully_extracted_ids  # 返回成功提取的供应商ID列表
                        
                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda m=error_msg: self.log_extract_message(f"从数据库提取执照图片时出错: {m}", "ERROR"))
                        return 0
                
                # 运行带进度更新的提取
                successfully_extracted_ids = loop.run_until_complete(extract_with_progress())
                
                # 提取完成后，只保存本次提取的执照信息到本地文件
                if successfully_extracted_ids:
                    self.save_extracted_licenses_to_files(save_path, successfully_extracted_ids)
                else:
                    self.root.after(0, lambda: self.log_extract_message("没有成功提取的供应商，跳过文件保存", "INFO"))
                
                # 完成后更新状态
                self.root.after(0, lambda: self.extract_progress.configure(value=100))
                self.root.after(0, lambda: self.extract_status_label.config(text="提取完成"))
                done_msg = f"并发提取完成: 成功处理 {len(successfully_extracted_ids) if successfully_extracted_ids else 0} 个供应商"
                self.root.after(0, lambda m=done_msg: self.log_extract_message(m, "SUCCESS"))
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda m=error_msg: self.log_extract_message(f"并发提取失败: {m}", "ERROR"))
        
        # 在新线程中运行并发提取
        thread = threading.Thread(target=run_concurrent_extract, daemon=True)
        thread.start()
    
    async def process_single_supplier_no_ip_check(self, company_id, company_name, action_url, proxy, session):
        """处理单个供应商（禁用IP检测）"""
        try:
            self.root.after(0, lambda: self.log_extract_message(f"开始处理: {company_name}", "INFO"))
            
            # 创建日志回调函数
            def log_callback(message, level="INFO"):
                self.root.after(0, lambda: self.log_extract_message(message, level))
            
            # 获取供应商页面HTML（禁用IP检测）
            html_content = await self.crawler.fetch_supplier_page(action_url, proxy, session, check_ip=False, log_callback=log_callback)
            
            if html_content:
                self.root.after(0, lambda: self.log_extract_message(f"  - {company_name}: 成功获取页面", "SUCCESS"))
                
                # 提取执照图片
                licenses = await self.crawler.extract_licenses_from_html(html_content)
                
                # 提取执照信息
                license_info = self.crawler.extract_license_info_from_html(html_content)
                
                # 保存到数据库
                conn = sqlite3.connect(self.crawler.db_path)
                cursor = conn.cursor()
                
                # 先删除该供应商的旧记录
                cursor.execute('DELETE FROM licenses WHERE supplier_id = ?', (company_id,))
                cursor.execute('DELETE FROM license_info WHERE supplier_id = ?', (company_id,))
                
                # 保存执照图片
                if licenses:
                    for license_item in licenses:
                        cursor.execute('''
                            INSERT INTO licenses (supplier_id, license_name, license_url, file_id)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            company_id,
                            license_item['name'],
                            license_item['url'],
                            license_item['fileId']
                        ))
                    print(f"  - {company_name}: 找到 {len(licenses)} 个执照图片")
                
                # 保存执照信息
                if license_info:
                    cursor.execute('''
                        INSERT INTO license_info (
                            supplier_id, registration_no, company_name, date_of_issue, 
                            date_of_expiry, registered_capital, country_territory, 
                            registered_address, year_established, legal_form, legal_representative
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        company_id,
                        license_info.get('registration_no', ''),
                        license_info.get('company_name', ''),
                        license_info.get('date_of_issue', ''),
                        license_info.get('date_of_expiry', ''),
                        license_info.get('registered_capital', ''),
                        license_info.get('country_territory', ''),
                        license_info.get('registered_address', ''),
                        license_info.get('year_established', ''),
                        license_info.get('legal_form', ''),
                        license_info.get('legal_representative', '')
                    ))
                    print("执照信息已保存到数据库")
                
                # 如果成功提取到执照信息，标记为已获取
                if licenses or license_info:
                    cursor.execute('UPDATE suppliers SET license_extracted = TRUE WHERE company_id = ?', (company_id,))
                    print(f"  - {company_name}: 标记为已提取")
                
                conn.commit()
                conn.close()
                
                return True
            else:
                print(f"  - {company_name}: 获取页面失败")
                return False
                
        except Exception as e:
            print(f"处理供应商时出错: {e}")
            return False
    
    def extract_single_license_with_save(self, company_id, company_name, action_url, proxy, save_path):
        """提取单个供应商执照并保存到文件"""
        try:
            # 使用新隧道代理
            fixed_proxy = {
                'host': 'y900.kdltps.com',
                'port': 15818,
                'username': 't15395136610470',
                'password': 'kyhxo4pj'
            }
            
            # 使用与db_viewer.py相同的方法
            import threading
            import asyncio
            from alibaba_supplier_crawler import AlibabaSupplierCrawler
            
            def run_extract():
                try:
                    # 创建爬虫实例
                    crawler = AlibabaSupplierCrawler()
                    
                    # 运行异步提取
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(
                        crawler.extract_single_license(company_id, company_name, action_url, fixed_proxy)
                    )
                    
                    if result:
                        # 从数据库获取提取的执照信息
                        conn = sqlite3.connect(crawler.db_path)
                        cursor = conn.cursor()
                        
                        # 获取执照图片
                        cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (company_id,))
                        licenses = cursor.fetchall()
                        
                        # 获取执照信息
                        cursor.execute('''
                            SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                                   registered_capital, country_territory, registered_address,
                                   year_established, legal_form, legal_representative
                            FROM license_info WHERE supplier_id = ?
                        ''', (company_id,))
                        license_info = cursor.fetchone()
                        conn.close()
                        
                        # 保存到文件
                        if licenses or license_info:
                            self.save_license_to_file(company_name, licenses, license_info, save_path, company_id)
                            return True
                    
                    return False
                    
                except Exception as e:
                    self.log_message(f"提取失败: {e}")
                    return False
            
            # 运行提取
            result = run_extract()
            return result
            
        except Exception as e:
            self.log_message(f"提取 {company_name} 时出错: {e}")
            return False
    
    def save_all_licenses_to_files(self, save_path):
        """保存所有执照信息到本地文件"""
        try:
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 获取所有有执照信息的供应商
            cursor.execute('''
                SELECT DISTINCT s.company_name, s.company_id
                FROM suppliers s
                INNER JOIN license_info li ON s.company_id = li.supplier_id
                ORDER BY s.created_at DESC
            ''')
            suppliers_with_license = cursor.fetchall()
            
            if not suppliers_with_license:
                self.log_message("没有找到有执照信息的供应商")
                return
            
            self.log_message(f"开始保存 {len(suppliers_with_license)} 个供应商的执照信息到本地文件")
            
            for company_name, company_id in suppliers_with_license:
                try:
                    # 获取执照图片
                    cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (company_id,))
                    licenses = cursor.fetchall()
                    
                    # 获取执照信息
                    cursor.execute('''
                        SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                               registered_capital, country_territory, registered_address,
                               year_established, legal_form, legal_representative
                        FROM license_info WHERE supplier_id = ?
                    ''', (company_id,))
                    license_info = cursor.fetchone()
                    
                    # 保存到文件
                    if licenses or license_info:
                        self.save_license_to_file(company_name, licenses, license_info, save_path, company_id)
                        self.log_message(f"✓ 已保存 {company_name} 的执照信息到本地文件")
                    else:
                        self.log_message(f"✗ {company_name} 没有找到执照信息")
                        
                except Exception as e:
                    self.log_message(f"保存 {company_name} 的执照信息时出错: {e}")
            
            conn.close()
            self.log_message("所有执照信息保存完成")
            
        except Exception as e:
            self.log_message(f"保存执照信息到本地文件时出错: {e}")
    
    def save_extracted_licenses_to_files(self, save_path, supplier_ids):
        """只保存指定供应商ID的执照信息到本地文件"""
        try:
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            if not supplier_ids:
                self.log_extract_message("没有指定的供应商ID", "WARNING")
                return
            
            # 构建IN查询的占位符
            placeholders = ','.join('?' * len(supplier_ids))
            
            # 获取指定供应商的执照信息
            cursor.execute(f'''
                SELECT DISTINCT s.company_name, s.company_id
                FROM suppliers s
                INNER JOIN license_info li ON s.company_id = li.supplier_id
                WHERE s.company_id IN ({placeholders})
                ORDER BY s.created_at DESC
            ''', supplier_ids)
            suppliers_with_license = cursor.fetchall()
            
            if not suppliers_with_license:
                self.log_extract_message("指定的供应商中没有找到执照信息", "WARNING")
                conn.close()
                return
            
            self.log_extract_message(f"开始保存 {len(suppliers_with_license)} 个新提取供应商的执照信息到本地文件", "INFO")
            
            saved_count = 0
            for company_name, company_id in suppliers_with_license:
                try:
                    # 获取执照图片
                    cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (company_id,))
                    licenses = cursor.fetchall()
                    
                    # 获取执照信息
                    cursor.execute('''
                        SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                               registered_capital, country_territory, registered_address,
                               year_established, legal_form, legal_representative
                        FROM license_info WHERE supplier_id = ?
                    ''', (company_id,))
                    license_info = cursor.fetchone()
                    
                    # 保存到文件
                    if licenses or license_info:
                        self.save_license_to_file(company_name, licenses, license_info, save_path, company_id)
                        saved_count += 1
                        self.log_extract_message(f"✓ 已保存 {company_name} 的执照信息到本地文件", "SUCCESS")
                    else:
                        self.log_extract_message(f"✗ {company_name} 没有找到执照信息", "WARNING")
                        
                except Exception as e:
                    self.log_extract_message(f"保存 {company_name} 的执照信息时出错: {e}", "ERROR")
            
            conn.close()
            self.log_extract_message(f"本次提取的执照信息保存完成，共保存 {saved_count} 个供应商", "INFO")
            
        except Exception as e:
            self.log_extract_message(f"保存本次提取的执照信息到本地文件时出错: {e}", "ERROR")

    def save_license_to_file(self, company_name, licenses, license_info, save_path, company_id=None):
        """保存执照信息到文件"""
        # 如果提供了company_id，尝试从数据库获取保存路径
        if company_id:
            try:
                conn = sqlite3.connect(self.crawler.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT save_path FROM suppliers WHERE company_id = ?', (company_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    # 使用数据库中的路径
                    folder_path = result[0]
                    os.makedirs(folder_path, exist_ok=True)
                else:
                    # 如果数据库中没有路径，使用默认路径
                    safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                    folder_path = os.path.join(save_path, safe_name)
                    os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                # 出错时使用默认路径
                safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                folder_path = os.path.join(save_path, safe_name)
                os.makedirs(folder_path, exist_ok=True)
        else:
            # 没有company_id时使用默认路径
            safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            folder_path = os.path.join(save_path, safe_name)
            os.makedirs(folder_path, exist_ok=True)
        
        # 保存执照信息
        if license_info:
            info_file = os.path.join(folder_path, "执照信息.txt")
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"供应商: {company_name}\n")
                f.write("=" * 50 + "\n\n")
                
                # license_info是tuple，按顺序访问字段
                fields = [
                    ("注册号", license_info[0] if license_info[0] else ''),
                    ("公司名称", license_info[1] if license_info[1] else ''),
                    ("发证日期", license_info[2] if license_info[2] else ''),
                    ("到期日期", license_info[3] if license_info[3] else ''),
                    ("注册资本", license_info[4] if license_info[4] else ''),
                    ("国家/地区", license_info[5] if license_info[5] else ''),
                    ("注册地址", license_info[6] if license_info[6] else ''),
                    ("成立年份", license_info[7] if license_info[7] else ''),
                    ("法律形式", license_info[8] if license_info[8] else ''),
                    ("法定代表人", license_info[9] if license_info[9] else '')
                ]
                
                for field_name, field_value in fields:
                    if field_value:
                        f.write(f"{field_name}: {field_value}\n")
        
        # 保存执照图片
        if licenses:
            try:
                import requests
                from PIL import Image
                
                for i, license_item in enumerate(licenses, 1):
                    try:
                        # license_item是tuple，按顺序访问字段 (license_url,)
                        license_url = license_item[0]
                        
                        # 下载图片
                        response = requests.get(license_url, timeout=10)
                        if response.status_code == 200:
                            # 获取原始文件扩展名
                            import urllib.parse
                            parsed_url = urllib.parse.urlparse(license_url)
                            file_extension = os.path.splitext(parsed_url.path)[1]
                            if not file_extension:
                                file_extension = '.jpg'  # 默认为jpg
                            
                            # 保存图片，保持原始格式
                            img_file = os.path.join(folder_path, f"执照图片_{i}{file_extension}")
                            with open(img_file, 'wb') as f:
                                f.write(response.content)
                                
                    except Exception as e:
                        self.log_message(f"保存图片 {i} 失败: {e}")
                        
            except ImportError:
                self.log_message("PIL库未安装，无法保存图片")
    
    def stop_extract(self):
        """停止提取"""
        self.extract_all_btn.config(state=tk.NORMAL)
        self.stop_extract_btn.config(state=tk.DISABLED)
        self.log_message("提取已停止")
    
    def extract_finished(self):
        """提取完成"""
        self.extract_all_btn.config(state=tk.NORMAL)
        self.stop_extract_btn.config(state=tk.DISABLED)
        self.extract_progress.configure(value=100)
        self.extract_status_label.config(text="提取完成")
        messagebox.showinfo("完成", "执照提取开始")
    
    def extract_error(self, error):
        """提取错误"""
        self.extract_all_btn.config(state=tk.NORMAL)
        self.stop_extract_btn.config(state=tk.DISABLED)
        self.log_message(f"提取失败: {error}")
        messagebox.showerror("错误", f"提取失败: {error}")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # 添加到主日志（如果存在）
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
        
        # 添加到爬虫日志（如果存在）
        if hasattr(self, 'crawl_log_text'):
            self.log_crawl_message(message, "INFO")
        
        # 添加到提取日志（如果存在）
        if hasattr(self, 'extract_log_text'):
            self.log_extract_message(message, "INFO")
    
    def load_categories(self):
        """加载分类数据"""
        try:
            # 尝试多个可能的文件名
            possible_files = ['cary.json', 'cary. json']
            data = None
            
            for filename in possible_files:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        print(f"成功加载分类文件: {filename}")
                        break
                except FileNotFoundError:
                    continue
                except Exception as e:
                    print(f"读取文件 {filename} 失败: {e}")
                    continue
            
            if data and 'data' in data and 'tabs' in data['data']:
                categories = []
                for tab in data['data']['tabs']:
                    categories.append(f"{tab['tabId']} - {tab['title']}")
                self.category_combobox['values'] = categories
                if categories:
                    self.category_combobox.set(categories[0])
                    print(f"加载了 {len(categories)} 个分类")
                else:
                    print("没有找到分类数据")
            else:
                print("分类文件格式不正确")
                self.category_combobox['values'] = []
        except Exception as e:
            print(f"加载分类文件失败: {e}")
            self.category_combobox['values'] = []

    def on_search_type_change(self):
        """搜索类型改变时的处理"""
        search_type = self.search_type_var.get()
        if search_type == "keyword":
            # 关键词搜索：启用关键词输入，禁用分类选择
            self.keyword_entry.config(state="normal")
            self.category_combobox.config(state="disabled")
        else:
            # 分类搜索：禁用关键词输入，启用分类选择
            self.keyword_entry.config(state="disabled")
            self.category_combobox.config(state="readonly")

    def get_selected_category_id(self):
        """获取选中的分类ID"""
        selected = self.category_var.get()
        if selected and " - " in selected:
            return selected.split(" - ")[0]
        return None
    
    def load_gateway_categories(self):
        """加载gatewayService.json中的分类数据"""
        try:
            with open('gatewayService.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if data and 'data' in data and 'categoryList' in data['data']:
                categories = []
                self._extract_categories(data['data']['categoryList'], categories, "")
                return categories
            else:
                print("gatewayService.json文件格式不正确")
                return []
        except FileNotFoundError:
            print("未找到gatewayService.json文件")
            return []
        except Exception as e:
            print(f"加载gatewayService.json失败: {e}")
            return []
    
    def _extract_categories(self, category_list, result, prefix):
        """递归提取分类名称"""
        for category in category_list:
            name = category.get('name', '')
            level = category.get('level', '1')
            
            # 根据层级添加缩进
            indent = "  " * (int(level) - 1)
            display_name = f"{indent}{name}"
            
            if prefix:
                full_name = f"{prefix} > {name}"
            else:
                full_name = name
                
            result.append({
                'display': display_name,
                'name': name,
                'full_path': full_name,
                'level': level
            })
            
            # 递归处理子分类
            if 'categoryList' in category and category['categoryList']:
                self._extract_categories(category['categoryList'], result, full_name)
    
    def show_category_selector(self):
        """显示分类选择对话框"""
        categories = self.load_gateway_categories()
        if not categories:
            messagebox.showwarning("提示", "无法加载分类数据，请确保gatewayService.json文件存在")
            return
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择分类关键词")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 搜索框
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 分类列表
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 创建Treeview来显示分层结构
        tree = ttk.Treeview(list_frame, columns=('path',), show='tree headings')
        tree.heading('#0', text='分类名称')
        tree.heading('path', text='完整路径')
        tree.column('#0', width=200)
        tree.column('path', width=280)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据
        def populate_tree(filter_text=""):
            tree.delete(*tree.get_children())
            for category in categories:
                if not filter_text or filter_text.lower() in category['name'].lower():
                    tree.insert('', 'end', text=category['display'], 
                              values=(category['full_path'],), 
                              tags=(category['name'],))
        
        populate_tree()
        
        # 搜索功能
        def on_search(*args):
            populate_tree(search_var.get())
        
        search_var.trace('w', on_search)
        
        # 按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def on_select():
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                category_name = item['tags'][0] if item['tags'] else item['text'].strip()
                self.keyword_entry.delete(0, tk.END)
                self.keyword_entry.insert(0, category_name)
                dialog.destroy()
            else:
                messagebox.showwarning("提示", "请选择一个分类")
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="确定", command=on_select).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
        
        # 双击选择
        def on_double_click(event):
            on_select()
        
        tree.bind('<Double-1>', on_double_click)
        
        # 设置焦点
        search_entry.focus_set()

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass # 如果没有选中项，则不显示菜单

    def on_double_click(self, event):
        """双击事件处理"""
        selected_item = self.db_tree.selection()
        if selected_item:
            item_values = self.db_tree.item(selected_item[0])['values']
            company_name = item_values[1]
            self.browse_supplier_files() # 双击时直接打开文件夹

    def recognize_selected_license(self):
        """识别选中的供应商执照"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return

        selected_item = selected_items[0] # 只处理第一个选中的项
        item_values = self.db_list_tree.item(selected_item)['values']
        company_name = item_values[1]
        action_url = item_values[2]

        self.log_message(f"尝试识别供应商: {company_name} (Action URL: {action_url})")

        # 使用新隧道代理
        fixed_proxy = {
            'host': 'y900.kdltps.com',
            'port': 15818,
            'username': 't15395136610470',
            'password': 'kyhxo4pj'
        }

        # 在新线程中运行识别
        def run_recognize():
            try:
                # 创建爬虫实例
                crawler = AlibabaSupplierCrawler()
                
                # 运行异步识别
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    crawler.recognize_license_from_url(action_url, fixed_proxy)
                )
                
                if result:
                    # 从数据库获取提取的执照信息
                    conn = sqlite3.connect(crawler.db_path)
                    cursor = conn.cursor()
                    
                    # 获取执照图片
                    cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (result['company_id'],))
                    licenses = cursor.fetchall()
                    
                    # 获取执照信息
                    cursor.execute('''
                        SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                               registered_capital, country_territory, registered_address,
                               year_established, legal_form, legal_representative
                        FROM license_info WHERE supplier_id = ?
                    ''', (result['company_id'],))
                    license_info = cursor.fetchone()
                    conn.close()
                    
                    # 保存到文件
                    if licenses or license_info:
                        # 使用默认保存路径，避免弹出对话框影响GUI
                        save_path = "./license_files"
                        os.makedirs(save_path, exist_ok=True)
                        self.save_license_to_file(company_name, licenses, license_info, save_path, company_id)
                        self.log_message(f"✓ 已保存 {company_name} 的执照信息到 {save_path}")
                    else:
                        self.log_message(f"✗ {company_name} 没有找到执照信息")
                else:
                    self.log_message(f"✗ 识别失败或未找到执照信息")
                    
            except Exception as e:
                self.log_message(f"识别失败: {e}")
                messagebox.showerror("错误", f"识别失败: {e}")
        
        threading.Thread(target=run_recognize, daemon=True).start()

    def refresh_db_list_page(self):
        """刷新数据库列表页面"""
        try:
            # 清空列表
            for item in self.db_list_tree.get_children():
                self.db_list_tree.delete(item)
            
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 检查表结构，确保有必要的字段
            try:
                cursor.execute("PRAGMA table_info(suppliers)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # 如果缺少license_extracted字段，添加它
                if 'license_extracted' not in columns:
                    self.log_message("添加license_extracted字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN license_extracted BOOLEAN DEFAULT FALSE')
                    conn.commit()
                
                # 如果缺少category_id或category_name字段，添加它们
                if 'category_id' not in columns:
                    self.log_message("添加category_id字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN category_id TEXT')
                    conn.commit()
                
                if 'category_name' not in columns:
                    self.log_message("添加category_name字段到数据库...")
                    cursor.execute('ALTER TABLE suppliers ADD COLUMN category_name TEXT')
                    conn.commit()
            except Exception as e:
                self.log_message(f"检查表结构时出错: {e}")
            
            # 检查并添加is_used字段
            if 'is_used' not in columns:
                self.log_message("添加is_used字段到数据库...")
                cursor.execute('ALTER TABLE suppliers ADD COLUMN is_used BOOLEAN DEFAULT FALSE')
                conn.commit()
                columns.append('is_used')
            
            # 检查并添加ocr_recognition_status字段
            if 'ocr_recognition_status' not in columns:
                self.log_message("添加ocr_recognition_status字段到数据库...")
                cursor.execute('ALTER TABLE suppliers ADD COLUMN ocr_recognition_status TEXT DEFAULT "pending"')
                conn.commit()
                columns.append('ocr_recognition_status')
            
            # 根据Tab选择查询条件
            tab_filter = self.db_list_tab_var.get()
            
            # 构建基本查询
            base_select = "SELECT id, company_name, action_url"
            base_count = "SELECT COUNT(*)"
            
            # 根据表结构添加字段
            if 'license_extracted' in columns:
                base_select += ", license_extracted"
            else:
                base_select += ", 0 as license_extracted"
                
            if 'category_id' in columns:
                base_select += ", category_id"
            else:
                base_select += ", '' as category_id"
                
            if 'category_name' in columns:
                base_select += ", category_name"
            else:
                base_select += ", '' as category_name"
                
            if 'is_used' in columns:
                base_select += ", is_used"
            else:
                base_select += ", 0 as is_used"
                
            if 'ocr_recognition_status' in columns:
                base_select += ", ocr_recognition_status"
            else:
                base_select += ", 'pending' as ocr_recognition_status"
            
            base_from = " FROM suppliers"
            
            # 添加过滤条件
            where_clause = ""
            if tab_filter == "success":
                where_clause = " WHERE license_extracted = 1"
            elif tab_filter == "pending":
                where_clause = " WHERE (license_extracted = 0 OR license_extracted IS NULL) AND (skip_extraction = 0 OR skip_extraction IS NULL)"
            elif tab_filter == "recognized":
                where_clause = " WHERE license_extracted = 1 AND (registration_no IS NOT NULL AND registration_no != '')"
            elif tab_filter == "used":
                where_clause = " WHERE is_used = 1"
            elif tab_filter == "unused":
                where_clause = " WHERE is_used = 0 OR is_used IS NULL"
            elif tab_filter == "problematic":
                where_clause = " WHERE skip_extraction = 1"
            elif tab_filter == "ocr_error":
                where_clause = " WHERE ocr_recognition_status = 'error'"
            # else: all - 无where条件
            
            order_clause = " ORDER BY created_at DESC"
            
            # 先获取总数
            count_query = base_count + base_from + where_clause
            cursor.execute(count_query)
            total_count = cursor.fetchone()[0]
            
            # 更新分页信息
            self.update_pagination_info(total_count)
            
            # 计算分页参数
            offset = (self.current_page - 1) * self.page_size
            limit_clause = f" LIMIT {self.page_size} OFFSET {offset}"
            
            # 构建分页查询
            query = base_select + base_from + where_clause + order_clause + limit_clause
            
            # 执行查询
            self.log_message(f"执行分页查询: {query}")
            cursor.execute(query)
            suppliers = cursor.fetchall()
            
            # 统计数量
            total_count = len(suppliers)
            success_count = sum(1 for s in suppliers if len(s) >= 4 and s[3])
            fail_count = total_count - success_count
            self.db_list_stats_label.config(text=f"总数: {total_count}，已成功: {success_count}，未提取: {fail_count}")
            
            # 添加到列表
            for i, supplier_data in enumerate(suppliers, 1):
                supplier_id = supplier_data[0]
                company_name = supplier_data[1]
                action_url = supplier_data[2]
                
                # 处理license_extracted
                license_extracted = False
                if len(supplier_data) > 3:
                    license_extracted = bool(supplier_data[3])
                
                # 处理分类信息
                category_id = ""
                category_name = ""
                if len(supplier_data) > 5:
                    category_id = supplier_data[4] if supplier_data[4] else ""
                    category_name = supplier_data[5] if supplier_data[5] else ""
                
                # 处理使用状态
                is_used = False
                if len(supplier_data) > 6:
                    is_used = bool(supplier_data[6])
                
                # 处理OCR识别状态
                ocr_status = "pending"
                if len(supplier_data) > 7:
                    ocr_status = supplier_data[7] if supplier_data[7] else "pending"
                
                # 截断长文本
                display_name = company_name[:50] + "..." if len(company_name) > 50 else company_name
                display_url = action_url[:80] + "..." if len(action_url) > 80 else action_url
                display_category = category_name[:20] + "..." if len(category_name) > 20 else category_name
                
                # 执照状态
                status = "已获取" if license_extracted else "未获取"
                status_color = "green" if license_extracted else "red"
                
                # 识别状态（基于OCR识别状态字段）
                if ocr_status == "completed":
                    recognize_status = "已识别"
                elif ocr_status == "error":
                    recognize_status = "识别错误"
                elif ocr_status == "processing":
                    recognize_status = "识别中"
                else:
                    recognize_status = "未识别"
                
                # 使用状态
                use_status = "已使用" if is_used else "未使用"
                
                # 插入数据到列表
                try:
                    item = self.db_list_tree.insert('', 'end', values=(i, display_name, display_url, display_category, status, recognize_status, use_status))
                    
                    # 设置颜色（如果支持）
                    try:
                        self.db_list_tree.tag_configure(status_color, foreground=status_color)
                        self.db_list_tree.item(item, tags=(status_color,))
                    except:
                        pass  # 如果不支持颜色，就忽略
                except Exception as e:
                    self.log_message(f"插入数据到列表时出错: {e}")
                    # 即使插入失败，也继续处理下一个
                    continue
            
            conn.close()
            
            self.log_message(f"数据库列表已刷新，共 {len(suppliers)} 个供应商")
            
        except Exception as e:
            self.log_message(f"刷新数据库列表失败: {e}")
            import traceback
            self.log_message(f"详细错误: {traceback.format_exc()}")

    def search_suppliers(self):
        """搜索供应商"""
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return

        self.log_message(f"开始搜索供应商: {search_term}")
        self.refresh_db_list_page() # 刷新列表以应用搜索条件

    def recognize_selected_db_list(self):
        """识别选中的供应商执照"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return

        selected_item = selected_items[0] # 只处理第一个选中的项
        item_values = self.db_list_tree.item(selected_item)['values']
        company_name = item_values[1]
        action_url = item_values[2]

        self.log_message(f"开始识别供应商执照: {company_name}")

        # 在新线程中运行识别
        def run_recognize():
            try:
                # 首先检查本地是否已有执照图片文件
                save_path = "./license_files"
                safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
                supplier_dir = os.path.join(save_path, "0_所有类目", safe_name)
                
                # 查找本地执照图片文件
                local_images = []
                if os.path.exists(supplier_dir):
                    for file in os.listdir(supplier_dir):
                        if file.startswith("执照图片_") and file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                            local_images.append(os.path.join(supplier_dir, file))
                
                if local_images:
                    # 如果本地已有执照图片，直接使用OCR处理
                    self.log_message(f"✓ 找到本地执照图片 {len(local_images)} 张，开始OCR识别")
                    
                    # 导入OCR处理器
                    import sys
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from ocr_license_complete import LicenseOCRProcessor
                    
                    # 创建OCR处理器
                    ocr_processor = LicenseOCRProcessor()
                    
                    # 处理每张图片
                    success_count = 0
                    for image_path in local_images:
                        self.log_message(f"正在OCR识别: {os.path.basename(image_path)}")
                        if ocr_processor.process_single_image(image_path):
                            success_count += 1
                            self.log_message(f"✓ OCR识别成功: {os.path.basename(image_path)}")
                        else:
                            self.log_message(f"✗ OCR识别失败: {os.path.basename(image_path)}")
                    
                    if success_count > 0:
                        self.log_message(f"✓ 执照OCR识别完成，成功处理 {success_count}/{len(local_images)} 张图片")
                    else:
                        self.log_message(f"✗ 所有执照图片OCR识别都失败")
                        
                else:
                    # 如果本地没有执照图片，从网络获取
                    self.log_message(f"本地未找到执照图片，尝试从网络获取: {action_url}")
                    
                    # 使用新隧道代理
                    fixed_proxy = {
                        'host': 'y900.kdltps.com',
                        'port': 15818,
                        'username': 't15395136610470',
                        'password': 'kyhxo4pj'
                    }
                    
                    # 创建爬虫实例
                    crawler = AlibabaSupplierCrawler()
                    
                    # 运行异步识别
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(
                        crawler.recognize_license_from_url(action_url, fixed_proxy)
                    )
                    
                    if result:
                        # 从数据库获取提取的执照信息
                        conn = sqlite3.connect(crawler.db_path)
                        cursor = conn.cursor()
                        
                        # 获取执照图片
                        cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (result['company_id'],))
                        licenses = cursor.fetchall()
                        
                        # 获取执照信息
                        cursor.execute('''
                            SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                                   registered_capital, country_territory, registered_address,
                                   year_established, legal_form, legal_representative
                            FROM license_info WHERE supplier_id = ?
                        ''', (result['company_id'],))
                        license_info = cursor.fetchone()
                        conn.close()
                        
                        # 保存到文件
                        if licenses or license_info:
                            os.makedirs(save_path, exist_ok=True)
                            self.save_license_to_file(company_name, licenses, license_info, save_path)
                            self.log_message(f"✓ 已保存 {company_name} 的执照信息到 {save_path}")
                            
                            # 对新下载的图片进行OCR识别
                            self.log_message(f"开始对新下载的执照图片进行OCR识别")
                            # 重新查找本地图片文件
                            new_images = []
                            if os.path.exists(supplier_dir):
                                for file in os.listdir(supplier_dir):
                                    if file.startswith("执照图片_") and file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                                        new_images.append(os.path.join(supplier_dir, file))
                            
                            if new_images:
                                # 导入OCR处理器
                                import sys
                                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                                from ocr_license_complete import LicenseOCRProcessor
                                
                                # 创建OCR处理器
                                ocr_processor = LicenseOCRProcessor()
                                
                                # 处理每张图片
                                success_count = 0
                                for image_path in new_images:
                                    self.log_message(f"正在OCR识别: {os.path.basename(image_path)}")
                                    if ocr_processor.process_single_image(image_path):
                                        success_count += 1
                                        self.log_message(f"✓ OCR识别成功: {os.path.basename(image_path)}")
                                    else:
                                        self.log_message(f"✗ OCR识别失败: {os.path.basename(image_path)}")
                                
                                if success_count > 0:
                                    self.log_message(f"✓ 执照OCR识别完成，成功处理 {success_count}/{len(new_images)} 张图片")
                                else:
                                    self.log_message(f"✗ 所有执照图片OCR识别都失败")
                        else:
                            self.log_message(f"✗ {company_name} 没有找到执照信息")
                    else:
                        self.log_message(f"✗ 从网络获取执照信息失败")
                    
            except Exception as e:
                self.log_message(f"识别失败: {e}")
                import traceback
                self.log_message(f"详细错误: {traceback.format_exc()}")
        
        threading.Thread(target=run_recognize, daemon=True).start()

    def browse_selected_db_list(self):
        """浏览选中的供应商文件"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return

        selected_item = selected_items[0] # 只处理第一个选中的项
        item_values = self.db_list_tree.item(selected_item)['values']
        company_name = item_values[1]

        # 从数据库获取供应商的保存路径
        conn = sqlite3.connect(self.crawler.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT save_path FROM suppliers WHERE company_name = ?', (company_name,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # 使用数据库中存储的保存路径
            folder_path = result[0]
            
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            if os.path.exists(folder_path):
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    subprocess.run(['explorer', folder_path])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])
                
                self.log_message(f"已打开文件夹: {folder_path}")
            else:
                messagebox.showinfo("提示", f"该供应商的文件还未保存到本地\n路径: {folder_path}")
        else:
            messagebox.showinfo("提示", "该供应商还没有保存路径信息")

    def export_selected_suppliers(self):
        """导出选中的供应商信息"""
        selected_items = self.db_list_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要导出的供应商")
            return

        suppliers_to_export = []
        for item_id in selected_items:
            item_values = self.db_list_tree.item(item_id)['values']
            company_name = item_values[1]
            action_url = item_values[2]
            license_extracted = item_values[4] # 执照状态
            recognize_status = item_values[5] # 识别状态

            # 只导出已获取执照且已识别的供应商
            if license_extracted == "已获取" and recognize_status == "已识别":
                suppliers_to_export.append({
                    "公司名称": company_name,
                    "Action URL": action_url,
                    "执照状态": license_extracted,
                    "识别状态": recognize_status
                })

        if not suppliers_to_export:
            messagebox.showwarning("提示", "没有选择要导出的供应商")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if save_path:
            try:
                import csv
                with open(save_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ["公司名称", "Action URL", "执照状态", "识别状态"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(suppliers_to_export)
                messagebox.showinfo("完成", f"已导出 {len(suppliers_to_export)} 个供应商到 {save_path}")
                self.log_message(f"已导出 {len(suppliers_to_export)} 个供应商到 {save_path}")
            except Exception as e:
                self.log_message(f"导出供应商失败: {e}")
                messagebox.showerror("错误", f"导出供应商失败: {e}")

    def export_all_suppliers(self):
        """导出所有供应商信息"""
        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )

            if save_path:
                # 连接数据库
                conn = sqlite3.connect(self.crawler.db_path)
                cursor = conn.cursor()
                
                # 获取所有供应商
                cursor.execute('''
                    SELECT company_name, action_url, license_extracted, (
                        SELECT COUNT(*) FROM license_info WHERE supplier_id = suppliers.id
                    ) as recognized_count
                    FROM suppliers
                    ORDER BY created_at DESC
                ''')
                all_suppliers = cursor.fetchall()
                conn.close()

                if not all_suppliers:
                    messagebox.showwarning("提示", "没有供应商数据可导出")
                    return

                try:
                    import csv
                    with open(save_path, 'w', newline='', encoding='utf-8') as f:
                        fieldnames = ["公司名称", "Action URL", "执照状态", "已识别执照数量"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(all_suppliers)
                    messagebox.showinfo("完成", f"已导出 {len(all_suppliers)} 个供应商到 {save_path}")
                    self.log_message(f"已导出 {len(all_suppliers)} 个供应商到 {save_path}")
                except Exception as e:
                    self.log_message(f"导出所有供应商失败: {e}")
                    messagebox.showerror("错误", f"导出所有供应商失败: {e}")
            else:
                self.log_message("导出所有供应商已取消")
        except Exception as e:
            self.log_message(f"导出所有供应商失败: {e}")
            messagebox.showerror("错误", f"导出所有供应商失败: {e}")

    def show_db_list_context_menu(self, event):
        """显示数据库列表的右键菜单"""
        try:
            self.db_list_context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass # 如果没有选中项，则不显示菜单

    def on_db_list_double_click(self, event):
        """双击事件处理"""
        selected_item = self.db_list_tree.selection()
        if selected_item:
            item_values = self.db_list_tree.item(selected_item[0])['values']
            company_name = item_values[1]
            self.browse_supplier_files() # 双击时直接打开文件夹

    def log_extract_message(self, message, level="INFO"):
        """添加提取日志消息（带级别）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 根据日志级别设置标签
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
            level = "INFO"
        
        # 检查日志级别过滤
        current_level = self.log_level_var.get()
        level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        
        if level_priority.get(level, 1) >= level_priority.get(current_level, 1):
            # 插入日志
            self.extract_log_text.insert(tk.END, log_entry, level)
            self.extract_log_text.see(tk.END)
            
            # 自动保存日志
            if self.auto_save_log_var.get() and level in ["WARNING", "ERROR"]:
                self.save_extract_log(auto=True)
        
        # 同时添加到主日志（如果存在）
        if hasattr(self, 'log_text'):
            self.log_message(message)
    
    def log_ocr_message(self, message, level="INFO"):
        """添加OCR识别日志消息（带级别）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 根据日志级别设置标签
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
            level = "INFO"
        
        # 插入日志到OCR日志文本框
        if hasattr(self, 'ocr_log_text'):
            self.ocr_log_text.insert(tk.END, log_entry, level)
            self.ocr_log_text.see(tk.END)
        
        # 同时添加到主日志（如果存在）
        if hasattr(self, 'log_text'):
            self.log_message(message)
    
    def save_extract_log(self, auto=False):
        """保存提取日志到文件"""
        try:
            if auto:
                # 自动保存使用时间戳命名
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = os.path.join(log_dir, f"extract_log_{timestamp}.txt")
            else:
                # 手动保存让用户选择路径
                log_file = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    initialdir="logs",
                    title="保存提取日志"
                )
                
                if not log_file:
                    return
            
            # 获取所有日志内容
            log_content = self.extract_log_text.get("1.0", tk.END)
            
            # 写入文件
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(log_content)
            
            if not auto:
                self.log_extract_message(f"日志已保存到: {log_file}", "SUCCESS")
                messagebox.showinfo("成功", f"日志已保存到: {log_file}")
            
        except Exception as e:
            self.log_extract_message(f"保存日志失败: {e}", "ERROR")
            if not auto:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def clear_extract_log(self):
        """清空提取日志"""
        if messagebox.askyesno("确认", "确定要清空提取日志吗？"):
            self.extract_log_text.delete("1.0", tk.END)
            self.log_extract_message("日志已清空", "INFO")
    
    def apply_log_filter(self):
        """应用日志过滤"""
        filter_text = self.log_filter_entry.get().strip()
        if not filter_text:
            messagebox.showwarning("提示", "请输入过滤条件")
            return
        
        # 保存原始日志内容
        if not hasattr(self, 'original_log_content'):
            self.original_log_content = self.extract_log_text.get("1.0", tk.END)
        
        # 清空当前显示
        self.extract_log_text.delete("1.0", tk.END)
        
        # 按行过滤并显示匹配行
        for line in self.original_log_content.split('\n'):
            if filter_text.lower() in line.lower():
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                self.extract_log_text.insert(tk.END, line + "\n", level)
        
        self.log_extract_message(f"已应用过滤: '{filter_text}'", "INFO")
    
    def clear_log_filter(self):
        """清除日志过滤"""
        if hasattr(self, 'original_log_content'):
            # 清空当前显示
            self.extract_log_text.delete("1.0", tk.END)
            
            # 恢复原始内容
            lines = self.original_log_content.split('\n')
            for line in lines:
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                self.extract_log_text.insert(tk.END, line + "\n", level)
            
            # 清除过滤条件
            self.log_filter_entry.delete(0, tk.END)
            self.log_extract_message("已清除过滤", "INFO")
        else:
            self.log_extract_message("没有应用过滤", "INFO")

    def apply_ocr_log_filter(self):
        """应用OCR日志过滤"""
        filter_text = self.ocr_log_filter_entry.get().strip()
        if not filter_text:
            messagebox.showwarning("提示", "请输入过滤条件")
            return
        
        # 保存原始日志内容
        if not hasattr(self, 'original_ocr_log_content'):
            self.original_ocr_log_content = self.ocr_log_text.get("1.0", tk.END)
        
        # 清空当前显示
        self.ocr_log_text.delete("1.0", tk.END)
        
        # 按行过滤并显示匹配行
        for line in self.original_ocr_log_content.split('\n'):
            if filter_text.lower() in line.lower():
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                self.ocr_log_text.insert(tk.END, line + "\n", level)
        
        self.log_ocr_message(f"已应用过滤: '{filter_text}'", "INFO")
    
    def clear_ocr_log_filter(self):
        """清除OCR日志过滤"""
        if hasattr(self, 'original_ocr_log_content'):
            # 清空当前显示
            self.ocr_log_text.delete("1.0", tk.END)
            
            # 恢复原始内容
            lines = self.original_ocr_log_content.split('\n')
            for line in lines:
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                if line.strip():  # 只插入非空行
                    self.ocr_log_text.insert(tk.END, line + "\n", level)
            
            # 清除过滤条件
            self.ocr_log_filter_entry.delete(0, tk.END)
            self.log_ocr_message("已清除过滤", "INFO")
            
            # 删除保存的原始内容
            delattr(self, 'original_ocr_log_content')
        else:
            self.log_ocr_message("没有应用过滤", "INFO")

    def log_crawl_message(self, message, level="INFO"):
        """添加爬虫日志消息（带级别）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 根据日志级别设置标签
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
            level = "INFO"
        
        # 检查日志级别过滤
        current_level = self.crawl_log_level_var.get()
        level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        
        if level_priority.get(level, 1) >= level_priority.get(current_level, 1):
            # 插入日志
            self.crawl_log_text.insert(tk.END, log_entry, level)
            self.crawl_log_text.see(tk.END)
            
            # 自动保存日志
            if self.crawl_auto_save_log_var.get() and level in ["WARNING", "ERROR"]:
                self.save_crawl_log(auto=True)
    
    def log_crawl_detail(self, message, level="DEBUG"):
        """添加详细的爬取过程日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # 根据日志级别设置标签
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
            level = "DEBUG"
        
        # 检查日志级别过滤
        current_level = self.crawl_log_level_var.get()
        level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        
        if level_priority.get(level, 0) >= level_priority.get(current_level, 1):
            # 插入日志
            self.crawl_log_text.insert(tk.END, log_entry, level)
            self.crawl_log_text.see(tk.END)
    
    def log_request(self, url, method="GET", status_code=None, response_size=None, duration=None):
        """记录HTTP请求日志"""
        if status_code:
            if status_code == 200:
                level = "SUCCESS"
                status_text = f"✓ {status_code}"
            elif status_code >= 400:
                level = "ERROR"
                status_text = f"✗ {status_code}"
            else:
                level = "WARNING"
                status_text = f"⚠ {status_code}"
        else:
            level = "INFO"
            status_text = "请求中..."
        
        # 构建日志消息
        log_parts = [f"{method} {url}"]
        if status_code:
            log_parts.append(f"状态: {status_text}")
        if response_size:
            log_parts.append(f"大小: {response_size} bytes")
        if duration:
            log_parts.append(f"耗时: {duration:.2f}s")
        
        message = " | ".join(log_parts)
        self.log_crawl_detail(message, level)
    
    def log_data_extraction(self, data_type, count, details=""):
        """记录数据提取日志"""
        message = f"提取{data_type}: {count} 条"
        if details:
            message += f" ({details})"
        self.log_crawl_detail(message, "INFO")
    
    def log_supplier_info(self, company_name, action_url, country_code=None):
        """记录供应商信息日志"""
        message = f"供应商: {company_name}"
        if country_code:
            message += f" [{country_code}]"
        message += f" | URL: {action_url}"
        self.log_crawl_detail(message, "SUCCESS")
    
    def log_page_info(self, page_num, total_suppliers, page_url=None):
        """记录页面信息日志"""
        message = f"第 {page_num} 页: 找到 {total_suppliers} 个供应商"
        if page_url:
            message += f" | URL: {page_url}"
        self.log_crawl_detail(message, "INFO")
    
    def log_error(self, error_type, error_message, url=None):
        """记录错误日志"""
        message = f"错误 [{error_type}]: {error_message}"
        if url:
            message += f" | URL: {url}"
        self.log_crawl_detail(message, "ERROR")
    
    def log_warning(self, warning_type, warning_message, url=None):
        """记录警告日志"""
        message = f"警告 [{warning_type}]: {warning_message}"
        if url:
            message += f" | URL: {url}"
        self.log_crawl_detail(message, "WARNING")
    
    def log_proxy_info(self, proxy_host, proxy_port, status="使用"):
        """记录代理信息日志"""
        message = f"代理 {status}: {proxy_host}:{proxy_port}"
        self.log_crawl_detail(message, "DEBUG")
    
    def log_delay_info(self, delay_seconds, reason=""):
        """记录延迟信息日志"""
        message = f"延迟 {delay_seconds:.1f} 秒"
        if reason:
            message += f" ({reason})"
        self.log_crawl_detail(message, "DEBUG")
    
    def save_crawl_log(self, auto=False):
        """保存爬虫日志到文件"""
        try:
            if auto:
                # 自动保存使用时间戳命名
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = os.path.join(log_dir, f"crawl_log_{timestamp}.txt")
            else:
                # 手动保存让用户选择路径
                log_file = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    initialdir="logs",
                    title="保存爬虫日志"
                )
                
                if not log_file:
                    return
            
            # 获取所有日志内容
            log_content = self.crawl_log_text.get("1.0", tk.END)
            
            # 写入文件
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(log_content)
            
            if not auto:
                self.log_crawl_message(f"日志已保存到: {log_file}", "SUCCESS")
                messagebox.showinfo("成功", f"日志已保存到: {log_file}")
            
        except Exception as e:
            self.log_crawl_message(f"保存日志失败: {e}", "ERROR")
            if not auto:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def clear_crawl_log(self):
        """清空爬虫日志"""
        if messagebox.askyesno("确认", "确定要清空爬虫日志吗？"):
            self.crawl_log_text.delete("1.0", tk.END)
            self.log_crawl_message("日志已清空", "INFO")
    
    def apply_crawl_log_filter(self):
        """应用爬虫日志过滤"""
        filter_text = self.crawl_log_filter_entry.get().strip()
        if not filter_text:
            messagebox.showwarning("提示", "请输入过滤条件")
            return
        
        # 保存原始日志内容
        if not hasattr(self, 'original_crawl_log_content'):
            self.original_crawl_log_content = self.crawl_log_text.get("1.0", tk.END)
        
        # 清空当前显示
        self.crawl_log_text.delete("1.0", tk.END)
        
        # 按行过滤并显示匹配行
        for line in self.original_crawl_log_content.split('\n'):
            if filter_text.lower() in line.lower():
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                self.crawl_log_text.insert(tk.END, line + "\n", level)
        
        self.log_crawl_message(f"已应用过滤: '{filter_text}'", "INFO")
    
    def clear_crawl_log_filter(self):
        """清除爬虫日志过滤"""
        if hasattr(self, 'original_crawl_log_content'):
            # 清空当前显示
            self.crawl_log_text.delete("1.0", tk.END)
            
            # 恢复原始内容
            lines = self.original_crawl_log_content.split('\n')
            for line in lines:
                # 确定行的日志级别
                level = "INFO"
                for tag in ["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]:
                    if f"[{tag}]" in line:
                        level = tag
                        break
                
                self.crawl_log_text.insert(tk.END, line + "\n", level)
            
            # 清除过滤条件
            self.crawl_log_filter_entry.delete(0, tk.END)
            self.log_crawl_message("已清除过滤", "INFO")
        else:
            self.log_crawl_message("没有应用过滤", "INFO")

    def edit_selected_supplier(self):
        """编辑选中的供应商"""
        selection = self.db_list_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        # 获取选中项的数据
        item = self.db_list_tree.item(selection[0])
        values = item['values']
        
        if len(values) < 3:
            messagebox.showerror("错误", "无法获取供应商信息")
            return
        
        company_name = values[1]  # 店铺名称
        action_url = values[2]    # Action URL
        
        # 从数据库获取完整信息
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 获取供应商基本信息
            cursor.execute('SELECT company_id, company_name, action_url FROM suppliers WHERE company_name = ?', (company_name,))
            supplier_info = cursor.fetchone()
            
            if not supplier_info:
                messagebox.showerror("错误", "未找到供应商信息")
                conn.close()
                return
            
            company_id = supplier_info[0]
            
            # 获取执照图片URL
            cursor.execute('SELECT license_url FROM licenses WHERE supplier_id = ?', (company_id,))
            license_urls = cursor.fetchall()
            
            conn.close()
            
            # 创建编辑弹框
            self.show_edit_dialog(company_id, company_name, action_url, license_urls)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取供应商信息失败: {e}")
    
    def show_edit_dialog(self, company_id, company_name, action_url, license_urls):
        """显示编辑对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑供应商信息")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        
        # 设置对话框居中
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 供应商基本信息
        info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 店铺名称
        ttk.Label(info_frame, text="店铺名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(info_frame, width=50)
        name_entry.insert(0, company_name)
        name_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=(10, 0))
        
        # Action URL
        ttk.Label(info_frame, text="Action URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(info_frame, width=50)
        url_entry.insert(0, action_url)
        url_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=(10, 0))
        
        info_frame.columnconfigure(1, weight=1)
        
        # 执照图片URL
        license_frame = ttk.LabelFrame(main_frame, text="执照图片URL", padding="10")
        license_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建文本框显示执照URL
        license_text = tk.Text(license_frame, height=10, wrap=tk.WORD)
        license_scrollbar = ttk.Scrollbar(license_frame, orient=tk.VERTICAL, command=license_text.yview)
        license_text.configure(yscrollcommand=license_scrollbar.set)
        
        # 显示执照URL
        if license_urls:
            for i, url_tuple in enumerate(license_urls, 1):
                license_text.insert(tk.END, f"执照图片 {i}: {url_tuple[0]}\n\n")
        else:
            license_text.insert(tk.END, "暂无执照图片")
        
        license_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        license_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_changes():
            """保存修改"""
            new_name = name_entry.get().strip()
            new_url = url_entry.get().strip()
            
            if not new_name or not new_url:
                messagebox.showwarning("提示", "店铺名称和Action URL不能为空")
                return
            
            try:
                conn = sqlite3.connect(self.crawler.db_path)
                cursor = conn.cursor()
                
                # 更新供应商信息
                cursor.execute('UPDATE suppliers SET company_name = ?, action_url = ? WHERE company_id = ?', 
                             (new_name, new_url, company_id))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("成功", "供应商信息已更新")
                dialog.destroy()
                self.refresh_db_list_page()  # 刷新列表
                
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        def close_dialog():
            """关闭对话框"""
            dialog.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="取消", command=close_dialog).pack(side=tk.RIGHT)
    
    def delete_selected_supplier(self):
        """删除选中的供应商"""
        selection = self.db_list_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        # 获取选中项的数据
        item = self.db_list_tree.item(selection[0])
        values = item['values']
        
        if len(values) < 2:
            messagebox.showerror("错误", "无法获取供应商信息")
            return
        
        company_name = values[1]  # 店铺名称
        
        # 确认删除
        result = messagebox.askyesno("确认删除", f"确定要删除供应商 '{company_name}' 吗？\n\n此操作将删除该供应商的所有相关数据，包括执照信息和图片记录。")
        
        if not result:
            return
        
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 获取供应商ID
            cursor.execute('SELECT company_id FROM suppliers WHERE company_name = ?', (company_name,))
            supplier_info = cursor.fetchone()
            
            if not supplier_info:
                messagebox.showerror("错误", "未找到供应商信息")
                conn.close()
                return
            
            company_id = supplier_info[0]
            
            # 删除相关数据
            cursor.execute('DELETE FROM licenses WHERE supplier_id = ?', (company_id,))
            cursor.execute('DELETE FROM license_info WHERE supplier_id = ?', (company_id,))
            cursor.execute('DELETE FROM suppliers WHERE company_id = ?', (company_id,))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("成功", f"供应商 '{company_name}' 已删除")
            self.refresh_db_list_page()  # 刷新列表
            
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {e}")
    
    def auto_recognize_local_files(self):
        """自动识别本地文件并更新数据库"""
        try:
            # 获取保存路径
            base_path = self.save_path_var.get().strip()
            if not base_path:
                base_path = "./license_files"
            
            # 检查路径是否存在
            if not os.path.exists(base_path):
                messagebox.showwarning("提示", f"路径不存在: {base_path}")
                return
            
            # 只扫描保存路径
            paths_to_scan = []
            
            if os.path.exists(base_path):
                paths_to_scan.append(base_path)
            
            if not paths_to_scan:
                messagebox.showwarning("提示", "没有找到可扫描的目录")
                return
            
            self.log_extract_message("开始自动识别本地文件...", "INFO")
            
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            total_recognized = 0
            total_updated = 0
            
            for scan_path in paths_to_scan:
                self.log_extract_message(f"扫描路径: {scan_path}", "INFO")
                
                # 扫描所有子目录
                for root, dirs, files in os.walk(scan_path):
                    # 跳过根目录
                    if root == scan_path:
                        continue
                    
                    # 获取目录名（可能包含分类信息）
                    dir_name = os.path.basename(root)
                    
                    # 检查是否有公司子目录
                    company_dirs = [d for d in dirs if os.path.isdir(os.path.join(root, d))]
                    
                    if company_dirs:
                        # 这是一个分类目录，包含公司子目录
                        category_name = dir_name
                        self.log_extract_message(f"发现分类目录: {category_name}", "INFO")
                        
                        for company_dir in company_dirs:
                            company_name = company_dir
                            company_path = os.path.join(root, company_dir)
                            
                            # 检查公司目录下是否有执照相关文件
                            license_files = []
                            for file in os.listdir(company_path):
                                if any(keyword in file.lower() for keyword in ['执照', 'license', '营业', '证书']):
                                    license_files.append(file)
                            
                            if license_files:
                                total_recognized += 1
                                
                                # 查找数据库中是否存在该公司（支持多种匹配方式）
                                # 1. 精确匹配
                                cursor.execute('SELECT company_id, license_extracted FROM suppliers WHERE company_name = ?', (company_name,))
                                supplier_info = cursor.fetchone()
                                
                                # 2. 如果精确匹配失败，尝试带句号匹配
                                if not supplier_info:
                                    cursor.execute('SELECT company_id, license_extracted FROM suppliers WHERE company_name = ?', (company_name + '.',))
                                    supplier_info = cursor.fetchone()
                                
                                # 3. 如果仍然失败，尝试模糊匹配（处理轻微拼写差异）
                                if not supplier_info:
                                    cursor.execute('SELECT company_id, license_extracted, company_name FROM suppliers WHERE company_name LIKE ?', (f'%{company_name}%',))
                                    fuzzy_results = cursor.fetchall()
                                    if fuzzy_results:
                                        # 选择最相似的匹配（长度最接近的）
                                        best_match = min(fuzzy_results, key=lambda x: abs(len(x[2]) - len(company_name)))
                                        supplier_info = (best_match[0], best_match[1])
                                        self.log_extract_message(f"模糊匹配成功: {company_name} -> {best_match[2]}", "INFO")
                                
                                if supplier_info:
                                    company_id, license_extracted = supplier_info
                                    
                                    # 如果还未标记为已提取，则更新
                                    if not license_extracted:
                                        cursor.execute('UPDATE suppliers SET license_extracted = TRUE, save_path = ? WHERE company_id = ?', 
                                                     (company_path, company_id))
                                        total_updated += 1
                                        self.log_extract_message(f"已更新: {company_name} (分类: {category_name})", "SUCCESS")
                                    else:
                                        self.log_extract_message(f"已存在: {company_name} (分类: {category_name})", "INFO")
                                else:
                                    self.log_extract_message(f"数据库中未找到: {company_name}", "WARNING")
                    else:
                        # 检查当前目录是否直接包含执照文件（可能是公司目录）
                        license_files = []
                        for file in files:
                            if any(keyword in file.lower() for keyword in ['执照', 'license', '营业', '证书']):
                                license_files.append(file)
                        
                        if license_files:
                            company_name = dir_name
                            total_recognized += 1
                            
                            # 查找数据库中是否存在该公司（支持多种匹配方式）
                            # 1. 精确匹配
                            cursor.execute('SELECT company_id, license_extracted FROM suppliers WHERE company_name = ?', (company_name,))
                            supplier_info = cursor.fetchone()
                            
                            # 2. 如果精确匹配失败，尝试带句号匹配
                            if not supplier_info:
                                cursor.execute('SELECT company_id, license_extracted FROM suppliers WHERE company_name = ?', (company_name + '.',))
                                supplier_info = cursor.fetchone()
                            
                            # 3. 如果仍然失败，尝试模糊匹配（处理轻微拼写差异）
                            if not supplier_info:
                                cursor.execute('SELECT company_id, license_extracted, company_name FROM suppliers WHERE company_name LIKE ?', (f'%{company_name}%',))
                                fuzzy_results = cursor.fetchall()
                                if fuzzy_results:
                                    # 选择最相似的匹配（长度最接近的）
                                    best_match = min(fuzzy_results, key=lambda x: abs(len(x[2]) - len(company_name)))
                                    supplier_info = (best_match[0], best_match[1])
                                    self.log_extract_message(f"模糊匹配成功: {company_name} -> {best_match[2]}", "INFO")
                            
                            if supplier_info:
                                company_id, license_extracted = supplier_info
                                
                                # 如果还未标记为已提取，则更新
                                if not license_extracted:
                                    cursor.execute('UPDATE suppliers SET license_extracted = TRUE, save_path = ? WHERE company_id = ?', 
                                                 (root, company_id))
                                    total_updated += 1
                                    self.log_extract_message(f"已更新: {company_name}", "SUCCESS")
                                else:
                                    self.log_extract_message(f"已存在: {company_name}", "INFO")
                            else:
                                self.log_extract_message(f"数据库中未找到: {company_name}", "WARNING")
            
            conn.commit()
            conn.close()
            
            self.log_extract_message(f"自动识别完成！识别到 {total_recognized} 个已有执照文件，更新了 {total_updated} 条记录", "SUCCESS")
            
            if total_updated > 0:
                messagebox.showinfo("完成", f"自动识别完成！\n\n识别到 {total_recognized} 个已有执照文件\n更新了 {total_updated} 条数据库记录")
            else:
                messagebox.showinfo("完成", f"自动识别完成！\n\n识别到 {total_recognized} 个已有执照文件\n但没有需要更新的记录")
                
        except Exception as e:
            self.log_extract_message(f"自动识别失败: {e}", "ERROR")
            messagebox.showerror("错误", f"自动识别失败: {e}")

    def show_batch_crawl_dialog(self):
        """显示一键爬取对话框"""
        categories = self.load_gateway_categories()
        if not categories:
            messagebox.showwarning("提示", "无法加载分类数据，请确保gatewayService.json文件存在")
            return
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("一键爬取设置")
        dialog.geometry("600x700")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 关键词选择区域
        keyword_frame = ttk.LabelFrame(dialog, text="选择关键词", padding="10")
        keyword_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 搜索框
        search_frame = ttk.Frame(keyword_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        
        # 全选/取消全选按钮
        select_frame = ttk.Frame(search_frame)
        select_frame.pack(side=tk.RIGHT)
        
        ttk.Button(select_frame, text="全选", command=lambda: self.select_all_keywords(tree)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(select_frame, text="取消全选", command=lambda: self.deselect_all_keywords(tree)).pack(side=tk.LEFT)
        
        # 关键词列表
        list_frame = ttk.Frame(keyword_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview来显示分层结构
        tree = ttk.Treeview(list_frame, columns=('selected',), show='tree headings')
        tree.heading('#0', text='分类名称')
        tree.heading('selected', text='选择')
        tree.column('#0', width=400)
        tree.column('selected', width=80)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 存储选中状态
        self.selected_keywords = set()
        
        # 填充数据
        def populate_tree():
            for category in categories:
                display_name = category['display']
                category_name = category['name']
                level = int(category['level'])
                
                # 根据层级确定父节点
                if level == 1:
                    parent = ''
                    item_id = tree.insert(parent, 'end', text=display_name, values=('',), tags=(category_name,))
                    # 一级分类默认展开
                    tree.item(item_id, open=True)
                else:
                    # 找到合适的父节点（这里简化处理，实际可能需要更复杂的逻辑）
                    parent = ''
                    for item in tree.get_children():
                        if tree.item(item)['text'].strip() in display_name:
                            parent = item
                            break
                    
                    item_id = tree.insert(parent, 'end', text=display_name, values=('',), tags=(category_name,))
        
        populate_tree()
        
        # 绑定点击事件
        def on_item_click(event):
            item = tree.selection()[0] if tree.selection() else None
            if item:
                category_name = tree.item(item)['tags'][0] if tree.item(item)['tags'] else tree.item(item)['text'].strip()
                if category_name in self.selected_keywords:
                    self.selected_keywords.remove(category_name)
                    tree.set(item, 'selected', '')
                else:
                    self.selected_keywords.add(category_name)
                    tree.set(item, 'selected', '✓')
        
        tree.bind('<Button-1>', on_item_click)
        
        # 搜索功能
        def filter_tree():
            search_text = search_var.get().lower()
            for item in tree.get_children(''):
                self.filter_tree_item(tree, item, search_text)
        
        search_var.trace('w', lambda *args: filter_tree())
        
        # 设置区域
        settings_frame = ttk.LabelFrame(dialog, text="爬取设置", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 页面范围
        page_frame = ttk.Frame(settings_frame)
        page_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(page_frame, text="页面范围:").pack(side=tk.LEFT)
        start_page_var = tk.StringVar(value="1")
        ttk.Entry(page_frame, textvariable=start_page_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(page_frame, text="到").pack(side=tk.LEFT, padx=(5, 0))
        end_page_var = tk.StringVar(value="5")
        ttk.Entry(page_frame, textvariable=end_page_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # 线程数设置
        thread_frame = ttk.Frame(settings_frame)
        thread_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(thread_frame, text="并发线程数:").pack(side=tk.LEFT)
        self.ocr_thread_count_var = tk.StringVar(value="3")
        ttk.Entry(thread_frame, textvariable=self.ocr_thread_count_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(thread_frame, text="(建议1-5个)").pack(side=tk.LEFT, padx=(5, 0))
        
        # 间隔设置
        delay_frame = ttk.Frame(settings_frame)
        delay_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(delay_frame, text="关键词间隔(秒):").pack(side=tk.LEFT)
        delay_var = tk.StringVar(value="2")
        ttk.Entry(delay_frame, textvariable=delay_var, width=8).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(delay_frame, text="(避免被封IP)").pack(side=tk.LEFT, padx=(5, 0))
        
        # 缓存模式设置
        cache_frame = ttk.LabelFrame(settings_frame, text="缓存模式", padding="5")
        cache_frame.pack(fill=tk.X, pady=10)
        
        cache_mode_var = tk.BooleanVar(value=True)
        cache_check = ttk.Checkbutton(cache_frame, text="启用缓存模式（先保存到文件，每5分钟生成一个新文件）", variable=cache_mode_var)
        cache_check.pack(anchor=tk.W)
        
        # 缓存文件路径
        cache_path_frame = ttk.Frame(cache_frame)
        cache_path_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(cache_path_frame, text="缓存文件:").pack(side=tk.LEFT)
        cache_file_var = tk.StringVar(value="cache/suppliers_cache.json")
        cache_file_entry = ttk.Entry(cache_path_frame, textvariable=cache_file_var, width=40)
        cache_file_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        
        def select_cache_file():
            filename = filedialog.asksaveasfilename(
                title="选择缓存文件",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile="suppliers_cache.json"
            )
            if filename:
                cache_file_var.set(filename)
        
        ttk.Button(cache_path_frame, text="选择", command=select_cache_file).pack(side=tk.RIGHT)
        
        # 按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def start_batch_crawl():
            if not self.selected_keywords:
                messagebox.showwarning("提示", "请至少选择一个关键词")
                return
            
            try:
                start_page = int(start_page_var.get())
                end_page = int(end_page_var.get())
                thread_count = int(self.ocr_thread_count_var.get())
                delay = float(delay_var.get())
                
                if start_page <= 0 or end_page <= 0:
                    messagebox.showerror("错误", "页面范围必须大于0")
                    return
                if start_page > end_page:
                    messagebox.showerror("错误", "起始页面不能大于结束页面")
                    return
                if thread_count <= 0 or thread_count > 10:
                    messagebox.showerror("错误", "线程数必须在1-10之间")
                    return
                if delay < 0:
                    messagebox.showerror("错误", "间隔时间不能为负数")
                    return
                    
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                return
            
            # 获取缓存模式设置
            cache_mode = cache_mode_var.get()
            cache_file = cache_file_var.get().strip() if cache_mode else None
            
            if cache_mode and not cache_file:
                messagebox.showerror("错误", "启用缓存模式时必须指定缓存文件路径")
                return
            
            dialog.destroy()
            self.start_batch_crawl_process(list(self.selected_keywords), start_page, end_page, thread_count, delay, cache_mode, cache_file)
        
        ttk.Button(button_frame, text="开始爬取", command=start_batch_crawl).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # 设置焦点
        search_entry.focus_set()
    
    def select_all_keywords(self, tree):
        """全选关键词"""
        for item in tree.get_children(''):
            self.select_tree_item(tree, item, True)
    
    def deselect_all_keywords(self, tree):
        """取消全选关键词"""
        self.selected_keywords.clear()
        for item in tree.get_children(''):
            self.select_tree_item(tree, item, False)
    
    def select_tree_item(self, tree, item, select):
        """递归选择/取消选择树项"""
        category_name = tree.item(item)['tags'][0] if tree.item(item)['tags'] else tree.item(item)['text'].strip()
        
        if select:
            self.selected_keywords.add(category_name)
            tree.set(item, 'selected', '✓')
        else:
            tree.set(item, 'selected', '')
        
        # 递归处理子项
        for child in tree.get_children(item):
            self.select_tree_item(tree, child, select)
    
    def filter_tree_item(self, tree, item, search_text):
        """过滤树项"""
        item_text = tree.item(item)['text'].lower()
        show_item = search_text in item_text
        
        # 检查子项
        children = tree.get_children(item)
        for child in children:
            child_visible = self.filter_tree_item(tree, child, search_text)
            show_item = show_item or child_visible
        
        # 显示或隐藏项目
        if show_item:
            tree.reattach(item, tree.parent(item), 'end')
        else:
            tree.detach(item)
        
        return show_item
    
    def start_batch_crawl_process(self, keywords, start_page, end_page, thread_count, delay, cache_mode=False, cache_file=None):
        """开始批量爬取过程"""
        # 禁用相关按钮
        self.start_crawl_btn.config(state=tk.DISABLED)
        self.batch_crawl_btn.config(state=tk.DISABLED)
        self.stop_crawl_btn.config(state=tk.NORMAL)
        
        # 清空日志
        self.crawl_log_text.delete("1.0", tk.END)
        
        # 设置进度条
        total_keywords = len(keywords)
        total_pages = (end_page - start_page + 1) * total_keywords
        self.progress['maximum'] = total_pages
        self.progress['value'] = 0
        
        self.log_crawl_message(f"开始一键爬取，共 {total_keywords} 个关键词，每个关键词爬取 {start_page}-{end_page} 页", "INFO")
        self.log_crawl_message(f"并发线程数: {thread_count}，关键词间隔: {delay} 秒", "INFO")
        
        # 保存缓存模式设置
        self.cache_mode = cache_mode
        self.cache_file = cache_file
        
        if cache_mode:
            self.log_crawl_message(f"启用缓存模式，数据将先保存到文件，每5分钟生成一个新文件", "INFO")
            self.log_crawl_message(f"缓存文件基础路径: {cache_file}", "INFO")
        
        # 在新线程中运行批量爬取
        self.batch_crawl_thread = threading.Thread(
            target=self.run_batch_crawl, 
            args=(keywords, start_page, end_page, thread_count, delay, cache_mode, cache_file)
        )
        self.batch_crawl_thread.daemon = True
        self.batch_crawl_thread.start()
    
    def run_batch_crawl(self, keywords, start_page, end_page, thread_count, delay, cache_mode=False, cache_file=None):
        """运行批量爬取"""
        try:
            # 获取代理设置
            proxy = None
            if self.use_proxy_var.get():
                proxy = self.proxy
            
            # 获取跳过重复选项
            skip_duplicates = self.skip_duplicates_var.get()
            
            total_suppliers = 0
            current_keyword = 0
            
            for keyword in keywords:
                current_keyword += 1
                self.root.after(0, lambda k=keyword, c=current_keyword, t=len(keywords): 
                    self.log_crawl_message(f"[{c}/{t}] 开始爬取关键词: {k}", "INFO"))
                
                try:
                    # 运行异步爬虫
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 创建进度回调
                    def progress_callback(current, total, message=""):
                        progress_value = ((current_keyword - 1) * (end_page - start_page + 1) + current)
                        self.root.after(0, lambda: self.progress.config(value=progress_value))
                        if message:
                            self.root.after(0, lambda m=message: self.log_crawl_message(m, "INFO"))
                    
                    # 创建爬虫实例
                    crawler = AlibabaSupplierCrawler()
                    
                    # 设置进度回调
                    crawler.progress_callback = progress_callback
                    
                    # 创建日志回调
                    def log_callback(message, level="INFO"):
                        self.root.after(0, lambda m=message, l=level: self.log_crawl_message(m, l))
                    
                    suppliers = loop.run_until_complete(
                        crawler.crawl_suppliers_range(
                            keyword, start_page, end_page, proxy, skip_duplicates=skip_duplicates, 
                            log_callback=log_callback, save_to_file=cache_mode, cache_file=cache_file
                        )
                    )
                    
                    total_suppliers += len(suppliers)
                    self.root.after(0, lambda k=keyword, count=len(suppliers): 
                        self.log_crawl_message(f"关键词 '{k}' 爬取完成，获取 {count} 个供应商", "SUCCESS"))
                    
                    # 关键词间隔
                    if current_keyword < len(keywords) and delay > 0:
                        self.root.after(0, lambda d=delay: 
                            self.log_crawl_message(f"等待 {d} 秒后继续下一个关键词...", "INFO"))
                        import time
                        time.sleep(delay)
                        
                except Exception as e:
                    self.root.after(0, lambda k=keyword, err=str(e): 
                        self.log_crawl_message(f"关键词 '{k}' 爬取失败: {err}", "ERROR"))
                    continue
            
            # 完成
            self.root.after(0, lambda total=total_suppliers: 
                self.batch_crawl_finished(total))
                
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.batch_crawl_error(err))
    
    def batch_crawl_finished(self, total_suppliers):
        """批量爬取完成"""
        self.start_crawl_btn.config(state=tk.NORMAL)
        self.batch_crawl_btn.config(state=tk.NORMAL)
        self.stop_crawl_btn.config(state=tk.DISABLED)
        
        # 如果是缓存模式，提示使用批量入库功能
        if hasattr(self, 'cache_mode') and self.cache_mode:
            self.log_crawl_message(f"一键爬取完成！缓存模式共获取 {total_suppliers} 个供应商", "SUCCESS")
            self.log_crawl_message("数据已保存到缓存文件，请使用'批量入库'按钮导入数据库", "INFO")
            self.status_label.config(text="一键爬取完成")
            messagebox.showinfo("完成", f"一键爬取完成！\n缓存模式共获取 {total_suppliers} 个供应商\n数据已保存到缓存文件，请使用'批量入库'按钮导入数据库")
        else:
            self.log_crawl_message(f"一键爬取完成！总共获取 {total_suppliers} 个供应商", "SUCCESS")
            self.status_label.config(text="一键爬取完成")
            
            # 刷新数据库列表
            self.refresh_db_list()
            
            messagebox.showinfo("完成", f"一键爬取完成！\n总共获取 {total_suppliers} 个供应商")
    
    def batch_crawl_error(self, error):
        """批量爬取错误"""
        self.start_crawl_btn.config(state=tk.NORMAL)
        self.batch_crawl_btn.config(state=tk.NORMAL)
        self.stop_crawl_btn.config(state=tk.DISABLED)
        
        # 清理缓存模式状态
        if hasattr(self, 'cache_mode'):
            self.cache_mode = False
        
        self.log_crawl_message(f"一键爬取失败: {error}", "ERROR")
        messagebox.showerror("错误", f"一键爬取失败: {error}")
    


    def show_batch_save_dialog(self):
        """显示批量入库对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("批量入库")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 缓存文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="缓存文件选择", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 缓存文件列表
        cache_dir = "cache"
        cache_files = []
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
        
        if not cache_files:
            ttk.Label(file_frame, text="未找到缓存文件", foreground="red").pack()
            return
        
        # 文件列表框
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview显示文件信息
        columns = ('文件名', '大小', '修改时间')
        file_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            file_tree.heading(col, text=col)
            file_tree.column(col, width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=file_tree.yview)
        file_tree.configure(yscrollcommand=scrollbar.set)
        
        file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充文件信息
        for filename in cache_files:
            filepath = os.path.join(cache_dir, filename)
            try:
                stat = os.stat(filepath)
                size = f"{stat.st_size / 1024:.1f} KB"
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                file_tree.insert('', tk.END, values=(filename, size, mtime))
            except:
                file_tree.insert('', tk.END, values=(filename, "未知", "未知"))
        
        # 选择全部复选框
        select_all_var = tk.BooleanVar(value=True)
        select_all_check = ttk.Checkbutton(file_frame, text="选择全部文件", variable=select_all_var)
        select_all_check.pack(pady=(10, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def start_batch_save():
            """开始批量入库"""
            selected_files = []
            
            if select_all_var.get():
                selected_files = cache_files
            else:
                # 获取选中的文件
                for item in file_tree.selection():
                    values = file_tree.item(item, 'values')
                    if values:
                        selected_files.append(values[0])
            
            if not selected_files:
                messagebox.showwarning("警告", "请选择要入库的文件")
                return
            
            dialog.destroy()
            self.start_batch_save_process(selected_files)
        
        ttk.Button(button_frame, text="开始入库", command=start_batch_save).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)

    def start_batch_save_process(self, cache_files):
        """开始批量入库处理"""
        self.log_crawl_message(f"[批量入库] 开始处理 {len(cache_files)} 个缓存文件", "INFO")
        
        def run_batch_save():
            total_saved = 0
            total_skipped = 0
            
            for i, filename in enumerate(cache_files, 1):
                filepath = os.path.join("cache", filename)
                
                try:
                    self.root.after(0, lambda f=filename, idx=i, total=len(cache_files): 
                        self.log_crawl_message(f"[批量入库] 处理文件 {idx}/{total}: {f}", "INFO"))
                    
                    # 使用爬虫的批量入库方法
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    saved_count = loop.run_until_complete(
                        self.crawler.batch_save_from_cache_file(
                            filepath,
                            skip_duplicates=True,
                            log_callback=lambda msg, level="INFO": self.root.after(0, lambda: self.log_crawl_message(f"[批量入库] {msg}", level))
                        )
                    )
                    skipped_count = 0  # batch_save_from_cache_file 只返回保存数量
                    
                    total_saved += saved_count
                    total_skipped += skipped_count
                    
                    self.root.after(0, lambda f=filename, s=saved_count, sk=skipped_count: 
                        self.log_crawl_message(f"[批量入库] {f} 完成: 保存 {s} 条，跳过 {sk} 条", "SUCCESS"))
                    
                except Exception as e:
                    self.root.after(0, lambda f=filename, err=str(e): 
                        self.log_crawl_message(f"[批量入库] {f} 失败: {err}", "ERROR"))
            
            # 完成后刷新数据库列表
            if total_saved > 0:
                self.root.after(0, lambda: self.refresh_db_list())
            
            self.root.after(0, lambda: self.log_crawl_message(
                f"[批量入库] 全部完成！总计保存 {total_saved} 条，跳过 {total_skipped} 条", "SUCCESS"))
        
        # 在新线程中执行批量入库
        batch_thread = threading.Thread(target=run_batch_save)
        batch_thread.daemon = True
        batch_thread.start()

    def start_ocr_recognition(self):
        """启动OCR识别"""
        if self.ocr_running:
            messagebox.showwarning("警告", "OCR识别正在进行中，请等待完成或停止后再试")
            return
        
        try:
            ocr_count = int(self.ocr_count_var.get())
            ocr_threads = int(self.ocr_threads_var.get())
            
            if ocr_count <= 0:
                messagebox.showerror("错误", "识别数量必须大于0")
                return
            
            if ocr_threads <= 0 or ocr_threads > 10:
                messagebox.showerror("错误", "OCR线程数必须在1-10之间")
                return
                
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        # 启动OCR识别线程
        self.ocr_running = True
        self.ocr_recognize_btn.config(state=tk.DISABLED)
        self.stop_ocr_btn.config(state=tk.NORMAL)
        
        self.ocr_thread = threading.Thread(
            target=self.run_ocr_recognition,
            args=(ocr_count, ocr_threads),
            daemon=True
        )
        self.ocr_thread.start()
        
        self.log_ocr_message(f"开始OCR识别，目标数量: {ocr_count}，线程数: {ocr_threads}", "INFO")
    
    def stop_ocr_recognition(self):
        """停止OCR识别"""
        if self.ocr_running:
            self.ocr_running = False
            self.log_ocr_message("正在停止OCR识别...", "WARNING")
    
    def run_ocr_recognition(self, ocr_count, ocr_threads):
        """运行OCR识别的主逻辑"""
        try:
            # 导入OCR模块
            import sys
            ocr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr')
            if ocr_path not in sys.path:
                sys.path.append(ocr_path)
            
            from ocr_baidu_api import BaiduLicenseOCRAPI
            
            # 获取未使用的供应商数据
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 查询未使用且有执照的供应商
            cursor.execute("""
                SELECT s.id, s.company_name, l.license_url 
                FROM suppliers s 
                JOIN licenses l ON s.company_id = l.supplier_id 
                WHERE s.is_used = 0 AND s.ocr_recognition_status = 'pending'
                AND l.license_url IS NOT NULL AND l.license_url != ''
                LIMIT ?
            """, (ocr_count,))
            
            suppliers_data = cursor.fetchall()
            conn.close()
            
            if not suppliers_data:
                self.root.after(0, lambda: self.log_ocr_message("没有找到需要识别的供应商数据", "WARNING"))
                return
            
            self.root.after(0, lambda: self.log_ocr_message(f"找到 {len(suppliers_data)} 个供应商需要识别", "INFO"))
            
            # 初始化OCR
            ocr = BaiduLicenseOCRAPI()
            
            # 使用线程池进行批量识别
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import time
            
            success_count = 0
            error_count = 0
            total_count = len(suppliers_data)
            
            # 初始化进度
            self.root.after(0, lambda: self.ocr_progress.configure(maximum=total_count, value=0))
            self.root.after(0, lambda: self.ocr_status_label.config(text="开始识别..."))
            self.root.after(0, lambda: self.ocr_detail_label.config(text=f"总计: {total_count} 个供应商"))
            
            with ThreadPoolExecutor(max_workers=ocr_threads) as executor:
                # 提交所有任务
                future_to_supplier = {
                    executor.submit(self.process_single_ocr, ocr, supplier_id, supplier_name, license_url): 
                    (supplier_id, supplier_name) 
                    for supplier_id, supplier_name, license_url in suppliers_data
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_supplier):
                    if not self.ocr_running:
                        break
                    
                    supplier_id, supplier_name = future_to_supplier[future]
                    try:
                        result = future.result()
                        if result['success']:
                            success_count += 1
                            self.root.after(0, lambda name=supplier_name: 
                                self.log_ocr_message(f"✓ {name} 识别成功", "SUCCESS"))
                        else:
                            error_count += 1
                            self.root.after(0, lambda name=supplier_name, err=result['error']: 
                                self.log_ocr_message(f"✗ {name} 识别失败: {err}", "ERROR"))
                    except Exception as e:
                        error_count += 1
                        self.root.after(0, lambda name=supplier_name, err=str(e): 
                            self.log_ocr_message(f"✗ {name} 处理异常: {err}", "ERROR"))
                    
                    # 更新进度
                    completed = success_count + error_count
                    progress_percent = (completed / total_count) * 100
                    self.root.after(0, lambda: self.ocr_progress.configure(value=completed))
                    self.root.after(0, lambda: self.ocr_status_label.config(text=f"进度: {completed}/{total_count} ({progress_percent:.1f}%)"))
                    self.root.after(0, lambda: self.ocr_detail_label.config(text=f"成功: {success_count}，失败: {error_count}"))
                    
                    # 添加小延迟避免过于频繁的API调用
                    time.sleep(0.1)
            
            # 完成统计
            self.root.after(0, lambda: self.log_ocr_message(
                f"OCR识别完成！成功: {success_count}，失败: {error_count}", "SUCCESS"))
            
            # 更新OCR进度状态
            self.root.after(0, lambda: self.ocr_progress.configure(value=100))
            self.root.after(0, lambda: self.ocr_status_label.config(text="识别完成"))
            self.root.after(0, lambda: self.ocr_detail_label.config(text=f"成功: {success_count}，失败: {error_count}"))
            
            # 批量导入OCR缓存文件到数据库
            self.root.after(0, lambda: self.batch_import_ocr_cache_to_db())
            
            # 刷新数据库列表
            if success_count > 0:
                self.root.after(0, lambda: self.refresh_db_list_page())
                
        except Exception as e:
            error_msg = f"OCR识别异常: {str(e)}"
            self.root.after(0, lambda: self.log_ocr_message(error_msg, "ERROR"))
        finally:
            # 重置状态
            self.ocr_running = False
            self.root.after(0, lambda: self.ocr_recognize_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_ocr_btn.config(state=tk.DISABLED))
    
    def process_single_ocr(self, ocr, supplier_id, supplier_name, license_url):
        """处理单个供应商的OCR识别"""
        try:
            # 调用OCR识别
            result = ocr.recognize_license_from_url(license_url)
            
            if result['success']:
                # 保存识别结果到company_registration表
                self.save_ocr_result(supplier_id, result['data'])
                
                # 更新suppliers表状态
                self.update_supplier_ocr_status(supplier_id, 'success', True)
                
                return {'success': True}
            else:
                # 标记识别失败
                self.update_supplier_ocr_status(supplier_id, 'error', False)
                return {'success': False, 'error': result.get('error', '未知错误')}
                
        except Exception as e:
            # 标记识别异常
            self.update_supplier_ocr_status(supplier_id, 'error', False)
            return {'success': False, 'error': str(e)}
    
    def save_ocr_result(self, supplier_id, ocr_data):
        """保存OCR识别结果到本地文件（避免数据库锁定问题）"""
        try:
            # 调试信息：打印OCR数据结构
            self.root.after(0, lambda: self.log_ocr_message(f"开始保存OCR结果，供应商ID: {supplier_id}", "INFO"))
            
            # 从OCR结果中提取数据
            data = ocr_data.get('Data', {}) if isinstance(ocr_data, dict) and 'Data' in ocr_data else ocr_data
            
            # 检查关键字段是否存在
            company_name = data.get('公司名称', '')
            registration_number = data.get('注册号', '')
            
            if not company_name and not registration_number:
                # 标记为无法识别
                self.update_supplier_ocr_status(supplier_id, 'failed', False)
                self.root.after(0, lambda: self.log_ocr_message(f"⚠️ 供应商ID {supplier_id} 无法识别关键信息，已标记为失败", "WARNING"))
                return
            
            # 创建OCR结果缓存目录
            cache_dir = os.path.join(os.path.dirname(self.crawler.db_path), 'ocr_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # 生成唯一的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 精确到毫秒
            cache_file = os.path.join(cache_dir, f'ocr_result_{supplier_id}_{timestamp}.json')
            
            # 准备保存的数据
            ocr_result = {
                'supplier_id': supplier_id,
                'profile_id': '',  # profile_id设置为空
                'registration_number': registration_number,
                'company_name': company_name,
                'registered_address': data.get('注册地址', ''),
                'province': data.get('省份', ''),
                'city': data.get('城市', ''),
                'district': data.get('区县', ''),
                'zip_code': data.get('邮编', ''),
                'legal_representative': data.get('法定代表人', ''),
                'issue_date': data.get('发证日期', ''),
                'expiration_date': data.get('到期日期', ''),
                'created_at': datetime.now().isoformat(),
                'raw_data': data  # 保存原始OCR数据
            }
            
            # 保存到本地文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(ocr_result, f, ensure_ascii=False, indent=2)
            
            self.root.after(0, lambda: self.log_ocr_message(f"✓ OCR结果已保存到缓存文件，供应商ID: {supplier_id}", "SUCCESS"))
            
        except Exception as e:
            # 标记为识别失败
            self.update_supplier_ocr_status(supplier_id, 'error', False)
            error_msg = f"保存OCR结果失败: {str(e)}"
            self.root.after(0, lambda: self.log_ocr_message(error_msg, "ERROR"))
    
    def update_supplier_ocr_status(self, supplier_id, status, is_used):
        """更新供应商的OCR识别状态"""
        try:
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE suppliers 
                SET ocr_recognition_status = ?, is_used = ?
                WHERE id = ?
            """, (status, 1 if is_used else 0, supplier_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.root.after(0, lambda: self.log_ocr_message(f"更新供应商状态失败: {str(e)}", "ERROR"))
    
    def batch_import_ocr_cache_to_db(self):
        """批量导入OCR缓存文件到数据库"""
        try:
            cache_dir = os.path.join(os.path.dirname(self.crawler.db_path), 'ocr_cache')
            if not os.path.exists(cache_dir):
                self.root.after(0, lambda: self.log_ocr_message("没有找到OCR缓存目录", "INFO"))
                return
            
            # 获取所有缓存文件
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
            if not cache_files:
                self.root.after(0, lambda: self.log_ocr_message("没有找到OCR缓存文件", "INFO"))
                return
            
            self.root.after(0, lambda: self.log_ocr_message(f"开始批量导入 {len(cache_files)} 个OCR缓存文件到数据库", "INFO"))
            
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            success_count = 0
            error_count = 0
            
            for cache_file in cache_files:
                try:
                    file_path = os.path.join(cache_dir, cache_file)
                    
                    # 读取缓存文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        ocr_result = json.load(f)
                    
                    # 插入到数据库
                    cursor.execute("""
                        INSERT OR REPLACE INTO company_registration (
                            profile_id, supplier_id, registration_number, company_name, 
                            registered_address, province, city, district, zip_code, 
                            legal_representative, issue_date, expiration_date, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ocr_result.get('profile_id', ''),
                        ocr_result.get('supplier_id', ''),
                        ocr_result.get('registration_number', ''),
                        ocr_result.get('company_name', ''),
                        ocr_result.get('registered_address', ''),
                        ocr_result.get('province', ''),
                        ocr_result.get('city', ''),
                        ocr_result.get('district', ''),
                        ocr_result.get('zip_code', ''),
                        ocr_result.get('legal_representative', ''),
                        ocr_result.get('issue_date', ''),
                        ocr_result.get('expiration_date', ''),
                        ocr_result.get('created_at', datetime.now().isoformat())
                    ))
                    
                    # 更新供应商状态为成功
                    cursor.execute("""
                        UPDATE suppliers 
                        SET ocr_recognition_status = 'success', is_used = 1
                        WHERE id = ?
                    """, (ocr_result.get('supplier_id'),))
                    
                    success_count += 1
                    
                    # 删除已处理的缓存文件
                    os.remove(file_path)
                    
                except Exception as e:
                    error_count += 1
                    self.root.after(0, lambda err=str(e), file=cache_file: self.log_ocr_message(f"导入缓存文件 {file} 失败: {err}", "ERROR"))
                    continue
            
            conn.commit()
            conn.close()
            
            self.root.after(0, lambda: self.log_ocr_message(f"✓ 批量导入完成：成功 {success_count} 个，失败 {error_count} 个", "SUCCESS"))
            
            # 刷新OCR结果列表
            self.refresh_ocr_results()
            
        except Exception as e:
            self.root.after(0, lambda: self.log_ocr_message(f"批量导入OCR缓存失败: {str(e)}", "ERROR"))

    def refresh_ocr_results(self):
        """刷新OCR识别结果列表"""
        try:
            # 清空现有数据
            for item in self.ocr_result_tree.get_children():
                self.ocr_result_tree.delete(item)
            
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 查询识别结果
            query = """
            SELECT cr.id, cr.company_name, cr.registration_number, 
                   cr.legal_representative, cr.registered_address, 
                   cr.province, cr.city, cr.district
            FROM company_registration cr
            ORDER BY cr.created_at DESC
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # 添加到列表
            for i, result in enumerate(results, 1):
                company_name = result[1] if result[1] else "未知"
                credit_code = result[2] if result[2] else "未识别"
                legal_rep = result[3] if result[3] else "未识别"
                address = result[4] if result[4] else "未识别"
                province = result[5] if result[5] else ""
                city = result[6] if result[6] else ""
                district = result[7] if result[7] else ""
                
                # 组合省市区信息
                location_parts = [part for part in [province, city, district] if part]
                location = "-".join(location_parts) if location_parts else "未识别"
                
                # 截断长文本
                display_name = company_name[:30] + "..." if len(company_name) > 30 else company_name
                display_address = address[:40] + "..." if len(address) > 40 else address
                
                self.ocr_result_tree.insert('', 'end', values=(
                    i, display_name, credit_code, legal_rep, display_address, location
                ))
            
            conn.close()
            self.log_message(f"识别结果列表已刷新，共 {len(results)} 条记录")
            
        except Exception as e:
            self.log_message(f"刷新识别结果列表失败: {e}")
    
    def export_ocr_results(self):
        """导出OCR识别结果"""
        try:
            # 选择保存文件
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="导出识别结果"
            )
            
            if not file_path:
                return
            
            # 连接数据库
            conn = sqlite3.connect(self.crawler.db_path)
            cursor = conn.cursor()
            
            # 查询所有识别结果
            query = """
            SELECT s.company_name, cr.unified_social_credit_code, cr.legal_representative,
                   cr.registered_capital, cr.establishment_date, cr.business_scope,
                   cr.registration_address, s.ocr_recognition_status, cr.created_at
            FROM company_registration cr
            JOIN suppliers s ON cr.supplier_id = s.id
            ORDER BY cr.created_at DESC
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # 写入CSV文件
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                # 写入标题行
                writer.writerow(['公司名称', '统一社会信用代码', '法定代表人', '注册资本', 
                               '成立日期', '经营范围', '注册地址', '识别状态', '识别时间'])
                # 写入数据行
                for result in results:
                    writer.writerow(result)
            
            conn.close()
            messagebox.showinfo("成功", f"识别结果已导出到: {file_path}")
            self.log_message(f"识别结果已导出到: {file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
            self.log_message(f"导出识别结果失败: {e}")
    
    def clear_ocr_results(self):
        """清空OCR识别结果"""
        if messagebox.askyesno("确认", "确定要清空所有识别结果吗？此操作不可恢复！"):
            try:
                conn = sqlite3.connect(self.crawler.db_path)
                cursor = conn.cursor()
                
                # 清空company_registration表
                cursor.execute('DELETE FROM company_registration')
                
                # 重置suppliers表的OCR状态
                cursor.execute('UPDATE suppliers SET ocr_recognition_status = "pending"')
                
                conn.commit()
                conn.close()
                
                # 刷新列表
                self.refresh_ocr_results()
                self.refresh_db_list_page()
                
                messagebox.showinfo("成功", "识别结果已清空")
                self.log_message("识别结果已清空")
                
            except Exception as e:
                messagebox.showerror("错误", f"清空失败: {e}")
                self.log_message(f"清空识别结果失败: {e}")

    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AlibabaCrawlerGUI()
    app.run()