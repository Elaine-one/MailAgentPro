#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
收件人管理对话框
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox, 
                               QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
                               QGroupBox)
from PySide6.QtCore import Qt
import pandas as pd
import os
from core.recipient_manager import RecipientManager
from ui.modern_styles import MODERN_FLAT_STYLE
from ui.wheel_combo import WheelComboBox


class ImportRecipientsDialog(QDialog):
    """导入收件人对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recipient_manager = RecipientManager()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("导入收件人")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("CSV文件:"))
        self.file_path_input = QLineEdit()
        self.file_path_input.setProperty("class", "input-field")
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setProperty("class", "secondary")
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)
        
        # 预览区域
        layout.addWidget(QLabel("数据预览:"))
        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setProperty("class", "table")
        self.preview_table.setHorizontalHeaderLabels(["姓名", "邮箱", "分组", "变量"])
        layout.addWidget(self.preview_table)
        
        # 分组设置
        group_box = QGroupBox("分组设置")
        group_box.setProperty("class", "group-box")
        group_layout = QHBoxLayout(group_box)
        group_layout.addWidget(QLabel("默认分组:"))
        self.group_combo = WheelComboBox()
        self.group_combo.setProperty("class", "combo-box")
        self.group_combo.setMaxVisibleItems(10)
        self.group_combo.setEditable(True)  # 允许手动输入新分组
        self.group_combo.addItem("无分组", "")  # 添加无分组选项
        
        # 加载现有分组
        try:
            groups = self.recipient_manager.get_groups()
            for group in groups:
                self.group_combo.addItem(group, group)
        except Exception:
            pass  # 如果加载分组失败，继续使用空列表
            
        group_layout.addWidget(self.group_combo)
        layout.addWidget(group_box)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setProperty("class", "secondary")
        self.import_btn = QPushButton("导入")
        self.import_btn.setProperty("class", "primary")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        
        btn_layout.addWidget(self.preview_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.browse_btn.clicked.connect(self.browse_file)
        self.preview_btn.clicked.connect(self.preview_data)
        self.import_btn.clicked.connect(self.import_recipients)
        self.cancel_btn.clicked.connect(self.reject)
        
    def browse_file(self):
        """浏览文件"""
        dialog = QFileDialog(self)
        dialog.setWindowTitle("选择CSV文件")
        dialog.setNameFilter("CSV文件 (*.csv)")
        dialog.setStyleSheet(MODERN_FLAT_STYLE)
        if dialog.exec():
            self.file_path_input.setText(dialog.selectedFiles()[0])
            
    def preview_data(self):
        """预览数据"""
        file_path = self.file_path_input.text().strip()
        if not file_path:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请选择CSV文件")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        if not os.path.exists(file_path):
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText("文件不存在")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            return
            
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 检查必要列
            required_columns = ['name', 'email']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText(f"缺少必要列: {', '.join(missing_columns)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
                
            # 显示预览
            self.preview_table.setRowCount(len(df))
            self.preview_table.setColumnCount(4)
            self.preview_table.setHorizontalHeaderLabels(["姓名", "邮箱", "分组", "变量"])
            
            for row, (_, record) in enumerate(df.iterrows()):
                self.preview_table.setItem(row, 0, QTableWidgetItem(str(record.get('name', ''))))
                self.preview_table.setItem(row, 1, QTableWidgetItem(str(record.get('email', ''))))
                self.preview_table.setItem(row, 2, QTableWidgetItem(str(record.get('group', ''))))
                self.preview_table.setItem(row, 3, QTableWidgetItem(str(record.get('variables', ''))))
                
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"读取文件失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def import_recipients(self):
        """导入收件人"""
        file_path = self.file_path_input.text().strip()
        if not file_path:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请选择CSV文件")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        if not os.path.exists(file_path):
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText("文件不存在")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            return
            
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 检查必要列
            required_columns = ['name', 'email']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText(f"缺少必要列: {', '.join(missing_columns)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
                
            # 导入数据
            default_group = self.group_combo.currentText().strip()
            imported_count = 0
            
            for _, record in df.iterrows():
                name = str(record.get('name', ''))
                email = str(record.get('email', ''))
                csv_group = str(record.get('group', ''))
                variables = str(record.get('variables', ''))
                
                # 确定最终分组：优先使用CSV中的分组，如果没有则使用默认分组
                group_name = csv_group if csv_group else default_group
                
                if name and email:
                    self.recipient_manager.add_recipient(
                        name=name,
                        email=email,
                        group_name=group_name if group_name else None,
                        variables=variables if variables else None
                    )
                    imported_count += 1
                    
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText(f"成功导入 {imported_count} 个收件人")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"导入失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()


class AddRecipientDialog(QDialog):
    """添加收件人对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recipient_manager = RecipientManager()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("添加收件人")
        self.setFixedSize(400, 300)
        self.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setProperty("class", "input-field")
        self.email_input = QLineEdit()
        self.email_input.setProperty("class", "input-field")
        self.group_input = QLineEdit()
        self.group_input.setProperty("class", "input-field")
        self.variables_input = QTextEdit()
        self.variables_input.setProperty("class", "input-field")
        self.variables_input.setMaximumHeight(80)
        self.variables_input.setPlaceholderText("格式: key1=value1,key2=value2")
        
        form_layout.addRow("姓名:", self.name_input)
        form_layout.addRow("邮箱:", self.email_input)
        form_layout.addRow("分组:", self.group_input)
        form_layout.addRow("变量:", self.variables_input)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "primary")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.ok_btn.clicked.connect(self.add_recipient)
        self.cancel_btn.clicked.connect(self.reject)
        
    def add_recipient(self):
        """添加收件人"""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        group_name = self.group_input.text().strip()
        variables_text = self.variables_input.toPlainText().strip()
        
        if not name or not email:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("姓名和邮箱为必填项")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            # 解析变量
            variables = None
            if variables_text:
                try:
                    variables_dict = {}
                    for pair in variables_text.split(','):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            variables_dict[key.strip()] = value.strip()
                    variables = str(variables_dict) if variables_dict else None
                except Exception:
                    msg = QMessageBox(self)
                    msg.setWindowTitle("警告")
                    msg.setText("变量格式错误，请使用 key=value 格式，多个变量用逗号分隔")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Warning)
                    msg.exec()
                    return
                    
            self.recipient_manager.add_recipient(
                name=name,
                email=email,
                group_name=group_name if group_name else None,
                variables=variables
            )
            
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("收件人添加成功")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"添加收件人失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()


