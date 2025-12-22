#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
侧边栏AI助手组件
支持邮件生成、摘要和翻译功能
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTextEdit, QLineEdit, QLabel, QComboBox, QFrame,
                               QScrollArea, QSizePolicy, QButtonGroup, QRadioButton, QApplication,
                               QStackedWidget)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont
from core.ai_writer import SmartLLMClient
from ui.modern_styles import MODERN_FLAT_STYLE


class AIWorker(QThread):
    """AI 生成任务工作线程"""
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, ai_writer, function, params):
        super().__init__()
        self.ai_writer = ai_writer
        self.function = function
        self.params = params
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            full_text = ""
            if self.function == "生成邮件":
                generator = self.ai_writer.generate_mail_stream(
                    self.params['input_text'],
                    tone=self.params.get('tone', 'formal'),
                    template_type=self.params.get('template_type', 'general'),
                    recipient_type=self.params.get('recipient_type', 'general')
                )
            elif self.function == "邮件摘要":
                generator = self.ai_writer.summarize_mail_stream(
                    self.params['input_text'],
                    summary_type=self.params.get('summary_type', 'general')
                )
            elif self.function == "邮件翻译":
                generator = self.ai_writer.translate_mail_stream(
                    self.params['input_text'],
                    target_language=self.params.get('target_language', 'en')
                )
            else:
                self.error.emit(f"不支持的功能: {self.function}")
                return

            for chunk in generator:
                if not self._is_running:
                    break
                if chunk:
                    full_text += chunk
                    self.chunk_received.emit(chunk)
            
            self.finished.emit(full_text)
        except Exception as e:
            self.error.emit(str(e))


