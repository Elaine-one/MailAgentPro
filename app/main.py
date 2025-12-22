#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MailAgent Pro - 智能邮件助理
主程序入口
"""

import sys
import os
import traceback

# 设置 Qt 插件路径，解决部分环境下的启动问题
import PySide6
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms')

from PySide6.QtWidgets import QApplication, QMessageBox, QProxyStyle, QStyle
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPointF
from ui.main_window import MainWindow
from db.db_manager import init_database, db_manager


class ModernCheckStyle(QProxyStyle):
    def pixelMetric(self, metric, option=None, widget=None):
        if metric in (QStyle.PM_IndicatorWidth, QStyle.PM_IndicatorHeight):
            return 18
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        if element in (QStyle.PE_IndicatorCheckBox, QStyle.PE_IndicatorItemViewItemCheck):
            rect = option.rect
            if rect.width() <= 0 or rect.height() <= 0:
                return

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)

            is_enabled = bool(option.state & QStyle.State_Enabled)
            is_hover = bool(option.state & QStyle.State_MouseOver)
            is_on = bool(option.state & QStyle.State_On)
            is_no_change = bool(option.state & QStyle.State_NoChange)

            background_color = QColor("#ffffff") if is_enabled else QColor("#f1f3f4")
            if is_hover and is_enabled and not is_on:
                background_color = QColor("#f8f9fa")

            border_color = QColor("#dadce0")
            if (is_hover or is_on or is_no_change) and is_enabled:
                border_color = QColor("#4285f4")

            pen = QPen(border_color, 2)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(background_color)

            draw_rect = rect.adjusted(1, 1, -1, -1)
            radius = max(3.0, min(draw_rect.width(), draw_rect.height()) * 0.22)
            painter.drawRoundedRect(draw_rect, radius, radius)

            if is_on:
                check_pen_width = max(2.5, min(draw_rect.width(), draw_rect.height()) * 0.16)
                check_pen = QPen(QColor("#3c4043"), check_pen_width)
                check_pen.setCapStyle(Qt.RoundCap)
                check_pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(check_pen)
                painter.setBrush(Qt.NoBrush)

                x = float(draw_rect.left())
                y = float(draw_rect.top())
                w = float(draw_rect.width())
                h = float(draw_rect.height())

                p1 = QPointF(x + w * 0.20, y + h * 0.55)
                p2 = QPointF(x + w * 0.43, y + h * 0.75)
                p3 = QPointF(x + w * 0.80, y + h * 0.30)
                painter.drawLine(p1, p2)
                painter.drawLine(p2, p3)

            painter.restore()
            return

        return super().drawPrimitive(element, option, painter, widget)


def main():
    try:
        # 初始化数据库
        print("正在初始化数据库...")
        init_database()
        
        # 测试数据库连接
        if not db_manager.test_connection():
            QMessageBox.critical(None, "数据库错误", "数据库连接失败，请检查数据库文件")
            return 1
            
        print("数据库连接正常")
        
        # 创建应用程序实例
        app = QApplication(sys.argv)
        
        # 确保使用 Fusion 风格以获得更好的 QSS 支持
        app.setStyle(ModernCheckStyle("Fusion"))
        
        # 导入并设置全局样式表
        from ui.modern_styles import MODERN_FLAT_STYLE
        app.setStyleSheet(MODERN_FLAT_STYLE)
        
        # 设置调色板确保浅色背景
        from PySide6.QtGui import QPalette, QColor
        palette = app.palette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(248, 249, 250))
        app.setPalette(palette)
        
        print("正在创建主窗口...")
        window = MainWindow()
        print("主窗口创建完成，正在显示...")
        window.show()
        print("主窗口已显示")
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = f"应用程序启动失败:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        
        # 如果已经存在QApplication实例，直接使用，否则创建新实例
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        QMessageBox.critical(None, "启动错误", error_msg)
        return 1


if __name__ == "__main__":
    main()
