#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理模块 - 性能优化版
负责初始化数据库表结构和提供ORM接口
- 实现了真正的连接池管理
- 添加了连接池健康监控
- 优化了性能监控和错误处理
"""

import os
import sqlite3
import time
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import DisconnectionError, TimeoutError
import logging

# 数据库错误分类
class DatabaseError(Exception):
    """数据库错误基类"""
    def __init__(self, message, error_type="general", recoverable=True):
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable


class NetworkError(DatabaseError):
    """网络相关错误"""
    def __init__(self, message, recoverable=True):
        super().__init__(message, "network", recoverable)


class TimeoutError(DatabaseError):
    """超时错误"""
    def __init__(self, message="操作超时", recoverable=True):
        super().__init__(message, "timeout", recoverable)


class DatabaseSetupError(DatabaseError):
    """数据库设置错误"""
    def __init__(self, message="数据库设置错误", recoverable=False):
        super().__init__(message, "setup", recoverable)


# 数据库基类
Base = declarative_base()

class Account(Base):
    """邮箱账户表"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False)
    smtp_server = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    auth_code = Column(String, nullable=False)  # 加密存储
    alias = Column(String)  # 备注名
    use_ssl = Column(Boolean, default=False)  # 是否使用SSL
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Account(email='{self.email}', alias='{self.alias}')>"


class Recipient(Base):
    """收件人表"""
    __tablename__ = 'recipients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    group_name = Column(String)  # 分组名称
    variables = Column(Text)  # 变量存储
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Recipient(name='{self.name}', email='{self.email}')>"


