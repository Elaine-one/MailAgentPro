#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
收件人管理模块
专门处理收件人相关的所有UI操作和业务逻辑
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTableWidget, QTableWidgetItem, QListWidget, 
                               QListWidgetItem, QSplitter, QMessageBox, QInputDialog,
                               QAbstractItemView, QDialog)
from PySide6.QtCore import Qt
from ui.recipient_dialogs import ImportRecipientsDialog, AddRecipientDialog, EditRecipientDialog
from ui.modern_styles import MODERN_FLAT_STYLE


class RecipientManagerWidget(QWidget):
    """收件人管理组件"""
    
    def __init__(self, recipient_manager, parent_window):
        """
        初始化收件人管理组件
        
        Args:
            recipient_manager: 收件人管理器实例
            parent_window: 父窗口实例
        """
        super().__init__()
        self.recipient_manager = recipient_manager
        self.parent_window = parent_window
        self.current_group_id = None
        self.init_ui()
        self.load_groups()
        self.load_recipients()
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QHBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：分组列表区域
        left_widget = self.create_group_panel()
        
        # 右侧：收件人列表区域
        right_widget = self.create_recipient_panel()
        
        # 将左右部件添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)  # 左侧不自动拉伸
        splitter.setStretchFactor(1, 1)  # 右侧自动拉伸
        splitter.setSizes([200, 600])    # 设置初始大小
        
        main_layout.addWidget(splitter)
    
    def create_group_panel(self):
        """创建分组面板"""
        widget = QWidget()
        widget.setProperty("class", "group-panel")
        widget.setFixedWidth(220) # 固定左侧面板宽度
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0) # 右侧留出一点间距
        
        # 分组列表标题
        title_label = QLabel("📁 收件人分组")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #202124; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # 分组列表
        self.group_list_widget = QListWidget()
        self.group_list_widget.setProperty("class", "list")
        self.group_list_widget.setMinimumWidth(180)
        self.group_list_widget.itemSelectionChanged.connect(self.on_group_selection_changed)
        layout.addWidget(self.group_list_widget)
        
        # 分组操作按钮 - 更加紧凑
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        self.add_group_btn = QPushButton("添加")
        self.add_group_btn.setProperty("class", "secondary")
        self.rename_group_btn = QPushButton("更名")
        self.rename_group_btn.setProperty("class", "secondary")
        self.delete_group_btn = QPushButton("删除")
        self.delete_group_btn.setProperty("class", "secondary")
        
        # 设置按钮固定高度，使其更整齐
        for btn in [self.add_group_btn, self.rename_group_btn, self.delete_group_btn]:
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
        
        # 连接信号
        self.add_group_btn.clicked.connect(self.add_group)
        self.rename_group_btn.clicked.connect(self.edit_group)
        self.delete_group_btn.clicked.connect(self.delete_group)
        
        btn_layout.addWidget(self.add_group_btn)
        btn_layout.addWidget(self.rename_group_btn)
        btn_layout.addWidget(self.delete_group_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_recipient_panel(self):
        """创建收件人面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 收件人列表标题（动态显示当前选中的分组）
        self.recipient_list_label = QLabel("所有收件人")
        layout.addWidget(self.recipient_list_label)
        
        # 收件人列表
        self.recipient_table = QTableWidget(0, 4)
        self.recipient_table.setProperty("class", "table")
        self.recipient_table.setHorizontalHeaderLabels(["ID", "姓名", "邮箱", "分组"])
        self.recipient_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recipient_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.recipient_table)
        
        # 收件人操作按钮
        btn_layout = QHBoxLayout()
        self.import_recipient_btn = QPushButton("导入CSV")
        self.import_recipient_btn.setProperty("class", "secondary")
        self.add_recipient_btn = QPushButton("添加收件人")
        self.add_recipient_btn.setProperty("class", "secondary")
        self.edit_recipient_btn = QPushButton("编辑收件人")
        self.edit_recipient_btn.setProperty("class", "secondary")
        self.delete_recipient_btn = QPushButton("删除收件人")
        self.delete_recipient_btn.setProperty("class", "secondary")
        self.move_to_group_btn = QPushButton("移动到分组")
        self.move_to_group_btn.setProperty("class", "secondary")
        self.copy_to_group_btn = QPushButton("复制到分组")
        self.copy_to_group_btn.setProperty("class", "secondary")
        
        # 连接信号
        self.import_recipient_btn.clicked.connect(self.import_recipients)
        self.add_recipient_btn.clicked.connect(self.add_recipient)
        self.edit_recipient_btn.clicked.connect(self.edit_recipient)
        self.delete_recipient_btn.clicked.connect(self.delete_recipient)
        self.move_to_group_btn.clicked.connect(self.move_to_group)
        self.copy_to_group_btn.clicked.connect(self.copy_to_group)
        
        btn_layout.addWidget(self.import_recipient_btn)
        btn_layout.addWidget(self.add_recipient_btn)
        btn_layout.addWidget(self.edit_recipient_btn)
        btn_layout.addWidget(self.delete_recipient_btn)
        btn_layout.addWidget(self.move_to_group_btn)
        btn_layout.addWidget(self.copy_to_group_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def load_groups(self):
        """加载分组列表"""
        try:
            groups = self.recipient_manager.get_groups()
            self.group_list_widget.clear()
            
            # 添加"所有分组"选项
            all_item = QListWidgetItem("所有分组")
            all_item.setData(Qt.UserRole, None)  # None表示所有分组
            self.group_list_widget.addItem(all_item)
            
            # 添加实际分组（groups是字符串列表）
            for group_name in groups:
                item = QListWidgetItem(group_name)
                item.setData(Qt.UserRole, group_name)  # 使用分组名称作为标识
                self.group_list_widget.addItem(item)
            
            # 默认选择第一项
            if self.group_list_widget.count() > 0:
                self.group_list_widget.setCurrentRow(0)
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载分组失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def load_recipients(self, group_name=None):
        """加载收件人列表"""
        try:
            recipients = self.recipient_manager.list_recipients(group_name)
            
            self.recipient_table.setRowCount(len(recipients))
            
            for row, recipient in enumerate(recipients):
                self.recipient_table.setItem(row, 0, QTableWidgetItem(str(recipient['id'])))
                self.recipient_table.setItem(row, 1, QTableWidgetItem(recipient['name']))
                self.recipient_table.setItem(row, 2, QTableWidgetItem(recipient['email']))
                self.recipient_table.setItem(row, 3, QTableWidgetItem(recipient['group_name'] or ''))
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"加载收件人失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def on_group_selection_changed(self):
        """分组选择变化时的处理"""
        try:
            current_item = self.group_list_widget.currentItem()
            if not current_item:
                return
            
            group_name = current_item.text()
            self.recipient_list_label.setText(f"{group_name} - 收件人")
            
            # 根据选择的分组加载对应的收件人
            if group_name == "所有分组":
                self.load_recipients()
            else:
                self.load_recipients(group_name)
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"切换分组失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def import_recipients(self):
        """导入收件人"""
        dialog = ImportRecipientsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_recipients()
            self.parent_window.refresh_send_tab_data()  # 刷新发送标签页数据
    
    def add_recipient(self):
        """添加收件人"""
        dialog = AddRecipientDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_recipients()
            self.parent_window.refresh_send_tab_data()  # 刷新发送标签页数据
    
    def edit_recipient(self):
        """编辑收件人"""
        selected_rows = self.recipient_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个收件人")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        row = selected_rows[0].row()
        recipient_id = int(self.recipient_table.item(row, 0).text())
        
        dialog = EditRecipientDialog(recipient_id, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_recipients()
            self.status_bar.showMessage("收件人更新成功")
    
    def delete_recipient(self):
        """删除收件人"""
        selected_rows = self.recipient_table.selectionModel().selectedRows()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请先选择要删除的收件人")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
        
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除选中的 {len(selected_rows)} 个收件人吗？")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        reply = msg.exec()
        
        if reply == QMessageBox.Yes:
            try:
                for row in selected_rows:
                    recipient_id = int(self.recipient_table.item(row.row(), 0).text())
                    self.recipient_manager.delete_recipient(recipient_id)
                
                self.load_recipients()
                self.parent_window.refresh_send_tab_data()  # 刷新发送标签页数据
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText("收件人删除成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("错误")
                msg.setText(f"删除收件人失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
    
    def add_group(self):
        """添加分组"""
        try:
            group_name, ok = QInputDialog.getText(
                self, "添加分组", "请输入分组名称:"
            )
            
            if ok and group_name.strip():
                group_name = group_name.strip()
                self.recipient_manager.add_group(group_name)
                self.load_groups()
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText(f"分组 '{group_name}' 添加成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("错误")
            msg.setText(f"添加分组失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def edit_group(self):
        """编辑分组"""
        selected_items = self.group_list_widget.selectedItems()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个分组")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        old_group_name = selected_items[0].text()
        new_group_name, ok = QInputDialog.getText(self, "编辑分组", "请输入新的分组名称:", text=old_group_name)
        
        if ok and new_group_name:
            try:
                # 更新分组名称
                self.recipient_manager.update_group_name(old_group_name, new_group_name)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("成功")
                msg_box.setText("分组名称更新成功")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.exec()
                self.load_groups()
                self.load_recipients()
            except Exception as e:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("错误")
                msg_box.setText(f"更新分组失败: {str(e)}")
                msg_box.setStyleSheet(MODERN_FLAT_STYLE)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.exec()
    
    def delete_group(self):
        """删除分组"""
        selected_items = self.group_list_widget.selectedItems()
        if not selected_rows:
            msg = QMessageBox(self)
            msg.setWindowTitle("警告")
            msg.setText("请先选择一个分组")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
            
        group_name = selected_items[0].text()
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除分组 '{group_name}' 吗？\n\n这将删除该分组下的所有收件人。")
        msg.setStyleSheet(MODERN_FLAT_STYLE)
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        reply = msg.exec()
        
        if reply == QMessageBox.Yes:
            try:
                # 删除分组及其收件人
                self.recipient_manager.delete_recipients_by_group(group_name)
                msg = QMessageBox(self)
                msg.setWindowTitle("成功")
                msg.setText("分组删除成功")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                self.load_groups()
                self.load_recipients()
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("错误")
                msg.setText(f"删除分组失败: {str(e)}")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
    
    def move_to_group(self):
        """移动收件人到分组"""
        try:
            # 获取选中的收件人
            selected_rows = self.recipient_table.selectionModel().selectedRows()
            if not selected_rows:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请先选择要移动的收件人")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 获取所有分组
            groups = self.recipient_manager.get_all_groups()
            if not groups:
                msg = QMessageBox(self)
                msg.setWindowTitle("提示")
                msg.setText("当前没有可用的分组")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                return
            
            # 创建分组选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("移动到分组")
            dialog.setFixedSize(300, 200)
            dialog.setStyleSheet(MODERN_FLAT_STYLE)
            
            layout = QVBoxLayout(dialog)
            
            # 分组选择列表
            layout.addWidget(QLabel("请选择目标分组:"))
            group_list = QListWidget()
            group_list.setProperty("class", "list")
            for group in groups:
                group_list.addItem(group['name'])
            layout.addWidget(group_list)
            
            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.setProperty("class", "primary")
            cancel_btn = QPushButton("取消")
            cancel_btn.setProperty("class", "secondary")
            btn_layout.addStretch()
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            def apply_move():
                selected_group_items = group_list.selectedItems()
                if not selected_group_items:
                    msg = QMessageBox(dialog)
                    msg.setWindowTitle("警告")
                    msg.setText("请先选择一个目标分组")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Warning)
                    msg.exec()
                    return
                
                target_group = selected_group_items[0].text()
                
                # 移动所有选中的收件人到目标分组
                for row in selected_rows:
                    recipient_id = int(self.recipient_table.item(row.row(), 0).text())
                    self.recipient_manager.update_recipient(
                        recipient_id=recipient_id,
                        group_name=target_group
                    )
                
                # 刷新收件人列表和发送标签页数据
                self.load_recipients()
                self.parent_window.refresh_send_tab_data()
                
                msg = QMessageBox(dialog)
                msg.setWindowTitle("成功")
                msg.setText(f"已将 {len(selected_rows)} 个收件人移动到分组 '{target_group}'")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                dialog.accept()
            
            ok_btn.clicked.connect(apply_move)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            msg = QMessageBox(dialog)
            msg.setWindowTitle("错误")
            msg.setText(f"移动收件人失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def copy_to_group(self):
        """复制收件人到分组"""
        try:
            # 获取选中的收件人
            selected_rows = self.recipient_table.selectionModel().selectedRows()
            if not selected_rows:
                msg = QMessageBox(self)
                msg.setWindowTitle("警告")
                msg.setText("请先选择要导出的收件人")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
                return
            
            # 获取所有分组
            groups = self.recipient_manager.get_all_groups()
            if not groups:
                msg = QMessageBox(self)
                msg.setWindowTitle("提示")
                msg.setText("当前没有可用的分组")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                return
            
            # 创建分组选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("复制到分组")
            dialog.setFixedSize(300, 200)
            dialog.setStyleSheet(MODERN_FLAT_STYLE)
            
            layout = QVBoxLayout(dialog)
            
            # 分组选择列表
            layout.addWidget(QLabel("请选择目标分组:"))
            group_list = QListWidget()
            group_list.setProperty("class", "list")
            for group in groups:
                group_list.addItem(group['name'])
            layout.addWidget(group_list)
            
            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.setProperty("class", "primary")
            cancel_btn = QPushButton("取消")
            cancel_btn.setProperty("class", "secondary")
            btn_layout.addStretch()
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            def apply_copy():
                selected_group_items = group_list.selectedItems()
                if not selected_group_items:
                    msg = QMessageBox(dialog)
                    msg.setWindowTitle("警告")
                    msg.setText("请先选择一个目标分组")
                    msg.setStyleSheet(MODERN_FLAT_STYLE)
                    msg.setIcon(QMessageBox.Warning)
                    msg.exec()
                    return
                
                target_group = selected_group_items[0].text()
                
                # 复制所有选中的收件人到目标分组
                for row in selected_rows:
                    name = self.recipient_table.item(row.row(), 1).text()
                    email = self.recipient_table.item(row.row(), 2).text()
                    # 创建新的收件人记录（复制操作）
                    self.recipient_manager.add_recipient(
                        name=name,
                        email=email,
                        group_name=target_group
                    )
                
                # 刷新收件人列表和发送标签页数据
                self.load_recipients()
                self.parent_window.refresh_send_tab_data()
                
                msg = QMessageBox(dialog)
                msg.setWindowTitle("成功")
                msg.setText(f"已将 {len(selected_rows)} 个收件人复制到分组 '{target_group}'")
                msg.setStyleSheet(MODERN_FLAT_STYLE)
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                dialog.accept()
            
            ok_btn.clicked.connect(apply_copy)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            msg = QMessageBox(dialog)
            msg.setWindowTitle("错误")
            msg.setText(f"复制收件人失败: {str(e)}")
            msg.setStyleSheet(MODERN_FLAT_STYLE)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def get_selected_recipients(self):
        """获取选中的收件人"""
        selected_recipients = []
        selected_rows = self.recipient_table.selectionModel().selectedRows()
        
        for row in selected_rows:
            recipient_id = int(self.recipient_table.item(row.row(), 0).text())
            name = self.recipient_table.item(row.row(), 1).text()
            email = self.recipient_table.item(row.row(), 2).text()
            selected_recipients.append({
                'id': recipient_id,
                'name': name,
                'email': email
            })
        
        return selected_recipients