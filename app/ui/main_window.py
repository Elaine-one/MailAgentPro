#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主窗口界面
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
                               QFileDialog, QMessageBox, QGroupBox, QFormLayout,
                               QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar, QStatusBar,
                               QAbstractItemView, QDialog, QListWidget, QListWidgetItem,
                               QInputDialog, QRadioButton, QSplitter, QToolBar, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QClipboard
from core.account_manager import AccountManager
from core.recipient_manager import RecipientManager
from core.mail_sender import MailSender
from core.history_tracker import HistoryTracker
from core.template_manager import TemplateManager
from core.history_tracker import HistoryTracker
from core.path_manager import get_path_manager
from db.db_manager import init_database
from ui.account_dialogs import AddAccountDialog, EditAccountDialog
from ui.recipient_dialogs import ImportRecipientsDialog, AddRecipientDialog, EditRecipientDialog
from ui.mail_dialogs import AISettingsDialog, AIGenerateDialog, TaskDetailsDialog
from ui.group_manager import GroupManager
from ui.ai_assistant_widget import AIAssistantWidget
from ui.settings_widget import SettingsWidget
from ui.ai_sidebar import AISidebar
from ui.modern_styles import MODERN_FLAT_STYLE
from ui.wheel_combo import WheelComboBox


