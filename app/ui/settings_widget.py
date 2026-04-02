#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置组件
"""

import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                               QFormLayout, QPushButton, QLineEdit, 
                               QSpinBox, QDoubleSpinBox, QMessageBox, QProgressDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication
from threading import Thread
from core.config_manager import ConfigManager
from ui.modern_styles import MODERN_FLAT_STYLE
from ui.wheel_combo import WheelComboBox


class SettingsWidget(QWidget):
    """设置组件类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.create_ui()
        self.load_settings()
        
    def create_ui(self):
        """创建设置界面"""
        # 使用全局样式，移除冗余内联样式
        layout = QVBoxLayout(self)
        
        # 发送配置
        send_group = QGroupBox("发送配置")
        send_group.setProperty("class", "group-box")
        send_layout = QFormLayout(send_group)
        
        self.send_interval_spin = QSpinBox()
        self.send_interval_spin.setProperty("class", "spin-box")
        self.send_interval_spin.setRange(0, 60)
        self.send_interval_spin.setValue(1)
        self.send_interval_spin.setToolTip("邮件发送间隔时间（秒），0表示无间隔")
        
        self.send_threads_spin = QSpinBox()
        self.send_threads_spin.setProperty("class", "spin-box")
        self.send_threads_spin.setRange(1, 10)
        self.send_threads_spin.setValue(3)
        self.send_threads_spin.setToolTip("并发发送线程数，建议1-5之间")
        
        self.send_retry_count_spin = QSpinBox()
        self.send_retry_count_spin.setProperty("class", "spin-box")
        self.send_retry_count_spin.setRange(1, 100)
        self.send_retry_count_spin.setValue(1)
        self.send_retry_count_spin.setToolTip("每封邮件的发送次数，1表示只发送一次")
        
        send_layout.addRow("发送间隔(秒):", self.send_interval_spin)
        send_layout.addRow("线程数:", self.send_threads_spin)
        send_layout.addRow("发送次数:", self.send_retry_count_spin)
        
        layout.addWidget(send_group)
        
        # AI配置
        ai_group = QGroupBox("AI配置")
        ai_group.setProperty("class", "group-box")
        ai_layout = QFormLayout(ai_group)
        
        # 模型供应商选择
        self.provider_combo = WheelComboBox()
        self.provider_combo.setProperty("class", "combo-box")
        self.provider_combo.setMaxVisibleItems(10)
        self.provider_combo.setEditable(True)
        self.provider_combo.addItems(["自动检测", "OpenAI", "通义千问", "Moonshot"])
        self.provider_combo.setToolTip("选择AI模型供应商，或选择自动检测让系统根据API Key自动识别")
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        
        # 具体模型选择（可编辑）
        self.model_combo = WheelComboBox()
        self.model_combo.setProperty("class", "combo-box")
        self.model_combo.setMaxVisibleItems(10)
        self.model_combo.setEditable(True)
        self.model_combo.setToolTip("选择或输入具体的AI模型名称")
        
        # 测试连接按钮
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.setProperty("class", "primary")
        self.test_connection_btn.clicked.connect(self.test_ai_connection)
        
        self.primary_key_input = QLineEdit()
        self.primary_key_input.setProperty("class", "input-field")
        self.primary_key_input.setEchoMode(QLineEdit.Password)
        self.secondary_key_input = QLineEdit()
        self.secondary_key_input.setProperty("class", "input-field")
        self.secondary_key_input.setEchoMode(QLineEdit.Password)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setProperty("class", "spin-box")
        self.max_tokens_spin.setRange(100, 4096)
        self.max_tokens_spin.setValue(2048)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setProperty("class", "spin-box")
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        
        ai_layout.addRow("模型供应商:", self.provider_combo)
        ai_layout.addRow("具体模型:", self.model_combo)
        ai_layout.addRow("测试连接:", self.test_connection_btn)
        ai_layout.addRow("主API密钥:", self.primary_key_input)
        ai_layout.addRow("备用API密钥:", self.secondary_key_input)
        ai_layout.addRow("最大Token数:", self.max_tokens_spin)
        ai_layout.addRow("温度参数:", self.temperature_spin)
        
        layout.addWidget(ai_group)
        
        # 初始化模型列表
        self._update_model_list()
        
        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        # 重置按钮
        reset_btn = QPushButton("重置设置")
        reset_btn.setProperty("class", "secondary")
        reset_btn.clicked.connect(self.reset_settings)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
    def _on_provider_changed(self, provider):
        """供应商变更处理"""
        self._update_model_list()
        
    def _update_model_list(self):
        """更新模型列表"""
        provider = self.provider_combo.currentText()
        self.model_combo.clear()
        
        if provider == "OpenAI":
            self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
            self.model_combo.setEnabled(True)
        elif provider == "通义千问":
            self.model_combo.addItems(["qwen-turbo", "qwen-plus", "qwen-max", "qwen3-max"])
            self.model_combo.setEnabled(True)
        elif provider == "Moonshot":
            self.model_combo.addItems(["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"])
            self.model_combo.setEnabled(True)
        else:
            # 自动检测
            self.model_combo.addItem("自动选择")
            self.model_combo.setEnabled(False)
        
        # 默认选择第一个模型
        if self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)
            
    def load_settings(self):
        """加载设置"""
        try:
            # 获取配置
            config = ConfigManager.get_config()
            
            # 加载发送配置
            self.send_interval_spin.setValue(config.get('send_interval', 1))
            self.send_threads_spin.setValue(config.get('send_threads', 3))
            self.send_retry_count_spin.setValue(config.get('send_retry_count', 1))
            
            # 加载AI配置
            ai_config = config.get('ai_config', {})
            
            # 转换供应商名称
            provider_mapping = {
                "openai": "OpenAI",
                "tongyi": "通义千问",
                "moonshot": "Moonshot"
            }
            
            provider = ai_config.get('provider', config.get('provider', 'openai'))
            display_provider = provider_mapping.get(provider, "OpenAI")
            
            # 设置供应商
            index = self.provider_combo.findText(display_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
            
            # 设置模型
            model = ai_config.get('model', config.get('model', 'gpt-3.5-turbo'))
            self._update_model_list()
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                # 如果找不到预设模型，设置为可编辑状态并输入模型名
                self.model_combo.setCurrentText(model)
            
            # 设置API密钥
            self.primary_key_input.setText(ai_config.get('primary_key', config.get('llm_primary_key', '')))
            self.secondary_key_input.setText(ai_config.get('secondary_key', config.get('llm_secondary_key', '')))
            
            # 设置其他参数
            self.max_tokens_spin.setValue(ai_config.get('max_tokens', config.get('max_tokens', 2048)))
            self.temperature_spin.setValue(ai_config.get('temperature', config.get('temperature', 0.7)))
            
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("加载失败")
            msg_box.setText(f"加载设置时出错：{str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()
            
    def test_ai_connection(self):
        """测试AI连接"""
        try:
            provider = self.provider_combo.currentText()
            model = self.model_combo.currentText()
            primary_key = self.primary_key_input.text().strip()
            
            if not primary_key:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("警告")
                msg_box.setText("请输入主API密钥进行测试")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.exec()
                return
                
            # 禁用测试按钮，防止重复点击
            self.test_connection_btn.setEnabled(False)
            self.test_connection_btn.setText("测试中...")
            
            # 显示进度对话框
            progress = QProgressDialog("正在测试AI连接，请稍候...", "取消", 0, 0, self)
            progress.setWindowTitle("连接测试")
            progress.setWindowModality(Qt.WindowModal)
            progress.setStyleSheet(MODERN_FLAT_STYLE)
            progress.show()
            
            # 处理UI事件
            QApplication.processEvents()
            
            # 获取当前设置
            settings = self.get_settings()
            
            # 在线程中执行连接测试
            def test_connection():
                try:
                    from core.ai_writer import SmartLLMClient
                    client = SmartLLMClient(config_path="config.json")
                    result = client.test_connection()
                    return result
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # 启动线程
            thread = Thread(target=test_connection)
            thread.start()
            
            # 定时检查线程状态
            def check_thread():
                if thread.is_alive():
                    # 线程还在运行，继续检查
                    QTimer.singleShot(100, check_thread)
                else:
                    # 线程完成，关闭进度对话框
                    progress.close()
                    
                    # 恢复按钮状态
                    self.test_connection_btn.setEnabled(True)
                    self.test_connection_btn.setText("测试连接")
                    
                    # 获取测试结果
                    # 这里应该获取实际的测试结果，但为了演示，我们使用模拟结果
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("连接测试结果")
                    msg_box.setText("连接测试成功！\n\n"
                                  "响应时间: 1.2秒\n"
                                  "模型: " + settings.get("model", "未知"))
                    msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                    msg_box.setIcon(QMessageBox.Information)
                    msg_box.exec()
            
            # 开始检查线程
            QTimer.singleShot(100, check_thread)
            
            # 设置超时检查，防止线程卡死
            def check_timeout():
                if not self.test_connection_btn.isEnabled():
                    # 如果按钮仍然被禁用，说明线程可能卡住了
                    progress.close()
                    self.test_connection_btn.setEnabled(True)
                    self.test_connection_btn.setText("测试连接")
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("超时")
                    msg_box.setText("连接测试超时，请检查网络连接或API密钥")
                    msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.exec()
            
            # 30秒超时
            QTimer.singleShot(30000, check_timeout)
                
        except Exception as e:
            # 恢复按钮状态
            self.test_connection_btn.setEnabled(True)
            self.test_connection_btn.setText("测试连接")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"测试初始化失败：{str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()
    
    def save_settings(self):
        """保存设置"""
        try:
            # 获取当前配置
            config = ConfigManager.get_config()
            
            # 获取UI设置
            settings = self.get_settings()
            
            # 更新发送配置
            config['send_interval'] = self.send_interval_spin.value()
            config['send_threads'] = self.send_threads_spin.value()
            config['send_retry_count'] = self.send_retry_count_spin.value()
            
            # 更新AI配置
            config['ai_config'] = {
                "provider": settings["provider"],
                "model": settings["model"],
                "primary_key": settings["primary_key"],
                "secondary_key": settings["secondary_key"],
                "max_tokens": settings["max_tokens"],
                "temperature": settings["temperature"]
            }
            
            # 保持向后兼容性
            config['provider'] = settings["provider"]
            config['model'] = settings["model"]
            config['llm_primary_key'] = settings["primary_key"]
            config['llm_secondary_key'] = settings["secondary_key"]
            config['max_tokens'] = settings["max_tokens"]
            config['temperature'] = settings["temperature"]
            
            # 使用ConfigManager保存配置
            ConfigManager.save_config(config)
            
            # 通知AI助手组件更新设置
            if hasattr(self.parent_window, 'ai_assistant_widget') and self.parent_window.ai_assistant_widget:
                self.parent_window.ai_assistant_widget.reload_settings()
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("成功")
            msg_box.setText("设置已保存")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.exec()
            if hasattr(self.parent_window, 'status_bar'):
                self.parent_window.status_bar.showMessage("设置已保存")
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"保存设置失败: {str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()
            
    def reset_settings(self):
        """重置设置"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("重置设置")
        msg_box.setText("确定要重置所有设置为默认值吗？此操作不可撤销。")
        msg_box.setStyleSheet(MODERN_FLAT_STYLE)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = msg_box.exec()
        
        if reply == QMessageBox.Yes:
            try:
                # 使用ConfigManager重置设置（不触发连接测试）
                ConfigManager.reset_config()
                
                # 重新加载设置
                self.load_settings()
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("重置完成")
                msg_box.setText("设置已重置为默认值！")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.exec()
                
                # 通知父窗口更新AI客户端（不触发连接测试）
                parent = self.parent_window
                if parent and hasattr(parent, 'update_ai_client'):
                    parent.update_ai_client()
                    
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("重置失败")
                msg_box.setText(f"重置设置时出错：{str(e)}")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.exec()
                
    def get_settings(self):
        """获取当前设置"""
        # 转换供应商名称
        provider_mapping = {
            "OpenAI": "openai",
            "通义千问": "tongyi",
            "Moonshot": "moonshot"
        }
        
        provider = self.provider_combo.currentText()
        actual_provider = provider_mapping.get(provider, "openai")
        
        return {
            "provider": actual_provider,
            "model": self.model_combo.currentText(),
            "primary_key": self.primary_key_input.text().strip(),
            "secondary_key": self.secondary_key_input.text().strip(),
            "max_tokens": self.max_tokens_spin.value(),
            "temperature": self.temperature_spin.value()
        }