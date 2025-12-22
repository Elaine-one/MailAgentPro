#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI助手组件 - 独立的AI功能模块
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox, 
                               QTextEdit, QComboBox, QGroupBox)
from PySide6.QtCore import Qt
from core.ai_writer import SmartLLMClient
from ui.modern_styles import MODERN_FLAT_STYLE


class AIAssistantWidget(QWidget):
    """AI助手组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.ai_writer = None
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        # 使用全局样式，移除冗余内联样式
        layout = QVBoxLayout(self)
        
        # AI设置
        settings_group = QGroupBox("AI设置")
        settings_group.setProperty("class", "group-box")
        settings_layout = QFormLayout(settings_group)
        
        # 模型供应商选择
        self.provider_combo = QComboBox()
        self.provider_combo.setProperty("class", "combo-box")
        self.provider_combo.addItems(["自动检测", "OpenAI", "通义千问", "Moonshot"])
        self.provider_combo.setToolTip("选择AI模型供应商，或选择自动检测让系统根据API Key自动识别")
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        
        # 模型选择
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.setProperty("class", "combo-box")
        self.ai_model_combo.setToolTip("选择具体的AI模型")
        
        # 初始化模型列表
        self._update_model_list()
        
        self.tone_combo = QComboBox()
        self.tone_combo.setProperty("class", "combo-box")
        self.tone_combo.addItems(["正式", "随意", "友好", "专业"])
        
        settings_layout.addRow("供应商:", self.provider_combo)
        settings_layout.addRow("模型:", self.ai_model_combo)
        settings_layout.addRow("语气:", self.tone_combo)
        
        layout.addWidget(settings_group)
        
        # AI功能
        ai_group = QGroupBox("AI功能")
        ai_group.setProperty("class", "group-box")
        ai_layout = QVBoxLayout(ai_group)
        
        # 邮件生成
        # 邮件主题输入
        self.subject_input = QLineEdit()
        self.subject_input.setProperty("class", "input-field")
        self.subject_input.setPlaceholderText("输入邮件主题（可选）")
        
        # 生成按钮
        self.generate_btn = QPushButton("生成邮件")
        self.generate_btn.setProperty("class", "primary")
        
        generate_layout = QHBoxLayout()
        generate_layout.addWidget(QLabel("邮件主题:"))
        generate_layout.addWidget(self.subject_input)
        generate_layout.addWidget(self.generate_btn)
        ai_layout.addLayout(generate_layout)
        
        # 语气调整
        self.tone_btn = QPushButton("调整语气")
        self.tone_btn.setProperty("class", "primary")
        self.tone_adjust_combo = QComboBox()
        self.tone_adjust_combo.setProperty("class", "combo-box")
        self.tone_adjust_combo.addItems(["正式", "随意", "友好", "专业"])
        
        tone_layout = QHBoxLayout()
        tone_layout.addWidget(QLabel("目标语气:"))
        tone_layout.addWidget(self.tone_adjust_combo)
        tone_layout.addWidget(self.tone_btn)
        ai_layout.addLayout(tone_layout)
        
        # 邮件摘要
        self.summary_btn = QPushButton("生成摘要")
        self.summary_btn.setProperty("class", "primary")
        self.translate_btn = QPushButton("翻译邮件")
        self.translate_btn.setProperty("class", "primary")
        
        summary_layout = QHBoxLayout()
        summary_layout.addWidget(self.summary_btn)
        summary_layout.addWidget(self.translate_btn)
        ai_layout.addLayout(summary_layout)
        
        layout.addWidget(ai_group)
        
        # AI输出
        layout.addWidget(QLabel("AI输出:"))
        self.ai_output = QTextEdit()
        self.ai_output.setProperty("class", "output-field")
        self.ai_output.setMinimumHeight(300)
        layout.addWidget(self.ai_output)
        
        # 连接信号槽
        self.generate_btn.clicked.connect(self.generate_mail)
        self.tone_btn.clicked.connect(self.adjust_tone)
        self.summary_btn.clicked.connect(self.summarize_mail)
        self.translate_btn.clicked.connect(self.translate_mail)
        
    def _on_provider_changed(self, provider):
        """供应商变更处理"""
        self._update_model_list()
        
    def _update_model_list(self):
        """更新模型列表"""
        provider = self.provider_combo.currentText()
        self.ai_model_combo.clear()
        
        if provider == "自动检测":
            self.ai_model_combo.addItems(["自动选择"])
            self.ai_model_combo.setEnabled(False)
        elif provider == "OpenAI":
            self.ai_model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
            self.ai_model_combo.setEnabled(True)
        elif provider == "通义千问":
            self.ai_model_combo.addItems(["qwen-turbo", "qwen-plus", "qwen-max"])
            self.ai_model_combo.setEnabled(True)
        elif provider == "Moonshot":
            self.ai_model_combo.addItems(["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"])
            self.ai_model_combo.setEnabled(True)
        
        # 默认选择第一个模型
        if self.ai_model_combo.count() > 0:
            self.ai_model_combo.setCurrentIndex(0)
            
    def _ensure_ai_initialized(self):
        """确保AI功能已初始化"""
        if self.ai_writer is None:
            try:
                self.ai_writer = SmartLLMClient()
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("错误")
                msg_box.setText(f"AI功能初始化失败: {str(e)}")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.exec()
                return False
        return True
        
    def generate_mail(self):
        """生成邮件"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        topic = self.subject_input.text()
        if not topic:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("警告")
            msg_box.setText("请输入邮件主题")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.exec()
            return
            
        tone_map = {"正式": "formal", "随意": "casual", "友好": "friendly", "专业": "professional"}
        tone = tone_map.get(self.tone_combo.currentText(), "formal")
        
        self._update_status("正在生成邮件...")
        content = self.ai_writer.generate_mail(topic, tone)
        self.ai_output.setPlainText(content)
        self._update_status("邮件生成完成")
        
    def adjust_tone(self):
        """调整语气"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        content = self.ai_output.toPlainText()
        if not content:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("警告")
            msg_box.setText("请先生成邮件内容或输入文本")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.exec()
            return
            
        tone_map = {"正式": "formal", "随意": "casual", "友好": "friendly", "专业": "professional"}
        target_tone = tone_map.get(self.tone_adjust_combo.currentText(), "formal")
        
        self._update_status("正在调整语气...")
        adjusted_content = self.ai_writer.adjust_tone(content, target_tone)
        self.ai_output.setPlainText(adjusted_content)
        self._update_status("语气调整完成")
        
    def summarize_mail(self):
        """生成摘要"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        content = self.ai_output.toPlainText()
        if not content:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("警告")
            msg_box.setText("请先生成邮件内容或输入文本")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.exec()
            return
            
        self._update_status("正在生成摘要...")
        summary = self.ai_writer.summarize_mail(content)
        self.ai_output.setPlainText(summary)
        self._update_status("摘要生成完成")
        
    def translate_mail(self):
        """翻译邮件"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        content = self.ai_output.toPlainText()
        if not content:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("警告")
            msg_box.setText("请先生成邮件内容或输入文本")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.exec()
            return
            
        self._update_status("正在翻译邮件...")
        translated = self.ai_writer.translate_mail(content)
        self.ai_output.setPlainText(translated)
        self._update_status("翻译完成")
        
    def _update_status(self, message):
        """更新状态信息"""
        if self.parent_window and hasattr(self.parent_window, 'status_bar'):
            self.parent_window.status_bar.showMessage(message)
        else:
            # 如果没有父窗口的状态栏，可以在这里添加其他状态显示方式
            pass
            
    def update_ai_config(self, primary_key=None, secondary_key=None, max_tokens=None, temperature=None):
        """更新AI配置"""
        if self.ai_writer:
            self.ai_writer.update_config(
                primary_key=primary_key,
                secondary_key=secondary_key,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
    def get_generated_content(self):
        """获取生成的邮件内容"""
        return self.ai_output.toPlainText()
        
    def set_content(self, content):
        """设置邮件内容"""
        self.ai_output.setPlainText(content)
        
    def clear_content(self):
        """清空邮件内容"""
        self.ai_output.clear()
        
    def save_ai_settings(self, provider, model, primary_key, secondary_key, max_tokens, temperature):
        """保存AI设置"""
        try:
            # 更新UI中的供应商和模型选择
            if provider and provider in ["自动检测", "OpenAI", "通义千问", "Moonshot"]:
                self.provider_combo.setCurrentText(provider)
                self._update_model_list()
                
            if model and self.ai_model_combo.count() > 0:
                index = self.ai_model_combo.findText(model)
                if index >= 0:
                    self.ai_model_combo.setCurrentIndex(index)
            
            # 确定首选模型
            if provider == "自动检测":
                preferred_model = "auto"
            elif provider == "OpenAI":
                preferred_model = model if model != "自动选择" else "gpt-3.5-turbo"
            elif provider == "通义千问":
                preferred_model = model if model != "自动选择" else "qwen-turbo"
            elif provider == "Moonshot":
                preferred_model = model if model != "自动选择" else "moonshot-v1-8k"
            else:
                preferred_model = "auto"
            
            # 确保AI功能已初始化
            if not self._ensure_ai_initialized():
                return False
                
            # 更新AI配置
            self.ai_writer.update_config(
                primary_key=primary_key,
                secondary_key=secondary_key,
                preferred_model=preferred_model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return True
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"保存AI设置失败: {str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()
            return False
            
    def reload_settings(self):
        """重新加载设置"""
        try:
            # 如果已有AI客户端，需要重新创建以应用新配置
            if self.ai_writer is not None:
                self.ai_writer = None
            
            # 确保AI功能已初始化（使用新配置）
            self._ensure_ai_initialized()
            
            self._update_status("设置已重新加载")
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"重新加载设置失败: {str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()