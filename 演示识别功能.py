#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class RecognitionDemo:
    def __init__(self):
        self.setup_gui()
    
    def setup_gui(self):
        """设置演示GUI"""
        self.root = tk.Tk()
        self.root.title("识别功能演示")
        self.root.geometry("800x600")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎯 识别功能演示", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 功能说明
        info_frame = ttk.LabelFrame(main_frame, text="功能说明", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info_text = """
        ✨ 新增识别功能：
        
        1. 📋 识别按钮：在数据列表上方添加"识别执照"按钮
        2. 🖱️ 右键菜单：右键点击列表项弹出操作菜单
        3. 👆 双击功能：双击列表项直接打开文件夹
        4. 📊 识别状态：新增"识别状态"列显示识别结果
        
        🚀 使用方法：
        • 选择供应商 → 点击"识别执照" → 自动识别并保存
        • 右键供应商 → 选择"识别执照" → 执行识别
        • 双击供应商 → 直接打开文件文件夹
        """
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack()
        
        # 演示区域
        demo_frame = ttk.LabelFrame(main_frame, text="演示操作", padding="15")
        demo_frame.pack(fill=tk.BOTH, expand=True)
        
        # 模拟数据列表
        list_frame = ttk.Frame(demo_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="刷新列表", command=self.refresh_demo_list).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="识别执照", command=self.demo_recognize).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="浏览文件", command=self.demo_browse).pack(side=tk.LEFT, padx=(0, 10))
        
        # 模拟数据列表
        columns = ('序号', '店铺名称', 'Action URL', '分类', '执照状态', '识别状态')
        self.demo_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.demo_tree.heading(col, text=col)
            self.demo_tree.column(col, width=120)
        
        self.demo_tree.column('店铺名称', width=200)
        self.demo_tree.column('Action URL', width=250)
        
        self.demo_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.demo_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.demo_tree.configure(yscrollcommand=scrollbar.set)
        
        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="识别执照", command=self.demo_recognize)
        self.context_menu.add_command(label="浏览文件", command=self.demo_browse)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="刷新", command=self.refresh_demo_list)
        
        # 绑定右键菜单和双击事件
        self.demo_tree.bind("<Button-3>", self.show_context_menu)
        self.demo_tree.bind("<Double-1>", self.demo_browse)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初始化演示数据
        self.init_demo_data()
    
    def init_demo_data(self):
        """初始化演示数据"""
        demo_data = [
            ("1", "广州碧莹化妆品有限公司", "https://example.com/company1", "化妆品", "已获取", "未识别"),
            ("2", "深圳电子科技有限公司", "https://example.com/company2", "电子产品", "已获取", "已识别"),
            ("3", "东莞服装制造厂", "https://example.com/company3", "服装", "未获取", "未识别"),
            ("4", "佛山家具制造有限公司", "https://example.com/company4", "家具", "已获取", "未识别"),
            ("5", "中山灯具制造厂", "https://example.com/company5", "灯具", "未获取", "未识别"),
        ]
        
        for item in demo_data:
            self.demo_tree.insert('', 'end', values=item)
        
        self.log_message("演示数据已加载")
    
    def refresh_demo_list(self):
        """刷新演示列表"""
        self.log_message("刷新数据列表...")
        # 模拟刷新过程
        time.sleep(0.5)
        self.log_message("数据列表已刷新")
    
    def demo_recognize(self):
        """演示识别功能"""
        selected_items = self.demo_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        selected_item = selected_items[0]
        item_values = self.demo_tree.item(selected_item)['values']
        company_name = item_values[1]
        
        self.log_message(f"开始识别供应商: {company_name}")
        
        # 模拟识别过程
        def simulate_recognition():
            self.log_message("正在获取供应商页面...")
            time.sleep(1)
            self.log_message("正在提取执照图片...")
            time.sleep(1)
            self.log_message("正在识别执照信息...")
            time.sleep(1)
            self.log_message("正在保存到数据库...")
            time.sleep(0.5)
            self.log_message(f"✅ {company_name} 识别完成！")
            
            # 更新识别状态
            self.root.after(0, lambda: self.update_recognition_status(selected_item))
        
        threading.Thread(target=simulate_recognition, daemon=True).start()
    
    def update_recognition_status(self, item_id):
        """更新识别状态"""
        item_values = list(self.demo_tree.item(item_id)['values'])
        item_values[5] = "已识别"  # 更新识别状态
        self.demo_tree.item(item_id, values=item_values)
    
    def demo_browse(self):
        """演示浏览文件功能"""
        selected_items = self.demo_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择一个供应商")
            return
        
        selected_item = selected_items[0]
        item_values = self.demo_tree.item(selected_item)['values']
        company_name = item_values[1]
        
        self.log_message(f"打开 {company_name} 的文件文件夹")
        messagebox.showinfo("提示", f"模拟打开文件夹: {company_name}")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass
    
    def log_message(self, message):
        """添加日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: (
            self.log_text.insert(tk.END, log_entry),
            self.log_text.see(tk.END)
        ))
    
    def run(self):
        """运行演示"""
        self.root.mainloop()

if __name__ == "__main__":
    demo = RecognitionDemo()
    demo.run() 