class AISidebar(QWidget):
    """侧边栏AI助手组件"""
    
    # 信号：当生成邮件内容时发出
    mail_generated = Signal(str, str)  # 主题, 内容
    closed = Signal()  # 当侧边栏关闭时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.ai_writer = None
        self.worker = None
        self.is_visible = False
        self.generated_subject = ""
        self.generated_content = ""
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        # 显式固定侧边栏宽度，防止动态内容导致宽度抖动
        self.setFixedWidth(340)
        self.setProperty("class", "ai-container")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部标题栏
        header_widget = QWidget()
        header_widget.setFixedHeight(48)
        header_widget.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e9ecef;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        title_label = QLabel("AI 智能助手")
        title_label.setProperty("class", "sidebar-title")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 16px;
                background-color: transparent;
                color: #5f6368;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f1f3f4;
                color: #202124;
            }
        """)
        self.close_btn.clicked.connect(self.hide_sidebar)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(header_widget)
        
        # 可滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #ffffff;")
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(10, 8, 10, 8)
        self.content_layout.setSpacing(8)
        
        # 1. 功能选择区
        func_group = QWidget()
        func_layout = QVBoxLayout(func_group)
        func_layout.setContentsMargins(0, 0, 0, 0)
        func_layout.setSpacing(2) # 极简间距
        
        func_label = QLabel("核心功能")
        func_label.setProperty("class", "sidebar-label")
        func_layout.addWidget(func_label)
        
        self.function_combo = QComboBox()
        self.function_combo.addItems(["生成邮件", "邮件摘要", "邮件翻译"])
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        func_layout.addWidget(self.function_combo)
        
        self.content_layout.addWidget(func_group)
        
        # 2. 动态选项区 (改为使用容器和布局切换，避免 QStackedWidget 导致的留白问题)
        self.options_container = QWidget()
        self.options_layout = QVBoxLayout(self.options_container)
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.options_layout.setSpacing(0)
        
        # 邮件生成面板
        self.mail_options_widget = QWidget()
        mail_layout = QVBoxLayout(self.mail_options_widget)
        mail_layout.setContentsMargins(0, 0, 0, 0)
        mail_layout.setSpacing(4) # 紧凑布局
        
        # 组合：邮件类型
        t_group = QWidget()
        tl = QVBoxLayout(t_group)
        tl.setContentsMargins(0, 0, 0, 0); tl.setSpacing(1)
        t_label = QLabel("邮件类型")
        t_label.setProperty("class", "sidebar-label")
        tl.addWidget(t_label)
        self.template_combo = QComboBox()
        self.template_combo.addItems(["通用邮件", "商务合作", "会议邀请", "跟进回复", "面试通知"])
        tl.addWidget(self.template_combo)
        mail_layout.addWidget(t_group)
        
        # 组合：收件人
        r_group = QWidget()
        rl = QVBoxLayout(r_group)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(1)
        r_label = QLabel("收件人关系")
        r_label.setProperty("class", "sidebar-label")
        rl.addWidget(r_label)
        self.recipient_combo = QComboBox()
        self.recipient_combo.addItems(["合作伙伴", "潜在客户", "团队同事", "上级领导"])
        rl.addWidget(self.recipient_combo)
        mail_layout.addWidget(r_group)
        
        # 组合：语气
        tn_group = QWidget()
        tnl = QVBoxLayout(tn_group)
        tnl.setContentsMargins(0, 0, 0, 0); tnl.setSpacing(1)
        tn_label = QLabel("创作语气")
        tn_label.setProperty("class", "sidebar-label")
        tnl.addWidget(tn_label)
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["专业正式", "亲切友好", "简洁明快", "诚恳礼貌"])
        tnl.addWidget(self.tone_combo)
        mail_layout.addWidget(tn_group)
        
        self.options_layout.addWidget(self.mail_options_widget)
        
        # 邮件翻译面板
        self.translate_options_widget = QWidget()
        trans_layout = QVBoxLayout(self.translate_options_widget)
        trans_layout.setContentsMargins(0, 0, 0, 0); trans_layout.setSpacing(4)
        
        l_group = QWidget()
        ll = QVBoxLayout(l_group)
        ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(1)
        l_label = QLabel("目标语言")
        l_label.setProperty("class", "sidebar-label")
        ll.addWidget(l_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["英文", "中文", "日文", "韩文", "德文"])
        ll.addWidget(self.lang_combo)
        trans_layout.addWidget(l_group)
        
        self.options_layout.addWidget(self.translate_options_widget)
        
        # 邮件摘要面板
        self.summary_options_widget = QWidget()
        summ_layout = QVBoxLayout(self.summary_options_widget)
        summ_layout.setContentsMargins(0, 0, 0, 0); summ_layout.setSpacing(4)
        
        st_group = QWidget()
        stl = QVBoxLayout(st_group)
        stl.setContentsMargins(0, 0, 0, 0); stl.setSpacing(1)
        st_label = QLabel("摘要重点")
        st_label.setProperty("class", "sidebar-label")
        stl.addWidget(st_label)
        self.summary_type_combo = QComboBox()
        self.summary_type_combo.addItems(["全文核心", "待办事项", "关键结论"])
        stl.addWidget(self.summary_type_combo)
        summ_layout.addWidget(st_group)
        
        self.options_layout.addWidget(self.summary_options_widget)
        
        # 默认显示第一个，隐藏其他
        self.translate_options_widget.hide()
        self.summary_options_widget.hide()
        
        self.content_layout.addWidget(self.options_container)
        
        # 3. 输入区
        in_group = QWidget()
        inl = QVBoxLayout(in_group)
        inl.setContentsMargins(0, 0, 0, 0); inl.setSpacing(2)
        self.input_label = QLabel("需求/原文")
        self.input_label.setProperty("class", "sidebar-label")
        inl.addWidget(self.input_label)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入要求或处理内容...")
        self.input_text.setMinimumHeight(60)
        self.input_text.textChanged.connect(self.update_word_count)
        inl.addWidget(self.input_text)
        
        self.word_count_label = QLabel("当前输入: 0 字")
        self.word_count_label.setStyleSheet("color: #80868b; font-size: 11px;")
        inl.addWidget(self.word_count_label)
        
        self.content_layout.addWidget(in_group)
        
        # 4. 输出区
        out_group = QWidget()
        outl = QVBoxLayout(out_group)
        outl.setContentsMargins(0, 2, 0, 0); outl.setSpacing(2)
        self.output_label = QLabel("生成结果")
        self.output_label.setProperty("class", "sidebar-label")
        outl.addWidget(self.output_label)
        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("生成结果显示区...")
        self.output_text.setMinimumHeight(120)
        outl.addWidget(self.output_text)
        self.content_layout.addWidget(out_group)
        
        # 在输出区之后添加一个伸缩，确保内容靠上
        self.content_layout.addStretch(1)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)
        
        # 5. 底部操作区 (整合生成、插入、重置)
        footer_widget = QWidget()
        footer_widget.setObjectName("sidebar_footer")
        footer_widget.setFixedHeight(65)
        # 使用更安全的 QSS 选择器，避免影响子部件
        footer_widget.setStyleSheet("""
            QWidget#sidebar_footer {
                background-color: #f8f9fa;
                border-top: 1px solid #e9ecef;
            }
        """)
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setSpacing(6)
        
        # 生成按钮 (移到底部)
        self.generate_btn = QPushButton("🚀 开始生成")
        self.generate_btn.setObjectName("generate_btn")
        # 显式设置样式以确保可见性，避免被全局 QSS 覆盖
        self.generate_btn.setStyleSheet("""
            QPushButton#generate_btn {
                background-color: #4285f4;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#generate_btn:hover {
                background-color: #3367d6;
            }
            QPushButton#generate_btn:disabled {
                background-color: #dadce0;
                color: #5f6368;
            }
        """)
        self.generate_btn.setFixedHeight(38)
        self.generate_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self.generate_content)
        
        # 插入按钮
        self.apply_btn = QPushButton("📥 插入正文")
        self.apply_btn.setObjectName("apply_btn")
        self.apply_btn.setStyleSheet("""
            QPushButton#apply_btn {
                background-color: #34a853;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton#apply_btn:hover {
                background-color: #2d9d48;
            }
            QPushButton#apply_btn:disabled {
                background-color: #dadce0;
                color: #5f6368;
            }
        """)
        self.apply_btn.setFixedHeight(38)
        self.apply_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.apply_btn.clicked.connect(self.apply_to_mail)
        self.apply_btn.setEnabled(False)
        
        # 重置按钮
        self.clear_btn = QPushButton("重置")
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.setFixedHeight(38)
        self.clear_btn.clicked.connect(self.clear_all)
        
        footer_layout.addWidget(self.generate_btn, 1)
        footer_layout.addWidget(self.apply_btn, 1)
        footer_layout.addWidget(self.clear_btn, 1)
        main_layout.addWidget(footer_widget, 0)
        
        # 初始隐藏
        self.hide()
        
    def update_word_count(self):
        """更新字数统计"""
        text = self.input_text.toPlainText()
        count = len(text)
        # 预设最小宽度，防止数字变化导致标签宽度微调引起布局抖动
        self.word_count_label.setMinimumWidth(100)
        self.word_count_label.setText(f"当前输入: {count} 字")
        
    def on_function_changed(self, function):
        """当功能选择改变时更新UI"""
        # 先隐藏所有面板
        self.mail_options_widget.hide()
        self.translate_options_widget.hide()
        self.summary_options_widget.hide()
        
        # 根据选择的功能切换到对应的选项面板
        if function == "生成邮件":
            self.mail_options_widget.show()
            self.input_label.setText("邮件需求:")
            self.input_text.setPlaceholderText("请输入邮件需求，例如：写一封邀请客户参加产品发布会的邮件...")
            self.output_label.setText("生成的邮件:")
            self.generate_btn.setText("🚀 开始生成")
        elif function == "邮件摘要":
            self.summary_options_widget.show()
            self.input_label.setText("邮件内容 (默认获取主面板内容):")
            self.input_text.setPlaceholderText("将自动获取主面板中的邮件内容，也可手动输入需要摘要的邮件...")
            self.output_label.setText("邮件摘要:")
            self.generate_btn.setText("📝 开始摘要")
        elif function == "邮件翻译":
            self.translate_options_widget.show()
            self.input_label.setText("待翻译邮件 (默认获取主面板内容):")
            self.input_text.setPlaceholderText("将自动获取主面板中的邮件内容，也可手动输入需要翻译的邮件...")
            self.output_label.setText("翻译结果:")
            self.generate_btn.setText("🌐 开始翻译")
            
        # 切换功能时，如果是摘要或翻译，尝试自动同步主界面的内容
        if function in ["邮件摘要", "邮件翻译"]:
            self.sync_main_content()
            
    def sync_main_content(self):
        """同步主界面的邮件内容到 AI 助手的输入框"""
        main_window = self.parent_window
        try:
            # 查找主窗口中的邮件输入框
            # 我们通过递归查找或者直接引用 main_window 的属性
            while main_window and not hasattr(main_window, 'subject_input_compose'):
                if hasattr(main_window, 'parent') and callable(main_window.parent):
                    main_window = main_window.parent()
                else:
                    break
        except:
            main_window = None
            
        if main_window:
            # 检查当前活动的标签页
            try:
                current_tab = main_window.tab_widget.currentIndex()
                subject = ""
                content = ""
                
                if current_tab == 2: # 撰写页
                    subject = main_window.subject_input_compose.text().strip()
                    content = main_window.body_input.toPlainText().strip()
                elif current_tab == 3: # 发送页
                    if hasattr(main_window, 'email_sender_widget'):
                        subject = main_window.email_sender_widget.subject_input.text().strip()
                        content = main_window.email_sender_widget.content_edit.toPlainText().strip()
                
                if subject or content:
                    input_text = f"主题：{subject}\n\n内容：{content}" if subject and content else (content or f"主题：{subject}")
                    self.input_text.setPlainText(input_text)
                    self.update_word_count()
            except Exception as e:
                print(f"Sync content failed: {e}")

    def _ensure_ai_initialized(self):
        """确保AI功能已初始化"""
        try:
            if self.ai_writer is None:
                # 第一次初始化
                print("AI Sidebar: 正在初始化 AI 客户端...")
                self.ai_writer = SmartLLMClient()
            
            # 如果虽然有了实例但模型仍然是 None (可能之前初始化失败)，尝试刷新
            if self.ai_writer.llm is None:
                print("AI Sidebar: 模型未就绪，尝试刷新配置...")
                self.ai_writer.refresh_models()
                
            if self.ai_writer.llm is None:
                # 如果刷新后仍然失败
                print("AI Sidebar: AI 模型初始化依然失败")
                self.show_message("提示", "AI模型初始化失败，请检查配置（API密钥）或网络连接。")
                return False
            
            print(f"AI Sidebar: AI 模型已就绪 (Provider: {self.ai_writer.config.get('provider')})")
            return True
        except Exception as e:
            print(f"AI Sidebar: 初始化异常: {str(e)}")
            self.show_message("错误", f"AI初始化异常: {str(e)}")
            return False
        
    def show_sidebar(self):
        """显示侧边栏"""
        if not self._ensure_ai_initialized():
            return
            
        self.is_visible = True
        self.show()
        self.raise_()
        self.activateWindow()
        
    def hide_sidebar(self):
        """隐藏侧边栏"""
        self.is_visible = False
        self.hide()
        self.closed.emit()
        
    def generate_content(self):
        """开始生成内容"""
        if not self._ensure_ai_initialized():
            return
            
        function = self.function_combo.currentText()
        
        # 1. 禁用 UI 并显示加载状态
        self.set_ui_enabled(False)
        
        if function == "邮件摘要":
            self.generate_btn.setText("⏳ 正在摘要...")
        elif function == "邮件翻译":
            self.generate_btn.setText("⏳ 正在翻译...")
        else:
            self.generate_btn.setText("⏳ 正在生成...")
            
        self.output_text.clear()
        self.generated_subject = ""
        self.generated_content = ""
        
        # 准备参数
        input_text = self.input_text.toPlainText().strip()
        params = {'input_text': input_text}
        
        if function == "生成邮件":
            if not input_text:
                self.show_message("提示", "请输入邮件需求")
                self.set_ui_enabled(True)
                self.on_function_changed(function)
                return
            
            tone_map = {"专业正式": "formal", "亲切友好": "friendly", "简洁明快": "casual", "诚恳礼貌": "polite"}
            template_map = {"通用邮件": "general", "商务合作": "business", "会议邀请": "invitation", "跟进回复": "follow_up", "面试通知": "interview"}
            recipient_map = {"合作伙伴": "partner", "潜在客户": "client", "团队同事": "colleague", "上级领导": "manager"}
            
            params.update({
                'tone': tone_map.get(self.tone_combo.currentText(), 'formal'),
                'template_type': template_map.get(self.template_combo.currentText(), 'general'),
                'recipient_type': recipient_map.get(self.recipient_combo.currentText(), 'general')
            })
            
        elif function == "邮件摘要":
            self.sync_main_content()
            input_text = self.input_text.toPlainText().strip()
            if not input_text:
                self.show_message("提示", "请先在主面板撰写邮件，或在输入框输入内容")
                self.set_ui_enabled(True)
                self.on_function_changed(function)
                return
            
            params['input_text'] = input_text
            type_map = {"全文核心": "general", "待办事项": "action_items", "关键结论": "key_points"}
            params['summary_type'] = type_map.get(self.summary_type_combo.currentText(), "general")
            
        elif function == "邮件翻译":
            self.sync_main_content()
            input_text = self.input_text.toPlainText().strip()
            if not input_text:
                self.show_message("提示", "请先在主面板撰写邮件，或在输入框输入内容")
                self.set_ui_enabled(True)
                self.on_function_changed(function)
                return
            
            params['input_text'] = input_text
            lang_map = {"英文": "en", "中文": "zh", "日文": "ja", "韩文": "ko", "德文": "de"}
            params['target_language'] = lang_map.get(self.lang_combo.currentText(), "en")

        # 启动工作线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        self.worker = AIWorker(self.ai_writer, function, params)
        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

    def on_chunk_received(self, chunk):
        """处理收到的文本块"""
        self.output_text.insertPlainText(chunk)
        # 自动滚动到底部
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    def on_generation_finished(self, full_text):
        """生成任务完成"""
        self.generated_content = full_text
        
        # 尝试解析主题和内容（支持中英文）
        subject, content = self._parse_subject_and_content(full_text)
        
        if subject:
            self.generated_subject = subject
            self.generated_content = content
        else:
            self.generated_subject = ""
            self.generated_content = full_text
        
        self.set_ui_enabled(True)
        self.on_function_changed(self.function_combo.currentText())
        
        if self.generated_content.strip():
            self.apply_btn.setEnabled(True)

    def on_generation_error(self, error_msg):
        """生成任务出错"""
        self.show_message("错误", f"处理失败: {error_msg}")
        self.set_ui_enabled(True)
        self.on_function_changed(self.function_combo.currentText())
            
    def set_ui_enabled(self, enabled):
        """统一控制 UI 组件的启用状态"""
        self.function_combo.setEnabled(enabled)
        self.options_container.setEnabled(enabled)
        self.input_text.setReadOnly(not enabled)
        self.generate_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        
        # 只有在启用 UI 且有生成内容时，才开启插入按钮
        if enabled:
            has_content = bool(self.output_text.toPlainText().strip())
            self.apply_btn.setEnabled(has_content)
        else:
            self.apply_btn.setEnabled(False)

    def apply_to_mail(self):
        """应用到邮件"""
        function = self.function_combo.currentText()
        
        # 优先使用已经解析好的主题和内容
        if self.generated_subject and self.generated_content:
            subject = self.generated_subject
            content = self.generated_content
        else:
            # 如果没有预解析的，尝试从输出文本框重新解析
            output_text = self.output_text.toPlainText().strip()
            if not output_text:
                self.show_message("提示", "请先生成内容")
                return
            subject, content = self._parse_subject_and_content(output_text)
            
        if function == "生成邮件":
            # 生成邮件功能：必须有内容，如果没有解析出主题则使用空字符串（主窗口会尝试提取）
            self.mail_generated.emit(subject or "", content)
            self.show_message("成功", "邮件内容已应用到撰写区域")
        else:
            # 对于摘要/翻译等功能
            if subject:
                # 如果解析出了主题，则同时应用主题和正文
                self.mail_generated.emit(subject, content)
                self.show_message("成功", "主题和内容已应用")
            else:
                # 如果没有解析出主题，则只应用正文，不更新主题
                self.mail_generated.emit("__SKIP_SUBJECT__", content)
                self.show_message("成功", "内容已应用到邮件正文")
    
    def _parse_subject_and_content(self, text):
        """
        从文本中解析主题和内容，支持中英文多种格式
        """
        if not text:
            return "", ""
            
        lines = text.split('\n')
        subject = ""
        content = ""
        
        # 1. 尝试按行查找明确的标记（主题：/Subject: 等）
        subject_line_idx = -1
        content_line_idx = -1
        
        subject_prefixes = ["主题：", "Subject:", "标题：", "Title:", "主题:"]
        content_prefixes = ["内容：", "Content:", "正文：", "Body:", "内容:"]
        
        for i, line in enumerate(lines):
            trimmed_line = line.strip()
            if not trimmed_line:
                continue
                
            # 查找主题行
            if subject_line_idx == -1:
                for prefix in subject_prefixes:
                    if trimmed_line.lower().startswith(prefix.lower()):
                        subject = trimmed_line[len(prefix):].strip()
                        subject_line_idx = i
                        break
            
            # 查找内容行
            if content_line_idx == -1:
                for prefix in content_prefixes:
                    if trimmed_line.lower().startswith(prefix.lower()):
                        content_line_idx = i
                        break
        
        # 如果找到了主题标记
        if subject_line_idx != -1:
            # 如果也找到了内容标记
            if content_line_idx != -1:
                # 提取内容行之后的所有行
                content_parts = []
                # 如果内容行本身除了前缀还有内容，也要加上
                start_line = lines[content_line_idx].strip()
                for prefix in content_prefixes:
                    if start_line.lower().startswith(prefix.lower()):
                        rem = start_line[len(prefix):].strip()
                        if rem:
                            content_parts.append(rem)
                        break
                
                # 加上后续所有行
                content_parts.extend(lines[content_line_idx + 1:])
                content = '\n'.join(content_parts).strip()
            else:
                # 没找到内容标记，则把主题行之后的所有非空行作为内容
                content_parts = []
                for i in range(subject_line_idx + 1, len(lines)):
                    content_parts.append(lines[i])
                content = '\n'.join(content_parts).strip()
                
            return subject, content
            
        # 2. 如果没找到明确标记，尝试查找 Markdown 格式 (# 主题 或 **主题**)
        for i, line in enumerate(lines):
            trimmed = line.strip()
            if trimmed.startswith('# '):
                subject = trimmed[2:].strip()
                content = '\n'.join(lines[i+1:]).strip()
                return subject, content
            if trimmed.startswith('**主题：') or trimmed.startswith('**Subject:'):
                # 提取粗体中的内容
                import re
                match = re.search(r'\*\*(?:主题：|Subject:)\s*(.*?)\*\*', trimmed, re.I)
                if match:
                    subject = match.group(1).strip()
                    content = '\n'.join(lines[i+1:]).strip()
                    return subject, content
        
        # 3. 启发式：第一行作为主题（如果不像正文）
        if len(lines) >= 1:
            first_line = lines[0].strip()
            # 排除常见的正文开头
            discards = ["尊敬的", "亲爱的", "Dear", "Hi", "Hello", "Greetings"]
            is_greeting = any(first_line.startswith(d) for d in discards)
            
            # 如果第一行不太长，且不是问候语，尝试作为主题
            if 2 <= len(first_line) <= 100 and not is_greeting:
                subject = first_line
                # 剩余部分作为正文，跳过紧随其后的空行
                content_start_idx = 1
                while content_start_idx < len(lines) and not lines[content_start_idx].strip():
                    content_start_idx += 1
                content = '\n'.join(lines[content_start_idx:]).strip()
                return subject, content
        
        # 4. 最后保底：全部作为正文
        return "", text.strip()
                
    def clear_all(self):
        """清空内容"""
        self.input_text.clear()
        self.output_text.clear()
        self.apply_btn.setEnabled(False)
        self.generated_subject = ""
        self.generated_content = ""
        
    def show_message(self, title, message):
        """显示消息"""
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()
        
    def set_position(self, x, y, width, height):
        """设置侧边栏位置"""
        self.setGeometry(x, y, width, height)