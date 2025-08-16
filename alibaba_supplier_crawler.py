import asyncio
import json
import sqlite3
import os
import time
import random
import re
from datetime import datetime
import aiohttp
import requests
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import urllib.parse
from urllib.parse import urlparse

class AlibabaSupplierCrawler:
    def __init__(self):
        self.db_path = "alibaba_supplier_data.db"
        self.init_database()
        
        # 读取分类数据
        self.categories = self.load_categories()
    
    def log(self, message, level="INFO", log_callback=None):
        """日志记录方法"""
        if log_callback:
            log_callback(message, level)
        else:
            # 根据日志级别添加前缀
            if level == "ERROR":
                prefix = "❌"
            elif level == "SUCCESS":
                prefix = "✅"
            elif level == "WARNING":
                prefix = "⚠️"
            elif level == "DEBUG":
                prefix = "🔍"
            else:
                prefix = "ℹ️"
            print(f"{prefix} {message}")
    
    async def save_suppliers_to_cache_file(self, suppliers, cache_file_base, log_callback=None):
        """将供应商数据保存到缓存文件（按时间分文件）"""
        try:
            # 生成带时间戳的文件名（每5分钟一个文件）
            now = datetime.now()
            # 计算5分钟间隔的时间戳
            interval_minutes = (now.hour * 60 + now.minute) // 5 * 5
            time_suffix = f"{now.strftime('%Y%m%d')}_{interval_minutes:04d}"
            
            # 构建实际文件路径
            cache_dir = os.path.dirname(cache_file_base)
            base_name = os.path.splitext(os.path.basename(cache_file_base))[0]
            actual_cache_file = os.path.join(cache_dir, f"{base_name}_{time_suffix}.json")
            
            # 确保缓存目录存在
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            # 读取现有数据
            existing_data = []
            if os.path.exists(actual_cache_file):
                try:
                    with open(actual_cache_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_data = []
            
            # 添加新数据
            existing_data.extend(suppliers)
            
            # 写入文件
            with open(actual_cache_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            if log_callback:
                log_callback(f"✅ 已将 {len(suppliers)} 个供应商数据保存到缓存文件: {actual_cache_file}")
            
            return actual_cache_file
            
        except Exception as e:
            error_msg = f"❌ 保存缓存文件失败: {str(e)}"
            if log_callback:
                log_callback(error_msg, "ERROR")
            else:
                print(error_msg)
            return None
    
    async def batch_save_from_cache_file(self, cache_file, skip_duplicates=True, log_callback=None):
        """从缓存文件批量保存到数据库（优化版本）"""
        try:
            if not os.path.exists(cache_file):
                if log_callback:
                    log_callback(f"⚠️ 缓存文件不存在: {cache_file}", "WARNING")
                return 0
            
            # 读取缓存数据
            with open(cache_file, 'r', encoding='utf-8') as f:
                suppliers_data = json.load(f)
            
            if not suppliers_data:
                if log_callback:
                    log_callback("📭 缓存文件为空，无数据需要入库")
                return 0
            
            if log_callback:
                log_callback(f"📦 开始批量入库，共 {len(suppliers_data)} 个供应商数据")
            
            # 性能优化：一次性加载所有已存在的company_id到内存
            existing_company_ids = set()
            if skip_duplicates:
                if log_callback:
                    log_callback("🔍 正在加载已存在的供应商ID到内存...")
                
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute('SELECT company_id FROM suppliers')
                for row in cursor.fetchall():
                    existing_company_ids.add(row[0])
                conn.close()
                
                if log_callback:
                    log_callback(f"✅ 已加载 {len(existing_company_ids)} 个已存在的供应商ID")
            
            # 过滤出需要保存的新供应商
            new_suppliers = []
            skipped_count = 0
            
            for supplier in suppliers_data:
                if skip_duplicates and supplier['company_id'] in existing_company_ids:
                    skipped_count += 1
                    if log_callback and skipped_count <= 10:  # 只显示前10个重复的
                        log_callback(f"  ✓ 跳过重复供应商: {supplier['company_name']} (ID: {supplier['company_id']})")
                else:
                    # 生成保存路径
                    save_path = self.generate_save_path(supplier)
                    supplier['save_path'] = save_path
                    new_suppliers.append(supplier)
                    # 更新内存中的ID集合，避免同一批次内的重复
                    existing_company_ids.add(supplier['company_id'])
            
            if log_callback:
                log_callback(f"📊 过滤完成：新增 {len(new_suppliers)} 个，跳过重复 {skipped_count} 个")
            
            # 批量插入新供应商
            saved_count = 0
            if new_suppliers:
                if log_callback:
                    log_callback(f"💾 开始批量插入 {len(new_suppliers)} 个新供应商...")
                
                # 分批处理，避免长时间锁定数据库
                batch_size = 50  # 每批50个供应商
                total_batches = (len(new_suppliers) + batch_size - 1) // batch_size
                
                batch_num = 0
                while batch_num < total_batches:
                    start_idx = batch_num * batch_size
                    end_idx = min(start_idx + batch_size, len(new_suppliers))
                    batch_suppliers = new_suppliers[start_idx:end_idx]
                    
                    if log_callback:
                        log_callback(f"🔄 开始处理批次 {batch_num + 1}/{total_batches}，包含 {len(batch_suppliers)} 个供应商")
                    
                    # 每批使用独立的数据库连接和事务
                    conn = None
                    retry_count = 0
                    max_retries = 3
                    batch_success = False
                    
                    while retry_count < max_retries and not batch_success:
                        try:
                            if retry_count > 0 and log_callback:
                                log_callback(f"🔄 批次 {batch_num + 1} 第 {retry_count + 1} 次尝试")
                            
                            if log_callback:
                                log_callback(f"🔗 正在连接数据库...")
                            
                            conn = sqlite3.connect(self.db_path, timeout=60.0)  # 增加超时时间
                            conn.execute('PRAGMA journal_mode=DELETE')  # 改为DELETE模式避免WAL锁定
                            conn.execute('PRAGMA synchronous=OFF')  # 关闭同步以提高性能
                            conn.execute('PRAGMA busy_timeout=60000')  # 60秒超时
                            conn.execute('PRAGMA cache_size=10000')  # 增加缓存
                            cursor = conn.cursor()
                            
                            if log_callback:
                                log_callback(f"✅ 数据库连接成功，开始事务")
                            
                            # 使用普通事务而不是IMMEDIATE，减少锁定
                            conn.execute('BEGIN')
                            
                            if log_callback:
                                log_callback(f"📝 开始插入批次 {batch_num + 1} 的 {len(batch_suppliers)} 个供应商")
                            
                            batch_saved = 0
                            for i, supplier in enumerate(batch_suppliers):
                                try:
                                    cursor.execute('''
                                        INSERT INTO suppliers (company_id, company_name, action_url, country_code, 
                                                           city, gold_years, verified_supplier, is_factory, 
                                                           review_score, review_count, company_on_time_shipping,
                                                           factory_size_text, total_employees_text, transaction_count_6months,
                                                           transaction_gmv_6months_text, gold_supplier, trade_assurance, response_time,
                                                           category_id, category_name, save_path)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        supplier['company_id'],
                                        supplier['company_name'],
                                        supplier['action_url'],
                                        supplier['country_code'],
                                        supplier['city'],
                                        supplier['gold_years'],
                                        supplier['verified_supplier'],
                                        supplier['is_factory'],
                                        supplier['review_score'],
                                        supplier['review_count'],
                                        supplier.get('company_on_time_shipping', ''),
                                        supplier.get('factory_size_text', ''),
                                        supplier.get('total_employees_text', ''),
                                        supplier.get('transaction_count_6months', ''),
                                        supplier.get('transaction_gmv_6months_text', ''),
                                        supplier.get('gold_supplier', False),
                                        supplier.get('trade_assurance', False),
                                        supplier.get('response_time', ''),
                                        supplier.get('category_id', ''),
                                        supplier.get('category_name', ''),
                                        supplier['save_path']
                                    ))
                                    batch_saved += 1
                                    saved_count += 1
                                    
                                    # 每10个显示一次进度
                                    if (i + 1) % 10 == 0 and log_callback:
                                        log_callback(f"  📊 批次 {batch_num + 1} 进度: {i + 1}/{len(batch_suppliers)} 已插入")
                                
                                except Exception as e:
                                    if log_callback:
                                        log_callback(f"⚠️ 插入供应商失败 {supplier.get('company_name', 'Unknown')}: {str(e)}", "WARNING")
                                    continue
                            
                            # 提交当前批次
                            conn.commit()
                            batch_success = True
                            
                            if log_callback:
                                log_callback(f"✅ 批次 {batch_num + 1}/{total_batches} 成功完成: 保存 {batch_saved} 个供应商")
                            
                            # 短暂休息，让其他操作有机会访问数据库
                            await asyncio.sleep(0.1)
                            
                        except sqlite3.OperationalError as e:
                            if conn:
                                try:
                                    conn.rollback()
                                    if log_callback:
                                        log_callback(f"🔄 批次 {batch_num + 1} 事务已回滚")
                                except Exception as rollback_e:
                                    if log_callback:
                                        log_callback(f"⚠️ 回滚失败: {str(rollback_e)}", "WARNING")
                            
                            if "database is locked" in str(e):
                                retry_count += 1
                                if log_callback:
                                    log_callback(f"⚠️ 数据库锁定，批次 {batch_num + 1} 第 {retry_count} 次重试 (最多 {max_retries} 次)", "WARNING")
                                if retry_count < max_retries:
                                    await asyncio.sleep(retry_count * 2.0)  # 递增延迟
                                else:
                                    if log_callback:
                                        log_callback(f"❌ 批次 {batch_num + 1} 重试次数已达上限，跳过该批次", "ERROR")
                            else:
                                if log_callback:
                                    log_callback(f"❌ 批次 {batch_num + 1} 数据库操作错误: {str(e)}", "ERROR")
                                break  # 非锁定错误，跳出重试循环
                        except Exception as e:
                            if conn:
                                try:
                                    conn.rollback()
                                    if log_callback:
                                        log_callback(f"🔄 批次 {batch_num + 1} 事务已回滚")
                                except Exception as rollback_e:
                                    if log_callback:
                                        log_callback(f"⚠️ 回滚失败: {str(rollback_e)}", "WARNING")
                            
                            if log_callback:
                                log_callback(f"❌ 批次 {batch_num + 1} 未知错误: {str(e)}", "ERROR")
                            break  # 其他错误，跳出重试循环
                        finally:
                            if conn:
                                try:
                                    conn.close()
                                except Exception as close_e:
                                    if log_callback:
                                        log_callback(f"⚠️ 关闭数据库连接失败: {str(close_e)}", "WARNING")
                    
                    if not batch_success:
                        if log_callback:
                            log_callback(f"❌ 批次 {batch_num + 1} 最终失败，已跳过该批次", "ERROR")
                    
                    batch_num += 1
            
            # 入库完成后清空缓存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            
            if log_callback:
                log_callback(f"✅ 批量入库完成！新增: {saved_count} 个，跳过重复: {skipped_count} 个", "SUCCESS")
            
            return saved_count
            
        except Exception as e:
            error_msg = f"❌ 批量入库失败: {str(e)}"
            if log_callback:
                log_callback(error_msg, "ERROR")
            else:
                print(error_msg)
            return 0
        
    def change_database_path(self, new_db_path):
        """更改数据库路径并重新初始化"""
        self.db_path = new_db_path
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建供应商表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT,
                company_name TEXT,
                action_url TEXT,
                country_code TEXT,
                city TEXT,
                gold_years TEXT,
                verified_supplier BOOLEAN,
                is_factory BOOLEAN,
                review_score TEXT,
                review_count INTEGER,
                company_on_time_shipping TEXT,
                factory_size_text TEXT,
                total_employees_text TEXT,
                transaction_count_6months TEXT,
                transaction_gmv_6months_text TEXT,
                gold_supplier BOOLEAN,
                trade_assurance BOOLEAN,
                response_time TEXT,
                category_id TEXT,
                category_name TEXT,
                save_path TEXT,
                license_extracted BOOLEAN DEFAULT FALSE,
                is_used BOOLEAN DEFAULT FALSE,
                extraction_failed_count INTEGER DEFAULT 0,
                skip_extraction BOOLEAN DEFAULT FALSE,
                last_extraction_attempt TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建执照图片表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                license_name TEXT,
                license_url TEXT,
                file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        ''')
        
        # 创建执照信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS license_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                registration_no TEXT,
                company_name TEXT,
                date_of_issue TEXT,
                date_of_expiry TEXT,
                registered_capital TEXT,
                country_territory TEXT,
                registered_address TEXT,
                year_established TEXT,
                legal_form TEXT,
                legal_representative TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        ''')
        
        # 创建公司注册信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_registration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id VARCHAR(100) NOT NULL,
                supplier_id VARCHAR(100) NOT NULL,
                registration_number VARCHAR(50) NOT NULL,
                company_name VARCHAR(200) NOT NULL,
                registered_address TEXT,
                province VARCHAR(50),
                city VARCHAR(50),
                district VARCHAR(50),
                zip_code VARCHAR(10),
                legal_representative VARCHAR(100),
                issue_date DATE,
                expiration_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(supplier_id, registration_number)
            )
        ''')
        
        # 为company_registration表创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_supplier_id ON company_registration(supplier_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_registration_number ON company_registration(registration_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON company_registration(company_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_province_city ON company_registration(province, city)')
        
        # 创建触发器，自动更新updated_at字段
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_company_registration_timestamp 
                AFTER UPDATE ON company_registration
                FOR EACH ROW
            BEGIN
                UPDATE company_registration 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        ''')
        
        # 创建代理配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT,
                password TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入默认代理配置（如果表为空）
        cursor.execute('SELECT COUNT(*) FROM proxies')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO proxies (name, host, port, username, password, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('默认代理', '127.0.0.1', 7890, 't15395136610470', 'Aa123456', True))
        
        # 检查并添加is_used字段（兼容现有数据库）
        cursor.execute("PRAGMA table_info(suppliers)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_used' not in columns:
            cursor.execute('ALTER TABLE suppliers ADD COLUMN is_used BOOLEAN DEFAULT FALSE')
            print("已添加is_used字段到suppliers表")
        
        # 检查并添加ocr_recognition_status字段（兼容现有数据库）
        if 'ocr_recognition_status' not in columns:
            cursor.execute('ALTER TABLE suppliers ADD COLUMN ocr_recognition_status TEXT DEFAULT "pending"')
            print("已添加ocr_recognition_status字段到suppliers表")
            # 创建索引以提高查询效率
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ocr_recognition_status ON suppliers(ocr_recognition_status)')
            print("已为ocr_recognition_status字段创建索引")
        
        conn.commit()
        conn.close()
        print("数据库初始化完成")
    
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
                categories = {}
                for tab in data['data']['tabs']:
                    categories[tab['tabId']] = tab['title']
                print(f"加载了 {len(categories)} 个分类")
                return categories
            else:
                print("分类文件格式不正确")
                return {}
        except Exception as e:
            print(f"加载分类文件失败: {e}")
            return {}

    def build_category_search_url(self, category_id, page_no=1, page_size=20):
        """构建分类搜索URL"""
        base_url = "https://insights.alibaba.com/openservice/gatewayService"
        
        params = {
            'endpoint': 'pc',
            'pageSize': str(page_size),
            'categoryIds': str(category_id),
            'pageNo': str(page_no),
            'modelId': '10300'
        }
        
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

    def extract_suppliers_from_category_api(self, data_list):
        """从分类API数据中提取供应商信息"""
        suppliers = []
        
        for item in data_list:
            # 从reviewsUrl构建action_url
            reviews_url = item.get('reviewsUrl', '')
            if reviews_url:
                # 提取域名部分
                if reviews_url.startswith('//'):
                    reviews_url = reviews_url[2:]
                
                # 解析URL获取域名
                parsed_url = urlparse(f"https://{reviews_url}")
                domain = parsed_url.netloc
                
                # 构建action_url
                action_url = f"https://{domain}/zh_CN/company_profile.html?subpage=onsiteDetail"
            else:
                action_url = ''
            
            supplier = {
                'company_id': item.get('companyId', ''),
                'company_name': item.get('companyName', ''),
                'action_url': action_url,
                'country_code': '',  # 新API中没有这个字段
                'city': '',  # 新API中没有这个字段
                'gold_years': item.get('goldSupplierYearsText', ''),
                'verified_supplier': item.get('assessedSupplier', False),
                'is_factory': True,  # 分类搜索都是工厂
                'review_score': item.get('rate', ''),
                'review_count': item.get('reviews', ''),
                # 新增字段
                'company_on_time_shipping': item.get('companyOnTimeShipping', ''),
                'factory_size_text': item.get('factorySizeText', ''),
                'total_employees_text': item.get('totalEmployeesText', ''),
                'transaction_count_6months': item.get('transactionCountDuring6Months', ''),
                'transaction_gmv_6months_text': item.get('transactionGmvDuring6MonthsText', ''),
                'gold_supplier': item.get('goldSupplier', False),
                'trade_assurance': item.get('tradeAssurance', False),
                'response_time': item.get('responseTime', '')
            }
            
            if supplier['company_id']:  # 只添加有公司ID的供应商
                suppliers.append(supplier)
        
        return suppliers

    def parse_proxy(self, proxy_string):
        """解析代理字符串"""
        if not proxy_string:
            return None
        
        try:
            # 解析代理格式: http://username:password@host:port
            if '@' in proxy_string:
                # 有认证信息的代理
                auth_part, server_part = proxy_string.split('@', 1)
                protocol = auth_part.split('://')[0]
                auth = auth_part.split('://')[1]
                username, password = auth.split(':')
                host, port = server_part.split(':')
                
                return {
                    'host': host,
                    'port': int(port),
                    'username': username,
                    'password': password
                }
            else:
                # 无认证信息的代理
                return None
        except Exception as e:
            print(f"代理解析失败: {e}")
            return None
    
    async def fetch_with_proxy(self, url, proxy=None, session=None, is_html=False, check_ip=True, max_retries=3, log_callback=None):
        """使用代理获取数据（带重试机制）"""
        # 检查IP变化（可选）
        if check_ip:
            await self.check_ip_change(proxy)
        
        if is_html:
            # HTML页面的请求头 - 使用随机移动端UA
            mobile_user_agents = [
                # iPhone系列
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.7 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
                
                # Samsung Galaxy系列
                'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Google Pixel系列
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 7a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # OnePlus系列
                'Mozilla/5.0 (Linux; Android 13; OnePlus 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; OnePlus 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; OnePlus 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; OnePlus 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; OnePlus 9R) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Xiaomi系列
                'Mozilla/5.0 (Linux; Android 13; M2102J20SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; 2311DRK48C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; M2012K11AG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; 2311DRK48I) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; M2102J20SI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # OPPO系列
                'Mozilla/5.0 (Linux; Android 13; CPH2205) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; CPH2411) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; CPH2211) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; CPH2413) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; CPH2207) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # vivo系列
                'Mozilla/5.0 (Linux; Android 13; V2114) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; V2307) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; V2118) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; V2309) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; V2127) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Huawei系列
                'Mozilla/5.0 (Linux; Android 13; HUAWEI P50 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; HUAWEI Mate 60 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; HUAWEI P60 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; HUAWEI Mate X5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; HUAWEI nova 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(mobile_user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        else:
            # API请求头 - 也使用随机移动端UA
            mobile_user_agents = [
                # iPhone系列
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.7 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
                
                # Samsung Galaxy系列
                'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Google Pixel系列
                'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; Pixel 7a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # OnePlus系列
                'Mozilla/5.0 (Linux; Android 13; OnePlus 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; OnePlus 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; OnePlus 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; OnePlus 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; OnePlus 9R) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Xiaomi系列
                'Mozilla/5.0 (Linux; Android 13; M2102J20SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; 2311DRK48C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; M2012K11AG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; 2311DRK48I) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; M2102J20SI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # OPPO系列
                'Mozilla/5.0 (Linux; Android 13; CPH2205) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; CPH2411) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; CPH2211) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; CPH2413) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; CPH2207) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # vivo系列
                'Mozilla/5.0 (Linux; Android 13; V2114) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; V2307) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; V2118) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; V2309) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; V2127) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                
                # Huawei系列
                'Mozilla/5.0 (Linux; Android 13; HUAWEI P50 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; HUAWEI Mate 60 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; HUAWEI P60 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 14; HUAWEI Mate X5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 13; HUAWEI nova 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(mobile_user_agents),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.alibaba.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site'
            }
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                if session:
                    # 使用aiohttp异步请求
                    if proxy:
                        # 使用HTTP代理格式
                        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                        async with session.get(url, headers=headers, proxy=proxy_url) as response:
                            if response.status == 200:
                                if is_html:
                                    return await response.text()
                                else:
                                    return await response.json()
                            else:
                                self.log(f"请求失败，状态码: {response.status} (尝试 {attempt + 1}/{max_retries})", "ERROR", log_callback)
                    else:
                        async with session.get(url, headers=headers) as response:
                            if response.status == 200:
                                if is_html:
                                    return await response.text()
                                else:
                                    return await response.json()
                            else:
                                self.log(f"请求失败，状态码: {response.status} (尝试 {attempt + 1}/{max_retries})", "ERROR", log_callback)
                else:
                    # 使用requests同步请求
                    proxies = None
                    if proxy:
                        # 使用HTTP代理格式
                        proxies = {
                            'http': f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}",
                            'https': f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                        }
                    response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
                    if response.status_code == 200:
                        if is_html:
                            return response.text
                        else:
                            return response.json()
                    else:
                        self.log(f"请求失败，状态码: {response.status_code} (尝试 {attempt + 1}/{max_retries})", "ERROR", log_callback)
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间：2秒、4秒、6秒
                    self.log(f"等待 {wait_time} 秒后重试...", "INFO", log_callback)
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                self.log(f"请求出错 (尝试 {attempt + 1}/{max_retries}): {e}", "ERROR", log_callback)
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    self.log(f"等待 {wait_time} 秒后重试...", "INFO", log_callback)
                    await asyncio.sleep(wait_time)
        
        self.log(f"请求失败，已达到最大重试次数 ({max_retries})", "ERROR", log_callback)
        return None
    
    async def check_ip_change(self, proxy=None):
        """检查IP变化"""
        if not proxy:
            return
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 获取当前IP（使用最快的icanhazip.com）
                ip_check_url = "https://icanhazip.com"
                proxies = None
                if proxy:
                    # 使用HTTP代理格式
                    proxies = {
                        'http': f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}",
                        'https': f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                    }
                
                response = requests.get(ip_check_url, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    current_ip = response.text.strip()  # 直接获取IP文本
                    print(f"当前IP: {current_ip}")
                    
                    # 检查IP是否变化
                    if hasattr(self, 'last_ip'):
                        if current_ip != self.last_ip:
                            print(f"IP已变化: {self.last_ip} -> {current_ip}")
                        else:
                            print(f"IP未变化: {current_ip}")
                    else:
                        print(f"首次获取IP: {current_ip}")
                    
                    self.last_ip = current_ip
                    return  # 成功获取IP，退出重试
                else:
                    print(f"IP检查失败，状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"检查IP变化时出错 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 等待2秒后重试
        
        print("IP检查失败，已达到最大重试次数")
    
    def build_search_url(self, keyword, page=1):
        """构建搜索URL"""
        base_url = "https://www.alibaba.com/search/api/supplierTextSearch"
        
        # URL参数
        params = {
            'productQpKeywords': keyword,
            'cateIdLv1List': '66',
            'qpListData': '201758404,201757704,201334819,201762603,202221803',
            'supplierQpProductName': keyword.split()[0] if keyword else 'perfume',
            'query': keyword,
            'productAttributes': keyword.split()[0] if keyword else 'perfume',
            'pageSize': '20',
            'queryMachineTranslate': keyword,
            'productName': keyword,
            'intention': '',
            'queryProduct': f' {keyword}',
            'supplierAttributes': '',
            'requestId': f'AI_Web_2500000600257_{int(time.time() * 1000)}',
            'queryRaw': keyword,
            'supplierQpKeywords': keyword.replace(' ', '%2C'),
            'startTime': str(int(time.time() * 1000)),
            'page': str(page),
            'verifiedManufactory': 'true'
        }
        
        # 构建查询字符串
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    async def crawl_suppliers(self, keyword, pages=1, proxy=None, extract_licenses=False):
        """爬取供应商数据（兼容旧版本）"""
        return await self.crawl_suppliers_range(keyword, 1, pages, proxy, extract_licenses)
    
    async def crawl_suppliers_range(self, keyword, start_page=1, end_page=1, proxy=None, extract_licenses=False, skip_duplicates=True, log_callback=None, save_to_file=False, cache_file=None):
        """爬取指定页面范围的供应商数据"""
        try:
            all_suppliers = []
            total_saved = 0
            total_skipped = 0
            
            # 创建异步会话
            connector = aiohttp.TCPConnector(limit=10)
            timeout = aiohttp.ClientTimeout(total=30)
            
            # 日志输出函数
            def log(message, level="INFO"):
                if log_callback:
                    log_callback(message, level)
                else:
                    print(message)
            
            log(f"🚀 开始爬取关键词: '{keyword}'，页面范围: {start_page}-{end_page}")
            if save_to_file:
                log(f"📁 数据将保存到文件: {cache_file}")
            log("=" * 60)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                for page in range(start_page, end_page + 1):
                    log(f"📄 正在爬取第 {page} 页 ({page}/{end_page})...")
                    
                    # 构建搜索URL
                    search_url = self.build_search_url(keyword, page)
                    log(f"🔗 请求URL: {search_url}")
                    
                    try:
                        # 使用代理请求
                        data = await self.fetch_with_proxy(search_url, proxy, session, log_callback=log_callback)
                        
                        if data.get('success') and 'model' in data and 'offers' in data['model']:
                            suppliers = self.extract_suppliers_from_api(data['model']['offers'])
                            log(f"📦 第 {page} 页获取到 {len(suppliers)} 个供应商")
                            
                            if suppliers:
                                # 为每个供应商添加关键词信息
                                for supplier in suppliers:
                                    supplier['keyword'] = keyword
                                    supplier['crawl_time'] = datetime.now().isoformat()
                                
                                if save_to_file:
                                    # 保存到文件
                                    await self.save_suppliers_to_cache_file(suppliers, cache_file, log_callback=log)
                                    log(f"📁 第 {page} 页数据已保存到缓存文件")
                                else:
                                    # 实时保存到数据库
                                    log(f"💾 开始保存第 {page} 页的供应商数据...")
                                    page_saved = 0
                                    page_skipped = 0
                                    
                                    for i, supplier in enumerate(suppliers, 1):
                                        result = await self.save_single_supplier(supplier, skip_duplicates)
                                        if result:
                                            page_saved += 1
                                            total_saved += 1
                                        else:
                                            page_skipped += 1
                                            total_skipped += 1
                                        
                                        # 显示进度
                                        log(f"  📊 进度: {i}/{len(suppliers)} - 新增: {page_saved}, 重复: {page_skipped}")
                                    
                                    log(f"✅ 第 {page} 页保存完成: 新增 {page_saved} 个，跳过 {page_skipped} 个重复", "SUCCESS")
                                
                                all_suppliers.extend(suppliers)
                            
                            # 打印API响应的分页信息（简化版）
                            if 'model' in data and 'pagination' in data['model']:
                                pagination = data['model']['pagination']
                                if 'totalCount' in pagination:
                                    log(f"📈 总供应商数: {pagination.get('totalCount', 'N/A')}")
                            
                        else:
                            log(f"❌ 第 {page} 页API返回错误", "ERROR")
                            if data:
                                log(f"   错误详情: {data.get('message', '未知错误')}", "ERROR")
                    
                    except Exception as e:
                        log(f"❌ 爬取第 {page} 页时出错: {e}", "ERROR")
                        continue
                    
                    # 页面间延迟
                    if page < end_page:
                        delay = random.uniform(0, 0)
                        log(f"⏱️  等待 {delay:.1f} 秒后继续下一页...")
                        await asyncio.sleep(delay)
            
            # Excel文件更新已移除
            
            # 总结
            log(f"🎉 爬取完成！", "SUCCESS")
            log(f"📊 总计: 新增 {total_saved} 个供应商，跳过 {total_skipped} 个重复")
            log("=" * 60)
            
            # 如果需要提取执照图片
            if extract_licenses and all_suppliers:
                log("🔍 开始提取供应商执照图片...")
                # 创建新的session用于获取HTML页面
                connector = aiohttp.TCPConnector(limit=10)
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as html_session:
                    await self.extract_all_licenses(all_suppliers, proxy, html_session, log_callback)
            
            return all_suppliers
            
        except Exception as e:
            log(f"❌ 爬取过程中出错: {e}", "ERROR")
            return []
    
    async def crawl_suppliers_by_category(self, category_id, start_page=1, end_page=1, proxy=None, extract_licenses=False, skip_duplicates=True, save_path=None, log_callback=None):
        """按分类爬取供应商"""
        # 日志输出函数
        def log(message, level="INFO"):
            if log_callback:
                log_callback(message, level)
            else:
                print(message)
        
        if category_id not in self.categories:
            log(f"❌ 未知的分类ID: {category_id}", "ERROR")
            return []
        
        category_name = self.categories[category_id]
        all_suppliers = []
        total_saved = 0
        total_skipped = 0
        
        log(f"🚀 开始爬取分类: {category_name} (ID: {category_id})，页面范围: {start_page}-{end_page}")
        log("=" * 60)
        
        # 为每个供应商添加分类信息
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for page in range(start_page, end_page + 1):
                log(f"📄 正在爬取第 {page} 页 ({page}/{end_page})...")
                
                # 构建搜索URL
                search_url = self.build_category_search_url(category_id, page)
                log(f"🔗 请求URL: {search_url}")
                
                try:
                    # 请求数据
                    data = await self.fetch_with_proxy(search_url, proxy, session, log_callback=log_callback)
                    
                    if data and data.get('code') == 200 and 'data' in data and 'list' in data['data']:
                        suppliers = self.extract_suppliers_from_category_api(data['data']['list'])
                        log(f"📦 第 {page} 页获取到 {len(suppliers)} 个供应商")
                        
                        # 为每个供应商添加分类信息
                        for supplier in suppliers:
                            supplier['category_id'] = category_id
                            supplier['category_name'] = category_name
                            supplier['save_path'] = save_path
                        
                        # 实时保存每个供应商
                        if suppliers:
                            log(f"💾 开始保存第 {page} 页的供应商数据...")
                            page_saved = 0
                            page_skipped = 0
                            
                            for i, supplier in enumerate(suppliers, 1):
                                result = await self.save_single_supplier(supplier, skip_duplicates)
                                if result:
                                    page_saved += 1
                                    total_saved += 1
                                else:
                                    page_skipped += 1
                                    total_skipped += 1
                                
                                # 显示进度
                                log(f"  📊 进度: {i}/{len(suppliers)} - 新增: {page_saved}, 重复: {page_skipped}")
                            
                            log(f"✅ 第 {page} 页保存完成: 新增 {page_saved} 个，跳过 {page_skipped} 个重复", "SUCCESS")
                            all_suppliers.extend(suppliers)
                        
                        # 打印分页信息（简化版）
                        if 'page' in data['data']:
                            page_info = data['data']['page']
                            if 'totalCount' in page_info:
                                log(f"📈 总供应商数: {page_info.get('totalCount', 'N/A')}")
                        
                    else:
                        log(f"❌ 第 {page} 页API返回错误", "ERROR")
                        if data:
                            log(f"   错误详情: {data.get('message', '未知错误')}", "ERROR")
                
                except Exception as e:
                    log(f"❌ 爬取第 {page} 页时出错: {e}", "ERROR")
                    continue
                
                # 延迟
                if page < end_page:
                    delay = random.uniform(0, 0)
                    log(f"⏱️  等待 {delay:.1f} 秒后继续下一页...")
                    await asyncio.sleep(delay)
        
        # Excel文件更新已移除
        
        # 总结
        log(f"🎉 分类爬取完成！", "SUCCESS")
        log(f"📊 总计: 新增 {total_saved} 个供应商，跳过 {total_skipped} 个重复", "SUCCESS")
        log("=" * 60)
        
        # 如果需要提取执照
        if extract_licenses and all_suppliers:
            log("开始提取执照信息...")
            await self.extract_licenses_from_database(proxy)
        
        return all_suppliers
    
    async def save_single_supplier_to_category(self, company_id, company_name, licenses, license_info, category_id, category_name):
        """保存单个供应商到对应分类目录"""
        try:
            # 创建保存目录
            save_path = "./license_files"
            category_dir = os.path.join(save_path, f"{category_id}_{category_name}")
            os.makedirs(category_dir, exist_ok=True)
            
            # 创建供应商目录
            safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
            supplier_dir = os.path.join(category_dir, safe_name)
            os.makedirs(supplier_dir, exist_ok=True)
            
            # 保存执照信息
            if license_info:
                info_file = os.path.join(supplier_dir, "执照信息.txt")
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(f"供应商: {company_name}\n")
                    f.write(f"公司ID: {company_id}\n")
                    f.write(f"分类: {category_name}\n")
                    f.write("=" * 50 + "\n")
                    for field_name, field_value in license_info.items():
                        f.write(f"{field_name}: {field_value}\n")
            
            # 下载执照图片
            if licenses:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    for i, license_item in enumerate(licenses):
                        try:
                            async with session.get(license_item['url']) as response:
                                if response.status == 200:
                                    content = await response.read()
                                    file_ext = license_item['url'].split('.')[-1] if '.' in license_item['url'] else 'jpg'
                                    img_file = os.path.join(supplier_dir, f"执照图片_{i+1}.{file_ext}")
                                    with open(img_file, 'wb') as f:
                                        f.write(content)
                        except Exception as e:
                            print(f"下载图片失败: {license_item['url']} - {e}")
            
            # 更新数据库中的save_path字段
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('UPDATE suppliers SET save_path = ? WHERE company_id = ?', (supplier_dir, company_id))
                conn.commit()
                conn.close()
            except Exception as db_e:
                print(f"更新数据库save_path失败: {db_e}")
            
            print(f"  - {company_name}: 已保存到分类目录: {supplier_dir}")
            return supplier_dir
            
        except Exception as e:
            print(f"保存供应商文件失败: {company_name} - {e}")
            return None
    
    def generate_save_path(self, supplier):
        """生成统一的保存路径"""
        base_path = "./license_files"
        
        # 清理公司名作为文件夹名
        safe_company_name = supplier['company_name'].replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
        
        # 根据关键词或分类生成路径
        if 'keyword' in supplier and supplier['keyword']:
            # 关键词搜索：./license_files/{关键词}/{公司名}/
            safe_keyword = supplier['keyword'].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            return os.path.join(base_path, safe_keyword, safe_company_name)
        elif 'category_id' in supplier and supplier['category_id'] and 'category_name' in supplier and supplier['category_name']:
            # 分类搜索：./license_files/{分类ID}_{分类名}/{公司名}/
            safe_category_name = supplier['category_name'].replace('/', '_').replace('\\', '_').replace(':', '_')
            category_folder = f"{supplier['category_id']}_{safe_category_name}"
            return os.path.join(base_path, category_folder, safe_company_name)
        else:
            # 默认路径：./license_files/{公司名}/
            return os.path.join(base_path, safe_company_name)
    
    async def save_single_supplier_to_keyword(self, company_id, company_name, licenses, license_info, keyword):
        """保存单个供应商到关键词目录"""
        try:
            # 创建保存目录
            save_path = "./license_files"
            # 清理关键词作为文件夹名
            safe_keyword = keyword.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            keyword_dir = os.path.join(save_path, safe_keyword)
            os.makedirs(keyword_dir, exist_ok=True)
            
            # 创建供应商目录
            safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
            supplier_dir = os.path.join(keyword_dir, safe_name)
            os.makedirs(supplier_dir, exist_ok=True)
            
            # 保存执照信息
            if license_info:
                info_file = os.path.join(supplier_dir, "执照信息.txt")
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(f"供应商: {company_name}\n")
                    f.write(f"公司ID: {company_id}\n")
                    f.write(f"关键词: {keyword}\n")
                    f.write("=" * 50 + "\n")
                    for field_name, field_value in license_info.items():
                        f.write(f"{field_name}: {field_value}\n")
            
            # 下载执照图片
            if licenses:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    for i, license_item in enumerate(licenses):
                        try:
                            async with session.get(license_item['url']) as response:
                                if response.status == 200:
                                    content = await response.read()
                                    file_ext = license_item['url'].split('.')[-1] if '.' in license_item['url'] else 'jpg'
                                    img_file = os.path.join(supplier_dir, f"执照图片_{i+1}.{file_ext}")
                                    with open(img_file, 'wb') as f:
                                        f.write(content)
                        except Exception as e:
                            print(f"下载图片失败: {license_item['url']} - {e}")
            
            print(f"  - {company_name}: 已保存到关键词目录: {supplier_dir}")
            return supplier_dir
            
        except Exception as e:
            print(f"保存供应商文件失败: {company_name} - {e}")
            return None
    
    async def save_suppliers_by_category(self, category_id, save_path=None):
        """按分类保存供应商数据到文件"""
        if category_id not in self.categories:
            print(f"未知的分类ID: {category_id}")
            return
        
        category_name = self.categories[category_id]
        print(f"开始保存分类: {category_name} 的供应商数据")
        
        # 从数据库获取该分类的供应商
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT company_id, company_name, action_url, country_code, city, 
                   gold_years, verified_supplier, is_factory, review_score, review_count,
                   company_on_time_shipping, factory_size_text, total_employees_text,
                   transaction_count_6months, transaction_gmv_6months_text, gold_supplier,
                   trade_assurance, response_time, save_path
            FROM suppliers 
            WHERE category_id = ?
            ORDER BY created_at DESC
        ''', (category_id,))
        
        suppliers = cursor.fetchall()
        conn.close()
        
        if not suppliers:
            print(f"分类 {category_name} 没有供应商数据")
            return
        
        # 创建保存目录
        if not save_path:
            save_path = "./license_files"
        
        category_dir = os.path.join(save_path, f"{category_id}_{category_name}")
        os.makedirs(category_dir, exist_ok=True)
        
        # 保存Excel文件
        import pandas as pd
        
        # 转换为DataFrame
        df_data = []
        for supplier in suppliers:
            df_data.append({
                'company_id': supplier[0],
                'company_name': supplier[1],
                'action_url': supplier[2],
                'country_code': supplier[3],
                'city': supplier[4],
                'gold_years': supplier[5],
                'verified_supplier': supplier[6],
                'is_factory': supplier[7],
                'review_score': supplier[8],
                'review_count': supplier[9],
                'company_on_time_shipping': supplier[10],
                'factory_size_text': supplier[11],
                'total_employees_text': supplier[12],
                'transaction_count_6months': supplier[13],
                'transaction_gmv_6months_text': supplier[14],
                'gold_supplier': supplier[15],
                'trade_assurance': supplier[16],
                'response_time': supplier[17],
                'save_path': supplier[18]
            })
        
        df = pd.DataFrame(df_data)
        excel_file = os.path.join(category_dir, f"{category_name}_供应商数据.xlsx")
        df.to_excel(excel_file, index=False)
        
        # 保存执照图片和信息
        for supplier in suppliers:
            company_id, company_name = supplier[0], supplier[1]
            
            # 获取执照图片
            cursor.execute('SELECT license_url FROM licenses WHERE company_id = ?', (company_id,))
            licenses = cursor.fetchall()
            
            # 获取执照信息
            cursor.execute('SELECT field_name, field_value FROM license_info WHERE company_id = ?', (company_id,))
            license_info = cursor.fetchall()
            
            if licenses or license_info:
                # 创建供应商目录
                safe_name = company_name.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
                supplier_dir = os.path.join(category_dir, safe_name)
                os.makedirs(supplier_dir, exist_ok=True)
                
                # 保存执照信息
                if license_info:
                    info_file = os.path.join(supplier_dir, "执照信息.txt")
                    with open(info_file, 'w', encoding='utf-8') as f:
                        f.write(f"供应商: {company_name}\n")
                        f.write(f"公司ID: {company_id}\n")
                        f.write("=" * 50 + "\n")
                        for field_name, field_value in license_info:
                            f.write(f"{field_name}: {field_value}\n")
                
                # 下载执照图片
                if licenses:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        for i, (license_url,) in enumerate(licenses):
                            try:
                                async with session.get(license_url) as response:
                                    if response.status == 200:
                                        content = await response.read()
                                        file_ext = license_url.split('.')[-1] if '.' in license_url else 'jpg'
                                        img_file = os.path.join(supplier_dir, f"执照图片_{i+1}.{file_ext}")
                                        with open(img_file, 'wb') as f:
                                            f.write(content)
                            except Exception as e:
                                print(f"下载图片失败: {license_url} - {e}")
        
        print(f"分类 {category_name} 的数据已保存到: {category_dir}")
        return category_dir
    
    def extract_suppliers_from_api(self, offers):
        """从API数据中提取供应商信息"""
        suppliers = []
        
        for offer in offers:
            # 处理action_url，确保包含subpage参数
            action_url = f"https:{offer.get('action', '')}" if offer.get('action', '').startswith('//') else offer.get('action', '')
            
            # 添加subpage参数
            if action_url:
                if '?' in action_url:
                    action_url += '&subpage=onsiteDetail'
                else:
                    action_url += '?subpage=onsiteDetail'
            
            supplier = {
                'company_id': offer.get('companyId', ''),
                'company_name': offer.get('companyName', ''),
                'action_url': action_url,
                'country_code': offer.get('countryCode', ''),
                'city': offer.get('city', ''),
                'gold_years': offer.get('goldYears', ''),
                'verified_supplier': offer.get('verifiedSupplier', False),
                'is_factory': offer.get('isFactory', False),
                'review_score': offer.get('reviewScore', ''),
                'review_count': offer.get('reviewCount', 0)
            }
            
            if supplier['company_id']:  # 只添加有公司ID的供应商
                suppliers.append(supplier)
        
        return suppliers
    
    async def save_single_supplier(self, supplier, skip_duplicates=True):
        """实时保存单个供应商数据"""
        max_retries = 3
        retry_delay = 0.5  # 500ms
        
        for attempt in range(max_retries):
            conn = None
            try:
                # 设置数据库连接超时和WAL模式
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA busy_timeout=10000')  # 10秒超时
                cursor = conn.cursor()
                
                # 开始事务
                conn.execute('BEGIN IMMEDIATE')
                
                if skip_duplicates:
                    # 检查是否已存在
                    cursor.execute('SELECT company_id FROM suppliers WHERE company_id = ?', (supplier['company_id'],))
                    existing = cursor.fetchone()
                    
                    if existing:
                        print(f"  ✓ 跳过重复供应商: {supplier['company_name']} (ID: {supplier['company_id']})")
                        conn.rollback()
                        return False
                
                # 生成保存路径
                save_path = self.generate_save_path(supplier)
                supplier['save_path'] = save_path
                
                cursor.execute('''
                    INSERT INTO suppliers (company_id, company_name, action_url, country_code, 
                                       city, gold_years, verified_supplier, is_factory, 
                                       review_score, review_count, company_on_time_shipping,
                                       factory_size_text, total_employees_text, transaction_count_6months,
                                       transaction_gmv_6months_text, gold_supplier, trade_assurance, response_time,
                                       category_id, category_name, save_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    supplier['company_id'],
                    supplier['company_name'],
                    supplier['action_url'],
                    supplier['country_code'],
                    supplier['city'],
                    supplier['gold_years'],
                    supplier['verified_supplier'],
                    supplier['is_factory'],
                    supplier['review_score'],
                    supplier['review_count'],
                    supplier.get('company_on_time_shipping', ''),
                    supplier.get('factory_size_text', ''),
                    supplier.get('total_employees_text', ''),
                    supplier.get('transaction_count_6months', ''),
                    supplier.get('transaction_gmv_6months_text', ''),
                    supplier.get('gold_supplier', False),
                    supplier.get('trade_assurance', False),
                    supplier.get('response_time', ''),
                    supplier.get('category_id', ''),
                    supplier.get('category_name', ''),
                    save_path
                ))
                
                conn.commit()
                print(f"  ✓ 成功保存供应商: {supplier['company_name']} (ID: {supplier['company_id']})")
                return True
                
            except sqlite3.OperationalError as e:
                if conn:
                    conn.rollback()
                
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"  ⚠️ 数据库锁定，第 {attempt + 1} 次重试: {supplier['company_name']}")
                    await asyncio.sleep(retry_delay * (attempt + 1))  # 递增延迟
                    continue
                else:
                    print(f"  ✗ 保存供应商失败: {supplier['company_name']} - {e}")
                    return False
            except Exception as e:
                if conn:
                    conn.rollback()
                print(f"  ✗ 保存供应商失败: {supplier['company_name']} - {e}")
                return False
            finally:
                if conn:
                    conn.close()
        
        return False
    
    async def save_suppliers(self, suppliers, skip_duplicates=True):
        """批量保存供应商数据（保持向后兼容）"""
        if not suppliers:
            print("没有供应商数据需要保存")
            return
        
        saved_count = 0
        skipped_count = 0
        
        for supplier in suppliers:
            result = await self.save_single_supplier(supplier, skip_duplicates)
            if result:
                saved_count += 1
            else:
                skipped_count += 1
        
        # Excel文件更新已移除
        
        if skip_duplicates:
            print(f"批量保存完成: {saved_count} 个新增，{skipped_count} 个重复")
        else:
            print(f"批量保存完成: {saved_count} 个供应商数据")
    
    async def check_image_size(self, url, base_name, file_ext):
        """异步检查单个图片大小"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content_length = response.headers.get('content-length')
                        if content_length:
                            file_size = int(content_length)
                            if file_size >= 20 * 1024:  # 20KB = 20 * 1024 bytes
                                license_item = {
                                    'name': f"{base_name.split('.')[0]}.{file_ext}",
                                    'type': 'img',
                                    'url': url,
                                    'fileId': base_name,
                                    'file_size': file_size
                                }
                                print(f"保留执照图片: {url} (大小: {file_size} bytes)")
                                return license_item
                            else:
                                print(f"忽略小图片: {url} (大小: {file_size} bytes, 小于20KB)")
                                return None
                        else:
                            # 如果没有content-length头，保留图片，设置默认大小为0
                            license_item = {
                                'name': f"{base_name.split('.')[0]}.{file_ext}",
                                'type': 'img',
                                'url': url,
                                'fileId': base_name,
                                'file_size': 0
                            }
                            print(f"保留执照图片: {url} (无法获取大小)")
                            return license_item
                    else:
                        print(f"无法访问图片: {url} (状态码: {response.status})")
                        return None
        except Exception as e:
            print(f"检查图片大小时出错: {url} - {e}")
            # 出错时保留图片
            license_item = {
                'name': f"{base_name.split('.')[0]}.{file_ext}",
                'type': 'img',
                'url': url,
                'fileId': base_name
            }
            return license_item

    async def extract_licenses_from_html(self, html_content):
        """从HTML内容中提取执照图片信息（异步版本）"""
        try:
            # 搜索所有执照图片URL（支持jpg和png格式）
            url_pattern = r'https://sc04\.alicdn\.com/kf/([^"]+\.(?:jpg|png))'
            matches = re.findall(url_pattern, html_content)
            
            if matches:
                # 去重处理：只保留原始尺寸的图片（不包含尺寸后缀）
                unique_urls = {}
                for file_id in matches:
                    # 提取基础文件名（去除尺寸后缀）
                    base_name = file_id
                    file_ext = file_id.split('.')[-1]  # 获取文件扩展名
                    
                    if '_' in file_id and any(size in file_id for size in ['_50x50', '_80x80', '_100x100', '_120x120', '_200x200', '_250x250', '_350x350']):
                        # 如果有尺寸后缀，尝试找到原始文件名
                        for size in ['_50x50', '_80x80', '_100x100', '_120x120', '_200x200', '_250x250', '_350x350']:
                            if file_id.endswith(size + '.' + file_ext):
                                base_name = file_id.replace(size + '.' + file_ext, '.' + file_ext)
                                break
                    
                    # 只保留原始尺寸的图片
                    if not any(size in base_name for size in ['_50x50', '_80x80', '_100x100', '_120x120', '_200x200', '_250x250', '_350x350']):
                        url = f"https://sc04.alicdn.com/kf/{base_name}"
                        unique_urls[base_name] = (url, base_name, file_ext)
                
                # 并发检查图片大小
                tasks = []
                for base_name, (url, base_name, file_ext) in unique_urls.items():
                    task = self.check_image_size(url, base_name, file_ext)
                    tasks.append(task)
                
                # 分批处理，每批10个（增加并发）
                batch_size = 10
                all_licenses = []
                
                for i in range(0, len(tasks), batch_size):
                    batch_tasks = tasks[i:i + batch_size]
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"检查图片大小时出错: {result}")
                        elif result is not None:
                            all_licenses.append(result)
                
                # 只保留最大的一张图片
                if all_licenses:
                    # 按文件大小排序，选择最大的一张
                    largest_license = max(all_licenses, key=lambda x: x.get('file_size', 0))
                    print(f"找到 {len(all_licenses)} 个有效执照图片，保留最大的一张: {largest_license['url']} (大小: {largest_license.get('file_size', 0)} bytes)")
                    return [largest_license]
                else:
                    print("未找到有效的执照图片")
                    return []
            else:
                print("未找到执照图片")
                return []
                
        except Exception as e:
            print(f"提取执照图片失败: {e}")
            return []
    
    def extract_license_info_from_html(self, html_content):
        """从HTML内容中提取执照详细信息"""
        try:
            # 提取营业执照信息的正则表达式
            info_patterns = {
                'registration_no': r'<span>Registration No\.</span>\s*:\s*([^<]+)',
                'company_name': r'<span>Company Name</span>\s*:\s*([^<]+)',
                'date_of_issue': r'<span>Date of Issue</span>\s*:\s*([^<]+)',
                'date_of_expiry': r'<span>Date of Expiry</span>\s*:\s*([^<]+)',
                'registered_capital': r'<span>Registered Capital</span>\s*:\s*([^<]+)',
                'country_territory': r'<span>Country/Territory</span>\s*:\s*([^<]+)',
                'registered_address': r'<span>Registered address</span>\s*:\s*([^<]+)',
                'year_established': r'<span>Year Established</span>\s*:\s*([^<]+)',
                'legal_form': r'<span>Legal Form</span>\s*:\s*([^<]+)',
                'legal_representative': r'<span>Legal Representative</span>\s*:\s*([^<]+)'
            }
            
            license_info = {}
            for field, pattern in info_patterns.items():
                match = re.search(pattern, html_content)
                if match:
                    license_info[field] = match.group(1).strip()
                else:
                    license_info[field] = ''
            
            # 检查是否找到了任何信息
            if any(license_info.values()):
                print(f"找到执照信息: {len([v for v in license_info.values() if v])} 个字段")
                return license_info
            else:
                print("未找到执照信息")
                return None
                
        except Exception as e:
            print(f"提取执照信息失败: {e}")
            return None
    
    async def fetch_supplier_page(self, action_url, proxy=None, session=None, check_ip=False, log_callback=None):
        """获取供应商页面HTML"""
        try:
            # 确保URL包含subpage参数
            if 'subpage=onsiteDetail' not in action_url:
                if '?' in action_url:
                    actual_url = action_url + '&subpage=onsiteDetail'
                else:
                    actual_url = action_url + '?subpage=onsiteDetail'
            else:
                actual_url = action_url
            
            self.log(f"请求供应商页面: {actual_url}", "INFO", log_callback)
            
            # 使用HTML请求头获取页面（可控制IP检查）
            html_content = await self.fetch_with_proxy(actual_url, proxy, session, is_html=True, check_ip=check_ip, log_callback=log_callback)
            
            if html_content:
                self.log(f"成功获取页面，长度: {len(html_content)} 字符", "SUCCESS", log_callback)
                return html_content
            else:
                self.log("获取页面失败", "ERROR", log_callback)
                return None
                
        except Exception as e:
            self.log(f"获取供应商页面失败: {e}", "ERROR", log_callback)
            return None
    
    async def extract_all_licenses(self, suppliers, proxy=None, session=None, log_callback=None):
        """提取所有供应商的执照图片"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for i, supplier in enumerate(suppliers, 1):
                self.log(f"处理第 {i}/{len(suppliers)} 个供应商: {supplier['company_name']}", "INFO", log_callback)
                
                # 获取供应商页面HTML（启用IP检测）
                html_content = await self.fetch_supplier_page(supplier['action_url'], proxy, session, check_ip=True, log_callback=log_callback)
                
                if html_content:
                    # 提取执照图片
                    licenses = await self.extract_licenses_from_html(html_content)
                    
                    if licenses:
                        # 保存执照图片到数据库
                        for license_item in licenses:
                            cursor.execute('''
                                INSERT INTO licenses (supplier_id, license_name, license_url, file_id)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                supplier['company_id'],  # 使用company_id作为supplier_id
                                license_item['name'],
                                license_item['url'],
                                license_item['fileId']
                            ))
                        
                        print(f"  - 找到 {len(licenses)} 个执照图片")
                    else:
                        print(f"  - 未找到执照图片")
                
                # 延迟避免请求过快
                if i < len(suppliers):
                    await asyncio.sleep(random.uniform(0.5, 1))
            
            conn.commit()
            conn.close()
            print("执照图片提取完成")
            
        except Exception as e:
            print(f"提取执照图片过程中出错: {e}")
            if 'conn' in locals():
                conn.close()
    
    async def extract_licenses_from_database(self, proxy=None):
        """从数据库中的供应商提取执照图片 - 使用10个并发线程"""
        try:
            # 获取数据库中的所有供应商
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT company_id, company_name, action_url 
                FROM suppliers 
                WHERE (license_extracted = FALSE OR license_extracted IS NULL)
                  AND (skip_extraction = FALSE OR skip_extraction IS NULL)
                ORDER BY created_at DESC
            ''')
            
            suppliers = cursor.fetchall()
            conn.close()
            
            if not suppliers:
                print("数据库中没有供应商数据")
                return 0
            
            print(f"从数据库获取到 {len(suppliers)} 个供应商，使用5个并发线程处理")
            
            # 创建异步会话 - 优化并发设置
            connector = aiohttp.TCPConnector(limit=20)  # 从60减少到20
            timeout = aiohttp.ClientTimeout(total=15)  # 从10增加到15秒
            
            processed_count = 0
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # 将供应商分成5个一组 - 减少批次大小
                batch_size = 5
                for i in range(0, len(suppliers), batch_size):
                    batch = suppliers[i:i + batch_size]
                    print(f"处理批次 {i//batch_size + 1}/{(len(suppliers) + batch_size - 1)//batch_size}: {len(batch)} 个供应商")
                    
                    # 创建5个并发任务
                    tasks = []
                    for company_id, company_name, action_url in batch:
                        task = self.process_single_supplier(company_id, company_name, action_url, proxy, session)
                        tasks.append(task)
                    
                    # 并发执行，不等待所有任务完成
                    # 使用asyncio.create_task来创建任务，然后立即开始下一批
                    running_tasks = []
                    for task in tasks:
                        running_tasks.append(asyncio.create_task(task))
                    
                    # 等待当前批次的任务完成（不阻塞下一批）
                    for task in running_tasks:
                        try:
                            result = await task
                            if result:
                                processed_count += 1
                        except Exception as e:
                            print(f"处理供应商时出错: {e}")
                    
                    # 批次间延迟（固定1秒延迟）
                    if i + batch_size < len(suppliers):
                        delay = 1.0  # 固定1秒延迟
                        print(f"批次间等待 {delay:.1f} 秒...")
                        await asyncio.sleep(delay)
            
            print(f"执照图片提取完成，成功处理 {processed_count} 个供应商")
            return processed_count
            
        except Exception as e:
            print(f"从数据库提取执照图片时出错: {e}")
            return 0
    
    async def process_single_supplier(self, company_id, company_name, action_url, proxy, session, log_callback=None):
        """处理单个供应商 - 用于并发处理"""
        try:
            self.log(f"开始处理: {company_name}", "INFO", log_callback)
            
            # 获取供应商页面HTML（启用IP检测）
            html_content = await self.fetch_supplier_page(action_url, proxy, session, check_ip=True, log_callback=log_callback)
            
            if html_content:
                self.log(f"  - {company_name}: 成功获取页面", "SUCCESS", log_callback)
                
                # 提取执照图片
                licenses = await self.extract_licenses_from_html(html_content)
                
                # 提取执照信息
                license_info = self.extract_license_info_from_html(html_content)
                
                # 保存到数据库
                conn = sqlite3.connect(self.db_path)
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
                    print(f"  - {company_name}: 执照信息已保存")
                
                # 如果成功提取到执照信息，标记为已获取并保存到文件
                if licenses or license_info:
                    cursor.execute('UPDATE suppliers SET license_extracted = TRUE WHERE company_id = ?', (company_id,))
                    
                    # 获取分类信息
                    cursor.execute('SELECT category_id, category_name FROM suppliers WHERE company_id = ?', (company_id,))
                    category_data = cursor.fetchone()
                    
                    if category_data and category_data[0]:
                        category_id, category_name = category_data
                        # 自动保存到对应分类目录
                        save_path = await self.save_single_supplier_to_category(company_id, company_name, licenses, license_info, category_id, category_name)
                        
                        # 更新数据库中的保存路径
                        if save_path:
                            cursor.execute('UPDATE suppliers SET save_path = ? WHERE company_id = ?', (save_path, company_id))
                    
                    conn.commit()
                
                conn.close()
                
                return bool(licenses or license_info)
            else:
                print(f"  - {company_name}: 无法获取页面")
                # 更新失败次数和最后尝试时间
                self.update_extraction_failure(company_id, company_name)
                return False
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"  - {company_name}: 处理出错: {e}")
            print(f"  - 详细错误信息: {error_detail}")
            if log_callback:
                self.log(f"  - {company_name}: 处理出错: {e}", "ERROR", log_callback)
                self.log(f"  - 详细错误: {error_detail}", "DEBUG", log_callback)
            # 更新失败次数和最后尝试时间
            self.update_extraction_failure(company_id, company_name)
            return False
    
    def update_extraction_failure(self, company_id, company_name, max_failures=3):
        """更新提取失败次数，超过阈值自动标记为跳过"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新失败次数和最后尝试时间
            cursor.execute('''
                UPDATE suppliers 
                SET extraction_failed_count = COALESCE(extraction_failed_count, 0) + 1,
                    last_extraction_attempt = CURRENT_TIMESTAMP
                WHERE company_id = ?
            ''', (company_id,))
            
            # 获取当前失败次数
            cursor.execute('SELECT extraction_failed_count FROM suppliers WHERE company_id = ?', (company_id,))
            result = cursor.fetchone()
            
            if result and result[0] >= max_failures:
                # 超过失败阈值，自动标记为跳过
                cursor.execute('UPDATE suppliers SET skip_extraction = TRUE WHERE company_id = ?', (company_id,))
                print(f"  - {company_name}: 失败次数达到{max_failures}次，已自动标记为跳过提取")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"更新失败次数时出错: {e}")
    
    async def extract_single_license(self, company_id, company_name, action_url, proxy=None, log_callback=None):
        """提取单个供应商的执照"""
        try:
            self.log(f"开始提取: {company_name}", "INFO", log_callback)
            
            # 获取供应商页面HTML
            html_content = await self.fetch_supplier_page(action_url, proxy, log_callback=log_callback)
            
            if html_content:
                self.log(f"  - {company_name}: 成功获取页面", "SUCCESS", log_callback)
                
                # 提取执照图片
                licenses = await self.extract_licenses_from_html(html_content)
                
                # 提取执照信息
                license_info = self.extract_license_info_from_html(html_content)
                
                # 保存到数据库
                conn = sqlite3.connect(self.db_path)
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

    async def recognize_license_from_url(self, action_url, proxy=None, log_callback=None):
        """从URL识别执照信息"""
        try:
            self.log(f"开始识别执照: {action_url}", "INFO", log_callback)
            
            # 获取供应商页面HTML
            html_content = await self.fetch_supplier_page(action_url, proxy, log_callback=log_callback)
            
            if html_content:
                self.log(f"成功获取页面", "SUCCESS", log_callback)
                
                # 提取执照图片
                licenses = await self.extract_licenses_from_html(html_content)
                
                # 提取执照信息
                license_info = self.extract_license_info_from_html(html_content)
                
                # 获取或创建供应商记录
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 尝试从URL中提取company_id
                company_id = None
                try:
                    # 从action_url中提取company_id
                    match = re.search(r'company_id=(\d+)', action_url)
                    if match:
                        company_id = match.group(1)
                    else:
                        # 如果没有找到，生成一个基于URL的ID
                        company_id = str(hash(action_url) % 1000000000)
                except:
                    company_id = str(hash(action_url) % 1000000000)
                
                # 检查是否已存在该供应商
                cursor.execute('SELECT company_id, company_name FROM suppliers WHERE action_url = ?', (action_url,))
                existing_supplier = cursor.fetchone()
                
                if existing_supplier:
                    company_id, company_name = existing_supplier
                else:
                    # 创建新的供应商记录
                    company_name = f"供应商_{company_id}"
                    cursor.execute('''
                        INSERT INTO suppliers (company_id, company_name, action_url, created_at)
                        VALUES (?, ?, ?, ?)
                    ''', (company_id, company_name, action_url, datetime.now()))
                    conn.commit()
                
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
                    print(f"找到 {len(licenses)} 个执照图片")
                
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
                
                # 标记为已提取
                cursor.execute('UPDATE suppliers SET license_extracted = TRUE WHERE company_id = ?', (company_id,))
                
                conn.commit()
                conn.close()
                
                return {
                    'company_id': company_id,
                    'company_name': company_name,
                    'licenses': licenses,
                    'license_info': license_info
                }
            else:
                print("获取页面失败")
                return None
                
        except Exception as e:
            print(f"识别执照时出错: {e}")
            return None

class AlibabaSupplierCrawlerGUI:
    def __init__(self):
        self.crawler = AlibabaSupplierCrawler()
        self.setup_gui()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("阿里巴巴供应商爬虫")
        self.root.geometry("700x500")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="爬取设置", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(input_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.keyword_entry = ttk.Entry(input_frame, width=40)
        self.keyword_entry.insert(0, "men's perfume")
        self.keyword_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="页数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pages_entry = ttk.Entry(input_frame, width=40)
        self.pages_entry.insert(0, "1")
        self.pages_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 代理配置
        ttk.Label(input_frame, text="代理服务器:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.proxy_entry = ttk.Entry(input_frame, width=40)
        # 预设新隧道代理信息
        self.proxy_entry.insert(0, "http://t15395136610470:kyhxo4pj@y900.kdltps.com:15818")
        self.proxy_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # 代理使用开关
        self.use_proxy_var = tk.BooleanVar()
        self.use_proxy_check = ttk.Checkbutton(input_frame, text="使用代理", variable=self.use_proxy_var)
        self.use_proxy_check.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 执照图片提取开关
        self.extract_licenses_var = tk.BooleanVar()
        self.extract_licenses_check = ttk.Checkbutton(input_frame, text="提取执照图片", variable=self.extract_licenses_var)
        self.extract_licenses_check.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始爬取", command=self.start_crawl)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_crawl, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.extract_button = ttk.Button(button_frame, text="手动提取执照", command=self.manual_extract_licenses)
        self.extract_button.pack(side=tk.LEFT)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack()
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 配置网格权重
        input_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def parse_proxy(self, proxy_string):
        """解析代理字符串"""
        if not proxy_string or not self.use_proxy_var.get():
            return None
        
        try:
            # 解析代理格式: http://username:password@host:port
            if '@' in proxy_string:
                # 有认证信息的代理
                auth_part, server_part = proxy_string.split('@', 1)
                protocol = auth_part.split('://')[0]
                auth = auth_part.split('://')[1]
                username, password = auth.split(':')
                host, port = server_part.split(':')
                
                return {
                    'host': host,
                    'port': int(port),
                    'username': username,
                    'password': password
                }
            else:
                # 无认证信息的代理
                return None
        except Exception as e:
            print(f"代理解析失败: {e}")
            return None
    
    def start_crawl(self):
        """开始爬取"""
        keyword = self.keyword_entry.get().strip()
        pages = self.pages_entry.get().strip()
        proxy_string = self.proxy_entry.get().strip()
        
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
        proxy = self.parse_proxy(proxy_string)
        if self.use_proxy_var.get() and not proxy:
            messagebox.showerror("错误", "代理格式不正确！\n格式示例: http://username:password@proxy.stock5.com:port")
            return
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress['value'] = 0
        self.progress['maximum'] = pages
        
        # 在新线程中运行爬虫
        extract_licenses = self.extract_licenses_var.get()
        self.crawl_thread = threading.Thread(target=self.run_crawler, args=(keyword, pages, proxy, extract_licenses))
        self.crawl_thread.daemon = True
        self.crawl_thread.start()
    
    def run_crawler(self, keyword, pages, proxy, extract_licenses):
        """运行爬虫"""
        try:
            if proxy:
                self.log(f"开始爬取供应商, 关键词: {keyword}, 页数: {pages}, 使用代理: {proxy['host']}:{proxy['port']}")
            else:
                self.log(f"开始爬取供应商, 关键词: {keyword}, 页数: {pages}")
            
            if extract_licenses:
                self.log("启用执照图片提取功能")
            
            # 运行异步爬虫
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            suppliers = loop.run_until_complete(
                self.crawler.crawl_suppliers(keyword, pages, proxy, extract_licenses)
            )
            
            self.log(f"爬取完成，共获取 {len(suppliers)} 个供应商")
            
            if extract_licenses:
                self.log("执照图片提取完成")
            
            # 更新UI
            self.root.after(0, lambda: self.crawl_finished())
            
        except Exception as e:
            self.log(f"爬取失败: {e}")
            self.root.after(0, lambda: self.crawl_finished())
    
    def crawl_finished(self):
        """爬取完成"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="爬取完成")
    
    def stop_crawl(self):
        """停止爬取"""
        self.log("用户停止爬取")
        self.crawl_finished()
    
    def manual_extract_licenses(self):
        """手动提取执照图片"""
        proxy_string = self.proxy_entry.get().strip()
        
        # 解析代理
        proxy = self.parse_proxy(proxy_string)
        if self.use_proxy_var.get() and not proxy:
            messagebox.showerror("错误", "代理格式不正确！")
            return
        
        self.log("开始手动提取执照图片...")
        
        # 在新线程中运行提取
        self.extract_thread = threading.Thread(target=self.run_manual_extract, args=(proxy,))
        self.extract_thread.daemon = True
        self.extract_thread.start()
    
    def run_manual_extract(self, proxy):
        """运行手动提取"""
        try:
            if proxy:
                self.log(f"使用代理: {proxy['host']}:{proxy['port']}")
            else:
                self.log("不使用代理")
            
            # 运行异步提取
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.crawler.extract_licenses_from_database(proxy)
            )
            
            self.log(f"提取完成，处理了 {result} 个供应商")
            
            # 更新UI
            self.root.after(0, lambda: self.extract_finished())
            
        except Exception as e:
            self.log(f"提取失败: {e}")
            self.root.after(0, lambda: self.extract_finished())
    
    def extract_finished(self):
        """提取完成"""
        self.status_label.config(text="提取完成")
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AlibabaSupplierCrawlerGUI()
    app.run()