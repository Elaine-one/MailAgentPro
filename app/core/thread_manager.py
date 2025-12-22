#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一线程管理模块
提供线程池、异步任务调度、线程安全等统一管理功能
"""

import threading
import queue
import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Dict, List, Optional
from enum import Enum

from .thread_types import TaskPriority, TaskStatus, PoolType
from .thread_pool_manager import get_thread_pool_manager, submit_to_pool


class ThreadTask:
    """线程任务封装类"""
    
    def __init__(self, 
                 task_id: str,
                 func: Callable,
                 args: tuple = (),
                 kwargs: Dict[str, Any] = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.callback = callback
        self.error_callback = error_callback
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.future: Optional[Future] = None
    
    def execute(self):
        """执行任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()
        
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
            if self.callback:
                self.callback(self.result)
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            if self.error_callback:
                self.error_callback(e)
        finally:
            self.end_time = time.time()
    
    def cancel(self):
        """取消任务"""
        if self.future and not self.future.done():
            self.future.cancel()
            self.status = TaskStatus.CANCELLED


class ThreadManager:
    """统一线程管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logging.getLogger(__name__)
            
            # 使用线程池管理器
            self.thread_pool_manager = get_thread_pool_manager()
            
            # 任务管理
            self.task_queue = queue.PriorityQueue()
            self.running_tasks: Dict[str, ThreadTask] = {}
            self.completed_tasks: Dict[str, ThreadTask] = {}
            self.task_lock = threading.Lock()
            
            # 监控统计
            self.stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'cancelled_tasks': 0,
                'active_threads': 0
            }
            
            self.logger.info("线程管理器初始化完成，使用统一线程池管理")
    
    def submit_task(self, 
                    task_id: str,
                    func: Callable,
                    args: tuple = (),
                    kwargs: Dict[str, Any] = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    callback: Optional[Callable] = None,
                    error_callback: Optional[Callable] = None,
                    pool_type: PoolType = PoolType.DEFAULT) -> str:
        """
        提交任务到线程池
        
        Args:
            task_id: 任务ID
            func: 要执行的函数
            args: 函数参数
            kwargs: 函数关键字参数
            priority: 任务优先级
            callback: 成功回调函数
            error_callback: 错误回调函数
            pool_type: 线程池类型
            
        Returns:
            任务ID
        """
        task = ThreadTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            callback=callback,
            error_callback=error_callback
        )
        
        with self.task_lock:
            self.running_tasks[task_id] = task
            self.stats['total_tasks'] += 1
        
        # 使用线程池管理器提交任务
        def task_wrapper():
            return self._execute_task_wrapper(task)
        
        future = self.thread_pool_manager.submit_task(
            task_wrapper, 
            pool_type=pool_type,
            priority=priority
        )
        task.future = future
        
        self.logger.info(f"任务提交成功: {task_id}, 优先级: {priority}, 线程池: {pool_type}")
        return task_id
    
    def _execute_task_wrapper(self, task: ThreadTask):
        """任务执行包装器"""
        try:
            task.execute()
        except Exception as e:
            self.logger.error(f"任务执行异常 {task.task_id}: {e}")
        finally:
            self._on_task_complete(task)
    
    def _on_task_complete(self, task: ThreadTask):
        """任务完成处理"""
        with self.task_lock:
            # 从运行中任务移除
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            # 添加到已完成任务
            self.completed_tasks[task.task_id] = task
            
            # 更新统计
            if task.status == TaskStatus.COMPLETED:
                self.stats['completed_tasks'] += 1
            elif task.status == TaskStatus.FAILED:
                self.stats['failed_tasks'] += 1
            elif task.status == TaskStatus.CANCELLED:
                self.stats['cancelled_tasks'] += 1
    
    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        with self.task_lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.cancel()
                self.logger.info(f"任务取消成功: {task_id}")
                return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        with self.task_lock:
            if task_id in self.running_tasks:
                return self.running_tasks[task_id].status
            elif task_id in self.completed_tasks:
                return self.completed_tasks[task_id].status
        return None
    
    def get_task_result(self, task_id: str) -> Any:
        """获取任务结果"""
        with self.task_lock:
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
                elif task.status == TaskStatus.FAILED:
                    raise Exception(f"任务执行失败: {task.error}")
        return None
    
    def wait_for_task(self, task_id: str, timeout: float = None) -> bool:
        """等待任务完成"""
        with self.task_lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                if task.future:
                    try:
                        task.future.result(timeout=timeout)
                        return True
                    except Exception:
                        return False
        return True  # 如果任务不存在或已完成，返回True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取线程池统计信息"""
        with self.task_lock:
            stats = self.stats.copy()
            stats['active_threads'] = len(self.running_tasks)
            
            # 获取线程池管理器的统计信息
            pool_stats = self.thread_pool_manager.get_pool_stats()
            stats['thread_pools'] = pool_stats
            
            # 计算平均执行时间
            total_time = 0
            completed_count = 0
            for task in self.completed_tasks.values():
                if task.status == TaskStatus.COMPLETED and task.start_time and task.end_time:
                    total_time += (task.end_time - task.start_time)
                    completed_count += 1
            
            stats['avg_execution_time'] = total_time / completed_count if completed_count > 0 else 0
            
            return stats
    
    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.thread_pool_manager.shutdown(wait=wait)
        self.logger.info("线程池管理器已关闭")
    
    def reconfigure(self, pool_type: PoolType = None, max_workers: int = None):
        """重新配置线程池"""
        # 注意：线程池管理器支持动态调整，这里主要提供接口兼容性
        self.logger.info("线程池管理器支持动态调整，无需手动重新配置")


# 全局线程管理器实例
_thread_manager = None


def get_thread_manager() -> ThreadManager:
    """获取全局线程管理器实例"""
    global _thread_manager
    if _thread_manager is None:
        _thread_manager = ThreadManager()
    return _thread_manager


def submit_task(task_id: str, 
                func: Callable,
                args: tuple = (),
                kwargs: Dict[str, Any] = None,
                priority: TaskPriority = TaskPriority.NORMAL,
                callback: Optional[Callable] = None,
                error_callback: Optional[Callable] = None,
                pool_type: PoolType = PoolType.DEFAULT) -> str:
    """
    便捷函数：提交任务到全局线程管理器
    """
    return get_thread_manager().submit_task(
        task_id, func, args, kwargs, priority, callback, error_callback, pool_type
    )


def cancel_task(task_id: str) -> bool:
    """便捷函数：取消任务"""
    return get_thread_manager().cancel_task(task_id)


def wait_for_task(task_id: str, timeout: float = None) -> bool:
    """便捷函数：等待任务完成"""
    return get_thread_manager().wait_for_task(task_id, timeout)


def get_task_status(task_id: str) -> Optional[TaskStatus]:
    """便捷函数：获取任务状态"""
    return get_thread_manager().get_task_status(task_id)


def get_statistics() -> Dict[str, Any]:
    """便捷函数：获取统计信息"""
    return get_thread_manager().get_statistics()