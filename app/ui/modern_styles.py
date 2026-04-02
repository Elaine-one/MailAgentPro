#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
现代扁平风格QSS样式表
用于MailAgentPro应用程序的UI美化
"""

# 现代扁平风格QSS样式表
MODERN_FLAT_STYLE = """
/* 全局样式 */
QApplication {
    font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
    font-size: 9pt;
    background-color: #ffffff;
    color: #3c4043;
}

/* 默认Widget样式 - 防止黑色背景 */
QWidget {
    background-color: #ffffff;
    color: #3c4043;
}

/* 全局 QAbstractItemView 样式 - 确保下拉框和列表没有多余边框 */
QAbstractItemView {
    border: none;
    outline: none;
}

QAbstractItemView QWidget {
    border: none;
}

QAbstractScrollArea {
    border: none;
}

QAbstractScrollArea QWidget {
    border: none;
}

/* 主窗口样式 - 优化视觉效果 */
QMainWindow {
    background-color: #f8f9fa;
    color: #3c4043;
    font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
}

/* 工具栏样式 - 优化视觉效果 */
QToolBar {
    background-color: #ffffff;
    border: none;
    border-bottom: 1px solid #e9ecef;
    spacing: 8px;
    padding: 8px;
}

QToolBar QToolButton {
    background-color: #f8f9fa;
    border: none;
    border-radius: 6px;
    padding: 8px;
    min-width: 32px;
    min-height: 32px;
}

QToolBar QToolButton:hover {
    background-color: #f1f3f4;
}

QToolBar QToolButton:pressed {
    background-color: #e8eaed;
}

/* 标签页样式 - 优化视觉效果 */
QTabWidget::pane {
    border: 1px solid #e9ecef;
    background-color: #ffffff;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #f8f9fa;
    color: #6c757d;
    border: 1px solid #e9ecef;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 16px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #495057;
    border-bottom: 2px solid #4285f4;
}

QTabBar::tab:hover:!selected {
    background-color: #f1f3f4;
}

/* 按钮样式 - 现代化设计 */
QPushButton {
    background-color: #4285f4;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    min-height: 28px;
    outline: none;
}

QPushButton:hover {
    background-color: #3367d6;
}

/* 按钮状态增强 */
QPushButton:pressed {
    background-color: #2a56c6;
}

QPushButton:disabled {
    background-color: #dadce0;
    color: #5f6368;
}

/* 次要按钮样式 */
QPushButton[class="secondary"] {
    background-color: #ffffff;
    color: #5f6368;
    border: 1px solid #dadce0;
}

QPushButton[class="secondary"]:hover {
    background-color: #f8f9fa;
    border-color: #c0c4cc;
    color: #3c4043;
}

QPushButton[class="secondary"]:pressed {
    background-color: #e8eaed;
}

/* 危险按钮样式 */
QPushButton[class="danger"] {
    background-color: #ea4335;
    color: white;
}

QPushButton[class="danger"]:hover {
    background-color: #d32f2f;
}

QPushButton[class="ai-btn"] {
    background-color: #e8f0fe;
    color: #1967d2;
    border: 1px solid #d2e3fc;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton[class="ai-btn"]:hover {
    background-color: #d2e3fc;
}

/* 成功按钮样式 */
QPushButton[class="success"] {
    background-color: #34a853;
    color: white;
}

QPushButton[class="success"]:hover {
    background-color: #2d9d48;
}

/* 工具栏按钮样式 */
QPushButton[class="toolbar-button"] {
    background-color: #f8f9fa;
    color: #5f6368;
    border: none;
    border-radius: 6px;
    padding: 6px;
    min-width: 28px;
    min-height: 28px;
}

QPushButton[class="toolbar-button"]:hover {
    background-color: #f1f3f4;
}

/* 输入框样式 - 优化交互体验 */
QLineEdit, QTextEdit, QPlainTextEdit, .input-field, .text-edit {
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #ffffff;
    color: #3c4043;
    selection-background-color: #d2e3fc;
    selection-color: #1967d2;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, .input-field:focus, .text-edit:focus {
    border: 1px solid #4285f4;
}

/* 下拉框样式 - 彻底重构以解决不协调问题 */
QComboBox, .combo-box {
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 4px 10px;
    background-color: #ffffff;
    color: #3c4043;
    min-height: 28px;
}

QComboBox:hover, .combo-box:hover {
    border-color: #4285f4;
}

QComboBox:on, .combo-box:on {
    border-color: #4285f4;
}

QComboBox::drop-down, .combo-box::drop-down {
    border: none;
    width: 24px;
    background: transparent;
}

