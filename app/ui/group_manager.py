#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分组管理模块
负责处理所有与分组相关的UI操作和业务逻辑
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTableWidget, QTableWidgetItem, QListWidget, 
                               QListWidgetItem, QSplitter, QMessageBox, QInputDialog,
                               QAbstractItemView, QGroupBox, QCheckBox, QWidget)
from PySide6.QtCore import Qt
from ui.modern_styles import MODERN_FLAT_STYLE


class GroupManager:
    """分组管理器类"""
    
    def __init__(self, recipient_manager, parent_window):
        """
        初始化分组管理器
        
        Args:
            recipient_manager: 收件人管理器实例
            parent_window: 父窗口实例
        """
        self.recipient_manager = recipient_manager
        self.parent_window = parent_window
    
    def create_group_management_dialog(self):
        """创建分组管理对话框"""
        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle("分组管理")
        dialog.setModal(True)
        dialog.resize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：分组列表
        left_widget = self._create_group_list_widget(dialog)
        
        # 右侧：组成员表格
        right_widget = self._create_group_members_widget(dialog)
        
        # 将左右部件添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # 底部按钮区域
        bottom_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.setProperty("class", "secondary")
        close_btn.clicked.connect(dialog.close)
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)
        
        # 加载初始数据
        self._load_groups(dialog)
        
        return dialog
    
    def _create_group_list_widget(self, dialog):
        """创建分组列表部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 分组列表标题
        layout.addWidget(QLabel("分组列表"))
        
        # 分组列表
        group_list_widget = QListWidget()
        group_list_widget.setProperty("class", "list")
        layout.addWidget(group_list_widget)
        
        # 分组操作按钮
        btn_layout = QHBoxLayout()
        add_group_btn = QPushButton("添加分组")
        add_group_btn.setProperty("class", "secondary")
        rename_group_btn = QPushButton("重命名")
        rename_group_btn.setProperty("class", "secondary")
        delete_group_btn = QPushButton("删除")
        delete_group_btn.setProperty("class", "secondary")
        
        # 连接信号
        add_group_btn.clicked.connect(lambda: self.add_group(dialog))
        rename_group_btn.clicked.connect(lambda: self.rename_group(dialog))
        delete_group_btn.clicked.connect(lambda: self.delete_group(dialog))
        
        btn_layout.addWidget(add_group_btn)
        btn_layout.addWidget(rename_group_btn)
        btn_layout.addWidget(delete_group_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 存储引用
        dialog.group_list_widget = group_list_widget
        
        # 连接选择变化信号
        group_list_widget.itemSelectionChanged.connect(
            lambda: self.on_group_selection_changed(dialog)
        )
        
        return widget
    
    def _create_group_members_widget(self, dialog):
        """创建组成员管理部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 组成员标签
        group_members_label = QLabel("组成员")
        layout.addWidget(group_members_label)
        
        # 组成员表格
        group_members_table = QTableWidget(0, 4)
        group_members_table.setProperty("class", "table")
        group_members_table.setHorizontalHeaderLabels(["", "ID", "姓名", "邮箱"])
        group_members_table.setSelectionBehavior(QTableWidget.SelectRows)
        group_members_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 设置第一列为复选框
        group_members_table.setColumnWidth(0, 30)
        layout.addWidget(group_members_table)
        
        # 组成员操作按钮
        btn_layout = QHBoxLayout()
        move_to_group_btn = QPushButton("移动到分组")
        move_to_group_btn.setProperty("class", "secondary")
        copy_to_group_btn = QPushButton("复制到分组")
        copy_to_group_btn.setProperty("class", "secondary")
        remove_from_group_btn = QPushButton("从分组移除")
        remove_from_group_btn.setProperty("class", "secondary")
        
        # 连接信号 - 传递UI组件参数
        move_to_group_btn.clicked.connect(
            lambda: self.parent_window.move_to_group(dialog, group_members_label, group_members_table)
        )
        copy_to_group_btn.clicked.connect(
            lambda: self.parent_window.copy_to_group(dialog, group_members_label, group_members_table)
        )
        remove_from_group_btn.clicked.connect(
            lambda: self.parent_window.remove_from_group(dialog, group_members_label, group_members_table)
        )
        
        btn_layout.addWidget(move_to_group_btn)
        btn_layout.addWidget(copy_to_group_btn)
        btn_layout.addWidget(remove_from_group_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 存储引用
        dialog.group_members_label = group_members_label
        dialog.group_members_table = group_members_table
        
        return widget
    
    def _load_groups(self, dialog):
        """加载分组列表"""
        groups = self.recipient_manager.get_groups()
        dialog.group_list_widget.clear()
        
        # 添加"所有分组"选项
        all_item = QListWidgetItem("所有分组")
        all_item.setData(Qt.UserRole, None)  # None表示所有分组
        dialog.group_list_widget.addItem(all_item)
        
        # 添加实际分组
        for group in groups:
            item = QListWidgetItem(group)
            item.setData(Qt.UserRole, group)
            dialog.group_list_widget.addItem(item)
        
        # 默认选择第一项
        if dialog.group_list_widget.count() > 0:
            dialog.group_list_widget.setCurrentRow(0)
    
    def on_group_selection_changed(self, dialog):
        """分组选择变化时的处理"""
        current_item = dialog.group_list_widget.currentItem()
        if not current_item:
            return
        
        group_id = current_item.data(Qt.UserRole)
        group_name = current_item.text()
        
        # 更新标签
        dialog.group_members_label.setText(f"{group_name} - 组成员")
        
        # 加载对应的收件人
        self._load_group_members(dialog, group_id)
    
    def _load_group_members(self, dialog, group_id):
        """加载分组成员"""
        if group_id is None:  # 所有分组
            recipients = self.recipient_manager.get_all_recipients()
        else:
            recipients = self.recipient_manager.get_recipients_by_group(group_id)
        
        table = dialog.group_members_table
        table.setRowCount(len(recipients))
        
        for row, recipient in enumerate(recipients):
            # 复选框
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QVBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 0, checkbox_widget)
            
            # ID
            table.setItem(row, 1, QTableWidgetItem(str(recipient['id'])))
            
            # 姓名
            table.setItem(row, 2, QTableWidgetItem(recipient['name']))
            
            # 邮箱
            table.setItem(row, 3, QTableWidgetItem(recipient['email']))
    
    def add_group(self, parent_dialog):
        """添加分组"""
        dialog = QInputDialog(parent_dialog)
        dialog.setWindowTitle("添加分组")
        dialog.setLabelText("分组名称:")
        dialog.setStyleSheet(MODERN_FLAT_STYLE)
        dialog.setInputMode(QInputDialog.TextInput)
        
        if dialog.exec() == QInputDialog.Accepted:
            name = dialog.textValue().strip()
            if name:
                try:
                    self.recipient_manager.add_group(name)
                    self._load_groups(parent_dialog)
                    msg = QMessageBox(parent_dialog)
                    msg.setWindowTitle("成功")
                    msg.setText("分组添加成功")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.exec()
                except Exception as e:
                    msg = QMessageBox(parent_dialog)
                    msg.setWindowTitle("错误")
                    msg.setText(f"添加分组失败: {str(e)}")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Critical)
                    msg.exec()
    
    def rename_group(self, parent_dialog):
        """重命名分组"""
        current_item = parent_dialog.group_list_widget.currentItem()
        if not current_item or current_item.data(Qt.UserRole) is None:
            msg = QMessageBox(parent_dialog)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个分组")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
        
        group_id = current_item.data(Qt.UserRole)
        old_name = current_item.text()
        
        dialog = QInputDialog(parent_dialog)
        dialog.setWindowTitle("重命名分组")
        dialog.setLabelText("新名称:")
        dialog.setTextValue(old_name)
        dialog.setStyleSheet(MODERN_FLAT_STYLE)
        dialog.setInputMode(QInputDialog.TextInput)
        
        if dialog.exec() == QInputDialog.Accepted:
            name = dialog.textValue().strip()
            if name and name != old_name:
                try:
                    self.recipient_manager.update_group(group_id, name)
                    self._load_groups(parent_dialog)
                    msg = QMessageBox(parent_dialog)
                    msg.setWindowTitle("成功")
                    msg.setText("分组重命名成功")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.exec()
                except Exception as e:
                    msg = QMessageBox(parent_dialog)
                    msg.setWindowTitle("错误")
                    msg.setText(f"重命名分组失败: {str(e)}")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Critical)
                    msg.exec()
    
    def delete_group(self, parent_dialog):
        """删除分组"""
        current_item = parent_dialog.group_list_widget.currentItem()
        if not current_item or current_item.data(Qt.UserRole) is None:
            msg = QMessageBox(parent_dialog)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个分组")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
        
        group_id = current_item.data(Qt.UserRole)
        group_name = current_item.text()
        
        msg = QMessageBox(parent_dialog)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除分组 '{group_name}' 吗？\n注意：这不会删除分组中的收件人。")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() == QMessageBox.Yes:
            try:
                self.recipient_manager.delete_group(group_id)
                self._load_groups(parent_dialog)
                success_msg = QMessageBox(parent_dialog)
                success_msg.setWindowTitle("成功")
                success_msg.setText("分组删除成功")
                success_msg.setStyleSheet(MODERN_FLAT_STYLE)
                success_msg.exec()
            except Exception as e:
                error_msg = QMessageBox(parent_dialog)
                error_msg.setWindowTitle("错误")
                error_msg.setText(f"删除分组失败: {str(e)}")
                error_msg.setStyleSheet(MODERN_FLAT_STYLE)
                error_msg.setIcon(QMessageBox.Critical)
                error_msg.exec()
    
    def get_selected_group_member_ids(self, group_members_table):
        """获取选中的分组成员ID列表"""
        selected_ids = []
        
        # 检查复选框
        for row in range(group_members_table.rowCount()):
            checkbox_widget = group_members_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    id_item = group_members_table.item(row, 1)
                    if id_item:
                        selected_ids.append(int(id_item.text()))
        
        return selected_ids