"""
邮件发送管理模块
负责邮件发送相关的所有功能
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QComboBox, QLineEdit, QTextEdit, QLabel, QCheckBox,
                             QDialog, QRadioButton, QMessageBox, QFileDialog, QFormLayout,
                             QListWidget, QListWidgetItem, QGroupBox, QProgressDialog, QInputDialog)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont
import os
from datetime import datetime
from ui.modern_styles import MODERN_FLAT_STYLE


class EmailSender(QWidget):
    """邮件发送管理组件"""
    
    def __init__(self, account_manager, recipient_manager, template_manager, parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self.recipient_manager = recipient_manager
        self.template_manager = template_manager
        self.parent_window = parent
        
        # 邮件发送工作线程
        self.send_thread = None
        self.send_worker = None
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 账户选择区域
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("发送账户:"))
        self.account_combo = QComboBox()
        self.account_combo.setProperty("class", "combo-box")
        self.account_combo.setMinimumWidth(250)
        account_layout.addWidget(self.account_combo)
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # 收件人区域
        recipient_layout = QVBoxLayout()
        recipient_layout.setSpacing(8)
        recipient_layout.addWidget(QLabel("收件人:"))
        
        # 收件人操作按钮
        recipient_btn_layout = QHBoxLayout()
        recipient_btn_layout.setSpacing(8)
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setProperty("class", "secondary")
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.setProperty("class", "secondary")
        self.select_by_group_btn = QPushButton("按组选择")
        self.select_by_group_btn.setProperty("class", "secondary")
        self.add_manual_btn = QPushButton("手动添加")
        self.add_manual_btn.setProperty("class", "secondary")
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setProperty("class", "secondary")
        
        recipient_btn_layout.addWidget(self.select_all_btn)
        recipient_btn_layout.addWidget(self.deselect_all_btn)
        recipient_btn_layout.addWidget(self.select_by_group_btn)
        recipient_btn_layout.addWidget(self.add_manual_btn)
        recipient_btn_layout.addWidget(self.refresh_btn)
        recipient_btn_layout.addStretch()
        
        recipient_layout.addLayout(recipient_btn_layout)
        
        # 收件人表格
        self.recipient_table = QTableWidget()
        self.recipient_table.setProperty("class", "table")
        self.recipient_table.setColumnCount(4)
        self.recipient_table.setHorizontalHeaderLabels(["选择", "姓名", "邮箱", "分组"])
        self.recipient_table.setColumnWidth(0, 40) # 设置选择列宽度
        self.recipient_table.horizontalHeader().setStretchLastSection(True)
        self.recipient_table.setMinimumHeight(150) # 给表格一个最小高度
        self.recipient_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recipient_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        recipient_layout.addWidget(self.recipient_table)
        layout.addLayout(recipient_layout)
        
        # 邮件内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        content_layout.addWidget(QLabel("邮件内容:"))
        
        # 主题输入
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("主题:"))
        self.subject_input = QLineEdit()
        self.subject_input.setProperty("class", "input-field")
        subject_layout.addWidget(self.subject_input)
        content_layout.addLayout(subject_layout)
        
        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.setSpacing(8)
        template_layout.addWidget(QLabel("模板:"))
        self.template_combo = QComboBox()
        self.template_combo.setProperty("class", "combo-box")
        self.template_combo.setMinimumWidth(150)
        template_layout.addWidget(self.template_combo)
        
        self.load_template_btn = QPushButton("加载模板")
        self.load_template_btn.setProperty("class", "secondary")
        template_layout.addWidget(self.load_template_btn)
        
        self.refresh_template_btn = QPushButton("刷新模板")
        self.refresh_template_btn.setProperty("class", "secondary")
        template_layout.addWidget(self.refresh_template_btn)
        
        # 添加 AI 快捷按钮
        self.translate_btn = QPushButton("🌐 AI 翻译")
        self.translate_btn.setProperty("class", "ai-btn")
        self.summary_btn = QPushButton("📝 AI 摘要")
        self.summary_btn.setProperty("class", "ai-btn")
        template_layout.addWidget(self.translate_btn)
        template_layout.addWidget(self.summary_btn)
        
        template_layout.addStretch()
        content_layout.addLayout(template_layout)
        
        # 正文输入
        self.content_edit = QTextEdit()
        self.content_edit.setProperty("class", "text-edit")
        self.content_edit.setPlaceholderText("在此输入邮件正文内容...")
        self.content_edit.setMinimumHeight(150)
        content_layout.addWidget(self.content_edit)
        
        # 附件区域
        attachment_layout = QHBoxLayout()
        attachment_layout.addWidget(QLabel("附件:"))
        self.attachment_input = QLineEdit()
        self.attachment_input.setReadOnly(True)
        self.attachment_input.setProperty("class", "input-field")
        self.attachment_input.setPlaceholderText("尚未选择附件...")
        attachment_layout.addWidget(self.attachment_input)
        
        self.select_attachment_btn = QPushButton("选择附件")
        self.select_attachment_btn.setProperty("class", "secondary")
        attachment_layout.addWidget(self.select_attachment_btn)
        content_layout.addLayout(attachment_layout)
        
        layout.addLayout(content_layout)
        
        # 底部操作按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.send_btn = QPushButton("发送邮件")
        self.send_btn.setProperty("class", "primary")
        self.send_btn.setFixedSize(120, 40)
        bottom_layout.addWidget(self.send_btn)
        layout.addLayout(bottom_layout)
        
        # 连接信号
        self.select_all_btn.clicked.connect(self.select_all_recipients)
        self.deselect_all_btn.clicked.connect(self.deselect_all_recipients)
        self.select_by_group_btn.clicked.connect(self.select_group_recipients)
        self.add_manual_btn.clicked.connect(self.add_manual_recipient)
        self.refresh_btn.clicked.connect(self.load_recipients)
        self.load_template_btn.clicked.connect(self.load_template)
        self.refresh_template_btn.clicked.connect(self.refresh_templates)
        self.select_attachment_btn.clicked.connect(self.select_attachment)
        self.send_btn.clicked.connect(self.send_emails)
        
        # 连接 AI 快捷按钮
        self.translate_btn.clicked.connect(lambda: self.quick_ai_action("邮件翻译"))
        self.summary_btn.clicked.connect(lambda: self.quick_ai_action("邮件摘要"))
        
        # 加载数据
        self.load_accounts()
        self.load_recipients()
        self.load_templates()
    
    def quick_ai_action(self, function_name):
        """调用主窗口的 AI 快捷操作"""
        if self.parent_window and hasattr(self.parent_window, 'quick_ai_action'):
            self.parent_window.quick_ai_action(function_name)

    def load_accounts(self):
        """加载账户列表"""
        try:
            # 优化：先获取数据，再一次性更新UI
            accounts = self.account_manager.list_accounts()
            
            self.account_combo.clear()
            # 预先生成所有账户项，然后一次性添加
            for account in accounts:
                self.account_combo.addItem(f"{account['alias']} ({account['email']})", account['id'])
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载账户失败: {str(e)}")
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def load_recipients(self):
        """加载收件人列表"""
        try:
            recipients = self.recipient_manager.list_recipients()
            self.recipient_table.setRowCount(len(recipients))
            
            for row, recipient in enumerate(recipients):
                # 第一列：复选框
                checkbox_item = QTableWidgetItem()
                checkbox_item.setCheckState(Qt.Unchecked)
                self.recipient_table.setItem(row, 0, checkbox_item)
                
                # 其他列
                self.recipient_table.setItem(row, 1, QTableWidgetItem(recipient['name']))
                self.recipient_table.setItem(row, 2, QTableWidgetItem(recipient['email']))
                self.recipient_table.setItem(row, 3, QTableWidgetItem(recipient['group_name'] or ''))
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载收件人失败: {str(e)}")
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def select_all_recipients(self):
        """全选收件人"""
        for row in range(self.recipient_table.rowCount()):
            item = self.recipient_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
    
    def deselect_all_recipients(self):
        """取消全选收件人"""
        for row in range(self.recipient_table.rowCount()):
            item = self.recipient_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
    
    def select_group_recipients(self):
        """按组选择收件人"""
        try:
            # 获取所有分组
            groups = self.recipient_manager.get_groups()
            if not groups:
                msg = QMessageBox(self)
                msg.setWindowTitle("提示")
                msg.setText("当前没有可用的分组")
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                return
            
            # 使用下拉框选择分组
            group_name, ok = QInputDialog.getItem(
                self, "按组选择", "请选择分组:", groups, 0, False
            )
            
            if ok and group_name:
                # 使用下拉框选择操作类型
                operations = ["选择该分组", "取消选择该分组"]
                operation, ok_op = QInputDialog.getItem(
                    self, "选择操作", "请选择操作类型:", operations, 0, False
                )
                
                if ok_op and operation:
                    is_select = operation == "选择该分组"
                    
                    for row in range(self.recipient_table.rowCount()):
                        group_item = self.recipient_table.item(row, 3)
                        if group_item and group_item.text() == group_name:
                            checkbox_item = self.recipient_table.item(row, 0)
                            if checkbox_item:
                                checkbox_item.setCheckState(Qt.Checked if is_select else Qt.Unchecked)
                    
                    msg = QMessageBox(self)
                    msg.setWindowTitle("成功")
                    msg.setText(f"已{'选择' if is_select else '取消选择'}分组 '{group_name}' 的所有收件人")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Information)
                    msg.exec()
            
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"按组选择失败: {str(e)}")
            msg_box.setStyleSheet(MODERN_FLAT_STYLE)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.exec()
    
    def add_manual_recipient(self):
        """手动添加收件人"""
        try:
            # 使用输入对话框获取收件人信息
            name, ok_name = QInputDialog.getText(self, "添加收件人", "请输入姓名:")
            if not ok_name or not name.strip():
                return
                
            email, ok_email = QInputDialog.getText(self, "添加收件人", "请输入邮箱:")
            if not ok_email or not email.strip():
                return
                
            group, ok_group = QInputDialog.getText(self, "添加收件人", "请输入分组(可选):")
            
            try:
                self.recipient_manager.add_recipient(
                    name=name.strip(),
                    email=email.strip(),
                    group_name=group.strip() if ok_group and group.strip() else None
                )
                
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText("收件人添加成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                self.load_recipients()
                
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("错误")
                msg.setText(f"添加失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"操作失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def load_template(self):
        """加载模板"""
        try:
            template_name = self.template_combo.currentText()
            if not template_name:
                return
            
            template = self.template_manager.get_template_by_name(template_name)
            if template:
                self.subject_input.setText(template.get('subject', ''))
                self.content_edit.setPlainText(template.get('content', ''))
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载模板失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def load_templates(self):
        """加载模板列表"""
        try:
            # 优化：先获取数据，再一次性更新UI
            templates = self.template_manager.list_templates()
            template_names = [template['name'] for template in templates]
            
            self.template_combo.clear()
            # 一次性添加所有模板，减少UI更新次数
            self.template_combo.addItems(template_names)
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载模板列表失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def refresh_templates(self):
        """刷新模板列表"""
        self.load_templates()
        msg = QMessageBox(self)
        msg.setWindowTitle("提示")
        msg.setText("模板列表已刷新")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setIcon(QMessageBox.Information)
        msg.exec()
    
    def select_attachment(self):
        """选择附件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择附件", "", "所有文件 (*.*)")
        if file_path:
            self.attachment_input.setText(file_path)
    
    def send_emails(self):
        """发送邮件"""
        try:
            # 获取选中的收件人
            selected_recipients = []
            for row in range(self.recipient_table.rowCount()):
                checkbox_item = self.recipient_table.item(row, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                    name_item = self.recipient_table.item(row, 1)
                    email_item = self.recipient_table.item(row, 2)
                    if name_item and email_item:
                        selected_recipients.append({
                            'name': name_item.text(),
                            'email': email_item.text()
                        })
            
            if not selected_recipients:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请至少选择一个收件人")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 获取邮件内容
            account_id = self.account_combo.currentData()
            subject = self.subject_input.text().strip()
            content = self.content_edit.toPlainText().strip()
            attachment_path = self.attachment_input.text().strip()
            
            if not account_id:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请选择发送账户")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            if not subject or not content:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("主题和正文不能为空")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 确认发送
            msg = QMessageBox(self)
            msg.setWindowTitle("确认发送")
            msg.setText(f"将向 {len(selected_recipients)} 个收件人发送邮件，是否继续？")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Question)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            
            reply = msg.exec()
            
            if reply != QMessageBox.Yes:
                return
            
            # 获取发送账户信息
            account = self.account_manager.get_account(account_id)
            if not account:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("发送账户不存在")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 创建邮件发送任务
            self.start_sending_emails(account, selected_recipients, subject, content, attachment_path)
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"发送失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def start_sending_emails(self, account, recipients, subject, content, attachment_path):
        """开始发送邮件"""
        try:
            # 禁用发送按钮
            self.send_btn.setEnabled(False)
            
            # 重置取消标志
            self._cancelled = False
            
            # 创建进度对话框
            self.progress_dialog = QProgressDialog("正在准备发送邮件...", "取消", 0, len(recipients), self)
            self.progress_dialog.setWindowTitle("邮件发送进度")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)  # 立即显示进度条
            self.progress_dialog.setStyleSheet(MODERN_FLAT_STYLE)
            self.progress_dialog.show()
            
            # 创建工作线程
            from core.mail_sender import MailSender
            from core.history_tracker import HistoryTracker
            
            self.send_thread = QThread()
            self.send_worker = EmailSendWorker(
                account, recipients, subject, content, 
                attachment_path, MailSender(), HistoryTracker()
            )
            self.send_worker.moveToThread(self.send_thread)
            
            # 连接信号
            self.send_thread.started.connect(self.send_worker.send_emails)
            self.send_worker.progress.connect(self.update_progress)
            self.send_worker.finished.connect(self.on_send_finished)
            self.send_worker.error.connect(self.on_send_error)
            self.progress_dialog.canceled.connect(self.cancel_sending)
            
            # 启动线程
            self.send_thread.start()
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"启动发送失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            self.send_btn.setEnabled(True)
            if self.progress_dialog:
                self.progress_dialog.close()
    
    def update_progress(self, current, total, message):
        """更新进度"""
        if self.progress_dialog:
            self.progress_dialog.setValue(current)
            self.progress_dialog.setMaximum(total)
            # 显示详细的进度信息
            progress_text = f"{message}\n进度: {current}/{total} ({int(current/total*100)}%)"
            self.progress_dialog.setLabelText(progress_text)
    
    def on_send_finished(self, success_count, failed_count, task_id):
        """发送完成处理"""
        # 检查是否已经取消发送，避免重复显示消息
        if hasattr(self, '_cancelled') and self._cancelled:
            # 如果已经取消，不显示任何完成消息
            self.cleanup_send_thread()
            self.send_btn.setEnabled(True)
            return
            
        self.cleanup_send_thread()
        self.send_btn.setEnabled(True)
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        # 验证发送结果
        total_sent = success_count + failed_count
        if total_sent == 0:
            # 如果一封邮件都没有发送成功，显示错误
            msg = QMessageBox(self)
            msg.setWindowTitle("发送失败")
            msg.setText("邮件发送失败，请检查网络连接和账户配置")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
        elif failed_count > 0:
            # 有部分失败
            message = f"邮件发送完成！\n成功: {success_count} 封\n失败: {failed_count} 封"
            msg = QMessageBox(self)
            msg.setWindowTitle("发送完成")
            msg.setText(message)
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
        else:
            # 全部成功
            message = f"邮件发送完成！\n成功发送: {success_count} 封邮件"
            msg = QMessageBox(self)
            msg.setWindowTitle("发送成功")
            msg.setText(message)
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
        
        # 清空选择
        self.deselect_all_recipients()
        
        # 刷新历史记录（如果父窗口有历史管理器）
        if hasattr(self.parent_window, 'load_history'):
            self.parent_window.load_history()
    
    def on_send_error(self, error_message):
        """发送错误处理"""
        self.cleanup_send_thread()
        self.send_btn.setEnabled(True)
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("发送错误")
        msg.setText(f"邮件发送失败: {error_message}")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setIcon(QMessageBox.Critical)
        msg.exec()
    
    def cancel_sending(self):
        """取消发送"""
        # 检查是否真的需要取消（避免误触发）
        if not self.send_worker or not self.send_thread or not self.send_thread.isRunning():
            return
            
        # 设置取消标志，防止on_send_finished再次显示消息
        self._cancelled = True
        
        if self.send_worker:
            self.send_worker.stop()
            # 等待一小段时间，让线程有机会检查停止标志
            self.send_thread.wait(100)
            
        self.cleanup_send_thread()
        self.send_btn.setEnabled(True)
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("取消")
        msg.setText("邮件发送已取消")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setIcon(QMessageBox.Information)
        msg.exec()
    
    def cleanup_send_thread(self):
        """清理发送线程"""
        if self.send_thread and self.send_thread.isRunning():
            self.send_thread.quit()
            self.send_thread.wait()
        
        if self.send_thread:
            self.send_thread.deleteLater()
        if self.send_worker:
            self.send_worker.deleteLater()
        
        self.send_thread = None
        self.send_worker = None