QComboBox::down-arrow, .combo-box::down-arrow {
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzVGNjM2OCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
    width: 12px;
    height: 8px;
}

/* 下拉列表视图样式 - 彻底消除多层边框 */
QComboBox QAbstractItemView {
    border: none !important;
    border-radius: 0px !important;
    background-color: #ffffff;
    outline: none;
    selection-background-color: #e8f0fe;
    selection-color: #1a73e8;
    padding: 0px;
    margin: 0px;
    alternate-background-color: #ffffff;
}

QComboBox QAbstractItemView::item {
    height: 32px;
    padding: 0px 16px;
    color: #3c4043;
    border: none;
    background-color: transparent;
    margin: 0px;
    border-radius: 0px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #e8f0fe;
    color: #1a73e8;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #f1f3f4;
}

/* QComboBox 弹出窗口和内部控件样式 - 彻底消除所有边框和阴影 */
QComboBox QAbstractItemView QWidget {
    border: none !important;
    background-color: #ffffff;
}

QComboBox QAbstractItemView::viewport {
    border: none !important;
    background-color: #ffffff;
}

/* 移除滚动条箭头 */
QComboBox QAbstractItemView QScrollBar::up-arrow,
QComboBox QAbstractItemView QScrollBar::down-arrow {
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}

QComboBox QAbstractItemView QScrollBar::add-line,
QComboBox QAbstractItemView QScrollBar::sub-line {
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}

/* QAbstractScrollArea 样式 - 确保下拉框不显示边框 */
QComboBox QAbstractScrollArea {
    border: none !important;
}

QComboBox QAbstractScrollArea QWidget {
    border: none !important;
}

/* 确保 QScrollBar 不添加额外边框 */
QComboBox QAbstractItemView QScrollBar {
    border: none !important;
}

/* Qt 内部弹出容器样式 - 彻底消除边框和阴影 */
QComboBoxPrivateContainer {
    border: none !important;
    border-radius: 0px !important;
    background-color: #ffffff;
    outline: none;
    outline-offset: 0px;
}

QComboBoxPrivateContainer QWidget {
    border: none !important;
    background-color: #ffffff;
}

QComboBoxPrivateScroller {
    border: none !important;
    border-radius: 0px !important;
    background-color: #ffffff;
    outline: none;
}

QComboBoxPrivateScroller QWidget {
    border: none !important;
    background-color: #ffffff;
}

/* 下拉框禁用状态 */
QComboBox:disabled, .combo-box:disabled {
    background-color: #f8f9fa;
    color: #9aa0a6;
    border-color: #e9ecef;
}

/* 下拉框焦点状态 */
QComboBox:focus, .combo-box:focus {
    border: 2px solid #4285f4;
    padding: 3px 9px;
}

/* 列表和表格样式 - 仅在有class时显示边框 */
.list, .table {
    border: 1px solid #dadce0;
    border-radius: 8px;
    background-color: #ffffff;
    gridline-color: #f1f3f4;
    outline: none;
}

QListWidget.list, QTableWidget.table {
    border: 1px solid #dadce0;
    border-radius: 8px;
    background-color: #ffffff;
    gridline-color: #f1f3f4;
    outline: none;
}

QTableWidget::item, QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f3f4;
}

QHeaderView::section {
    background-color: #f8f9fa;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #dadce0;
    font-weight: bold;
    color: #5f6368;
}

/* 分组框样式 */
QGroupBox {
    border: 1px solid #dadce0;
    border-radius: 8px;
    margin-top: 1.2em;
    padding-top: 10px;
    font-weight: bold;
    color: #202124;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: #ffffff;
}

/* 侧边栏专属样式 */
.ai-container {
    background-color: #ffffff;
    border-left: 1px solid #e9ecef;
}

.sidebar-title {
    color: #202124;
    font-weight: bold;
}

.sidebar-label {
    color: #5f6368;
    font-weight: 500;
    margin-top: 4px;
}

/* 表格样式 */
QTableWidget, QTableView {
    border: 1px solid #dadce0;
    background-color: #ffffff;
    gridline-color: #f1f3f4;
    outline: none;
    selection-background-color: #e8f0fe;
    selection-color: #1967d2;
}

QTableWidget::item, QTableView::item {
    padding: 8px;
    border-bottom: 1px solid #f1f3f4;
}

/* 表格内的编辑器样式 - 彻底修复备注名编辑框 */
QTableWidget QLineEdit, QTableView QLineEdit {
    border: 1px solid #4285f4;
    border-radius: 0px;
    margin: 0px;
    padding: 0px 8px;
    background-color: #ffffff;
    color: #3c4043;
    selection-background-color: #d2e3fc;
    selection-color: #1967d2;
    min-height: 28px;
}