class EditRecipientDialog(QDialog):
    """编辑收件人对话框"""
    
    def __init__(self, recipient_id, parent=None):
        super().__init__(parent)
        self.recipient_id = recipient_id
        self.recipient_manager = RecipientManager()
        self.init_ui()
        self.load_recipient_data()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("编辑收件人")
        self.setFixedSize(400, 300)
        self.setStyleSheet(MODERN_FLAT_STYLE)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setProperty("class", "input-field")
        self.email_input = QLineEdit()
        self.email_input.setProperty("class", "input-field")
        self.group_input = QLineEdit()
        self.group_input.setProperty("class", "input-field")
        self.variables_input = QTextEdit()
        self.variables_input.setProperty("class", "input-field")
        self.variables_input.setMaximumHeight(80)
        self.variables_input.setPlaceholderText("格式: key1=value1,key2=value2")
        
        form_layout.addRow("姓名:", self.name_input)
        form_layout.addRow("邮箱:", self.email_input)
        form_layout.addRow("分组:", self.group_input)
        form_layout.addRow("变量:", self.variables_input)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "primary")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号槽
        self.ok_btn.clicked.connect(self.update_recipient)
        self.cancel_btn.clicked.connect(self.reject)
        
    def load_recipient_data(self):
        """加载收件人数据"""
        try:
            recipient = self.recipient_manager.get_recipient(self.recipient_id)
            if recipient:
                self.name_input.setText(recipient['name'])
                self.email_input.setText(recipient['email'])
                self.group_input.setText(recipient['group_name'] or '')
                self.variables_input.setPlainText(recipient['variables'] or '')
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载收件人数据失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def update_recipient(self):
        """更新收件人"""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        group_name = self.group_input.text().strip()
        variables_text = self.variables_input.toPlainText().strip()
        
        if not name or not email:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("姓名和邮箱为必填项")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        try:
            # 解析变量
            variables = None
            if variables_text:
                try:
                    variables_dict = {}
                    for pair in variables_text.split(','):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            variables_dict[key.strip()] = value.strip()
                    variables = str(variables_dict) if variables_dict else None
                except Exception:
                    msg = QMessageBox(self)
                    msg.setWindowTitle("警告")
                    msg.setText("变量格式错误，请使用 key=value 格式，多个变量用逗号分隔")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Warning)
                    msg.exec()
                    return
                    
            self.recipient_manager.update_recipient(
                recipient_id=self.recipient_id,
                name=name,
                email=email,
                group_name=group_name if group_name else None,
                variables=variables
            )
            
            msg = QMessageBox(self)
            msg.setWindowTitle("成功")
            msg.setText("收件人更新成功")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            self.accept()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"更新收件人失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()