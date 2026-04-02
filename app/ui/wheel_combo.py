from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt


class WheelComboBox(QComboBox):
    """
    滚轮选择器 - 禁用下拉弹出窗口，只保留滚轮选择功能
    
    交互方式：
    - 鼠标滚轮：在控件上滚动鼠标滚轮切换选项
    - 键盘上下键：切换选项
    - 双击：进入编辑模式（如果可编辑）
    - 不弹出窗口：始终显示当前选中的选项
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._wheel_enabled = True
        
    def showPopup(self):
        """重写，阻止弹出窗口"""
        pass
    
    def wheelEvent(self, event):
        """滚轮事件 - 切换选项"""
        if not self._wheel_enabled or self.count() == 0:
            return
            
        delta = event.angleDelta().y()
        if delta > 0:
            new_index = self.currentIndex() - 1
            if new_index >= 0:
                self.setCurrentIndex(new_index)
        elif delta < 0:
            new_index = self.currentIndex() + 1
            if new_index < self.count():
                self.setCurrentIndex(new_index)
        
        event.accept()
    
    def keyPressEvent(self, event):
        """键盘事件 - 上下键切换选项"""
        if event.key() == Qt.Key_Up:
            new_index = self.currentIndex() - 1
            if new_index >= 0:
                self.setCurrentIndex(new_index)
            event.accept()
        elif event.key() == Qt.Key_Down:
            new_index = self.currentIndex() + 1
            if new_index < self.count():
                self.setCurrentIndex(new_index)
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件 - 进入编辑模式"""
        if self.isEditable():
            self.lineEdit().selectAll()
            self.lineEdit().setFocus()
        event.accept()
    
    def setWheelEnabled(self, enabled):
        """设置是否启用滚轮选择"""
        self._wheel_enabled = enabled
