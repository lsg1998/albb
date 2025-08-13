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
        self.setup_gui()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("阿里巴巴供应商爬虫 - 增强版")
        self.root.geometry("1000x700")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        
        # 代理配置页面
        proxy_frame = ttk.Frame(notebook)
        notebook.add(proxy_frame, text="代理配置")
        
        # 设置数据库列表页面 - 先设置第一个标签页
        self.setup_db_list_page(db_list_frame)
        
        # 设置爬取页面
        self.setup_crawl_page(crawl_frame)
        
        # 设置执照提取页面
        self.setup_license_page(license_frame)
        
        # 设置代理配置页面
        self.setup_proxy_page(proxy_frame)
    
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
        self.keyword_entry = ttk.Entry(input_frame, width=50)
        self.keyword_entry.insert(0, "men's perfume")
        self.keyword_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
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
        self.thread_count_var = tk.StringVar(value="5")
        self.thread_count_entry = ttk.Entry(settings_frame, textvariable=self.thread_count_var, width=10)
        self.thread_count_entry.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 批次间隔设置
        ttk.Label(settings_frame, text="批次间隔(秒):").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(20, 0))
        self.batch_delay_var = tk.StringVar(value="1.0")
        self.batch_delay_entry = ttk.Entry(settings_frame, textvariable=self.batch_delay_var, width=10)
        self.batch_delay_entry.grid(row=0, column=3, sticky=tk.W, pady=2, padx=(10, 0))
        
        # IP检测开关
        self.enable_ip_check_var = tk.BooleanVar(value=True)
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
        
        # 数据库列表
        list_frame = ttk.LabelFrame(parent, text="供应商列表", padding="15")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表
        columns = ('序号', '店铺名称', 'Action URL', '分类', '执照状态', '识别状态')
        self.db_list_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.db_list_tree.heading(col, text=col)
            self.db_list_tree.column(col, width=150)
        
        self.db_list_tree.column('店铺名称', width=250)
        self.db_list_tree.column('Action URL', width=350)
        self.db_list_tree.column('分类', width=150)
        self.db_list_tree.column('执照状态', width=100)
        self.db_list_tree.column('识别状态', width=100)
        
        self.db_list_tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加右键菜单
        self.db_list_context_menu = tk.Menu(self.root, tearoff=0)
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
            
            # 统计数量
            total_count = len(suppliers)
            success_count = sum(1 for s in suppliers if len(s) >= 4 and s[3])
            fail_count = total_count - success_count
            self.db_list_stats_label.config(text=f"总数: {total_count}，已成功: {success_count}，未提取: {fail_count}")
            
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
                    save_path = self.save_path_var.get().strip() if hasattr(self, 'save_path_var') else "result"
                    
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
            cursor.execute('SELECT company_id, company_name, action_url FROM suppliers WHERE license_extracted = 0 OR license_extracted IS NULL')
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
                            WHERE license_extracted = 0 OR license_extracted IS NULL
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
                                            self.root.after(0, lambda: self.log_extract_message(f"成功处理供应商 {processed_count}/{len(suppliers)}", "SUCCESS"))
                                        else:
                                            failed_count += 1
                                            self.root.after(0, lambda: self.log_extract_message(f"处理供应商失败 {processed_count}/{len(suppliers)}", "ERROR"))
                                    except Exception as e:
                                        failed_count += 1
                                        error_msg = str(e)
                                        self.root.after(0, lambda m=error_msg: self.log_extract_message(f"处理供应商时出错: {m}", "ERROR"))
                                
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
            print(f"开始处理: {company_name}")
            
            # 获取供应商页面HTML（禁用IP检测）
            html_content = await self.crawler.fetch_supplier_page(action_url, proxy, session, check_ip=False)
            
            if html_content:
                print(f"  - {company_name}: 成功获取页面")
                
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
                            self.save_license_to_file(company_name, licenses, license_info, save_path)
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
                        self.save_license_to_file(company_name, licenses, license_info, save_path)
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
                        self.save_license_to_file(company_name, licenses, license_info, save_path)
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

    def save_license_to_file(self, company_name, licenses, license_info, save_path):
        """保存执照信息到文件"""
        # 清理文件名
        safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # 创建文件夹
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
                            # 保存图片
                            img_file = os.path.join(folder_path, f"执照图片_{i}.png")
                            with open(img_file, 'wb') as f:
                                f.write(response.content)
                            
                            # 保存图片信息
                            info_file = os.path.join(folder_path, f"执照图片_{i}_信息.txt")
                            with open(info_file, 'w', encoding='utf-8') as f:
                                f.write(f"图片URL: {license_url}\n")
                                f.write(f"图片序号: {i}\n")
                                
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
        messagebox.showinfo("完成", "执照提取完成")
    
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
                        self.save_license_to_file(company_name, licenses, license_info, save_path)
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
            
            base_query += " FROM suppliers"
            
            # 添加过滤条件
            if tab_filter == "success":
                query = f"{base_query} WHERE license_extracted = 1 ORDER BY created_at DESC"
            elif tab_filter == "pending":
                query = f"{base_query} WHERE license_extracted = 0 OR license_extracted IS NULL ORDER BY created_at DESC"
            elif tab_filter == "recognized":
                query = f"{base_query} WHERE license_extracted = 1 AND (registration_no IS NOT NULL AND registration_no != '') ORDER BY created_at DESC"
            else: # all
                query = f"{base_query} ORDER BY created_at DESC"
            
            # 执行查询
            self.log_message(f"执行查询: {query}")
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
                
                # 截断长文本
                display_name = company_name[:50] + "..." if len(company_name) > 50 else company_name
                display_url = action_url[:80] + "..." if len(action_url) > 80 else action_url
                display_category = category_name[:20] + "..." if len(category_name) > 20 else category_name
                
                # 执照状态
                status = "已获取" if license_extracted else "未获取"
                status_color = "green" if license_extracted else "red"
                
                # 识别状态（检查是否有OCR识别结果）
                recognize_status = "未识别"
                try:
                    # 使用supplier_id直接查询
                    cursor.execute('SELECT COUNT(*) FROM license_info WHERE supplier_id = ? AND (registration_no IS NOT NULL AND registration_no != "")', (supplier_id,))
                    ocr_count = cursor.fetchone()[0]
                    recognize_status = "已识别" if ocr_count > 0 else "未识别"
                except Exception as e:
                    # 如果识别状态检查失败，不影响数据显示
                    self.log_message(f"检查识别状态时出错: {e}")
                
                # 插入数据到列表
                try:
                    item = self.db_list_tree.insert('', 'end', values=(i, display_name, display_url, display_category, status, recognize_status))
                    
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
                        self.save_license_to_file(company_name, licenses, license_info, save_path)
                        self.log_message(f"✓ 已保存 {company_name} 的执照信息到 {save_path}")
                    else:
                        self.log_message(f"✗ {company_name} 没有找到执照信息")
                else:
                    self.log_message(f"✗ 识别失败或未找到执照信息")
                    
            except Exception as e:
                self.log_message(f"识别失败: {e}")
                messagebox.showerror("错误", f"识别失败: {e}")
        
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

    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AlibabaCrawlerGUI()
    app.run()