class TemplateSelectDialog(QDialog):
    """模板选择对话框 - 使用滚轮选择器"""
    
    def __init__(self, template_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("加载模板")
        self.setMinimumWidth(300)
        self.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("请选择模板:")
        layout.addWidget(label)
        
        self.template_combo = WheelComboBox()
        self.template_combo.addItems(template_names)
        self.template_combo.setProperty("class", "combo-box")
        layout.addWidget(self.template_combo)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "primary")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_selected_template(self):
        return self.template_combo.currentText()


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MailAgent Pro - 智能邮件助理")
        # 减小初始化大小，使其更协调
        self.resize(1100, 720)
        
        # 居中显示窗口
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        
        # 确保主窗口背景色为浅色
        # 数据库已在main.py中初始化，此处无需重复初始化
        
        # 初始化核心模块
        self.account_manager = AccountManager()
        self.recipient_manager = RecipientManager()
        self.mail_sender = MailSender()
        self.ai_writer = None  # 延迟初始化AI功能
        self.history_tracker = HistoryTracker()
        
        # 使用路径管理器初始化模板管理器，确保模板保存位置一致
        path_manager = get_path_manager()
        template_path = str(path_manager.get_templates_path())
        self.template_manager = TemplateManager(template_path)
        
        # 初始化分组管理器
        self.group_manager = GroupManager(self.recipient_manager, self)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建侧边栏AI助手
        self.ai_sidebar = AISidebar(self)
        self.ai_sidebar.mail_generated.connect(self.on_mail_generated)
        self.ai_sidebar.closed.connect(self.on_ai_sidebar_closed)
        
        # 创建主界面
        self.create_main_ui()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # 使用说明动作
        help_action = QAction("使用说明", self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)
        
    def show_about_dialog(self):
        """显示关于对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("关于 MailAgent Pro")
        dialog.setFixedSize(450, 350)
        dialog.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("MailAgent Pro - 智能邮件助理")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a73e8;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 版本信息
        version_label = QLabel("版本: 1.0.0")
        version_label.setStyleSheet("font-size: 12px; color: #5f6368;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #dadce0;")
        layout.addWidget(line)
        
        # 功能介绍
        features_label = QLabel(
            "📧 智能邮件撰写 - AI 辅助生成专业邮件\n"
            "👥 收件人管理 - 批量导入与分组管理\n"
            "📬 多账户支持 - 灵活切换发送账户\n"
            "📊 发送历史追踪 - 完整记录邮件发送状态\n"
            "🤖 AI 助手 - 智能摘要、翻译与语气调整"
        )
        features_label.setStyleSheet("font-size: 13px; color: #3c4043; line-height: 1.8;")
        layout.addWidget(features_label)
        
        # 技术支持
        tech_label = QLabel("技术支持: elaine")
        tech_label.setStyleSheet("font-size: 11px; color: #5f6368;")
        tech_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tech_label)
        
        layout.addStretch()
        
        # 版权信息
        copyright_label = QLabel("© 2024 MailAgent Pro 保留所有权利")
        copyright_label.setStyleSheet("font-size: 11px; color: #5f6368;")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "primary")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.exec()
        
    def show_help_dialog(self):
        """显示使用说明对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("使用说明")
        dialog.setFixedSize(550, 450)
        dialog.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        
        # 帮助内容
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3 style="color: #1a73e8;">快速入门指南</h3>
        
        <h4>1. 账户管理</h4>
        <p>• 添加邮箱账户，支持 SMTP 发送</p>
        <p>• 可添加多个账户，发送时灵活切换</p>
        
        <h4>2. 收件人管理</h4>
        <p>• 支持手动添加或批量导入收件人</p>
        <p>• 可创建分组，便于批量发送</p>
        
        <h4>3. 邮件撰写</h4>
        <p>• 使用 AI 助手智能生成邮件内容</p>
        <p>• 支持保存和加载邮件模板</p>
        <p>• <b>滚轮选择器：</b>使用鼠标滚轮或键盘上下键切换选项</p>
        
        <h4>4. 邮件发送</h4>
        <p>• 选择账户和收件人进行发送</p>
        <p>• 支持附件添加</p>
        
        <h4>5. AI 功能</h4>
        <p>• 邮件生成：根据主题生成专业邮件</p>
        <p>• 邮件摘要：提取邮件核心内容</p>
        <p>• 邮件翻译：支持多语言翻译</p>
        
        <h4>6. 设置</h4>
        <p>• 配置 AI 模型和 API Key</p>
        <p>• 测试连接确保配置正确</p>
        """)
        layout.addWidget(help_text)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "primary")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.exec()
        
    def create_main_ui(self):
        """创建主界面"""
        # 创建主窗口布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 使用 QSplitter 来管理布局，这样可以更美观地控制侧边栏的“向左扩展”
        from PySide6.QtWidgets import QSplitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #e9ecef; }")
        
        # 左侧：主内容区域（标签页）
        self.tab_widget = QTabWidget()
        
        # 添加各个功能标签页
        self.tab_widget.addTab(self.create_account_tab(), "账户管理")
        self.tab_widget.addTab(self.create_recipient_tab(), "收件人管理")
        self.tab_widget.addTab(self.create_compose_tab(), "邮件撰写")
        self.tab_widget.addTab(self.create_send_tab(), "邮件发送")
        self.tab_widget.addTab(self.create_history_tab(), "发送历史")
        self.tab_widget.addTab(self.create_settings_tab(), "设置")
        
        # 将组件添加到分割器中
        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.addWidget(self.ai_sidebar)
        
        # 设置初始伸缩因子：主内容占满，侧边栏不占位
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        
        # 初始隐藏侧边栏
        self.ai_sidebar.hide()
        
        main_layout.addWidget(self.main_splitter)
        
        # 创建 AI 助手切换按钮并放入 TabWidget 的右上角
        self.ai_toggle_btn = QPushButton("开启 AI 助手")
        self.ai_toggle_btn.setCheckable(True)
        self.ai_toggle_btn.setChecked(False)
        self.ai_toggle_btn.setFixedWidth(110)
        self.ai_toggle_btn.setFixedHeight(30)
        self.ai_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.ai_toggle_btn.clicked.connect(self.toggle_ai_sidebar)
        
        # 将按钮添加到 TabWidget 的右上角
        self.tab_widget.setCornerWidget(self.ai_toggle_btn, Qt.TopRightCorner)
        
        self.setCentralWidget(main_widget)
        
    def toggle_ai_sidebar(self):
        """切换侧边栏AI助手的显示/隐藏"""
        if self.ai_toggle_btn.isChecked():
            # 记录当前窗口的总宽度
            total_w = self.width()
            
            # 显示侧边栏
            self.ai_sidebar.show()
            
            # 目标宽度
            sidebar_w = 340
            main_w = total_w - sidebar_w
            
            # 关键：先设置比例再设置大小，并立即强制调整窗口大小防止向右扩展
            self.main_splitter.setSizes([main_w, sidebar_w])
            
            # 强制保持窗口宽度不变，这样就会迫使左侧区域向左压缩
            self.setFixedWidth(total_w)
            QTimer.singleShot(100, lambda: self.setMinimumWidth(800))
            QTimer.singleShot(100, lambda: self.setMaximumWidth(16777215))
            
            self.ai_toggle_btn.setText("隐藏 AI 助手")
        else:
            self.ai_sidebar.hide()
            self.ai_toggle_btn.setText("开启 AI 助手")
            # 恢复 splitter 大小
            self.main_splitter.setSizes([self.width(), 0])

    def on_ai_sidebar_closed(self):
        """当侧边栏关闭按钮被点击时的回调"""
        self.ai_toggle_btn.setChecked(False)
        self.ai_toggle_btn.setText("开启 AI 助手")
        # 恢复 splitter 大小
        self.main_splitter.setSizes([self.width(), 0])
            
    def on_mail_generated(self, subject, content):
        """处理AI生成的邮件内容"""
        # 1. 预处理
        content = content.strip() if content else ""
        
        # 约定：
        # - 如果 subject == "": 说明需要从 content 中尝试提取主题和正文 (用于 AI 写信)
        # - 如果 subject == "__SKIP_SUBJECT__": 说明只应用正文，不更新主题 (用于 摘要/翻译)
        # - 如果 subject 有值: 直接使用该主题
        
        if subject == "" and content:
            subject, content = self._extract_subject_from_content(content)
        elif subject == "__SKIP_SUBJECT__":
            subject = None # 标记为不更新主题
        
        # 如果依然没有内容，显示错误
        if not content:
            self.status_bar.showMessage("AI生成的邮件内容为空")
            return
            
        # 2. 确定应用位置
        current_index = self.tab_widget.currentIndex()
        
        # 3. 填充内容
        if current_index == 3:  # 邮件发送页面
            if hasattr(self, 'email_sender_widget'):
                # 只有在明确有新主题时才更新主题
                if subject and subject != "（无主题）":
                    if hasattr(self.email_sender_widget, 'subject_input'):
                        self.email_sender_widget.subject_input.setText(subject)
                
                if hasattr(self.email_sender_widget, 'content_edit'):
                    self.email_sender_widget.content_edit.setPlainText(content)
        else: # 默认为撰写页面或其他页面
            # 切换到撰写页
            self.tab_widget.setCurrentIndex(2)
            
            # 只有在明确有新主题时才更新主题
            if subject and subject != "（无主题）":
                self.subject_input_compose.setText(subject)
            
            # 填充正文
            if content:
                self.body_input.setPlainText(content)
            
            self.status_bar.showMessage(f"AI生成的内容已应用")
    
    def _extract_subject_from_content(self, content):
        """
        从内容中智能提取主题和正文
        支持多种常见AI输出格式，并针对英文识别进行增强
        """
        import re
        lines = content.split('\n')
        subject = ""
        remaining_content = ""
        
        # 1. 检查标准的关键词前缀格式 (增强正则匹配)
        # 支持: Subject: xxx, Subject:xxx, **Subject:** xxx, [Subject] xxx 等
        subject_patterns = [
            r'(?i)^(?:主题|Subject|Title|标题|Topic)[:：]\s*(.*)',
            r'(?i)^\*\*(?:主题|Subject|Title|标题|Topic)[:：]\*\*\s*(.*)',
            r'(?i)^\[(?:主题|Subject|Title|标题|Topic)\]\s*(.*)',
            r'(?i)^#{1,3}\s*(?:主题|Subject|Title|标题|Topic)[:：]\s*(.*)'
        ]
        
        content_patterns = [
            r'(?i)^(?:正文|内容|Content|Body|Message)[:：]\s*',
            r'(?i)^\*\*(?:正文|内容|Content|Body|Message)[:：]\*\*\s*',
            r'(?i)^\[(?:正文|内容|Content|Body|Message)\]\s*',
            r'(?i)^#{1,3}\s*(?:正文|内容|Content|Body|Message)[:：]\s*'
        ]
        
        # 先尝试寻找主题行
        found_subject = ""
        found_subject_line_idx = -1
        
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            # 针对英文邮件常见的 "Subject: " 格式优化
            for pattern in subject_patterns:
                match = re.match(pattern, line)
                if match:
                    found_subject = match.group(1).strip()
                    # 去掉可能的 Markdown 加粗符号
                    found_subject = found_subject.replace('**', '').strip()
                    found_subject_line_idx = idx
                    break
            if found_subject: break
            
        if found_subject:
            # 找到主题后，寻找内容开始的位置
            content_start_line_idx = -1
            for idx in range(found_subject_line_idx + 1, len(lines)):
                line = lines[idx].strip()
                if not line: continue
                
                for pattern in content_patterns:
                    if re.match(pattern, line):
                        content_start_line_idx = idx
                        # 提取该行剩余部分作为正文开始
                        remaining_content = re.sub(pattern, '', line).strip()
                        break
                if content_start_line_idx != -1: break
            
            if content_start_line_idx != -1:
                # 拼接后续所有行
                subsequent_content = '\n'.join(lines[content_start_line_idx + 1:])
                if remaining_content:
                    remaining_content = remaining_content + '\n' + subsequent_content
                else:
                    remaining_content = subsequent_content
                return found_subject, remaining_content.strip()
            else:
                # 如果没找到内容前缀，则将主题行之后的所有内容作为正文
                # 但要跳过紧随其后的空行
                content_lines = lines[found_subject_line_idx + 1:]
                while content_lines and not content_lines[0].strip():
                    content_lines.pop(0)
                remaining_content = '\n'.join(content_lines)
                return found_subject, remaining_content.strip()

        # 2. 检查 Markdown 标题格式 (e.g., # 主题 或 ## 主题)
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if line.startswith('#') and not subject:
                # 提取标题作为主题，去掉 # 号
                subject = line.lstrip('#').strip()
                # 剩下的作为正文
                remaining_content = '\n'.join(lines[line_idx+1:]).strip()
                if subject and remaining_content:
                    return subject, remaining_content

        # 3. 启发式：第一行看起来像主题，后面有空行
        if len(lines) >= 2:
            first_line = lines[0].strip()
            # 排除常见的称呼语作为主题
            greetings = ['Dear', 'Hi', 'Hello', '尊敬的', '您好', '你好', 'Greetings']
            is_greeting = any(first_line.startswith(g) for g in greetings)
            
            # 如果第一行长度适中且不是称呼
            if 2 <= len(first_line) <= 60 and not is_greeting:
                # 如果第二行是空行，或者全文行数较少
                if (len(lines) > 1 and not lines[1].strip()) or len(lines) < 5:
                    subject = first_line
                    remaining_content = '\n'.join(lines[1:]).strip()
                    return subject, remaining_content

        # 4. 保底方案：如果没有找到明显的主题，将第一行作为主题（如果不太长），否则全部作为正文
        if lines:
            first_line = lines[0].strip()
            if 2 <= len(first_line) <= 50:
                subject = first_line
                remaining_content = '\n'.join(lines[1:]).strip()
            else:
                subject = "（无主题）"
                remaining_content = content
        
        return subject, remaining_content
        
    def create_account_tab(self):
        """创建账户管理标签页"""
        widget = QWidget()
        widget.setProperty("class", "tab-container")
        layout = QVBoxLayout(widget)
        
        # 账户列表
        self.account_table = QTableWidget(0, 5)
        self.account_table.setProperty("class", "table")
        self.account_table.setHorizontalHeaderLabels(["ID", "邮箱", "SMTP服务器", "端口", "备注名"])
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(QLabel("账户列表:"))
        layout.addWidget(self.account_table)
        
        # 账户操作按钮
        btn_layout = QHBoxLayout()
        self.add_account_btn = QPushButton("添加账户")
        self.add_account_btn.setProperty("class", "success")
        self.edit_account_btn = QPushButton("编辑账户")
        self.edit_account_btn.setProperty("class", "secondary")
        self.delete_account_btn = QPushButton("删除账户")
        self.delete_account_btn.setProperty("class", "danger")
        self.test_account_btn = QPushButton("测试连接")
        self.test_account_btn.setProperty("class", "secondary")
        
        btn_layout.addWidget(self.add_account_btn)
        btn_layout.addWidget(self.edit_account_btn)
        btn_layout.addWidget(self.delete_account_btn)
        btn_layout.addWidget(self.test_account_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.add_account_btn.clicked.connect(self.add_account)
        self.edit_account_btn.clicked.connect(self.edit_account)
        self.delete_account_btn.clicked.connect(self.delete_account)
        self.test_account_btn.clicked.connect(self.test_account)
        
        # 加载账户数据
        self.load_accounts()
        
        return widget
        
    def create_recipient_tab(self):
        """创建收件人管理标签页 - 使用独立的收件人管理组件"""
        from ui.recipient_manager_widget import RecipientManagerWidget
        self.recipient_manager_widget = RecipientManagerWidget(self.recipient_manager, self)
        return self.recipient_manager_widget
        
    def refresh_send_tab_data(self):
        """刷新邮件发送标签页数据"""
        if hasattr(self, 'email_sender_widget'):
            self.email_sender_widget.load_accounts()
            self.email_sender_widget.load_recipients()
            self.email_sender_widget.load_templates()
        
    def create_compose_tab(self):
        """创建邮件撰写标签页"""
        widget = QWidget()
        widget.setProperty("class", "tab-container")
        layout = QVBoxLayout(widget)
        
        # 邮件主题
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("主题:"))
        self.subject_input_compose = QLineEdit()  # 使用不同的控件名避免冲突
        self.subject_input_compose.setProperty("class", "input-field")
        subject_layout.addWidget(self.subject_input_compose)
        layout.addLayout(subject_layout)
        
        # 邮件正文
        layout.addWidget(QLabel("正文:"))
        self.body_input = QTextEdit()
        self.body_input.setProperty("class", "input-field")
        self.body_input.setMinimumHeight(300)
        layout.addWidget(self.body_input)
        
        # 附件
        attachment_layout = QHBoxLayout()
        attachment_layout.addWidget(QLabel("附件:"))
        self.attachment_input = QLineEdit()
        self.attachment_input.setProperty("class", "input-field")
        self.attachment_input.setReadOnly(True)
        self.attachment_btn = QPushButton("选择文件")
        self.attachment_btn.setProperty("class", "secondary")
        attachment_layout.addWidget(self.attachment_input)
        attachment_layout.addWidget(self.attachment_btn)
        layout.addLayout(attachment_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.save_template_btn_compose = QPushButton("保存为模板")  # 使用不同的控件名避免冲突
        self.save_template_btn_compose.setProperty("class", "secondary")
        self.load_template_btn_compose = QPushButton("加载模板")   # 使用不同的控件名避免冲突
        self.load_template_btn_compose.setProperty("class", "secondary")
        
        # 添加 AI 快捷按钮
        self.translate_btn_compose = QPushButton("🌐 AI 翻译")
        self.translate_btn_compose.setProperty("class", "ai-btn")
        self.summary_btn_compose = QPushButton("📝 AI 摘要")
        self.summary_btn_compose.setProperty("class", "ai-btn")
        
        btn_layout.addWidget(self.save_template_btn_compose)
        btn_layout.addWidget(self.load_template_btn_compose)
        btn_layout.addWidget(self.translate_btn_compose)
        btn_layout.addWidget(self.summary_btn_compose)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.attachment_btn.clicked.connect(self.select_attachment)
        self.save_template_btn_compose.clicked.connect(self.save_template_compose)
        self.load_template_btn_compose.clicked.connect(self.load_template_compose)
        self.translate_btn_compose.clicked.connect(lambda: self.quick_ai_action("邮件翻译"))
        self.summary_btn_compose.clicked.connect(lambda: self.quick_ai_action("邮件摘要"))
        
        return widget
        
    def create_send_tab(self):
        """创建邮件发送标签页 - 使用EmailSender组件"""
        from ui.email_sender import EmailSender
        
        # 创建EmailSender组件实例
        self.email_sender_widget = EmailSender(
            self.account_manager, 
            self.recipient_manager, 
            self.template_manager, 
            self
        )
        
        return self.email_sender_widget
        

        
    def create_history_tab(self):
        """创建发送历史标签页"""
        widget = QWidget()
        widget.setProperty("class", "tab-container")
        layout = QVBoxLayout(widget)
        
        # 历史记录列表
        self.history_table = QTableWidget(0, 7)
        self.history_table.setProperty("class", "table")
        self.history_table.setHorizontalHeaderLabels(["ID", "主题", "发送时间", "总计", "成功", "失败", "状态"])
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(QLabel("发送历史:"))
        layout.addWidget(self.history_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.refresh_history_btn = QPushButton("刷新")
        self.refresh_history_btn.setProperty("class", "secondary")
        self.toggle_select_history_btn = QPushButton("全选/取消")
        self.toggle_select_history_btn.setProperty("class", "secondary")
        self.view_details_btn = QPushButton("查看详情")
        self.view_details_btn.setProperty("class", "secondary")
        self.export_history_btn = QPushButton("导出历史")
        self.export_history_btn.setProperty("class", "secondary")
        self.delete_history_btn = QPushButton("删除记录")
        self.delete_history_btn.setProperty("class", "danger")
        self.clear_all_history_btn = QPushButton("全部清除")
        self.clear_all_history_btn.setProperty("class", "danger")
        
        btn_layout.addWidget(self.refresh_history_btn)
        btn_layout.addWidget(self.toggle_select_history_btn)
        btn_layout.addWidget(self.view_details_btn)
        btn_layout.addWidget(self.export_history_btn)
        btn_layout.addWidget(self.delete_history_btn)
        btn_layout.addWidget(self.clear_all_history_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 统计信息
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
        
        # 连接信号槽
        self.refresh_history_btn.clicked.connect(self.load_history)
        self.toggle_select_history_btn.clicked.connect(self.toggle_select_history)
        self.view_details_btn.clicked.connect(self.view_task_details)
        self.export_history_btn.clicked.connect(self.export_history)
        self.delete_history_btn.clicked.connect(self.delete_history)
        self.clear_all_history_btn.clicked.connect(self.clear_all_history)
        
        # 加载历史数据
        self.load_history()
        
        return widget
        
    def create_settings_tab(self):
        """创建设置标签页 - 使用独立的设置组件"""
        self.settings_widget = SettingsWidget(self)
        return self.settings_widget
        
    # 账户管理相关方法
    def load_accounts(self):
        """加载账户列表"""
        try:
            accounts = self.account_manager.list_accounts()
            self.account_table.setRowCount(len(accounts))
            
            for row, account in enumerate(accounts):
                self.account_table.setItem(row, 0, QTableWidgetItem(str(account['id'])))
                self.account_table.setItem(row, 1, QTableWidgetItem(account['email']))
                self.account_table.setItem(row, 2, QTableWidgetItem(account['smtp_server']))
                self.account_table.setItem(row, 3, QTableWidgetItem(str(account['port'])))
                self.account_table.setItem(row, 4, QTableWidgetItem(account['alias']))
                
            self.status_bar.showMessage(f"已加载 {len(accounts)} 个账户")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"加载账户失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            
    def add_account(self):
        """添加账户"""
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_accounts()
            self.load_accounts_for_sending()
            self.status_bar.showMessage("账户添加成功")
        
    def edit_account(self):
        """编辑账户"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个账户")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        
        dialog = EditAccountDialog(account_id, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_accounts()
            self.load_accounts_for_sending()
            self.status_bar.showMessage("账户更新成功")
        
    def delete_account(self):
        """删除账户"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个账户")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        email = self.account_table.item(row, 1).text()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认")
        msg.setText(f"确定要删除账户 {email} 吗？")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        reply = msg.exec()
        if reply == QMessageBox.Yes:
            try:
                self.account_manager.delete_account(account_id)
                self.load_accounts()
                self.load_accounts_for_sending()
                self.status_bar.showMessage("账户删除成功")
            except Exception as e:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("错误")
                msg.setText(f"删除账户失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
        
    def test_account(self):
        """测试账户连接"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个账户")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        
        try:
            account = self.account_manager.get_account(account_id)
            if account:
                success, message = self.account_manager.test_smtp_connection(account_id)
                if success:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle("成功")
                    msg.setText("连接测试成功")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.exec()
                else:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Critical)
                    msg.setWindowTitle("失败")
                    msg.setText(f"连接测试失败: {message}")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("错误")
                msg.setText("未找到账户信息")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"连接测试出错: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
        
    def refresh_send_tab_data(self):
        """刷新发送标签页的数据 - 由RecipientManagerWidget处理"""
        pass
    
    def save_template_compose(self):
        """保存模板（邮件撰写标签页）"""
        try:
            subject = self.subject_input_compose.text().strip()
            content = self.body_input.toPlainText().strip()
            
            if not subject or not content:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("警告")
                msg.setText("主题和正文不能为空")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
                return
            
            # 获取模板名称
            template_name, ok = QInputDialog.getText(
                self, "保存模板", "请输入模板名称:"
            )
            
            if not ok or not template_name.strip():
                return
            
            template_name = template_name.strip()
            
            # 检查模板名称是否已存在
            existing_templates = self.template_manager.list_templates()
            if any(t['name'] == template_name for t in existing_templates):
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("确认覆盖")
                msg.setText(f"模板 '{template_name}' 已存在，是否覆盖？")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                reply = msg.exec()
                if reply != QMessageBox.Yes:
                    return
            
            # 保存模板
            success = self.template_manager.add_template(
                template_name, subject, content
            )
            
            if success:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("成功")
                msg.setText(f"模板 '{template_name}' 保存成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("失败")
                msg.setText("模板保存失败")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"保存模板失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
    
    def load_template_compose(self):
        """加载模板（邮件撰写标签页）"""
        try:
            # 获取所有模板
            templates = self.template_manager.list_templates()
            if not templates:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("提示")
                msg.setText("当前没有可用的模板")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
                return
            
            # 使用自定义对话框选择模板
            template_names = [template['name'] for template in templates]
            dialog = TemplateSelectDialog(template_names, self)
            
            if dialog.exec() == QDialog.Accepted:
                template_name = dialog.get_selected_template()
                if template_name:
                    template = self.template_manager.get_template_by_name(template_name)
                    if template:
                        self.subject_input_compose.setText(template.get('subject', ''))
                        self.body_input.setPlainText(template.get('content', ''))
                    else:
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Critical)
                        msg.setWindowTitle("错误")
                        msg.setText("模板加载失败")
                        msg.setStyleSheet(MODERN_FLAT_STYLE)
                        msg.exec()
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"加载模板失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
    
        
    # 邮件撰写相关方法
    def select_attachment(self):
        """选择附件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择附件", "", "所有文件 (*.*)")
        if file_path:
            self.attachment_input.setText(file_path)
            
    # load_template方法已在文件后面完整实现
        
    # 邮件发送相关方法
    def load_accounts_for_sending(self):
        """加载发送账户列表"""
        try:
            accounts = self.account_manager.list_accounts()
            self.account_combo.clear()
            for account in accounts:
                self.account_combo.addItem(f"{account['alias']} ({account['email']})", account['id'])
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"加载账户失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            
    # 发送标签页的收件人管理功能已移至RecipientManagerWidget
        
    # 邮件发送相关功能已迁移到EmailSender类
    
    def load_accounts_for_sending(self):
        """加载发送账户列表 - 已废弃，使用EmailSender组件"""
        pass
        
    def load_recipients_for_sending(self):
        """加载发送收件人列表 - 已废弃，使用EmailSender组件"""
        pass
        
    def select_all_recipients(self):
        """全选收件人 - 已废弃，使用EmailSender组件"""
        pass
        
    def deselect_all_recipients(self):
        """取消全选收件人 - 已废弃，使用EmailSender组件"""
        pass
        
    def select_group_recipients(self):
        """按组选择收件人 - 已废弃，使用EmailSender组件"""
        pass
        
    def add_manual_recipient(self):
        """手动添加收件人 - 已废弃，使用EmailSender组件"""
        pass
        
    def send_emails(self):
        """发送邮件 - 已废弃，使用EmailSender组件"""
        pass
    
    def closeEvent(self, event):
        """主窗口关闭事件"""
        # 清理进度对话框（如果存在）
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            try:
                self.progress_dialog.close()
            except:
                pass
            finally:
                self.progress_dialog = None
        event.accept()
        
    # AI助手相关方法
    def quick_ai_action(self, function_name):
        """快捷 AI 操作：打开侧边栏并切换到对应功能"""
        # 如果侧边栏没开启，先开启它
        if not self.ai_toggle_btn.isChecked():
            self.ai_toggle_btn.setChecked(True)
            self.toggle_ai_sidebar()
            
        # 切换侧边栏功能
        if hasattr(self, 'ai_sidebar'):
            self.ai_sidebar.function_combo.setCurrentText(function_name)
            # 自动触发一次“获取内容”逻辑（通过触发on_function_changed）
            self.ai_sidebar.on_function_changed(function_name)
            
    def open_ai_settings(self):
        """打开AI设置"""
        dialog = AISettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.status_bar.showMessage("AI设置已保存")
        
    def use_ai_template(self):
        """使用AI模板"""
        # 这里可以实现一些预设的AI提示词模板
        templates = {
            "营销邮件": "请帮我写一封营销邮件，推广产品 {{product_name}} 给潜在客户，突出产品的优势和特价活动。",
            "通知邮件": "请帮我写一封通知邮件，告知团队成员关于 {{event_name}} 的安排，包括时间、地点和注意事项。",
            "感谢邮件": "请帮我写一封感谢邮件，感谢 {{recipient_name}} 的支持与合作，表达对未来的期待。"
        }
        
        # 创建模板选择对话框
        template_names = list(templates.keys())
        dialog = TemplateSelectDialog(template_names, self)
        
        if dialog.exec() == QDialog.Accepted:
            item = dialog.get_selected_template()
            if item:
                # 将选中的模板插入到AI提示词输入框
                if hasattr(self, 'ai_prompt_input'):
                    self.ai_prompt_input.setPlainText(templates[item])
                    self.status_bar.showMessage(f"已选择模板: {item}")
                else:
                    # 如果没有专门的AI提示词输入框，就插入到内容输入框
                    self.content_input.setPlainText(templates[item])
                    self.status_bar.showMessage(f"已选择模板: {item}，请在AI生成时使用")
        
    def generate_mail(self):
        """生成邮件"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        topic = self.topic_input.text()
        if not topic:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请输入邮件主题")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        tone_map = {"正式": "formal", "随意": "casual", "友好": "friendly", "专业": "professional"}
        tone = tone_map.get(self.tone_combo.currentText(), "formal")
        
        self.status_bar.showMessage("正在生成邮件...")
        content = self.ai_writer.generate_mail(topic, tone)
        self.ai_output.setPlainText(content)
        self.status_bar.showMessage("邮件生成完成")
        
    def adjust_tone(self):
        """调整语气"""
        # 确保AI功能已初始化
        if not self._ensure_ai_initialized():
            return
            
        content = self.ai_output.toPlainText()
        if not content:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先生成邮件内容或输入文本")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        tone_map = {"正式": "formal", "随意": "casual", "友好": "friendly", "专业": "professional"}
        target_tone = tone_map.get(self.tone_adjust_combo.currentText(), "formal")
        
        self.status_bar.showMessage("正在调整语气...")
        adjusted_content = self.ai_writer.adjust_tone(content, target_tone)
        self.ai_output.setPlainText(adjusted_content)
        self.status_bar.showMessage("语气调整完成")
        

        

        
    # 历史记录相关方法
    def load_history(self):
        """加载历史记录"""
        # 清空现有数据
        self.history_table.setRowCount(0)
        
        try:
            # 获取所有任务记录
            tasks = self.history_tracker.list_tasks()
            
            # 填充表格
            for task in tasks:
                row_position = self.history_table.rowCount()
                self.history_table.insertRow(row_position)
                
                # 添加任务数据
                self.history_table.setItem(row_position, 0, QTableWidgetItem(str(task['id'])))
                self.history_table.setItem(row_position, 1, QTableWidgetItem(task['subject']))
                self.history_table.setItem(row_position, 2, QTableWidgetItem(task['send_time'].strftime("%Y-%m-%d %H:%M:%S") if task['send_time'] else ""))
                self.history_table.setItem(row_position, 3, QTableWidgetItem(str(task['total'])))
                self.history_table.setItem(row_position, 4, QTableWidgetItem(str(task['success_count'])))
                self.history_table.setItem(row_position, 5, QTableWidgetItem(str(task['fail_count'])))
                self.history_table.setItem(row_position, 6, QTableWidgetItem(task['status']))
                
                # 设置任务ID作为UserRole数据，便于后续操作
                for column in range(7):
                    self.history_table.item(row_position, column).setData(Qt.UserRole, task['id'])
                    
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"加载历史记录失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
        
    def view_task_details(self):
        """查看任务详情"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个任务记录")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        row = selected_rows[0].row()
        task_id = self.history_table.item(row, 0).data(Qt.UserRole)
        
        # 获取任务详情
        try:
            # 显示任务详情对话框
            dialog = TaskDetailsDialog(task_id, self)
            dialog.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"获取任务详情失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
        
    def export_history(self):
        """导出历史记录"""
        try:
            # 让用户选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(self, "导出历史记录", "", "CSV文件 (*.csv)")
            if file_path:
                self.history_tracker.export_to_csv(file_path)
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("成功")
                msg.setText(f"历史记录已导出到: {file_path}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
                self.status_bar.showMessage("历史记录导出成功")
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"导出历史记录失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
        
    def delete_history(self):
        """删除历史记录"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("请先选择要删除的任务记录")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.exec()
            return
            
        # 获取所有选中的任务ID
        task_ids = []
        for model_index in selected_rows:
            row = model_index.row()
            task_id = self.history_table.item(row, 0).data(Qt.UserRole)
            task_ids.append(task_id)
        
        # 确认删除
        if len(task_ids) == 1:
            timestamp = self.history_table.item(selected_rows[0].row(), 6).text()
            message = f"确定要删除 {timestamp} 的任务记录吗？"
        else:
            message = f"确定要删除选中的 {len(task_ids)} 条任务记录吗？"
            
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认删除")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        reply = msg.exec()
        if reply == QMessageBox.Yes:
            try:
                # 批量删除所有选中的任务
                for task_id in task_ids:
                    self.history_tracker.delete_task(task_id)
                self.load_history()
                self.status_bar.showMessage(f"成功删除 {len(task_ids)} 条任务记录")
            except Exception as e:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("错误")
                msg.setText(f"删除任务记录失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
    
    def toggle_select_history(self):
        """切换全选/取消全选历史记录"""
        if self.history_table.selectionModel().hasSelection():
            # 如果有选中的行，则取消全选
            self.history_table.clearSelection()
            self.toggle_select_history_btn.setText("全选")
        else:
            # 如果没有选中的行，则全选
            self.history_table.selectAll()
            self.toggle_select_history_btn.setText("取消全选")
        
    def clear_all_history(self):
        """清除所有历史记录"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("确认清除")
        msg.setText("确定要清除所有历史记录吗？此操作不可恢复！")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        reply = msg.exec()
        if reply == QMessageBox.Yes:
            try:
                # 获取所有任务ID
                tasks = self.history_tracker.list_tasks()
                task_ids = [task['id'] for task in tasks]
                
                # 批量删除所有任务
                for task_id in task_ids:
                    self.history_tracker.delete_task(task_id)
                    
                self.load_history()
                self.status_bar.showMessage("所有历史记录已清除")
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("成功")
                msg.setText("所有历史记录已清除")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
            except Exception as e:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("错误")
                msg.setText(f"清除历史记录失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.exec()
        
    # 设置相关方法
    def get_settings(self):
        """获取设置配置"""
        if hasattr(self, 'settings_widget'):
            return self.settings_widget.get_settings()
        return {}


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())