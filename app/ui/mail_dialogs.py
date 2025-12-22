#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮件发送和AI助手对话框
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox, 
                               QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
                               QComboBox, QGroupBox, QProgressBar, QSpinBox,
                               QDoubleSpinBox, QCheckBox, QTabWidget, QSplitter, QHeaderView, QWidget)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication
from ui.modern_styles import MODERN_FLAT_STYLE
import os
import time
from core.mail_sender import MailSender
from core.ai_writer import SmartLLMClient


class SendProgressDialog(QDialog):
    """发送进度对话框"""
    
    # 定义信号用于线程安全的UI更新
    progress_updated = Signal(int, int, bool, str)  # current, total, success, recipient_email
    status_updated = Signal(str)  # status message
    finished = Signal()  # 发送完成信号
    
    def __init__(self, total_count=0, parent=None):
        super().__init__(parent)
        self.total_count = total_count
        
        # 初始化统计计数
        self._success_count = 0
        self._failed_count = 0
        self._is_finished = False
        self._timer = None
        
        self.init_ui()
        
        # 连接信号槽
        self.progress_updated.connect(self._update_progress_safe)
        self.status_updated.connect(self._update_status_safe)
        self.finished.connect(self._on_finished)
        
        # 设置对话框属性
        self.setModal(False)  # 设置为非模态对话框，避免阻塞UI
        self.setAttribute(Qt.WA_DeleteOnClose)  # 关闭时自动删除
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # 保持窗口在最前
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("发送进度")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # 进度信息
        self.status_label = QLabel("准备发送...")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setProperty("class", "progress-bar")
        layout.addWidget(self.progress_bar)
        
        # 统计信息
        self.stats_label = QLabel("总计: 0 | 成功: 0 | 失败: 0")
        layout.addWidget(self.stats_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.cancel_btn.clicked.connect(self.reject)
        
    def update_progress(self, current, total, success, recipient_email):
        """更新进度（线程安全版本）"""
        # 限制更新频率，避免UI线程过载
        import time
        current_time = time.time()
        if not hasattr(self, '_last_update_time') or current_time - self._last_update_time >= 0.1:  # 至少100ms更新一次
            self._last_update_time = current_time
            self.progress_updated.emit(current, total, success, recipient_email)
        
    def update_status(self, status):
        """更新状态（线程安全版本）"""
        self.status_updated.emit(status)
        
    def _update_progress_safe(self, current, total, success, recipient_email):
        """线程安全的进度更新实现"""
        if not self.isVisible():
            return
            
        # 根据success参数更新计数
        if success:
            self._success_count += 1
        else:
            self._failed_count += 1
            
        # 设置进度条
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        # 更新统计显示
        self.stats_label.setText(f"总计: {total} | 成功: {self._success_count} | 失败: {self._failed_count}")
        self.status_label.setText(f"正在发送给: {recipient_email}")
        
        # 如果完成，延迟关闭
        if current >= total and not self._is_finished:
            self._is_finished = True
            self.finished.emit()
        
    def _update_status_safe(self, status):
        """线程安全的状态更新实现"""
        if not self.isVisible():
            return
        self.status_label.setText(status)
    
    def _on_finished(self):
        """发送完成处理"""
        self.status_label.setText("发送完成！")
        # 显示完成按钮，让用户手动关闭对话框
        self.cancel_btn.setText("完成")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.disconnect()  # 断开原来的取消信号
        self.cancel_btn.clicked.connect(self.close)


class AISettingsDialog(QDialog):
    """AI设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_client = SmartLLMClient()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI设置")
        self.setFixedSize(500, 500)
        self.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(self)
        
        # 主要配置
        main_group = QGroupBox("主要配置")
        main_group.setProperty("class", "group-box")
        main_layout = QFormLayout(main_group)
        
        # 模型供应商选择
        self.provider_combo = QComboBox()
        self.provider_combo.setProperty("class", "combo-box")
        self.provider_combo.addItems(["自动检测", "OpenAI", "通义千问", "Moonshot"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        
        # 具体模型选择
        self.model_combo = QComboBox()
        self.model_combo.setProperty("class", "combo-box")
        self.model_combo.setToolTip("选择具体的AI模型")
        
        self.primary_key_input = QLineEdit()
        self.primary_key_input.setProperty("class", "input-field")
        self.primary_key_input.setEchoMode(QLineEdit.Password)
        self.primary_key_input.setToolTip("输入主API密钥")
        
        self.secondary_key_input = QLineEdit()
        self.secondary_key_input.setProperty("class", "input-field")
        self.secondary_key_input.setEchoMode(QLineEdit.Password)
        self.secondary_key_input.setToolTip("输入备用API密钥（可选）")
        
        main_layout.addRow("模型供应商:", self.provider_combo)
        main_layout.addRow("具体模型:", self.model_combo)
        main_layout.addRow("主API密钥:", self.primary_key_input)
        main_layout.addRow("备用API密钥:", self.secondary_key_input)
        
        layout.addWidget(main_group)
        
        # 初始化模型列表
        self._update_model_list()
        
        # 参数配置
        params_group = QGroupBox("参数配置")
        params_group.setProperty("class", "group-box")
        params_layout = QFormLayout(params_group)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setProperty("class", "spin-box")
        self.max_tokens_spin.setRange(100, 4096)
        self.max_tokens_spin.setValue(2048)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setProperty("class", "spin-box")
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setProperty("class", "spin-box")
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.1)
        self.top_p_spin.setValue(0.9)
        
        params_layout.addRow("最大Token数:", self.max_tokens_spin)
        params_layout.addRow("温度参数:", self.temperature_spin)
        params_layout.addRow("Top-P参数:", self.top_p_spin)
        
        layout.addWidget(params_group)
        
        # 容错配置
        fault_group = QGroupBox("容错配置")
        fault_group.setProperty("class", "group-box")
        fault_layout = QVBoxLayout(fault_group)
        
        self.fallback_checkbox = QCheckBox("启用自动降级")
        self.fallback_checkbox.setProperty("class", "checkbox")
        self.fallback_checkbox.setChecked(True)
        self.retry_spin = QSpinBox()
        self.retry_spin.setProperty("class", "spin-box")
        self.retry_spin.setRange(0, 5)
        self.retry_spin.setValue(2)
        
        fault_layout.addWidget(self.fallback_checkbox)
        fault_layout.addWidget(QLabel("重试次数:"))
        fault_layout.addWidget(self.retry_spin)
        
        layout.addWidget(fault_group)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setProperty("class", "secondary")
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "primary")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        
        btn_layout.addWidget(self.test_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.test_btn.clicked.connect(self.test_connection)
        self.ok_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        
    def _on_provider_changed(self, provider):
        """供应商变更处理"""
        self._update_model_list()
        
    def _update_model_list(self):
        """更新模型列表"""
        provider = self.provider_combo.currentText()
        self.model_combo.clear()
        
        if provider == "自动检测":
            self.model_combo.addItems(["自动选择"])
            self.model_combo.setEnabled(False)
        elif provider == "OpenAI":
            self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
            self.model_combo.setEnabled(True)
        elif provider == "通义千问":
            self.model_combo.addItems(["qwen-turbo", "qwen-plus", "qwen-max", "qwen3-max"])
            self.model_combo.setEnabled(True)
        elif provider == "Moonshot":
            self.model_combo.addItems(["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"])
            self.model_combo.setEnabled(True)
        
        # 默认选择第一个模型
        if self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)
            
    def load_settings(self):
        """加载设置"""
        try:
            config = self.ai_client.get_config()
            
            # 设置供应商和模型
            preferred_model = config.get('preferred_model', 'auto')
            if preferred_model == 'auto':
                self.provider_combo.setCurrentText("自动检测")
            elif preferred_model in ['openai', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']:
                self.provider_combo.setCurrentText("OpenAI")
                if preferred_model in ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']:
                    self.model_combo.setCurrentText(preferred_model)
            elif preferred_model in ['qwen', 'qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen3-max']:
                self.provider_combo.setCurrentText("通义千问")
                if preferred_model in ['qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen3-max']:
                    self.model_combo.setCurrentText(preferred_model)
            elif preferred_model in ['moonshot', 'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k']:
                self.provider_combo.setCurrentText("Moonshot")
                if preferred_model in ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k']:
                    self.model_combo.setCurrentText(preferred_model)
            
            self.primary_key_input.setText(config.get('primary_key', ''))
            self.secondary_key_input.setText(config.get('secondary_key', ''))
            self.max_tokens_spin.setValue(config.get('max_tokens', 2048))
            self.temperature_spin.setValue(config.get('temperature', 0.7))
            self.top_p_spin.setValue(config.get('top_p', 0.9))
            self.fallback_checkbox.setChecked(config.get('enable_fallback', True))
            self.retry_spin.setValue(config.get('retry_count', 2))
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载设置失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def save_settings(self):
        """保存设置"""
        try:
            # 获取供应商和模型
            provider = self.provider_combo.currentText()
            model = self.model_combo.currentText()
            
            # 验证供应商选择
            if provider == "自动检测":
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("自动检测已禁用，请手动选择供应商")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
                
            # 映射供应商名称到配置值
            provider_map = {
                "OpenAI": "openai",
                "通义千问": "tongyi", 
                "Moonshot": "moonshot"
            }
            
            # 映射模型名称到配置值
            model_map = {
                "自动选择": "gpt-3.5-turbo",
                "GPT-3.5 Turbo": "gpt-3.5-turbo",
                "GPT-4": "gpt-4",
                "Qwen Turbo": "qwen-turbo",
                "Qwen Plus": "qwen-plus",
                "Qwen Max": "qwen-max",
                "Qwen3 Max": "qwen3-max",
                "Moonshot 8K": "moonshot-v1-8k",
                "Moonshot 32K": "moonshot-v1-32k",
                "Moonshot 128K": "moonshot-v1-128k"
            }
            
            # 验证密钥格式
            primary_key = self.primary_key_input.text().strip()
            if not primary_key:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请输入主API密钥")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
                
            # 正确传递配置参数
            self.ai_client.update_config(
                primary_key=self.primary_key_input.text(),
                secondary_key=self.secondary_key_input.text(),
                provider=provider_map.get(provider, "openai"),
                model=model_map.get(model, "gpt-3.5-turbo"),
                max_tokens=self.max_tokens_spin.value(),
                temperature=self.temperature_spin.value()
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("设置已保存")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"保存设置失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def test_connection(self):
        """测试连接"""
        try:
            # 获取供应商和模型
            provider = self.provider_combo.currentText()
            model = self.model_combo.currentText()
            
            # 验证供应商选择
            if provider == "自动检测":
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("自动检测已禁用，请手动选择供应商")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
                
            # 映射供应商名称到配置值
            provider_map = {
                "OpenAI": "openai",
                "通义千问": "tongyi", 
                "Moonshot": "moonshot"
            }
            
            # 映射模型名称到配置值
            model_map = {
                "自动选择": "gpt-3.5-turbo",
                "GPT-3.5 Turbo": "gpt-3.5-turbo",
                "GPT-4": "gpt-4",
                "Qwen Turbo": "qwen-turbo",
                "Qwen Plus": "qwen-plus",
                "Qwen Max": "qwen-max",
                "Qwen3 Max": "qwen3-max",
                "Moonshot 8K": "moonshot-v1-8k",
                "Moonshot 32K": "moonshot-v1-32k",
                "Moonshot 128K": "moonshot-v1-128k"
            }
            
            # 验证密钥格式
            primary_key = self.primary_key_input.text().strip()
            if not primary_key:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请输入主API密钥")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 显示测试中对话框
            progress_dialog = QMessageBox(self)
            progress_dialog.setWindowTitle("连接测试")
            progress_dialog.setText("正在测试连接，请稍候...")
            progress_dialog.setStandardButtons(QMessageBox.NoButton)
            progress_dialog.setStyleSheet(MODERN_FLAT_STYLE)
            progress_dialog.show()
            
            # 处理UI事件，确保对话框显示
            QApplication.processEvents()
            
            # 临时设置配置用于测试
            temp_config = {
                'llm_primary_key': self.primary_key_input.text(),
                'llm_secondary_key': self.secondary_key_input.text(),
                'provider': provider_map.get(provider, "openai"),
                'model': model_map.get(model, "gpt-3.5-turbo"),
                'max_tokens': self.max_tokens_spin.value(),
                'temperature': self.temperature_spin.value()
            }
            
            # 创建临时客户端进行测试
            test_client = SmartLLMClient()
            test_client.update_config(**temp_config)
            
            # 测试连接
            result = test_client.test_connection()
            
            # 关闭进度对话框
            progress_dialog.close()
            
            # 显示测试结果
            if result['success']:
                msg = QMessageBox(self)
                msg.setWindowTitle("连接成功")
                success_msg = f"连接测试成功！\n\n"
                success_msg += f"供应商: {provider}\n"
                success_msg += f"模型: {result['model']}\n"
                success_msg += f"响应时间: {result.get('response_time', 0)} 毫秒"
                msg.setText(success_msg)
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle("连接失败")
                error_msg = f"连接测试失败！\n\n"
                error_msg += f"供应商: {provider}\n"
                error_msg += f"模型: {model}\n"
                error_msg += f"错误: {result['error']}\n"
                if result.get('response_time', 0) > 0:
                    error_msg += f"响应时间: {result.get('response_time', 0)} 毫秒"
                msg.setText(error_msg)
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                
        except Exception as e:
            # 确保关闭进度对话框
            if 'progress_dialog' in locals():
                progress_dialog.close()
                
            error_msg = f"测试连接时发生异常: {str(e)}\n\n"
            error_msg += "请检查:\n"
            error_msg += "1. API密钥是否正确\n"
            error_msg += "2. 网络连接是否正常\n"
            error_msg += "3. 模型服务是否可用"
            
            msg = QMessageBox(self)
            msg.setWindowTitle("测试异常")
            msg.setText(error_msg)
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()


class AIGenerateDialog(QDialog):
    """AI生成对话框"""
    
    # 信号：当生成完成时发出
    generation_completed = Signal(str, str)  # 主题, 内容
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_client = SmartLLMClient()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI生成")
        self.setFixedSize(600, 500)
        # 确保使用浅色主题样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #3c4043;
            }
            QLabel, QComboBox, QTextEdit, QLineEdit {
                color: #3c4043;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 输入区域
        input_group = QGroupBox("输入")
        input_group.setProperty("class", "group-box")
        input_layout = QVBoxLayout(input_group)
        
        # 主题输入
        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("主题:"))
        self.topic_input = QLineEdit()
        self.topic_input.setProperty("class", "input-field")
        topic_layout.addWidget(self.topic_input)
        input_layout.addLayout(topic_layout)
        
        # 详细描述
        input_layout.addWidget(QLabel("详细描述:"))
        self.description_input = QTextEdit()
        self.description_input.setProperty("class", "input-field")
        self.description_input.setMaximumHeight(100)
        input_layout.addWidget(self.description_input)
        
        # 参数设置
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("语气:"))
        self.tone_combo = QComboBox()
        self.tone_combo.setProperty("class", "combo-box")
        self.tone_combo.addItems(["formal", "casual", "friendly", "professional"])
        params_layout.addWidget(self.tone_combo)
        
        params_layout.addWidget(QLabel("语言:"))
        self.language_combo = QComboBox()
        self.language_combo.setProperty("class", "combo-box")
        self.language_combo.addItems(["zh", "en"])
        params_layout.addWidget(self.language_combo)
        
        input_layout.addLayout(params_layout)
        
        layout.addWidget(input_group)
        
        # 输出区域
        output_group = QGroupBox("输出")
        output_group.setProperty("class", "group-box")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QTextEdit()
        self.output_text.setProperty("class", "input-field")
        output_layout.addWidget(self.output_text)
        
        layout.addWidget(output_group)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("生成")
        self.generate_btn.setProperty("class", "primary")
        self.copy_btn = QPushButton("复制到邮件")
        self.copy_btn.setProperty("class", "secondary")
        self.close_btn = QPushButton("关闭")
        self.close_btn.setProperty("class", "secondary")
        
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.generate_btn.clicked.connect(self.generate_content)
        self.copy_btn.clicked.connect(self.copy_to_mail)
        self.close_btn.clicked.connect(self.accept)
        
    def generate_content(self):
        """生成内容"""
        topic = self.topic_input.text().strip()
        description = self.description_input.toPlainText().strip()
        tone = self.tone_combo.currentText()
        language = self.language_combo.currentText()
        
        if not topic:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请输入主题")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("生成中...")
            
            # 构造提示词
            prompt = f"主题: {topic}\n"
            if description:
                prompt += f"描述: {description}\n"
            prompt += f"请用{language}语言，以{tone}的语气写一封邮件。"
            
            # 生成内容
            content = self.ai_client.generate_mail(prompt, tone)
            self.output_text.setPlainText(content)
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"生成内容失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
        finally:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成")
            
    def copy_to_mail(self):
        """复制到邮件"""
        content = self.output_text.toPlainText()
        if content:
            # 将内容复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("内容已复制到剪贴板")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("没有内容可复制")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()


class TaskDetailsDialog(QDialog):
    """任务详情对话框"""
    
    def __init__(self, task_id, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.mail_sender = MailSender()
        self.init_ui()
        self.load_task_details()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("任务详情")
        self.setMinimumSize(900, 800)  # 设置最小尺寸，允许用户调整窗口大小
        # 确保使用浅色主题样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #3c4043;
            }
            QLabel, QTextEdit, QTableWidget {
                color: #3c4043;
            }
            QTableWidget::item {
                color: #3c4043;
                background-color: #ffffff;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建分割器，允许用户调整邮件内容和结果表格的比例
        splitter = QSplitter(Qt.Vertical)
        
        # 上半部分：任务信息和邮件内容
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # 任务基本信息
        info_group = QGroupBox("任务信息")
        info_group.setProperty("class", "group-box")
        info_layout = QFormLayout(info_group)
        
        self.subject_label = QLabel()
        self.send_time_label = QLabel()
        self.status_label = QLabel()
        
        info_layout.addRow("邮件主题:", self.subject_label)
        info_layout.addRow("发送时间:", self.send_time_label)
        info_layout.addRow("任务状态:", self.status_label)
        
        top_layout.addWidget(info_group)
        
        # 邮件内容 - 增加高度，使用更好的显示比例
        content_group = QGroupBox("邮件内容")
        content_group.setProperty("class", "group-box")
        content_layout = QVBoxLayout(content_group)
        
        self.content_text = QTextEdit()
        self.content_text.setProperty("class", "input-field")
        self.content_text.setReadOnly(True)
        self.content_text.setMinimumHeight(200)  # 增加最小高度
        content_layout.addWidget(self.content_text)
        
        top_layout.addWidget(content_group)
        
        # 下半部分：详细结果
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        result_group = QGroupBox("发送结果")
        result_group.setProperty("class", "group-box")
        result_layout = QVBoxLayout(result_group)
        
        self.result_table = QTableWidget(0, 5)
        self.result_table.setProperty("class", "table")
        self.result_table.setHorizontalHeaderLabels(["收件人", "发送结果", "错误信息", "发送轮次", "备注"])
        
        # 优化表格显示
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setAlternatingRowColors(True)  # 交替行颜色，提高可读性
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 设置列宽比例
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 收件人列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 状态列自适应
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # 错误信息列拉伸
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # 发送时间列自适应
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # 备注列自适应
        
        result_layout.addWidget(self.result_table)
        bottom_layout.addWidget(result_group)
        
        # 将上下部分添加到分割器
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        
        # 设置分割器初始比例（邮件内容占40%，结果表格占60%）
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        # 添加导出按钮
        self.export_btn = QPushButton("导出详情")
        self.export_btn.setProperty("class", "secondary")
        self.close_btn = QPushButton("关闭")
        self.close_btn.setProperty("class", "secondary")
        
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        main_layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.export_btn.clicked.connect(self.export_details)
        self.close_btn.clicked.connect(self.accept)
        
    def load_task_details(self):
        """加载任务详情"""
        try:
            # 获取任务基本信息
            task = self.mail_sender.get_task(self.task_id)
            if task:
                self.subject_label.setText(task.get('subject', ''))
                self.send_time_label.setText(
                    task.get('send_time').strftime('%Y-%m-%d %H:%M:%S') if task.get('send_time') else '')
                self.status_label.setText(task.get('status', ''))
                # 显示邮件内容
                self.content_text.setPlainText(task.get('content', ''))
                
            # 获取详细结果 - 使用HistoryTracker获取正确的字段名
            from core.history_tracker import HistoryTracker
            tracker = HistoryTracker()
            task_details = tracker.get_task_details(self.task_id)
            
            self.result_table.setRowCount(len(task_details))
            
            for row, detail in enumerate(task_details):
                self.result_table.setItem(row, 0, QTableWidgetItem(detail.get('recipient_email', '')))
                self.result_table.setItem(row, 1, QTableWidgetItem(detail.get('result', '')))  # 使用result字段而不是status
                self.result_table.setItem(row, 2, QTableWidgetItem(detail.get('error_msg', '')))  # 使用error_msg字段而不是error_message
                # 显示发送轮次
                self.result_table.setItem(row, 3, QTableWidgetItem(str(detail.get('send_round', 1))))
                # 备注字段在TaskDetail表中不存在，使用空字符串
                self.result_table.setItem(row, 4, QTableWidgetItem(''))
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载任务详情失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def export_details(self):
        """导出任务详情到CSV文件"""
        try:
            # 让用户选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出任务详情", 
                f"任务详情_{self.task_id}.csv", 
                "CSV文件 (*.csv)"
            )
            
            if file_path:
                # 使用HistoryTracker导出详情
                from core.history_tracker import HistoryTracker
                tracker = HistoryTracker()
                count = tracker.export_task_details_to_csv(self.task_id, file_path)
                
                msg = QMessageBox(self)
                msg.setWindowTitle("导出成功")
                msg.setText(f"任务详情已成功导出到:\n{file_path}\n共导出 {count} 条记录")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"导出任务详情失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()