#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块
负责应用程序配置的读取、写入和管理
"""

import json
import os
from typing import Dict, Any, Optional
from core.path_manager import get_path_manager

class ConfigManager:
    """配置管理器类"""
    
    _instance = None
    _config = None
    _config_file = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if ConfigManager._config is None:
            # 使用路径管理器获取配置文件路径
            path_manager = get_path_manager()
            ConfigManager._config_file = str(path_manager.get_config_path())
            ConfigManager._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        # 默认配置
        default_config = {
            "sender_name": "",
            "sender_email": "",
            "smtp_server": "",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "ai_config": {
                "provider": "OpenAI",
                "model": "gpt-3.5-turbo",
                "primary_key": "",
                "secondary_key": "",
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "send_interval": 1,
            "send_threads": 3,
            "send_retry_count": 1
        }
        
        # 如果配置文件存在，加载它
        if os.path.exists(ConfigManager._config_file):
            try:
                with open(ConfigManager._config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置，确保所有必需的键都存在
                    return {**default_config, **loaded_config}
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载配置文件失败: {e}")
                return default_config
        else:
            # 创建默认配置文件
            self.save_config(default_config)
            return default_config
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取当前配置"""
        if cls._instance is None:
            cls()
        return cls._config.copy()
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        if cls._instance is None:
            cls()
        
        try:
            # 更新内存中的配置
            cls._config = config.copy()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(cls._config_file), exist_ok=True)
            
            # 写入文件
            with open(cls._config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except (IOError, json.JSONEncodeError) as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    @classmethod
    def update_config(cls, updates: Dict[str, Any]) -> bool:
        """更新部分配置"""
        if cls._instance is None:
            cls()
        
        # 获取当前配置
        current_config = cls._config.copy()
        
        # 递归更新配置
        def update_dict(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    update_dict(d[k], v)
                else:
                    d[k] = v
        
        update_dict(current_config, updates)
        
        # 保存更新后的配置
        return cls.save_config(current_config)
    
    @classmethod
    def reset_config(cls) -> bool:
        """重置为默认配置"""
        if cls._instance is None:
            cls()
        
        # 默认配置
        default_config = {
            "sender_name": "",
            "sender_email": "",
            "smtp_server": "",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "ai_config": {
                "provider": "OpenAI",
                "model": "gpt-3.5-turbo",
                "primary_key": "",
                "secondary_key": "",
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "send_interval": 1,
            "send_threads": 3,
            "send_retry_count": 1
        }
        
        return cls.save_config(default_config)
    
    @classmethod
    def get_config_file_path(cls) -> Optional[str]:
        """获取配置文件路径"""
        if cls._instance is None:
            cls()
        return cls._config_file
    
    @classmethod
    def get_ai_config(cls) -> Dict[str, Any]:
        """获取AI配置"""
        if cls._instance is None:
            cls()
        config = cls._config.copy()
        return config.get('ai_config', {})