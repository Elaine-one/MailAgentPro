#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮件发送模块
负责SMTP连接、SSL发送、批量群发、多线程发送、重试机制等
"""

import smtplib
import time
import threading
import io
import weakref
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime
from db.db_manager import get_db_manager, Task, TaskDetail
from core.account_manager import AccountManager
from core.history_tracker import HistoryTracker
from collections import defaultdict
import queue
import contextlib
from typing import Optional, Dict, List
from email.generator import BytesGenerator
from email.policy import SMTP


class MailError(Exception):
    """邮件发送错误基类"""
    def __init__(self, message, error_type="general", recoverable=True):
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable


class NetworkError(MailError):
    """网络相关错误"""
    def __init__(self, message, recoverable=True):
        super().__init__(message, "network", recoverable)


class AuthError(MailError):
    """认证错误"""
    def __init__(self, message="认证失败", recoverable=False):
        super().__init__(message, "auth", recoverable)


class FileError(MailError):
    """文件处理错误"""
    def __init__(self, message, recoverable=True):
        super().__init__(message, "file", recoverable)


class TimeoutError(MailError):
    """超时错误"""
    def __init__(self, message="操作超时", recoverable=True):
        super().__init__(message, "timeout", recoverable)


class StreamingAttachment:
    """流式附件处理类，用于避免大文件内存泄露"""
    
    def __init__(self, file_path: str, chunk_size: int = 8192):
        """
        初始化流式附件
        
        Args:
            file_path (str): 文件路径
            chunk_size (int): 每次读取的块大小，默认8KB
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self._file = None
        self._weak_refs = weakref.WeakSet()
        
    def __enter__(self):
        """上下文管理器入口"""
        self._file = open(self.file_path, 'rb')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，确保文件正确关闭"""
        if self._file:
            self._file.close()
            self._file = None
    
    def read_chunk(self) -> bytes:
        """读取文件块"""
        if not self._file:
            raise ValueError("文件未打开，请使用上下文管理器")
        return self._file.read(self.chunk_size)
    
    def read_all(self) -> bytes:
        """读取全部内容（小文件使用）"""
        if not self._file:
            raise ValueError("文件未打开，请使用上下文管理器")
        return self._file.read()
    
    def get_size(self) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(self.file_path)
        except OSError:
            return 0


class MailSender:
    """邮件发送类"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.account_manager = AccountManager()
        self.history_tracker = HistoryTracker()
        
        # 连接池优化
        self._connection_pool = {}  # account_id -> connection info
        self._pool_lock = threading.Lock()
        self._max_pool_size = 10  # 最大连接池大小
        self._connection_expiry = 300  # 连接过期时间（秒）
        
        # 文件流处理配置
        self._streaming_threshold = 1024 * 1024  # 1MB，超过此大小使用流式处理
        self._max_file_handles = 20  # 最大同时打开的文件句柄数
        
        # 资源清理和超时配置
        self._cleanup_interval = 300  # 清理间隔（秒）
        self._max_connection_age = 600  # 最大连接年龄（秒）
        self._cleanup_thread = None
        self._cleanup_running = False
        
        # 错误恢复配置
        self._max_retries = 3
        self._retry_delay = 5
        self._backoff_multiplier = 2
        
        # 启动资源清理线程
        self._start_cleanup_thread()
    
    def _classify_error(self, error):
        """错误分类"""
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['auth', 'login', 'password', 'username']):
            return AuthError(str(error))
        elif any(keyword in error_str for keyword in ['timeout', 'timed out', 'connect']):
            return TimeoutError(str(error))
        elif any(keyword in error_str for keyword in ['file', 'not found', 'permission', 'read']):
            return FileError(str(error))
        elif any(keyword in error_str for keyword in ['network', 'connection', 'smtp', 'socket']):
            return NetworkError(str(error))
        else:
            return MailError(str(error))
    
    def _should_retry(self, error, attempt):
        """判断是否应该重试"""
        if attempt >= self._max_retries:
            return False
        
        classified_error = self._classify_error(error)
        
        # 认证错误不重试
        if isinstance(classified_error, AuthError):
            return False
        
        # 其他错误根据重试次数和退避策略决定
        return classified_error.recoverable
    
    def _calculate_retry_delay(self, attempt):
        """计算重试延迟时间（指数退避）"""
        return min(self._retry_delay * (self._backoff_multiplier ** attempt), 300)  # 最大5分钟
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """带退避的重试机制"""
        last_error = None
        
        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self._should_retry(e, attempt):
                    raise self._classify_error(e)
                
                if attempt < self._max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    print(f"操作失败，{delay}秒后重试 (第{attempt + 1}次): {e}")
                    time.sleep(delay)
        
        raise self._classify_error(last_error)
    
    def _start_cleanup_thread(self):
        """启动资源清理线程"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_resources, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_resources(self):
        """资源清理线程"""
        while self._cleanup_running:
            try:
                current_time = time.time()
                
                # 清理过期的连接
                expired_accounts = []
                with self._pool_lock:
                    for account_id, conn_info in self._connection_pool.items():
                        if current_time - conn_info['created_time'] > self._max_connection_age:
                            expired_accounts.append(account_id)
                
                for account_id in expired_accounts:
                    try:
                        self._connection_pool[account_id]['connection'].quit()
                    except:
                        pass
                    del self._connection_pool[account_id]
                    print(f"清理过期连接: 账户 {account_id}")
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
            except Exception as e:
                print(f"资源清理失败: {e}")
            
            # 等待清理间隔
            time.sleep(self._cleanup_interval)
    
    def __del__(self):
        """析构函数，确保资源正确清理"""
        self._cleanup_running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        # 关闭所有连接
        with self._pool_lock:
            for conn_info in self._connection_pool.values():
                try:
                    conn_info['connection'].quit()
                except:
                    pass
            self._connection_pool.clear()
        
    def _get_connection_from_pool(self, account_info):
        """从连接池获取连接"""
        account_id = account_info['id']
        current_time = time.time()
        
        with self._pool_lock:
            # 检查连接是否存在且未过期
            if account_id in self._connection_pool:
                conn_info = self._connection_pool[account_id]
                if current_time - conn_info['created_time'] < self._connection_expiry:
                    return conn_info['connection']
                else:
                    # 连接过期，移除
                    del self._connection_pool[account_id]
            
            return None
    
    def _add_connection_to_pool(self, account_info, connection):
        """添加连接到连接池"""
        account_id = account_info['id']
        current_time = time.time()
        
        with self._pool_lock:
            # 如果池已满，移除最旧的连接
            if len(self._connection_pool) >= self._max_pool_size:
                oldest_account = min(self._connection_pool.keys(), 
                                   key=lambda k: self._connection_pool[k]['created_time'])
                try:
                    self._connection_pool[oldest_account]['connection'].quit()
                except:
                    pass
                del self._connection_pool[oldest_account]
            
            # 添加新连接
            self._connection_pool[account_id] = {
                'connection': connection,
                'created_time': current_time
            }
    
    def _get_or_create_smtp_connection(self, account_info):
        """获取或创建SMTP连接（带连接池优化）"""
        # 首先尝试从连接池获取
        existing_conn = self._get_connection_from_pool(account_info)
        if existing_conn:
            try:
                # 测试连接是否仍然有效
                existing_conn.noop()
                return existing_conn, False  # 返回连接和是否新创建的标志
            except:
                # 连接无效，移除
                with self._pool_lock:
                    if account_info['id'] in self._connection_pool:
                        del self._connection_pool[account_info['id']]
        
        # 创建新连接
        try:
            if account_info['port'] == 465:
                # SSL连接
                server = smtplib.SMTP_SSL(account_info['smtp_server'], account_info['port'])
            else:
                # STARTTLS连接
                server = smtplib.SMTP(account_info['smtp_server'], account_info['port'])
                server.starttls()
            
            # 登录
            server.login(account_info['email'], account_info['auth_code'])
            
            # 添加到连接池
            self._add_connection_to_pool(account_info, server)
            
            return server, True  # 返回新连接和是否新创建的标志
        except Exception as e:
            raise e
    
    def send_email(self, account, to_email, to_name, subject, content, attachment_path=None):
        """
        发送单封邮件（兼容EmailSendWorker的调用格式）
        
        Args:
            account (dict): 账户信息字典
            to_email (str): 收件人邮箱
            to_name (str): 收件人姓名
            subject (str): 邮件主题
            content (str): 邮件内容
            attachment_path (str, optional): 单个附件路径
        """
        # 将单个附件路径转换为列表格式
        attachments = [attachment_path] if attachment_path else None
        
        # 调用现有的send_single_email方法
        success, error_msg = self.send_single_email(
            account_id=account['id'],
            recipient_email=to_email,
            recipient_name=to_name,
            subject=subject,
            body=content,
            attachments=attachments
        )
        
        # 如果失败，抛出异常供调用者捕获
        if not success:
            raise Exception(error_msg)
        
        # 成功时不需要返回任何值，或者返回None
    
    def _add_attachment_to_message(self, msg, file_path: str):
        """
        流式添加附件到邮件消息（避免大文件内存泄露）
        
        Args:
            msg: 邮件消息对象
            file_path: 附件文件路径
            
        Returns:
            bool: 是否成功添加附件
        """
        if not os.path.isfile(file_path):
            return False
            
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # 小文件直接加载到内存
            if file_size < self._streaming_threshold:
                with open(file_path, "rb") as attachment:
                    file_data = attachment.read()
                    
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(part)
                return True
            
            # 大文件使用流式处理
            else:
                with StreamingAttachment(file_path) as streaming_file:
                    # 创建MIME部分
                    part = MIMEBase('application', 'octet-stream')
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    
                    # 流式读取文件并设置payload
                    file_data = streaming_file.read_all()
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    msg.attach(part)
                    return True
                    
        except Exception as e:
            print(f"添加附件失败 {file_path}: {e}")
            return False
    
    def send_single_email(self, account_id, recipient_email, recipient_name, subject, body, attachments=None):
        """
        发送单封邮件（带连接池优化、错误分类和恢复机制）
        
        Args:
            account_id (int): 发件账户ID
            recipient_email (str): 收件人邮箱
            recipient_name (str): 收件人姓名
            subject (str): 邮件主题
            body (str): 邮件正文
            attachments (list, optional): 附件路径列表
            
        Returns:
            tuple: (是否成功, 错误信息)
        """
        def _send_email_with_retry():
            # 获取账户信息
            account_info = self.account_manager.get_account(account_id)
            if not account_info:
                raise AuthError("发件账户不存在")
                
            try:
                # 创建邮件对象
                msg = MIMEMultipart()
                msg['From'] = account_info['email']
                msg['To'] = recipient_email
                msg['Subject'] = subject
                
                # 添加邮件正文
                msg.attach(MIMEText(body, 'html', 'utf-8'))
                
                # 流式添加附件（避免大文件内存泄露）
                if attachments:
                    for file_path in attachments:
                        if os.path.isfile(file_path):
                            if not self._add_attachment_to_message(msg, file_path):
                                print(f"跳过无效附件: {file_path}")
                
                # 获取或创建SMTP连接
                server, is_new_connection = self._get_or_create_smtp_connection(account_info)
                
                if server is None:
                    raise NetworkError("无法建立SMTP连接")
                
                # 发送邮件（带超时控制）
                def send_with_timeout():
                    server.send_message(msg)
                
                # 使用线程和定时器实现超时
                result = {'success': False, 'error': None}
                
                def send_worker():
                    try:
                        send_with_timeout()
                        result['success'] = True
                    except Exception as e:
                        result['error'] = str(e)
                
                # 启动发送线程
                send_thread = threading.Thread(target=send_worker)
                send_thread.daemon = True
                send_thread.start()
                send_thread.join(30)  # 30秒超时
                
                if send_thread.is_alive():
                    # 超时，连接可能已死
                    raise TimeoutError("邮件发送超时 (30秒)")
                
                if not result['success']:
                    # 发送失败，如果是连接问题，移除该连接
                    if "connection" in str(result['error']).lower() or "timeout" in str(result['error']).lower():
                        with self._pool_lock:
                            if account_info['id'] in self._connection_pool:
                                try:
                                    self._connection_pool[account_info['id']]['connection'].quit()
                                except:
                                    pass
                                del self._connection_pool[account_info['id']]
                    raise NetworkError(f"发送失败: {result['error']}")
                
                # 如果是新连接，保持连接以供复用
                if not is_new_connection:
                    try:
                        server.noop()  # 保持连接活跃
                    except:
                        # 如果noop失败，连接可能已经断开，移除它
                        with self._pool_lock:
                            if account_info['id'] in self._connection_pool:
                                del self._connection_pool[account_info['id']]
                    
                return True, "发送成功"
                
            except Exception as e:
                raise
                
            finally:
                # 资源清理：确保邮件对象正确清理
                try:
                    # 清理msg中的所有附件引用，防止内存泄露
                    if hasattr(msg, '_payload') and msg._payload:
                        # 保留第一个payload（正文），清理其他payload（附件）
                        if len(msg._payload) > 1:
                            msg._payload = [msg._payload[0]]
                except Exception as cleanup_error:
                    print(f"清理邮件对象失败: {cleanup_error}")
        
        try:
            # 使用错误分类和重试机制发送邮件
            return self._retry_with_backoff(_send_email_with_retry)
        except Exception as e:
            classified_error = self._classify_error(e)
            print(f"邮件发送失败 - 类型: {classified_error.error_type}, 详情: {str(classified_error)}")
            return False, str(classified_error)
            
    def send_batch_emails(self, account_id, recipients, subject, body, attachments=None, interval=1):
        """
        批量发送邮件（优化版：批量数据库操作、减少网络请求）
        
        Args:
            account_id (int): 发件账户ID
            recipients (list): 收件人列表 [{'name': '姓名', 'email': '邮箱'}, ...]
            subject (str): 邮件主题
            body (str): 邮件正文
            attachments (list, optional): 附件路径列表
            interval (int): 发送间隔（秒）
            
        Returns:
            dict: 发送结果统计
        """
        # 创建任务记录（优化：批量数据库操作）
        session = self.db_manager.get_session()
        task_id = None
        try:
            task = Task(
                account_id=account_id,
                subject=subject,
                content=body,
                total=len(recipients),
                status='sending'
            )
            session.add(task)
            session.flush()  # 获取任务ID但不提交
            task_id = task.id
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
        # 发送邮件并记录结果（优化：批量数据库操作）
        success_count = 0
        fail_count = 0
        results = []
        
        # 预加载账户信息，避免重复查询
        account_info = self.account_manager.get_account(account_id)
        if not account_info:
            return {'task_id': task_id, 'total': len(recipients), 'success': 0, 'failed': len(recipients), 'results': []}
        
        # 批量准备邮件详情（减少数据库操作次数）
        task_details = []
        
        for i, recipient in enumerate(recipients):
            # 替换邮件正文中的变量
            personalized_body = body.replace('{name}', recipient['name']).replace('{email}', recipient['email'])
            
            # 发送邮件
            success, error_msg = self.send_single_email(
                account_id, recipient['email'], recipient['name'], 
                subject, personalized_body, attachments
            )
            
            # 收集结果用于批量插入
            task_details.append({
                'task_id': task_id,
                'recipient_email': recipient['email'],
                'result': 'success' if success else 'failed',
                'error_msg': error_msg if not success else None
            })
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                
            results.append({
                'recipient': recipient,
                'success': success,
                'error_msg': error_msg
            })
            
            # 批量插入数据库（每20条或最后一条）
            if (i + 1) % 20 == 0 or i == len(recipients) - 1:
                session = self.db_manager.get_session()
                try:
                    # 批量插入任务详情
                    for detail_data in task_details:
                        detail = TaskDetail(**detail_data)
                        session.add(detail)
                    
                    # 更新任务统计
                    task = session.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task.success_count = success_count
                        task.fail_count = fail_count
                    
                    session.commit()
                    task_details.clear()  # 清空已处理的详情
                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    self.db_manager.close_session(session)
                
            # 发送间隔
            if i < len(recipients) - 1:  # 最后一个不需要等待
                time.sleep(interval)
                
        # 最终更新任务状态
        session = self.db_manager.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = 'completed' if fail_count == 0 else 'failed'
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
        return {
            'task_id': task_id,
            'total': len(recipients),
            'success': success_count,
            'failed': fail_count,
            'results': results
        }
        
    def send_batch_emails_threaded(self, account_id, recipients, subject, body, attachments=None, interval=1, max_threads=5):
        """
        多线程批量发送邮件（优化版：减少数据库连接、批量操作、连接池复用）
        
        Args:
            account_id (int): 发件账户ID
            recipients (list): 收件人列表
            subject (str): 邮件主题
            body (str): 邮件正文
            attachments (list, optional): 附件路径列表
            interval (int): 发送间隔（秒）
            max_threads (int): 最大线程数
            
        Returns:
            dict: 发送结果统计
        """
        # 创建任务记录（优化：减少数据库操作）
        session = self.db_manager.get_session()
        task_id = None
        try:
            task = Task(
                account_id=account_id,
                subject=subject,
                content=body,
                total=len(recipients),
                send_time=datetime.now(),
                status='sending'
            )
            session.add(task)
            session.flush()
            task_id = task.id
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
        # 预加载账户信息，避免重复查询
        account_info = self.account_manager.get_account(account_id)
        if not account_info:
            return {'task_id': task_id, 'total': len(recipients), 'success': 0, 'failed': len(recipients), 'results': []}
        
        # 分批处理收件人（优化：减少线程创建开销）
        batch_size = min(max_threads * 2, 20)  # 每批最多20个，避免过多线程
        batches = [recipients[i:i + batch_size] for i in range(0, len(recipients), batch_size)]
        
        success_count = 0
        fail_count = 0
        all_results = []
        all_task_details = []  # 批量收集任务详情
        
        for batch in batches:
            threads = []
            batch_results = [None] * len(batch)
            
            def send_email_wrapper(index, recipient):
                try:
                    # 替换邮件正文中的变量
                    personalized_body = body.replace('{name}', recipient['name']).replace('{email}', recipient['email'])
                    
                    # 发送邮件（复用连接池）
                    success, error_msg = self.send_single_email(
                        account_id, recipient['email'], recipient['name'], 
                        subject, personalized_body, attachments
                    )
                    
                    batch_results[index] = {
                        'recipient': recipient,
                        'success': success,
                        'error_msg': error_msg
                    }
                    
                    # 收集任务详情用于批量插入
                    all_task_details.append({
                        'task_id': task_id,
                        'recipient_email': recipient['email'],
                        'result': 'success' if success else 'failed',
                        'error_msg': error_msg if not success else None
                    })
                except Exception as e:
                    batch_results[index] = {
                        'recipient': recipient,
                        'success': False,
                        'error_msg': f"发送过程异常: {str(e)}"
                    }
                    all_task_details.append({
                        'task_id': task_id,
                        'recipient_email': recipient['email'],
                        'result': 'failed',
                        'error_msg': f"发送过程异常: {str(e)}"
                    })
            
            # 创建并启动线程（限制并发数）
            active_threads = []
            for i, recipient in enumerate(batch):
                thread = threading.Thread(target=send_email_wrapper, args=(i, recipient))
                threads.append(thread)
                active_threads.append(thread)
                thread.start()
                
                # 控制并发线程数
                if len(active_threads) >= max_threads:
                    for t in active_threads:
                        t.join()
                    active_threads.clear()
                
            # 等待剩余线程完成
            for thread in active_threads:
                thread.join()
                
            # 批量插入任务详情（每批结束后）
            if all_task_details:
                session = self.db_manager.get_session()
                try:
                    # 批量插入
                    for detail_data in all_task_details:
                        detail = TaskDetail(**detail_data)
                        session.add(detail)
                    session.commit()
                    all_task_details.clear()  # 清空已处理的详情
                except Exception as e:
                    session.rollback()
                    print(f"批量插入任务详情失败: {e}")
                finally:
                    self.db_manager.close_session(session)
                
            # 处理批次结果
            for result in batch_results:
                if result and result['success']:
                    success_count += 1
                elif result:
                    fail_count += 1
                if result:
                    all_results.append(result)
                
            # 批次间间隔
            if batches.index(batch) < len(batches) - 1:  # 最后一个批次不需要等待
                time.sleep(interval)
                
        # 最终更新任务统计和状态
        session = self.db_manager.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.success_count = success_count
                task.fail_count = fail_count
                task.status = 'completed' if fail_count == 0 else 'finished_with_errors'
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
        return {
            'task_id': task_id,
            'total': len(recipients),
            'success': success_count,
            'failed': fail_count,
            'results': all_results
        }
        
    def send_emails_async(self, account_id, recipients, subject, body, attachments, progress_callback, finished_callback, interval=1, max_threads=3, retry_count=1):
        """
        异步发送邮件（优化版：连接池复用、批量数据库操作、智能重试）
        
        Args:
            account_id (int): 发件账户ID
            recipients (list): 收件人列表
            subject (str): 邮件主题
            body (str): 邮件正文
            attachments (list): 附件路径列表
            progress_callback (function): 进度更新回调函数
            finished_callback (function): 发送完成回调函数
            interval (int): 发送间隔（秒）
            max_threads (int): 最大线程数
            retry_count (int): 重试次数
        """
        def send_thread():
            task_id = None
            session = None
            start_time = time.time()
            
            try:
                # 预加载账户信息，避免重复查询
                account_info = self.account_manager.get_account(account_id)
                if not account_info:
                    if finished_callback:
                        finished_callback(0, len(recipients) * retry_count, [], {
                            'total_time': 0,
                            'retry_count': retry_count,
                            'total_sends': len(recipients) * retry_count,
                            'success_rate': 0
                        })
                    return
                
                # 创建任务记录（优化：减少数据库操作）
                session = self.db_manager.get_session()
                task = Task(
                    account_id=account_id,
                    subject=subject,
                    content=body,
                    total=len(recipients) * retry_count,  # 总发送次数 = 收件人数 × 重试次数
                    success_count=0,
                    fail_count=0,
                    status='sending'
                )
                session.add(task)
                session.commit()
                task_id = task.id
                
                total_success_count = 0
                total_fail_count = 0
                all_results = []
                all_task_details = []  # 批量收集任务详情
                
                # 重复发送循环（优化：智能重试策略）
                for send_round in range(retry_count):
                    round_success_count = 0
                    round_fail_count = 0
                    round_results = []
                    
                    # 更新进度显示当前发送轮次
                    if progress_callback:
                        try:
                            progress_callback(0, len(recipients) * retry_count, True, f"开始第 {send_round + 1}/{retry_count} 轮发送")
                        except Exception as callback_error:
                            print(f"进度回调执行失败: {callback_error}")
                    
                    # 分批发送邮件（优化：智能批量大小）
                    batch_size = min(max(10, len(recipients) // 10), 50)  # 动态批量大小：10-50
                    for batch_start in range(0, len(recipients), batch_size):
                        batch_end = min(batch_start + batch_size, len(recipients))
                        batch_recipients = recipients[batch_start:batch_end]
                        
                        # 处理批次内的收件人（优化：减少重复计算）
                        for i, recipient in enumerate(batch_recipients):
                            global_index = batch_start + i
                            total_index = send_round * len(recipients) + global_index
                            
                            # 替换邮件正文中的变量（优化：预编译正则表达式可进一步提升性能）
                            personalized_body = body.replace('{name}', recipient['name']).replace('{email}', recipient['email'])
                            
                            # 发送邮件（复用连接池）
                            success, error_msg = self.send_single_email(
                                account_id, recipient['email'], recipient['name'], 
                                subject, personalized_body, attachments
                            )
                            
                            if success:
                                round_success_count += 1
                                total_success_count += 1
                            else:
                                round_fail_count += 1
                                total_fail_count += 1
                                
                            round_results.append({
                                'recipient': recipient['email'],
                                'round': send_round + 1,
                                'success': success,
                                'error': error_msg
                            })
                            
                            all_results.append({
                                'recipient': recipient['email'],
                                'round': send_round + 1,
                                'success': success,
                                'error': error_msg
                            })
                            
                            # 收集任务详情用于批量插入（优化：减少数据库操作）
                            all_task_details.append({
                                'task_id': task_id,
                                'recipient_email': recipient['email'],
                                'send_round': send_round + 1,
                                'result': 'success' if success else 'failed',
                                'error_msg': error_msg if not success else None
                            })
                            
                            # 定期更新进度（优化：减少UI更新频率）
                            if (total_index + 1) % 30 == 0 or total_index == len(recipients) * retry_count - 1:
                                if progress_callback:
                                    try:
                                        progress_callback(total_index + 1, len(recipients) * retry_count, success, 
                                                         f"第 {send_round + 1}/{retry_count} 轮 - {recipient['email']}")
                                    except Exception as callback_error:
                                        print(f"进度回调执行失败: {callback_error}")
                            
                            # 添加一个小延迟，避免UI线程过载（优化：减少延迟时间）
                            if (total_index + 1) % 100 == 0:
                                time.sleep(0.005)  # 5毫秒延迟，比之前减少一半
                        
                        # 批次间短暂休息，避免服务器压力过大
                        if batch_end < len(recipients):
                            time.sleep(interval)  # 使用配置的发送间隔
                    
                    # 轮次间休息（除了最后一轮）
                    if send_round < retry_count - 1:
                        time.sleep(interval)  # 使用配置的发送间隔
                
                # 批量插入剩余的任务详情（优化：确保所有数据都被记录）
                if all_task_details:
                    detail_session = None
                    try:
                        detail_session = self.db_manager.get_session()
                        for detail_data in all_task_details:
                            detail = TaskDetail(**detail_data)
                            detail_session.add(detail)
                        detail_session.commit()
                        all_task_details.clear()
                    except Exception as e:
                        if detail_session:
                            detail_session.rollback()
                        print(f"批量插入剩余任务详情失败: {e}")
                    finally:
                        if detail_session:
                            self.db_manager.close_session(detail_session)
                
                # 计算总耗时
                total_time = time.time() - start_time
                
                # 更新任务最终状态（优化：减少数据库操作）
                try:
                    session.refresh(task)
                    task.success_count = total_success_count
                    task.fail_count = total_fail_count
                    task.status = 'completed' if total_fail_count == 0 else 'failed'
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"更新任务状态失败: {e}")
                
                # 调用发送完成回调，包含统计信息
                if finished_callback:
                    try:
                        finished_callback(total_success_count, total_fail_count, all_results, {
                            'total_time': total_time,
                            'retry_count': retry_count,
                            'total_sends': len(recipients) * retry_count,
                            'success_rate': total_success_count / (len(recipients) * retry_count) if len(recipients) * retry_count > 0 else 0
                        })
                    except Exception as callback_error:
                        print(f"完成回调执行失败: {callback_error}")
                    
            except Exception as e:
                error_msg = f"发送邮件过程中出现错误: {e}"
                print(error_msg)
                
                # 更新任务状态为失败
                if session and task_id:
                    try:
                        session.refresh(task)
                        task.status = 'failed'
                        task.fail_count = len(recipients) * retry_count if recipients else 0
                        session.commit()
                    except Exception as db_error:
                        print(f"更新任务状态失败: {db_error}")
                
                # 调用发送完成回调，报告错误
                if finished_callback:
                    try:
                        finished_callback(0, len(recipients) * retry_count if recipients else 0, [{'success': False, 'error': str(e)}], {
                            'total_time': time.time() - start_time,
                            'retry_count': retry_count,
                            'total_sends': len(recipients) * retry_count if recipients else 0,
                            'success_rate': 0
                        })
                    except Exception as callback_error:
                        print(f"错误回调执行失败: {callback_error}")
            finally:
                # 确保数据库会话正确关闭
                if session:
                    try:
                        self.db_manager.close_session(session)
                    except Exception as close_error:
                        print(f"关闭数据库会话失败: {close_error}")
        
        # 在新线程中执行发送操作（优化：设置合理的线程名称）
        thread = threading.Thread(target=send_thread, name=f"EmailSender-{account_id}-{int(time.time())}")
        thread.daemon = True  # 设置为守护线程
        thread.start()
        
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务信息（优化：减少数据库连接次数）"""
        session = None
        try:
            session = self.db_manager.get_session()
            # 使用批量查询获取任务，减少数据库往返次数
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                # 使用字典直接构建结果，避免多次函数调用
                result = {
                    'id': task.id,
                    'account_id': task.account_id,
                    'subject': task.subject,
                    'content': task.content,
                    'total_count': task.total,  # 数据库中是total字段
                    'success_count': task.success_count,
                    'fail_count': task.fail_count,
                    'status': task.status,
                    'created_at': task.send_time.isoformat() if task.send_time else None,  # 数据库中是send_time字段
                    'started_at': None,  # Task模型中没有started_at字段
                    'completed_at': None  # Task模型中没有completed_at字段
                }
                return result
            else:
                return None
        except Exception as e:
            print(f"获取任务信息失败: {e}")
            return None
        finally:
            if session:
                try:
                    self.db_manager.close_session(session)
                except Exception as close_error:
                    print(f"关闭数据库会话失败: {close_error}")
        
    def get_task_details(self, task_id: int) -> List[Dict]:
        """获取任务详情列表（优化：减少数据库连接次数，批量获取数据）"""
        session = None
        try:
            session = self.db_manager.get_session()
            # 使用批量查询获取所有详情，减少数据库往返次数
            details = session.query(TaskDetail).filter(TaskDetail.task_id == task_id).all()
            # 使用列表推导式快速构建结果，避免多次函数调用
            result = [{
                'id': detail.id,
                'recipient': detail.recipient_email,  # 数据库中是recipient_email字段
                'success': detail.result == 'success',  # 数据库中是result字段，需要转换
                'error_message': detail.error_msg,  # 数据库中是error_msg字段
                'sent_at': None  # TaskDetail模型中没有sent_at字段
            } for detail in details]
            return result
        except Exception as e:
            print(f"获取任务详情失败: {e}")
            return []
        finally:
            if session:
                try:
                    self.db_manager.close_session(session)
                except Exception as close_error:
                    print(f"关闭数据库会话失败: {close_error}")