/* 表头样式 */
QHeaderView::section {
    background-color: #f8f9fa;
    color: #5f6368;
    padding: 8px;
    border: none;
    border-right: 1px solid #dadce0;
    border-bottom: 1px solid #dadce0;
    font-weight: 500;
}

QHeaderView::section:last {
    border-right: none;
}

/* 滚动条样式 - 现代化细长设计 */
QScrollBar:vertical {
    border: none;
    background: #f1f3f4;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #dadce0;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #bdc1c6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f3f4;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #dadce0;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QHeaderView::section:first {
    border-top-left-radius: 8px;
}

QHeaderView::section:last {
    border-top-right-radius: 8px;
    border-right: none;
}

/* 分组框样式 - 简化样式，减少计算复杂度 */
QGroupBox {
    font-weight: 500;
    color: #3c4043;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px 0 8px;
    background-color: #f8f9fa;
}

/* 复选框样式 - 现代化设计 */
QCheckBox {
    spacing: 8px;
    color: #3c4043;
    font-weight: 400;
    outline: none;
    padding: 4px;
}

/* 单选框样式 - 简化样式，减少计算复杂度 */
QRadioButton {
    spacing: 8px;
    color: #3c4043;
    font-weight: 400;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #dadce0;
    border-radius: 9px;
    background-color: #ffffff;
}

QRadioButton::indicator:hover {
    border: 2px solid #c0c4cc;
    background-color: #f8f9fa;
}

QRadioButton::indicator:checked {
    background-color: #4285f4;
    border: 2px solid #4285f4;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNSIgY3k9IjUiIHI9IjMiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPgo=);
}

/* 进度条样式 - 简化样式，减少计算复杂度 */
QProgressBar {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    text-align: center;
    color: #3c4043;
    background-color: #f8f9fa;
    height: 12px;
}

QProgressBar::chunk {
    background-color: #4285f4;
    border-radius: 7px;
}

/* 对话框样式 - 现代化设计 */
QDialog, QMessageBox, QInputDialog {
    background-color: #ffffff;
    color: #3c4043;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 10px;
    min-width: 350px;
    outline: none;
}

/* 消息框样式增强 */
QMessageBox {
    min-width: 350px;
    min-height: 150px;
}

QMessageBox::title {
    font-weight: 500;
    font-size: 10pt;
    color: #3c4043;
}

/* 输入对话框样式增强 */
QInputDialog {
    min-width: 400px;
}

/* 对话框按钮盒样式 */
QDialogButtonBox {
    background-color: #ffffff;
    padding: 16px 0 0 0;
    margin-top: 16px;
    border-top: 1px solid #e9ecef;
}

/* 确保对话框内的按钮样式统一 - 优化为更紧凑精致的样式 */
QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {
    margin: 4px;
    padding: 4px 12px;
    border-radius: 6px;
    font-weight: 500;
    font-size: 9pt;
    min-width: 80px;
    min-height: 28px;
    background-color: #4285f4;
    color: white;
}

QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
    background-color: #3367d6;
}

/* 消息框内容样式增强 */
QMessageBox QLabel {
    margin-bottom: 10px;
    line-height: 1.4;
    background-color: transparent;
}

/* 菜单样式 - 简化样式，减少计算复杂度 */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e9ecef;
    font-weight: 500;
}

QMenuBar::item {
    padding: 8px 12px;
    background-color: #f8f9fa;
}

QMenuBar::item:selected {
    background-color: #f1f3f4;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 4px 0;
}

QMenu::item {
    padding: 10px 16px;
}

QMenu::item:selected {
    background-color: #e8f0fe;
    color: #1967d2;
}

/* 工具提示样式 - 现代化设计 */
QToolTip {
    background-color: #f8f9fa;
    color: #3c4043;
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 9pt;
    font-weight: 400;
}

/* 滚动条样式 - 现代化设计 */
QScrollBar:vertical {
    background-color: #f8f9fa;
    width: 8px;
    border-radius: 4px;
    margin: 8px 4px;
}

QScrollBar::handle:vertical {
    background-color: #dadce0;
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background-color: #c0c4cc;
}

QScrollBar::handle:vertical:pressed {
    background-color: #4285f4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: #f8f9fa;
}

QScrollBar:horizontal {
    background-color: #f8f9fa;
    height: 8px;
    border-radius: 4px;
    margin: 4px 8px;
}