class Task(Base):
    """任务表"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    subject = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    send_time = Column(DateTime, default=datetime.now)
    total = Column(Integer, default=0)  # 总收件数
    success_count = Column(Integer, default=0)  # 成功数
    fail_count = Column(Integer, default=0)  # 失败数
    status = Column(String, default='pending')  # 状态: pending, sending, completed, failed
    
    # 关联关系
    account = relationship("Account")
    details = relationship("TaskDetail", back_populates="task")
    
    def __repr__(self):
        return f"<Task(subject='{self.subject}', status='{self.status}')>"


class TaskDetail(Base):
    """任务详情表"""
    __tablename__ = 'task_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    recipient_email = Column(String, nullable=False)
    result = Column(String, default='pending')  # 成功/失败
    error_msg = Column(Text)  # 错误描述
    send_round = Column(Integer, default=1)  # 发送轮次，默认为第1轮
    
    # 关联关系
    task = relationship("Task", back_populates="details")
    
    def __repr__(self):
        return f"<TaskDetail(recipient_email='{self.recipient_email}', result='{self.result}', send_round={self.send_round})>"


class ConnectionPoolMonitor:
    """连接池监控器"""
    
    def __init__(self, engine, check_interval=30):
        self.engine = engine
        self.check_interval = check_interval
        self.is_monitoring = False
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """启动连接池监控"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("连接池监控已启动")
    
    def stop_monitoring(self):
        """停止连接池监控"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self.logger.info("连接池监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 检查连接池状态
                pool = self.engine.pool
                if hasattr(pool, 'checkedout'):
                    checked_out = pool.checkedout()
                    pool_size = pool.size() if hasattr(pool, 'size') else 0
                    
                    self.logger.debug(f"连接池状态: 已检出={checked_out}, 总大小={pool_size}")
                    
                    # 如果检出连接过多，触发清理
                    if checked_out > pool_size * 0.8:
                        self.logger.warning("连接池使用率过高，尝试清理")
                        self._cleanup_connections()
                
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"连接池监控错误: {e}")
                time.sleep(self.check_interval)
    
    def _cleanup_connections(self):
        """清理连接"""
        try:
            if hasattr(self.engine, 'pool'):
                self.engine.pool.dispose()
                self.logger.info("已清理连接池连接")
        except Exception as e:
            self.logger.error(f"清理连接失败: {e}")


class DBManager:
    """数据库管理类 - 性能优化版"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path=None):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # 使用绝对路径，避免相对路径问题
        if db_path is None:
            # 默认使用app目录下的数据库文件
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(app_dir, "mail_sender.db")
        else:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
        
        self.db_path = db_path
        
        # 确保数据库路径存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # 性能统计
        self.stats = {
            'total_queries': 0,
            'failed_queries': 0,
            'avg_query_time': 0.0,
            'total_connection_time': 0.0,
            'connection_count': 0
        }
        self.stats_lock = threading.Lock()
        
        # 创建真正的连接池引擎
        self._create_engine()
        
        # 创建连接池监控器
        self.pool_monitor = ConnectionPoolMonitor(self.engine)
        
        # 启动连接池监控
        self.pool_monitor.start_monitoring()
        
        self.logger.info(f"数据库管理器初始化完成: {self.db_path}")
    
    def _create_engine(self):
        """创建优化的数据库引擎"""
        try:
            # 数据库连接参数优化
            connect_args = {
                'check_same_thread': False,
                'timeout': 30,  # 连接超时
            }
            
            # 创建带真正连接池的引擎
            self.engine = create_engine(
                f'sqlite:///{self.db_path}',
                echo=False,
                poolclass=QueuePool,  # 使用真正的连接池
                pool_size=10,  # 基础连接池大小
                max_overflow=20,  # 最大溢出连接数
                pool_pre_ping=True,  # 连接预检查
                pool_recycle=3600,  # 连接回收时间(1小时)
                connect_args=connect_args
            )
            
            # 创建线程安全的Session工厂
            self.Session = scoped_session(
                sessionmaker(
                    bind=self.engine,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False
                )
            )
            
            self.logger.info("数据库引擎创建成功，使用QueuePool连接池")
            
        except Exception as e:
            self.logger.error(f"创建数据库引擎失败: {e}")
            raise
        
    def init_db(self):
        """初始化数据库表结构"""
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info(f"数据库初始化成功: {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
        
    def get_session(self, timeout: Optional[float] = None):
        """获取数据库会话，带性能监控和错误处理"""
        start_time = time.time()
        session = None
        
        try:
            # 性能统计
            with self.stats_lock:
                self.stats['total_queries'] += 1
                self.stats['connection_count'] += 1
            
            # 获取会话，带超时控制
            if timeout:
                # 简化的超时处理，实际项目中可能需要更复杂的超时机制
                session = self.Session()
            else:
                session = self.Session()
            
            # 记录连接时间
            connection_time = time.time() - start_time
            with self.stats_lock:
                self.stats['total_connection_time'] += connection_time
                self.stats['avg_query_time'] = (
                    (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + connection_time) 
                    / self.stats['total_queries']
                )
            
            self.logger.debug(f"获取数据库会话成功，耗时: {connection_time:.3f}秒")
            return session
            
        except (DisconnectionError, TimeoutError) as e:
            # 记录失败统计
            with self.stats_lock:
                self.stats['failed_queries'] += 1
            
            self.logger.warning(f"数据库连接超时，尝试重连: {e}")
            
            # 尝试重新连接
            self._reconnect()
            
            # 重试获取会话
            try:
                session = self.Session()
                self.logger.info("重连后获取会话成功")
                return session
            except Exception as retry_e:
                self.logger.error(f"重连后获取会话仍然失败: {retry_e}")
                raise
                
        except Exception as e:
            # 记录失败统计
            with self.stats_lock:
                self.stats['failed_queries'] += 1
            
            self.logger.error(f"获取数据库会话失败: {e}")
            raise
        
    def close_session(self, session):
        """关闭数据库会话，带错误处理"""
        if session:
            try:
                # 如果会话有未提交的更改，尝试回滚
                if hasattr(session, 'is_active') and session.is_active:
                    try:
                        session.rollback()
                    except Exception as rollback_e:
                        self.logger.warning(f"回滚会话失败: {rollback_e}")
                
                session.close()
                self.logger.debug("数据库会话关闭成功")
                
            except Exception as e:
                self.logger.error(f"关闭数据库会话失败: {e}")
                # 尝试强制清理
                try:
                    session.invalidate()
                except Exception as invalidate_e:
                    self.logger.error(f"强制清理会话失败: {invalidate_e}")
    
    @contextmanager
    def session_scope(self, timeout: Optional[float] = None):
        """数据库会话上下文管理器，自动管理会话生命周期"""
        session = self.get_session(timeout=timeout)
        try:
            yield session
            # 提交事务
            session.commit()
            self.logger.debug("数据库事务提交成功")
        except Exception as e:
            # 回滚事务
            try:
                session.rollback()
                self.logger.debug("数据库事务已回滚")
            except Exception as rollback_e:
                self.logger.error(f"回滚事务失败: {rollback_e}")
            raise
        finally:
            # 关闭会话
            self.close_session(session)
    
    def _reconnect(self):
        """重新连接数据库"""
        try:
            self.logger.info("开始重新连接数据库...")
            
            # 停止监控
            if hasattr(self, 'pool_monitor'):
                self.pool_monitor.stop_monitoring()
            
            # 关闭现有连接
            if hasattr(self, 'engine'):
                self.engine.dispose()
            
            # 重新创建引擎
            self._create_engine()
            
            # 重新启动监控
            if hasattr(self, 'pool_monitor'):
                self.pool_monitor = ConnectionPoolMonitor(self.engine)
                self.pool_monitor.start_monitoring()
            
            self.logger.info("数据库连接已重新建立")
            
        except Exception as e:
            self.logger.error(f"数据库重连失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.session_scope() as session:
                # 执行简单查询测试连接
                from sqlalchemy import text
                result = session.execute(text("SELECT 1 as test_value"))
                test_value = result.fetchone()
                
                if test_value and test_value[0] == 1:
                    self.logger.info("数据库连接测试成功")
                    return True
                else:
                    self.logger.error("数据库连接测试返回异常结果")
                    return False
                    
        except Exception as e:
            self.logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库性能统计信息"""
        return self._retry_db_operation(self._get_stats)
    
    def _get_stats(self) -> Dict[str, Any]:
        """实际获取统计信息的方法"""
        with self.stats_lock:
            stats = self.stats.copy()
            # 添加连接池状态信息
            if hasattr(self, 'engine') and hasattr(self.engine, 'pool'):
                try:
                    pool = self.engine.pool
                    stats.update({
                        'pool_checkedout': pool.checkedout() if hasattr(pool, 'checkedout') else 0,
                        'pool_size': pool.size() if hasattr(pool, 'size') else 0,
                        'pool_overflow': pool.overflow() if hasattr(pool, 'overflow') else 0
                    })
                except Exception as e:
                    self.logger.warning(f"获取连接池状态失败: {e}")
            
            return stats
    
    def _classify_db_error(self, error: Exception) -> DatabaseError:
        """分类数据库错误"""
        error_message = str(error).lower()
        
        # 分类为网络相关错误
        if any(keyword in error_message for keyword in ['connection', 'network', 'timeout', 'disconnected']):
            return NetworkError(str(error), recoverable=True)
        
        # 分类为超时错误
        if any(keyword in error_message for keyword in ['timeout', 'timed out']):
            return TimeoutError(str(error), recoverable=True)
        
        # 分类为数据库设置错误
        if any(keyword in error_message for keyword in ['setup', 'initialization', 'create', 'schema']):
            return DatabaseSetupError(str(error), recoverable=False)
        
        # 默认分类为通用数据库错误
        return DatabaseError(str(error), "general", recoverable=True)
    
    def _should_retry_db_operation(self, error: Exception, attempt: int, max_attempts: int = 3) -> bool:
        """判断是否应该重试数据库操作"""
        if attempt >= max_attempts:
            return False
        
        # 分类错误
        classified_error = self._classify_db_error(error)
        
        # 可恢复的错误可以重试
        return classified_error.recoverable
    
    def _retry_db_operation(self, operation, max_attempts: int = 3, delay: float = 1.0):
        """重试数据库操作"""
        for attempt in range(1, max_attempts + 1):
            try:
                return operation()
            except Exception as e:
                classified_error = self._classify_db_error(e)
                
                if attempt < max_attempts and classified_error.recoverable:
                    wait_time = delay * (2 ** (attempt - 1))  # 指数退避
                    self.logger.warning(f"数据库操作失败 (尝试 {attempt}/{max_attempts}): {e}, {wait_time:.1f}秒后重试")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"数据库操作最终失败 (尝试 {attempt}/{max_attempts}): {e}")
                    raise classified_error
        
        # 如果到达这里，说明所有重试都失败了
        raise DatabaseError("所有重试均失败", "retry_exhausted", recoverable=False)
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止监控
            if hasattr(self, 'pool_monitor'):
                self.pool_monitor.stop_monitoring()
            
            # 关闭所有会话
            if hasattr(self, 'Session'):
                self.Session.remove()
            
            # 关闭引擎
            if hasattr(self, 'engine'):
                self.engine.dispose()
            
            self.logger.info("数据库管理器资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass


# 全局数据库管理实例
db_manager = DBManager()


def get_db_manager():
    """获取全局数据库管理实例"""
    return db_manager


def init_database():
    """初始化数据库"""
    db_manager.init_db()
    print("数据库初始化完成")