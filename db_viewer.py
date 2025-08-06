import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os

class DatabaseViewer:
    def __init__(self):
        self.setup_gui()
        self.load_databases()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("阿里巴巴数据库查看器")
        self.root.geometry("1200x700")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 数据库选择区域
        db_frame = ttk.LabelFrame(main_frame, text="数据库选择", padding="10")
        db_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(db_frame, text="选择数据库:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.db_var = tk.StringVar()
        self.db_combo = ttk.Combobox(db_frame, textvariable=self.db_var, width=50)
        self.db_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        self.db_combo.bind('<<ComboboxSelected>>', self.on_db_selected)
        
        # 刷新按钮
        refresh_btn = ttk.Button(db_frame, text="刷新数据库列表", command=self.load_databases)
        refresh_btn.grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # 统计信息区域
        stats_frame = ttk.LabelFrame(main_frame, text="统计信息", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_label = ttk.Label(stats_frame, text="请选择数据库查看统计信息")
        self.stats_label.pack()
        
        # 搜索区域
        search_frame = ttk.LabelFrame(main_frame, text="搜索", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="关键词:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        search_btn = ttk.Button(search_frame, text="搜索", command=self.search_data)
        search_btn.grid(row=0, column=2, padx=(10, 0), pady=5)
        
        clear_btn = ttk.Button(search_frame, text="清除搜索", command=self.clear_search)
        clear_btn.grid(row=0, column=3, padx=(10, 0), pady=5)
        
        # 导出按钮
        export_btn = ttk.Button(search_frame, text="导出Excel", command=self.export_excel)
        export_btn.grid(row=0, column=4, padx=(10, 0), pady=5)
        
        # 获取供应商按钮
        fetch_btn = ttk.Button(search_frame, text="获取供应商", command=self.fetch_suppliers)
        fetch_btn.grid(row=0, column=5, padx=(10, 0), pady=5)
        
        # 数据表格区域
        table_frame = ttk.LabelFrame(main_frame, text="商品数据", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建表格
        columns = ('ID', '公司ID', '公司名称', 'Action URL', '执照图片', '执照详情', '执照信息', '创建时间', '操作')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=20)
        
        # 设置列标题
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, minwidth=80)
        
        # 绑定单击事件
        self.tree.bind('<Button-1>', self.on_item_click)
        
        # 设置特定列的宽度
        self.tree.column('公司名称', width=200)
        self.tree.column('Action URL', width=300)
        self.tree.column('执照图片', width=150)
        self.tree.column('执照详情', width=100)
        self.tree.column('执照信息', width=100)
        self.tree.column('创建时间', width=150)
        self.tree.column('操作', width=100)
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # 配置网格权重
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        search_frame.columnconfigure(1, weight=1)
        db_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 双击事件
        self.tree.bind('<Double-1>', self.on_item_double_click)
        
        # 单击事件 - 处理提取执照按钮
        self.tree.bind('<Button-1>', self.on_item_click)
    
    def load_databases(self):
        """加载数据库列表"""
        databases = []
        
        # 查找当前目录下的所有.db文件
        for file in os.listdir('.'):
            if file.endswith('.db'):
                databases.append(file)
        
        self.db_combo['values'] = databases
        if databases:
            self.db_combo.set(databases[0])
            self.on_db_selected()
    
    def on_db_selected(self, event=None):
        """数据库选择事件"""
        selected_db = self.db_var.get()
        if selected_db:
            self.load_data(selected_db)
    
    def load_data(self, db_path):
        """加载数据库数据"""
        try:
            conn = sqlite3.connect(db_path)
            
            # 检查suppliers表是否存在
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers';")
            if not cursor.fetchone():
                messagebox.showwarning("警告", "数据库中没有suppliers表")
                return
            
            # 获取供应商数据和执照图片数据
            query = """
                SELECT s.id, s.company_id, s.company_name, s.action_url, s.created_at,
                       COUNT(l.id) as license_count,
                       GROUP_CONCAT(l.license_url, '|') as license_urls,
                       CASE WHEN li.id IS NOT NULL THEN '有' ELSE '无' END as has_license_info
                FROM suppliers s
                LEFT JOIN licenses l ON s.company_id = l.supplier_id
                LEFT JOIN license_info li ON s.company_id = li.supplier_id
                GROUP BY s.id, s.company_id, s.company_name, s.action_url, s.created_at
                ORDER BY s.created_at DESC
            """
            df = pd.read_sql_query(query, conn)
            
            conn.close()
            
            # 清空表格
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 填充数据
            for index, row in df.iterrows():
                # 格式化时间
                created_at = row['created_at']
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                # 截断长文本
                company_name = str(row['company_name'])[:50] if pd.notna(row['company_name']) else ''
                action_url = str(row['action_url'])[:80] if pd.notna(row['action_url']) else ''
                
                # 执照图片数量和详情
                license_count = row['license_count']
                license_text = f"{license_count} 张" if license_count > 0 else "无"
                license_urls = row['license_urls'] if pd.notna(row['license_urls']) else ""
                
                # 执照详情按钮文本
                license_detail_text = "查看详情" if license_count > 0 else "无"
                
                # 执照信息状态
                has_license_info = row.get('has_license_info', '无')
                
                self.tree.insert('', 'end', values=(
                    row['id'],
                    row['company_id'],
                    company_name,
                    action_url,
                    license_text,
                    license_detail_text,
                    has_license_info,
                    created_at,
                    "提取执照"
                ))
            
            # 更新统计信息
            self.update_stats(df, db_path)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载数据库失败: {e}")
    
    def update_stats(self, df, db_path):
        """更新统计信息"""
        stats_text = f"""
数据库: {db_path}
总记录数: {len(df)} 条
数据列数: {len(df.columns)} 列
最新记录: {df['created_at'].max() if 'created_at' in df.columns else 'N/A'}
        """
        self.stats_label.config(text=stats_text)
    
    def search_data(self):
        """搜索数据"""
        keyword = self.search_entry.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return
        
        selected_db = self.db_var.get()
        if not selected_db:
            messagebox.showwarning("警告", "请先选择数据库")
            return
        
        try:
            conn = sqlite3.connect(selected_db)
            cursor = conn.cursor()
            
            # 获取表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            if not tables:
                return
            
            table_name = tables[0][0]
            
            # 搜索查询
            query = f"""
            SELECT * FROM {table_name} 
            WHERE product_id LIKE ? OR shop_name LIKE ? OR detail_url LIKE ?
            """
            
            search_pattern = f"%{keyword}%"
            cursor.execute(query, (search_pattern, search_pattern, search_pattern))
            results = cursor.fetchall()
            
            # 获取列名
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 清空表格
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 填充搜索结果
            for row in results:
                values = []
                for i, col in enumerate(columns):
                    if col == 'created_at':
                        try:
                            dt = datetime.fromisoformat(row[i].replace('Z', '+00:00'))
                            values.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
                        except:
                            values.append(str(row[i]))
                    elif col in ['trade_assurance', 'gold_supplier', 'assessed_supplier']:
                        values.append('是' if row[i] else '否')
                    else:
                        values.append(str(row[i]) if row[i] is not None else '')
                
                self.tree.insert('', 'end', values=values)
            
            conn.close()
            
            messagebox.showinfo("搜索结果", f"找到 {len(results)} 条匹配记录")
            
        except Exception as e:
            messagebox.showerror("错误", f"搜索失败: {e}")
    
    def clear_search(self):
        """清除搜索"""
        self.search_entry.delete(0, tk.END)
        self.on_db_selected()
    
    def export_excel(self):
        """导出Excel"""
        selected_db = self.db_var.get()
        if not selected_db:
            messagebox.showwarning("警告", "请先选择数据库")
            return
        
        try:
            # 选择保存路径
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="保存Excel文件"
            )
            
            if file_path:
                conn = sqlite3.connect(selected_db)
                cursor = conn.cursor()
                
                # 获取表名
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                if not tables:
                    return
                
                table_name = tables[0][0]
                
                # 读取数据
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # 导出到Excel
                df.to_excel(file_path, index=False)
                
                conn.close()
                
                messagebox.showinfo("成功", f"数据已导出到: {file_path}")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def on_item_click(self, event):
        """单击事件处理"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            
            if item and column == '#9':  # 操作列
                self.extract_license_for_item(item)
            elif item and column == '#6':  # 执照详情列
                self.show_license_details(item)
            elif item and column == '#7':  # 执照信息列
                self.show_license_info(item)
    
    def extract_license_for_item(self, item):
        """为指定供应商提取执照图片"""
        values = self.tree.item(item)['values']
        if not values:
            return
        
        company_id = values[1]
        company_name = values[2]
        action_url = values[3]
        
        # 确认对话框
        result = messagebox.askyesno("确认", f"是否要为供应商 {company_name} 提取执照图片？")
        if not result:
            return
        
        # 在新线程中执行提取
        import threading
        import asyncio
        from alibaba_supplier_crawler import AlibabaSupplierCrawler
        
        def run_extract():
            try:
                # 创建爬虫实例
                crawler = AlibabaSupplierCrawler()
                
                # 设置代理 - 使用新隧道代理 (SOCKS5格式)
                proxy = {
                    'host': 'y900.kdltps.com',
                    'port': 15818,
                    'username': 't15395136610470',
                    'password': 'kyhxo4pj'
                }
                
                # 运行异步提取
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    crawler.extract_single_license(company_id, company_name, action_url, proxy)
                )
                
                if result:
                    messagebox.showinfo("成功", f"成功为 {company_name} 提取执照图片")
                    # 刷新数据
                    self.load_data(self.db_var.get())
                else:
                    messagebox.showwarning("警告", f"为 {company_name} 提取执照图片失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"提取失败: {e}")
        
        # 启动线程
        thread = threading.Thread(target=run_extract)
        thread.daemon = True
        thread.start()
    
    def show_license_details(self, item):
        """显示执照图片详情"""
        values = self.tree.item(item)['values']
        if not values:
            return
        
        company_id = values[1]
        company_name = values[2]
        
        # 从数据库获取执照图片信息和执照信息
        conn = sqlite3.connect(self.db_var.get())
        cursor = conn.cursor()
        
        # 获取执照图片
        cursor.execute('''
            SELECT license_name, license_url, file_id 
            FROM licenses 
            WHERE supplier_id = ?
        ''', (company_id,))
        
        licenses = cursor.fetchall()
        
        # 获取执照信息
        cursor.execute('''
            SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                   registered_capital, country_territory, registered_address,
                   year_established, legal_form, legal_representative
            FROM license_info 
            WHERE supplier_id = ?
        ''', (company_id,))
        
        license_info = cursor.fetchone()
        conn.close()
        
        if not licenses and not license_info:
            messagebox.showinfo("提示", f"{company_name} 暂无执照信息")
            return
        
        # 创建新窗口显示所有信息
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"{company_name} - 执照详情")
        detail_window.geometry("1200x900")
        
        # 创建主框架
        main_frame = ttk.Frame(detail_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text=f"供应商: {company_name}", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 创建滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 1. 显示执照信息
        if license_info:
            info_frame = ttk.LabelFrame(scrollable_frame, text="营业执照信息", padding="15")
            info_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 执照信息字段
            fields = [
                ("注册号", license_info[0]),
                ("公司名称", license_info[1]),
                ("发证日期", license_info[2]),
                ("到期日期", license_info[3]),
                ("注册资本", license_info[4]),
                ("国家/地区", license_info[5]),
                ("注册地址", license_info[6]),
                ("成立年份", license_info[7]),
                ("法律形式", license_info[8]),
                ("法定代表人", license_info[9])
            ]
            
            # 创建两列布局
            info_left = ttk.Frame(info_frame)
            info_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            
            info_right = ttk.Frame(info_frame)
            info_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            # 显示执照信息
            for i, (field_name, field_value) in enumerate(fields):
                if field_value:
                    parent_frame = info_left if i < 5 else info_right
                    row = i if i < 5 else i - 5
                    
                    field_label = ttk.Label(parent_frame, text=f"{field_name}:", font=("Arial", 10, "bold"))
                    field_label.grid(row=row, column=0, sticky=tk.W, pady=2)
                    
                    value_label = ttk.Label(parent_frame, text=field_value, wraplength=400)
                    value_label.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 2. 显示执照图片
        if licenses:
            images_frame = ttk.LabelFrame(scrollable_frame, text="执照图片", padding="15")
            images_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 导入PIL用于图片处理
            try:
                from PIL import Image, ImageTk
                import requests
                from io import BytesIO
                
                # 显示每个执照图片
                for i, (license_name, license_url, file_id) in enumerate(licenses, 1):
                    # 执照图片框架
                    license_frame = ttk.LabelFrame(images_frame, text=f"执照图片 {i}: {license_name}", padding="10")
                    license_frame.pack(fill=tk.X, pady=(0, 15))
                    
                    # 图片URL标签
                    url_label = ttk.Label(license_frame, text=f"URL: {license_url}", wraplength=800)
                    url_label.pack(anchor=tk.W, pady=(0, 10))
                    
                    # 文件ID标签
                    file_id_label = ttk.Label(license_frame, text=f"文件ID: {file_id}")
                    file_id_label.pack(anchor=tk.W, pady=(0, 10))
                    
                    # 尝试显示图片
                    try:
                        # 下载图片
                        response = requests.get(license_url, timeout=10)
                        if response.status_code == 200:
                            # 打开图片
                            img = Image.open(BytesIO(response.content))
                            
                            # 调整图片大小
                            max_width = 600
                            max_height = 400
                            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                            
                            # 转换为Tkinter可用的格式
                            photo = ImageTk.PhotoImage(img)
                            
                            # 创建图片标签
                            img_label = ttk.Label(license_frame, image=photo)
                            img_label.image = photo  # 保持引用
                            img_label.pack(pady=10)
                            
                        else:
                            error_label = ttk.Label(license_frame, text=f"无法加载图片 (状态码: {response.status_code})", foreground="red")
                            error_label.pack(pady=10)
                            
                    except Exception as e:
                        error_label = ttk.Label(license_frame, text=f"图片加载失败: {str(e)}", foreground="red")
                        error_label.pack(pady=10)
                    
                    # 分隔线
                    if i < len(licenses):
                        separator = ttk.Separator(license_frame, orient='horizontal')
                        separator.pack(fill=tk.X, pady=10)
                        
            except ImportError:
                # 如果没有PIL，只显示URL
                for i, (license_name, license_url, file_id) in enumerate(licenses, 1):
                    license_frame = ttk.LabelFrame(images_frame, text=f"执照图片 {i}: {license_name}", padding="10")
                    license_frame.pack(fill=tk.X, pady=(0, 10))
                    
                    url_label = ttk.Label(license_frame, text=f"URL: {license_url}", wraplength=800)
                    url_label.pack(anchor=tk.W)
                    
                    file_id_label = ttk.Label(license_frame, text=f"文件ID: {file_id}")
                    file_id_label.pack(anchor=tk.W)
        
        # 布局滚动组件
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 解绑鼠标滚轮
        def _on_destroy():
            canvas.unbind_all("<MouseWheel>")
        
        detail_window.protocol("WM_DELETE_WINDOW", lambda: [detail_window.destroy(), _on_destroy()])
    
    def show_license_info(self, item):
        """显示执照详细信息"""
        values = self.tree.item(item)['values']
        if not values:
            return
        
        company_id = values[1]
        company_name = values[2]
        
        # 从数据库获取执照信息
        conn = sqlite3.connect(self.db_var.get())
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT registration_no, company_name, date_of_issue, date_of_expiry,
                   registered_capital, country_territory, registered_address,
                   year_established, legal_form, legal_representative
            FROM license_info 
            WHERE supplier_id = ?
        ''', (company_id,))
        
        license_info = cursor.fetchone()
        conn.close()
        
        if not license_info:
            messagebox.showinfo("提示", f"{company_name} 暂无执照信息")
            return
        
        # 创建新窗口显示执照信息
        info_window = tk.Toplevel(self.root)
        info_window.title(f"{company_name} - 执照信息")
        info_window.geometry("800x600")
        
        # 创建主框架
        main_frame = ttk.Frame(info_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text=f"供应商: {company_name}", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 创建文本区域
        text_widget = tk.Text(main_frame, wrap=tk.WORD, padx=10, pady=10, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 执照信息字段
        fields = [
            ("注册号", license_info[0]),
            ("公司名称", license_info[1]),
            ("发证日期", license_info[2]),
            ("到期日期", license_info[3]),
            ("注册资本", license_info[4]),
            ("国家/地区", license_info[5]),
            ("注册地址", license_info[6]),
            ("成立年份", license_info[7]),
            ("法律形式", license_info[8]),
            ("法定代表人", license_info[9])
        ]
        
        # 显示执照信息
        text_widget.insert(tk.END, "营业执照详细信息\n")
        text_widget.insert(tk.END, "=" * 50 + "\n\n")
        
        for field_name, field_value in fields:
            if field_value:
                text_widget.insert(tk.END, f"{field_name}: {field_value}\n\n")
        
        text_widget.config(state=tk.DISABLED)
    
    def fetch_suppliers(self):
        """获取供应商数据"""
        # 创建输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("获取供应商")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 输入框架
        input_frame = ttk.Frame(dialog, padding="20")
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        # 关键词输入
        ttk.Label(input_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, pady=5)
        keyword_entry = ttk.Entry(input_frame, width=30)
        keyword_entry.insert(0, "men's perfume")
        keyword_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 页数输入
        ttk.Label(input_frame, text="页数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        pages_entry = ttk.Entry(input_frame, width=30)
        pages_entry.insert(0, "1")
        pages_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 代理配置
        ttk.Label(input_frame, text="代理服务器:").grid(row=2, column=0, sticky=tk.W, pady=5)
        proxy_entry = ttk.Entry(input_frame, width=30)
        proxy_entry.insert(0, "http://t15395136610470:kyhxo4pj@y900.kdltps.com:15818")
        proxy_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 代理使用开关
        use_proxy_var = tk.BooleanVar(value=True)
        use_proxy_check = ttk.Checkbutton(input_frame, text="使用代理", variable=use_proxy_var)
        use_proxy_check.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        def start_fetch():
            keyword = keyword_entry.get().strip()
            pages = pages_entry.get().strip()
            proxy_string = proxy_entry.get().strip()
            
            if not keyword:
                messagebox.showerror("错误", "请输入搜索关键词！")
                return
            
            try:
                pages = int(pages)
                if pages <= 0:
                    messagebox.showerror("错误", "页数必须大于0！")
                    return
            except ValueError:
                messagebox.showerror("错误", "页数必须是数字！")
                return
            
            # 解析代理
            proxy = None
            if use_proxy_var.get() and proxy_string:
                try:
                    if '@' in proxy_string:
                        auth_part, server_part = proxy_string.split('@', 1)
                        protocol = auth_part.split('://')[0]
                        auth = auth_part.split('://')[1]
                        username, password = auth.split(':')
                        host, port = server_part.split(':')
                        
                        proxy = {
                            'host': host,
                            'port': int(port),
                            'username': username,
                            'password': password
                        }
                except Exception as e:
                    messagebox.showerror("错误", f"代理格式不正确: {e}")
                    return
            
            dialog.destroy()
            
            # 在新线程中运行爬虫
            import threading
            import asyncio
            from alibaba_supplier_crawler import AlibabaSupplierCrawler
            
            def run_fetch():
                try:
                    crawler = AlibabaSupplierCrawler()
                    
                    # 运行异步爬虫
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    suppliers = loop.run_until_complete(
                        crawler.crawl_suppliers(keyword, pages, proxy)
                    )
                    
                    messagebox.showinfo("成功", f"成功获取 {len(suppliers)} 个供应商")
                    
                    # 刷新数据
                    self.load_data(self.db_var.get())
                    
                except Exception as e:
                    messagebox.showerror("错误", f"获取供应商失败: {e}")
            
            # 启动线程
            thread = threading.Thread(target=run_fetch)
            thread.daemon = True
            thread.start()
        
        # 按钮
        ttk.Button(button_frame, text="开始获取", command=start_fetch).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        # 配置网格权重
        input_frame.columnconfigure(1, weight=1)
    
    def on_item_double_click(self, event):
        """双击事件 - 显示详细信息"""
        item = self.tree.selection()
        if item:
            values = self.tree.item(item[0])['values']
            
            # 创建详细信息窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title("供应商详细信息")
            detail_window.geometry("800x600")
            
            # 详细信息文本
            text_widget = tk.Text(detail_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(detail_window, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            # 显示详细信息
            columns = ('ID', '公司ID', '公司名称', 'Action URL', '执照图片', '执照详情', '执照信息', '创建时间')
            
            for i, col in enumerate(columns):
                text_widget.insert(tk.END, f"{col}: {values[i]}\n\n")
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = DatabaseViewer()
    app.run() 