QScrollBar::handle:horizontal {
    background-color: #dadce0;
    border-radius: 4px;
    min-width: 40px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #c0c4cc;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #4285f4;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background-color: #f8f9fa;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #f8f9fa;
    color: #5f6368;
    border-top: 1px solid #e9ecef;
}

/* 侧边栏样式 - 优化视觉效果 */
QDockWidget {
    background-color: #ffffff !important;
    color: #3c4043 !important;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    titlebar-close-icon: url();
    titlebar-normal-icon: url();
}

QDockWidget::title {
    background-color: #f8f9fa;
    padding: 12px 8px;
    border-bottom: 1px solid #e9ecef;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    font-weight: 500;
    color: #3c4043;
}

/* 标签样式 */
QLabel {
    color: #3c4043 !important;
    background-color: #ffffff;
    font-size: 9pt;
}

/* AI助手容器样式 */
QWidget[class="ai-container"] {
    background-color: #ffffff !important;
    color: #3c4043 !important;
}

/* 列表样式 - 现代化设计 */
QListWidget, QListView {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    background-color: #ffffff;
    selection-background-color: #e8f0fe;
    selection-color: #1967d2;
    alternate-background-color: #f8f9fa;
    color: #3c4043;
    outline: none;
}

QListWidget::item, QListView::item {
    padding: 12px 16px;
    border-bottom: 1px solid #f1f3f4;
    height: 40px;
    font-size: 9pt;
    font-weight: 400;
}

QListWidget::item:last-child, QListView::item:last-child {
    border-bottom: none;
}

QListWidget::item:hover, QListView::item:hover {
    background-color: #f8f9fa;
}

QListWidget::item:selected, QListView::item:selected {
    background-color: #e8f0fe;
    color: #1967d2;
    border-bottom: 1px solid #e8f0fe;
}

QListWidget::item:selected:hover, QListView::item:selected:hover {
    background-color: #d7e3fc;
}

/* 滚动区域样式 - 确保统一外观 */
QScrollArea {
    border: none;
    background-color: #ffffff;
}

QScrollArea > QWidget > QWidget {
    background-color: #ffffff;
}

QScrollArea > QWidget > QWidget > QWidget {
    background-color: #ffffff;
}

/* 侧边栏滚动内容样式 */
.scroll-content {
    background-color: #ffffff;
}

/* 树形控件样式 - 现代化设计 */
QTreeWidget {
    border: 1px solid #e9ecef;
    border-radius: 8px;
    background-color: #ffffff !important;
    selection-background-color: #e8f0fe;
    selection-color: #1967d2;
    alternate-background-color: #f8f9fa;
}

QTreeWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f1f3f4;
}

QTreeWidget::item:hover {
    background-color: #f8f9fa;
}

QTreeWidget::item:selected {
    background-color: #e8f0fe;
    color: #1967d2;
    border-bottom: 1px solid #e8f0fe;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    border-image: none;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYgNEwxMCA4TDYgMTJINOIiIHN0cm9rZT0iIzVjNjM2OCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
}

QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {
    border-image: none;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgNkgxMkg0IiBzdHJva2U9IiM1YzYzNjgiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
}

/* 选项卡样式 */
QTabWidget {
    background-color: #f8f9fa;
}

/* 成功文本样式 */
QLabel[class="success"] {
    color: #34a853;
    font-weight: 500;
}

/* 工具栏按钮样式 */
QPushButton[class="toolbar-button"] {
    background-color: #f8f9fa;
    color: #5f6368;
    border: none;
    border-radius: 6px;
    padding: 8px;
    min-width: 32px;
    min-height: 32px;
}

QPushButton[class="toolbar-button"]:hover {
    background-color: #f1f3f4;
}

QPushButton[class="toolbar-button"]:pressed {
    background-color: #e8eaed;
}

/* 分隔器样式 - 现代化设计 */
QSplitter::handle {
    background-color: #e9ecef;
}

QSplitter::handle:horizontal {
    width: 6px; /* 增加宽度，更易操作 */
    margin: 0 2px;
    border-radius: 3px;
}

QSplitter::handle:vertical {
    height: 6px;
    margin: 2px 0;
    border-radius: 3px;
}

QSplitter::handle:pressed {
    background-color: #4285f4;
    border-radius: 1.5px;
}

QSplitter::handle:hover {
    background-color: #dadce0;
}
"""


def setup_combo_box(combo):
    """统一设置 QComboBox/WheelComboBox 样式"""
    combo.setProperty("class", "combo-box")
    combo.setMaxVisibleItems(10)
