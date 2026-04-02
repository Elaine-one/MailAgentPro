#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路径管理模块
统一管理应用程序中所有文件和目录路径
"""

import os
from pathlib import Path
from typing import Optional
import logging


class PathManager:
    """
    统一路径管理器
    
    使用单例模式确保全局只有一个实例
    所有路径使用 pathlib.Path 进行管理，提供跨平台兼容性
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化路径管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # 初始化所有路径
        self._init_paths()
        
        # 确保所有必需的目录存在
        self.ensure_dirs()
        
        self.logger.info("路径管理器初始化完成")
    
    def _init_paths(self):
        """初始化所有路径定义"""
        # 应用根目录 (app/)
        self.app_dir = Path(__file__).parent.parent
        
        # 核心目录
        self.core_dir = self.app_dir / 'core'
        self.db_dir = self.app_dir / 'db'
        self.ui_dir = self.app_dir / 'ui'
        
        # 数据目录 (app/data/)
        self.data_dir = self.app_dir / 'data'
        
        # 日志目录 (app/logs/)
        self.logs_dir = self.app_dir / 'logs'
        
        # 备份目录 (app/backups/)
        self.backups_dir = self.app_dir / 'backups'
        
        # 导出目录 (app/exports/)
        self.exports_dir = self.app_dir / 'exports'
        
        # 数据文件路径
        self.db_file = self.data_dir / 'mail_sender.db'
        self.config_file = self.data_dir / 'config.json'
        self.templates_file = self.data_dir / 'templates.json'
        self.encryption_key_file = self.data_dir / 'encryption.key'
        
        # 日志文件路径
        self.llm_errors_log = self.logs_dir / 'llm_errors.log'
        self.app_log = self.logs_dir / 'app.log'
        
        # 旧版本数据文件路径（用于迁移）
        self.legacy_db_file = self.app_dir / 'mail_sender.db'
        self.legacy_config_file = self.app_dir / 'config.json'
        self.legacy_templates_file = self.app_dir / 'templates.json'
        self.legacy_encryption_key_file = self.app_dir / 'data' / 'encryption.key'
    
    def ensure_dirs(self):
        """确保所有必需的目录存在"""
        dirs_to_create = [
            self.data_dir,
            self.logs_dir,
            self.backups_dir,
            self.exports_dir
        ]
        
        for dir_path in dirs_to_create:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"目录已确认: {dir_path}")
            except Exception as e:
                self.logger.error(f"创建目录失败 {dir_path}: {e}")
                raise
    
    def get_db_path(self) -> Path:
        """
        获取数据库文件路径
        
        Returns:
            Path: 数据库文件路径
        """
        # 如果新位置存在，使用新位置
        if self.db_file.exists():
            return self.db_file
        
        # 如果旧位置存在，返回旧位置（兼容性）
        if self.legacy_db_file.exists():
            self.logger.warning(f"使用旧版本数据库路径: {self.legacy_db_file}")
            return self.legacy_db_file
        
        # 默认返回新位置
        return self.db_file
    
    def get_config_path(self) -> Path:
        """
        获取配置文件路径
        
        Returns:
            Path: 配置文件路径
        """
        # 如果新位置存在，使用新位置
        if self.config_file.exists():
            return self.config_file
        
        # 如果旧位置存在，返回旧位置（兼容性）
        if self.legacy_config_file.exists():
            self.logger.warning(f"使用旧版本配置文件路径: {self.legacy_config_file}")
            return self.legacy_config_file
        
        # 默认返回新位置
        return self.config_file
    
    def get_templates_path(self) -> Path:
        """
        获取模板文件路径
        
        Returns:
            Path: 模板文件路径
        """
        # 如果新位置存在，使用新位置
        if self.templates_file.exists():
            return self.templates_file
        
        # 如果旧位置存在，返回旧位置（兼容性）
        if self.legacy_templates_file.exists():
            self.logger.warning(f"使用旧版本模板文件路径: {self.legacy_templates_file}")
            return self.legacy_templates_file
        
        # 默认返回新位置
        return self.templates_file
    
    def get_encryption_key_path(self) -> Path:
        """
        获取加密密钥文件路径
        
        Returns:
            Path: 加密密钥文件路径
        """
        # 加密密钥已经在正确的位置
        if self.encryption_key_file.exists():
            return self.encryption_key_file
        
        # 返回默认位置
        return self.encryption_key_file
    
    def get_log_path(self, log_name: str) -> Path:
        """
        获取日志文件路径
        
        Args:
            log_name: 日志文件名称
            
        Returns:
            Path: 日志文件路径
        """
        return self.logs_dir / log_name
    
    def get_backup_path(self, backup_name: str) -> Path:
        """
        获取备份文件路径
        
        Args:
            backup_name: 备份文件名称
            
        Returns:
            Path: 备份文件路径
        """
        return self.backups_dir / backup_name
    
    def get_export_path(self, export_name: str) -> Path:
        """
        获取导出文件路径
        
        Args:
            export_name: 导出文件名称
            
        Returns:
            Path: 导出文件路径
        """
        return self.exports_dir / export_name
    
    def needs_migration(self) -> bool:
        """
        检查是否需要数据迁移
        
        Returns:
            bool: 是否需要迁移
        """
        # 检查旧版本文件是否存在且新版本文件不存在
        legacy_files = [
            (self.legacy_db_file, self.db_file),
            (self.legacy_config_file, self.config_file),
            (self.legacy_templates_file, self.templates_file)
        ]
        
        for legacy_path, new_path in legacy_files:
            if legacy_path.exists() and not new_path.exists():
                return True
        
        return False
    
    def get_migration_info(self) -> dict:
        """
        获取迁移信息
        
        Returns:
            dict: 迁移信息字典
        """
        files_to_migrate = []
        
        migration_pairs = [
            ('database', self.legacy_db_file, self.db_file),
            ('config', self.legacy_config_file, self.config_file),
            ('templates', self.legacy_templates_file, self.templates_file)
        ]
        
        for file_type, legacy_path, new_path in migration_pairs:
            if legacy_path.exists() and not new_path.exists():
                files_to_migrate.append({
                    'type': file_type,
                    'from': str(legacy_path),
                    'to': str(new_path),
                    'size': legacy_path.stat().st_size if legacy_path.exists() else 0
                })
        
        return {
            'needs_migration': len(files_to_migrate) > 0,
            'files': files_to_migrate
        }
    
    def __repr__(self):
        """字符串表示"""
        return f"PathManager(app_dir={self.app_dir}, data_dir={self.data_dir})"


# 全局路径管理器实例
path_manager = PathManager()


def get_path_manager() -> PathManager:
    """
    获取全局路径管理器实例
    
    Returns:
        PathManager: 路径管理器实例
    """
    return path_manager
