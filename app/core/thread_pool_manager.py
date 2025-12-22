"""
线程池管理模块
提供统一的线程池管理机制，支持动态调整线程池大小和任务调度
修复死锁和性能问题
"""

import threading
import queue
import time
import logging
import weakref
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager

from .thread_types import TaskPriority, PoolType


class ThreadPoolManager:
    """线程池管理器"""
    
    _instance = None
    _lock = threading.Lock()
    _instance_ref = None  # 使用弱引用避免循环引用
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance_ref = weakref.ref(cls._instance)
            return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._initialized = True
        self._pools: Dict[PoolType, ThreadPoolExecutor] = {}
        self._pool_configs: Dict[PoolType, Dict] = {}
        self._task_queues: Dict[PoolType, queue.PriorityQueue] = {}
        self._pool_stats: Dict[PoolType, Dict] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._resize_lock = threading.RLock()  # 使用可重入锁防止死锁
        self._submit_lock = threading.RLock()  # 提交任务的锁
        
        self._setup_pools()
        self._start_monitor()
        
        logging.info("ThreadPoolManager initialized successfully")
    
    def _setup_pools(self):
        """初始化各种类型的线程池"""
        # CPU密集型任务 - 线程数等于CPU核心数
        cpu_count = max(1, min(4, threading.active_count()))  # 限制最大线程数
        self._pools[PoolType.CPU_INTENSIVE] = ThreadPoolExecutor(
            max_workers=cpu_count,
            thread_name_prefix="cpu_pool"
        )
        
        # IO密集型任务 - 线程数较多
        io_workers = max(5, min(20, cpu_count * 4))
        self._pools[PoolType.IO_INTENSIVE] = ThreadPoolExecutor(
            max_workers=io_workers,
            thread_name_prefix="io_pool"
        )
        
        # 网络密集型任务 - 中等线程数
        network_workers = max(3, min(10, cpu_count * 2))
        self._pools[PoolType.NETWORK_INTENSIVE] = ThreadPoolExecutor(
            max_workers=network_workers,
            thread_name_prefix="network_pool"
        )
        
        # 默认线程池
        self._pools[PoolType.DEFAULT] = ThreadPoolExecutor(
            max_workers=max(2, min(8, cpu_count)),
            thread_name_prefix="default_pool"
        )
        
        # 配置信息
        for pool_type in PoolType:
            self._pool_configs[pool_type] = {
                'max_workers': self._pools[pool_type]._max_workers,
                'created_time': time.time(),
                'active_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0
            }
            self._task_queues[pool_type] = queue.PriorityQueue()
            self._pool_stats[pool_type] = {
                'active_threads': 0,
                'queue_size': 0,
                'avg_task_time': 0.0,
                'last_update': time.time()
            }
    
    def _start_monitor(self):
        """启动监控线程"""
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="pool_monitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._update_pool_stats()
                self._adjust_pool_sizes()
                time.sleep(5)  # 每5秒更新一次
            except Exception as e:
                logging.error(f"Pool monitor error: {e}")
                time.sleep(10)
    
    def _update_pool_stats(self):
        """更新线程池统计信息"""
        for pool_type, pool in self._pools.items():
            stats = self._pool_stats[pool_type]
            config = self._pool_configs[pool_type]
            
            # 更新活跃线程数 - 使用len获取线程数量
            stats['active_threads'] = len(pool._threads)
            
            # 更新队列大小
            stats['queue_size'] = self._task_queues[pool_type].qsize()
            
            # 更新平均任务时间
            if config['completed_tasks'] > 0:
                total_time = time.time() - config['created_time']
                stats['avg_task_time'] = total_time / config['completed_tasks']
            
            stats['last_update'] = time.time()
    
    def _adjust_pool_sizes(self):
        """动态调整线程池大小"""
        for pool_type, pool in self._pools.items():
            stats = self._pool_stats[pool_type]
            config = self._pool_configs[pool_type]
            
            current_workers = pool._max_workers
            queue_size = stats['queue_size']
            active_threads = stats['active_threads']
            
            # 根据队列大小和活跃线程数调整线程池大小
            if queue_size > 10 and active_threads == current_workers:
                # 队列积压严重，增加线程数
                new_size = min(current_workers + 2, 50)  # 最大50个线程
                if new_size > current_workers:
                    self._resize_pool(pool_type, new_size)
            elif queue_size == 0 and active_threads < current_workers // 2:
                # 队列空闲，减少线程数
                new_size = max(current_workers - 1, 1)  # 最少1个线程
                if new_size < current_workers:
                    self._resize_pool(pool_type, new_size)
    
    def _resize_pool(self, pool_type: PoolType, new_size: int):
        """安全地调整线程池大小，避免死锁"""
        with self._resize_lock:
            try:
                old_pool = self._pools[pool_type]
                old_size = old_pool._max_workers
                
                # 如果大小相同，直接返回
                if old_size == new_size:
                    return
                
                # 使用单独的线程来关闭旧线程池，避免阻塞
                def close_old_pool():
                    try:
                        # 不等待线程完成，只设置退出标志
                        old_pool.shutdown(wait=False)
                    except Exception as e:
                        logging.warning(f"Error closing old pool: {e}")
                
                # 创建新线程异步关闭旧池
                close_thread = threading.Thread(
                    target=close_old_pool,
                    name=f"close_{pool_type.value}_pool",
                    daemon=True
                )
                
                # 创建新的线程池
                new_pool = ThreadPoolExecutor(
                    max_workers=new_size,
                    thread_name_prefix=f"{pool_type.value}_pool",
                    thread_factory=self._create_daemon_thread
                )
                
                # 原子性替换
                self._pools[pool_type] = new_pool
                self._pool_configs[pool_type]['max_workers'] = new_size
                
                # 启动关闭线程（不等待）
                close_thread.start()
                
                # 记录统计信息
                self._pool_configs[pool_type]['resized_at'] = time.time()
                self._pool_configs[pool_type]['resized_from'] = old_size
                
                logging.info(f"Resized {pool_type.value} pool from {old_size} to {new_size} workers (async close)")
                
            except Exception as e:
                logging.error(f"Failed to resize {pool_type.value} pool: {e}")
                # 如果resize失败，尝试恢复状态
                self._recover_pool_state(pool_type)
    
    def _recover_pool_state(self, pool_type: PoolType):
        """恢复线程池状态"""
        try:
            # 尝试重新创建线程池为默认大小
            default_size = 4  # 默认线程数
            if pool_type == PoolType.CPU_INTENSIVE:
                default_size = min(4, threading.active_count())
            elif pool_type == PoolType.IO_INTENSIVE:
                default_size = min(20, threading.active_count() * 4)
            elif pool_type == PoolType.NETWORK_INTENSIVE:
                default_size = min(10, threading.active_count() * 2)
            
            self._pools[pool_type] = ThreadPoolExecutor(
                max_workers=default_size,
                thread_name_prefix=f"{pool_type.value}_recovery_pool"
            )
            self._pool_configs[pool_type]['max_workers'] = default_size
            
            logging.info(f"Recovered {pool_type.value} pool to default size: {default_size}")
        except Exception as e:
            logging.error(f"Failed to recover {pool_type.value} pool: {e}")
    
    def _create_daemon_thread(self, target, name):
        """创建守护线程，避免线程泄露"""
        import threading
        thread = threading.Thread(target=target, name=name)
        thread.daemon = True
        return thread
    
    @contextmanager
    def _safe_pool_access(self, pool_type: PoolType):
        """安全访问线程池的上下文管理器"""
        with self._submit_lock:
            if pool_type not in self._pools:
                raise ValueError(f"Unknown pool type: {pool_type}")
            
            pool = self._pools[pool_type]
            config = self._pool_configs[pool_type]
            
            try:
                yield pool, config
            except Exception as e:
                logging.error(f"Error accessing {pool_type.value} pool: {e}")
                raise
    
    def submit_task(self, 
                   func: Callable, 
                   args: tuple = (), 
                   kwargs: Dict = None,
                   pool_type: PoolType = PoolType.DEFAULT,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: Optional[float] = None) -> Future:
        """安全地提交任务到线程池"""
        if kwargs is None:
            kwargs = {}
        
        with self._safe_pool_access(pool_type) as (pool, config):
            try:
                # 包装任务以跟踪统计信息，避免竞争条件
                def wrapped_task():
                    start_time = time.time()
                    
                    # 线程安全地更新活跃任务数
                    with self._submit_lock:
                        config['active_tasks'] += 1
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        # 线程安全地更新统计信息
                        with self._submit_lock:
                            config['completed_tasks'] += 1
                            
                        return result
                    except Exception as e:
                        # 线程安全地更新失败统计
                        with self._submit_lock:
                            config['failed_tasks'] += 1
                        logging.error(f"Task execution failed: {e}")
                        raise
                    finally:
                        # 线程安全地减少活跃任务数
                        with self._submit_lock:
                            config['active_tasks'] -= 1
                            # 更新平均任务时间
                            task_time = time.time() - start_time
                            if 'total_task_time' not in config:
                                config['total_task_time'] = 0.0
                            config['total_task_time'] += task_time
                            config['avg_task_time'] = config['total_task_time'] / max(1, config['completed_tasks'])
                    
                # 提交到线程池，带超时保护
                if timeout:
                    future = pool.submit(wrapped_task)
                    # 简化的超时处理，实际项目中可能需要更复杂的超时机制
                    return future
                else:
                    return pool.submit(wrapped_task)
                
            except Exception as e:
                logging.error(f"Failed to submit task to {pool_type.value} pool: {e}")
                raise
    
    def submit_batch_tasks(self, 
                          tasks: List[tuple], 
                          pool_type: PoolType = PoolType.DEFAULT,
                          timeout: Optional[float] = None) -> List[Future]:
        """批量提交任务，改进版"""
        futures = []
        
        with self._safe_pool_access(pool_type) as (pool, config):
            for task_data in tasks:
                if isinstance(task_data, tuple) and len(task_data) >= 2:
                    func, args = task_data[0], task_data[1] if len(task_data) > 1 else ()
                    kwargs = task_data[2] if len(task_data) > 2 else {}
                    
                    try:
                        future = self.submit_task(func, args, kwargs, pool_type, timeout=timeout)
                        futures.append(future)
                    except Exception as e:
                        logging.error(f"Failed to submit batch task: {e}")
                        # 继续提交其他任务
                        continue
        
        return futures
    
    def get_pool_stats(self, pool_type: PoolType = None) -> Dict:
        """线程安全地获取线程池统计信息"""
        stats = {}
        
        with self._submit_lock:  # 确保线程安全访问
            if pool_type:
                if pool_type in self._pool_stats:
                    pool_stats = self._pool_stats[pool_type].copy()
                    config = self._pool_configs[pool_type]
                    
                    # 添加实时统计信息，线程安全地读取
                    pool_stats.update({
                        'max_workers': config['max_workers'],
                        'active_tasks': config.get('active_tasks', 0),
                        'completed_tasks': config.get('completed_tasks', 0),
                        'failed_tasks': config.get('failed_tasks', 0),
                        'avg_task_time': config.get('avg_task_time', 0.0),
                        'total_tasks': config.get('completed_tasks', 0) + config.get('failed_tasks', 0)
                    })
                    
                    stats[pool_type] = pool_stats
            else:
                for p_type in self._pool_stats:
                    pool_stats = self._pool_stats[p_type].copy()
                    config = self._pool_configs[p_type]
                    
                    pool_stats.update({
                        'max_workers': config['max_workers'],
                        'active_tasks': config.get('active_tasks', 0),
                        'completed_tasks': config.get('completed_tasks', 0),
                        'failed_tasks': config.get('failed_tasks', 0),
                        'avg_task_time': config.get('avg_task_time', 0.0),
                        'total_tasks': config.get('completed_tasks', 0) + config.get('failed_tasks', 0)
                    })
                    
                    stats[p_type] = pool_stats
        
        return stats
    
    def get_pool_config(self, pool_type: PoolType = None) -> Dict:
        """获取线程池配置信息"""
        if pool_type:
            return self._pool_configs[pool_type].copy()
        else:
            return {pt: self._pool_configs[pt].copy() for pt in PoolType}
    
    def shutdown(self, wait: bool = True):
        """关闭所有线程池"""
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        
        for pool_type, pool in self._pools.items():
            try:
                pool.shutdown(wait=wait)
                logging.info(f"Shutdown {pool_type.value} pool")
            except Exception as e:
                logging.error(f"Error shutting down {pool_type.value} pool: {e}")
    
    def __del__(self):
        """析构函数"""
        self.shutdown(wait=False)


def get_thread_pool_manager() -> ThreadPoolManager:
    """获取线程池管理器实例"""
    return ThreadPoolManager()


def submit_to_pool(func: Callable, 
                  args: tuple = (), 
                  kwargs: Dict = None,
                  pool_type: PoolType = PoolType.DEFAULT) -> Future:
    """便捷函数：提交任务到线程池"""
    manager = get_thread_pool_manager()
    return manager.submit_task(func, args, kwargs, pool_type)


def get_pool_statistics(pool_type: PoolType = None) -> Dict:
    """获取线程池统计信息"""
    manager = get_thread_pool_manager()
    return manager.get_pool_stats(pool_type)