class EmailSendWorker(QObject):
    """邮件发送工作线程"""
    
    progress = Signal(int, int, str)  # 当前进度，总数，消息
    finished = Signal(int, int, str)  # 成功数，失败数，任务ID
    error = Signal(str)  # 错误消息
    
    def __init__(self, account, recipients, subject, content, attachment_path, mail_sender, history_manager):
        super().__init__()
        self.account = account
        self.recipients = recipients
        self.subject = subject
        self.content = content
        self.attachment_path = attachment_path
        self.mail_sender = mail_sender
        self.history_manager = history_manager
        self._stop_flag = False
        
        # 获取配置参数
        from core.config_manager import ConfigManager
        config = ConfigManager.get_config()
        self.send_interval = config.get('send_interval', 1)  # 发送间隔（秒）
        self.send_retry_count = config.get('send_retry_count', 1)  # 重试次数
    
    def stop(self):
        """停止发送"""
        self._stop_flag = True
    
    def send_emails(self):
        """发送邮件"""
        try:
            success_count = 0
            failed_count = 0
            total_count = len(self.recipients)
            
            # 创建发送任务记录
            task_id = self.history_manager.add_task(
                account_id=self.account['id'],
                subject=self.subject,
                content=self.content,
                total=total_count * self.send_retry_count,  # 总发送次数 = 收件人数 × 重试次数
                success_count=0,
                fail_count=0
            )
            
            # 发送邮件（带重试机制）
            for send_round in range(self.send_retry_count):
                round_success_count = 0
                round_fail_count = 0
                
                # 更新进度显示当前发送轮次
                self.progress.emit(0, total_count * self.send_retry_count, f"开始第 {send_round + 1}/{self.send_retry_count} 轮发送")
                
                for i, recipient in enumerate(self.recipients):
                    if self._stop_flag:
                        # 如果已停止，直接返回，不发送finished信号
                        # 更新任务状态为取消
                        self.history_manager.update_task_status(int(task_id), "cancelled", success_count, failed_count)
                        return
                    
                    try:
                        # 计算当前总进度
                        current_total = send_round * total_count + i + 1
                        
                        # 更新进度
                        self.progress.emit(current_total, total_count * self.send_retry_count, 
                                         f"第 {send_round + 1}/{self.send_retry_count} 轮 - 正在发送给 {recipient['email']}...")
                        
                        # 发送邮件
                        self.mail_sender.send_email(
                            account=self.account,
                            to_email=recipient['email'],
                            to_name=recipient['name'],
                            subject=self.subject,
                            content=self.content,
                            attachment_path=self.attachment_path if self.attachment_path else None
                        )
                        
                        # 记录成功
                        success_count += 1
                        round_success_count += 1
                        self.history_manager.add_task_detail(task_id, recipient['email'], True, f"第{send_round + 1}轮发送成功")
                        
                    except Exception as e:
                        # 记录失败
                        failed_count += 1
                        round_fail_count += 1
                        error_msg = str(e)
                        self.history_manager.add_task_detail(task_id, recipient['email'], False, f"第{send_round + 1}轮发送失败: {error_msg}")
                        
                        # 继续发送给其他人
                        continue
                    
                    # 发送间隔（除了最后一个收件人）
                    if i < len(self.recipients) - 1:
                        import time
                        time.sleep(self.send_interval)
                
                # 轮次间休息（除了最后一轮）
                if send_round < self.send_retry_count - 1:
                    import time
                    time.sleep(self.send_interval)
            
            # 只有在没有取消的情况下才更新任务状态和发送完成信号
            if not self._stop_flag:
                # 更新任务状态
                self.history_manager.update_task_status(int(task_id), "completed", success_count, failed_count)
                # 发送完成信号
                self.finished.emit(success_count, failed_count, str(task_id))
            else:
                # 如果取消，任务状态已经在取消时更新过了
                pass
            
        except Exception as e:
            self.error.emit(str(e))