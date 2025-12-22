"""
线程相关类型定义模块
用于避免循环导入问题
"""

from enum import Enum


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PoolType(Enum):
    """线程池类型枚举"""
    CPU_INTENSIVE = "cpu_intensive"  # CPU密集型任务
    IO_INTENSIVE = "io_intensive"   # IO密集型任务
    NETWORK_INTENSIVE = "network_intensive"  # 网络密集型任务
    DEFAULT = "default"  # 默认线程池