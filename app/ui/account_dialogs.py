#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
账户管理对话框
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QSpinBox, QPushButton, 
                               QMessageBox, QCheckBox, QTextEdit)
from PySide6.QtCore import Qt
from core.account_manager import AccountManager
from ui.modern_styles import MODERN_FLAT_STYLE


class AddAccountDialog(QDialog):
    """添加账户对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("添加账户")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        self.email_input = QLineEdit()
        self.email_input.setProperty("class", "input-field")
        self.smtp_server_input = QLineEdit()
        self.smtp_server_input.setProperty("class", "input-field")
        self.port_input = QSpinBox()
        self.port_input.setProperty("class", "spin-box")
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(587)
        self.alias_input = QLineEdit()
        self.alias_input.setProperty("class", "input-field")
        self.password_input = QLineEdit()
        self.password_input.setProperty("class", "input-field")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.ssl_checkbox = QCheckBox("启用SSL")
        self.ssl_checkbox.setProperty("class", "checkbox")
        # 使用全局样式，避免重复设置样式表
        
        form_layout.addRow("邮箱地址:", self.email_input)
        form_layout.addRow("SMTP服务器:", self.smtp_server_input)
        form_layout.addRow("端口:", self.port_input)
        form_layout.addRow("备注名:", self.alias_input)
        form_layout.addRow("授权码:", self.password_input)
        form_layout.addRow("", self.ssl_checkbox)
        
        # 连接邮箱地址输入框的文本变化信号
        self.email_input.textChanged.connect(self.auto_fill_smtp_config)
        
        layout.addLayout(form_layout)
        
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
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.add_account)
        
    def test_connection(self):
        """测试连接"""
        email = self.email_input.text().strip()
        smtp_server = self.smtp_server_input.text().strip()
        port = self.port_input.value()
        password = self.password_input.text()
        use_ssl = self.ssl_checkbox.isChecked()
        
        if not email or not smtp_server or not password:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请填写必填字段")
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            success, message = self.account_manager.test_smtp_connection_with_params(
                smtp_server, port, email, password, use_ssl)
            if success:
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText("连接测试成功")
                msg.setIcon(QMessageBox.Information)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle("失败")
                msg.setText(f"连接测试失败: {message}")
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"连接测试出错: {str(e)}")
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def auto_fill_smtp_config(self, email):
        """根据邮箱地址自动填充SMTP配置"""
        if not email or "@" not in email:
            return
            
        # 获取SMTP配置
        smtp_config = self.account_manager._get_smtp_config(email)
        
        # 自动填充SMTP服务器和端口
        if smtp_config['smtp_server']:
            self.smtp_server_input.setText(smtp_config['smtp_server'])
        if smtp_config['port']:
            self.port_input.setValue(smtp_config['port'])
        # 根据端口号设置use_ssl复选框状态
        self.ssl_checkbox.setChecked(smtp_config['port'] == 465)
            
    def add_account(self):
        """添加账户"""
        email = self.email_input.text().strip()
        smtp_server = self.smtp_server_input.text().strip()
        port = self.port_input.value()
        alias = self.alias_input.text().strip()
        password = self.password_input.text()
        use_ssl = self.ssl_checkbox.isChecked()
        
        if not email or not smtp_server or not password:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请填写必填字段")
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            self.account_manager.add_account(
                email=email,
                auth_code=password,
                alias=alias,
                smtp_server=smtp_server,
                port=port,
                use_ssl=use_ssl
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("账户添加成功")
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"添加账户失败: {str(e)}")
            msg.setIcon(QMessageBox.Critical)
            msg.exec()


class EditAccountDialog(QDialog):
    """编辑账户对话框"""
    
    def __init__(self, account_id, parent=None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_manager = AccountManager()
        self.init_ui()
        self.load_account_data()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑账户")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        self.email_input = QLineEdit()
        self.email_input.setProperty("class", "input-field")
        self.smtp_server_input = QLineEdit()
        self.smtp_server_input.setProperty("class", "input-field")
        self.port_input = QSpinBox()
        self.port_input.setProperty("class", "spin-box")
        self.port_input.setRange(1, 65535)
        self.alias_input = QLineEdit()
        self.alias_input.setProperty("class", "input-field")
        self.password_input = QLineEdit()
        self.password_input.setProperty("class", "input-field")
        self.password_input.setPlaceholderText("留空表示不修改密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.ssl_checkbox = QCheckBox("启用SSL")
        self.ssl_checkbox.setProperty("class", "checkbox")
        
        form_layout.addRow("邮箱地址:", self.email_input)
        form_layout.addRow("SMTP服务器:", self.smtp_server_input)
        form_layout.addRow("端口:", self.port_input)
        form_layout.addRow("备注名:", self.alias_input)
        form_layout.addRow("授权码:", self.password_input)
        form_layout.addRow("", self.ssl_checkbox)
        
        # 连接邮箱地址输入框的文本变化信号
        self.email_input.textChanged.connect(self.auto_fill_smtp_config)
        
        layout.addLayout(form_layout)
        
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
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.update_account)
        
    def load_account_data(self):
        """加载账户数据"""
        try:
            account = self.account_manager.get_account(self.account_id)
            if account:
                self.email_input.setText(account['email'])
                self.smtp_server_input.setText(account['smtp_server'])
                self.port_input.setValue(account['port'])
                self.alias_input.setText(account['alias'])
                self.ssl_checkbox.setChecked(account['use_ssl'])
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载账户数据失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def test_connection(self):
        """测试连接"""
        email = self.email_input.text().strip()
        smtp_server = self.smtp_server_input.text().strip()
        port = self.port_input.value()
        password = self.password_input.text()
        use_ssl = self.ssl_checkbox.isChecked()
        
        # 如果密码为空，则使用原密码测试
        if not password:
            try:
                account = self.account_manager.get_account(self.account_id)
                if account:
                    password = account['auth_code']
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("错误")
                msg.setText(f"获取原密码失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                return
                
        if not email or not smtp_server or not password:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请填写必填字段")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            success, message = self.account_manager.test_smtp_connection_with_params(
                smtp_server, port, email, password, use_ssl)
            if success:
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText("连接测试成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle("失败")
                msg.setText(f"连接测试失败: {message}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"连接测试出错: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def auto_fill_smtp_config(self, email):
        """根据邮箱地址自动填充SMTP配置"""
        if not email or "@" not in email:
            return
            
        # 获取SMTP配置
        smtp_config = self.account_manager._get_smtp_config(email)
        
        # 自动填充SMTP服务器和端口
        if smtp_config['smtp_server']:
            self.smtp_server_input.setText(smtp_config['smtp_server'])
        if smtp_config['port']:
            self.port_input.setValue(smtp_config['port'])
            
    def update_account(self):
        """更新账户"""
        email = self.email_input.text().strip()
        smtp_server = self.smtp_server_input.text().strip()
        port = self.port_input.value()
        alias = self.alias_input.text().strip()
        password = self.password_input.text()
        use_ssl = self.ssl_checkbox.isChecked()
        
        if not email or not smtp_server:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请填写必填字段")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            # 准备更新数据
            update_kwargs = {
                'email': email,
                'smtp_server': smtp_server,
                'port': port,
                'alias': alias,
                'use_ssl': use_ssl
            }
            
            # 只有当密码不为空时才更新密码
            if password:
                update_kwargs['auth_code'] = password
                
            self.account_manager.update_account(self.account_id, **update_kwargs)
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("账户更新成功")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"更新账户失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()