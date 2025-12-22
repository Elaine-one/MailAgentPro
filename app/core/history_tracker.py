#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务历史记录模块
负责存储发送任务摘要、统计发送状态、导出历史记录等
"""

import csv
from datetime import datetime
from db.db_manager import get_db_manager, Task, TaskDetail


class HistoryTracker:
    """任务历史记录类"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
    def get_task(self, task_id):
        """
        获取指定任务信息
        
        Args:
            task_id (int): 任务ID
            
        Returns:
            dict: 任务信息
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
                
            return {
                'id': task.id,
                'account_id': task.account_id,
                'subject': task.subject,
                'content': task.content,
                'send_time': task.send_time,
                'total': task.total,
                'success_count': task.success_count,
                'fail_count': task.fail_count,
                'status': task.status
            }
        finally:
            self.db_manager.close_session(session)

    def add_task(self, account_id, subject, content, total, success_count, fail_count):
        """
        添加新任务记录
        
        Args:
            account_id (int): 账户ID
            subject (str): 邮件主题
            content (str): 邮件内容
            total (int): 总收件人数
            success_count (int): 成功发送数
            fail_count (int): 发送失败数
            
        Returns:
            int: 新增任务ID
        """
        session = self.db_manager.get_session()
        try:
            # 确定任务状态
            if success_count == total:
                status = "已完成"
            elif success_count > 0:
                status = "部分完成"
            else:
                status = "失败"
                
            new_task = Task(
                account_id=account_id,
                subject=subject,
                content=content,
                send_time=datetime.now(),
                total=total,
                success_count=success_count,
                fail_count=fail_count,
                status=status
            )
            
            session.add(new_task)
            session.commit()
            return new_task.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def list_tasks(self, limit=50, offset=0):
        """
        获取任务列表
        
        Args:
            limit (int): 返回记录数限制
            offset (int): 偏移量
            
        Returns:
            list: 任务列表
        """
        session = self.db_manager.get_session()
        try:
            tasks = session.query(Task).order_by(Task.send_time.desc()).limit(limit).offset(offset).all()
            return [{
                'id': task.id,
                'account_id': task.account_id,
                'subject': task.subject,
                'send_time': task.send_time,
                'total': task.total,
                'success_count': task.success_count,
                'fail_count': task.fail_count,
                'status': task.status
            } for task in tasks]
        finally:
            self.db_manager.close_session(session)
            
    def get_task_details(self, task_id):
        """
        获取任务详细信息
        
        Args:
            task_id (int): 任务ID
            
        Returns:
            list: 任务详情列表
        """
        session = self.db_manager.get_session()
        try:
            details = session.query(TaskDetail).filter(TaskDetail.task_id == task_id).all()
            return [{
                'id': detail.id,
                'recipient_email': detail.recipient_email,
                'result': detail.result,
                'error_msg': detail.error_msg,
                'send_round': detail.send_round
            } for detail in details]
        finally:
            self.db_manager.close_session(session)
            
    def search_tasks(self, keyword, limit=50):
        """
        搜索任务（按主题）
        
        Args:
            keyword (str): 搜索关键词
            limit (int): 返回记录数限制
            
        Returns:
            list: 匹配的任务列表
        """
        session = self.db_manager.get_session()
        try:
            tasks = session.query(Task).filter(Task.subject.contains(keyword)).order_by(
                Task.send_time.desc()).limit(limit).all()
            return [{
                'id': task.id,
                'account_id': task.account_id,
                'subject': task.subject,
                'send_time': task.send_time,
                'total': task.total,
                'success_count': task.success_count,
                'fail_count': task.fail_count,
                'status': task.status
            } for task in tasks]
        finally:
            self.db_manager.close_session(session)
            
    def export_tasks_to_csv(self, file_path, start_date=None, end_date=None):
        """
        导出任务记录到CSV文件
        
        Args:
            file_path (str): 导出文件路径
            start_date (datetime, optional): 开始日期
            end_date (datetime, optional): 结束日期
            
        Returns:
            int: 导出的任务数量
        """
        session = self.db_manager.get_session()
        try:
            # 构建查询
            query = session.query(Task)
            if start_date:
                query = query.filter(Task.send_time >= start_date)
            if end_date:
                query = query.filter(Task.send_time <= end_date)
                
            tasks = query.order_by(Task.send_time.desc()).all()
            
            # 写入CSV文件 - 使用UTF-8编码并添加BOM头，确保中文字符正确显示
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # 扩展字段列表，添加更多详细信息
                fieldnames = [
                    '任务ID', '邮件主题', '发送时间', '总收件人数', '成功数量', '失败数量', 
                    '成功率', '失败率', '任务状态', '账户ID', '邮件内容摘要'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for task in tasks:
                    # 计算成功率
                    success_rate = round((task.success_count / task.total) * 100, 2) if task.total > 0 else 0
                    fail_rate = round((task.fail_count / task.total) * 100, 2) if task.total > 0 else 0
                    
                    # 生成邮件内容摘要（前100个字符）
                    content_summary = task.content[:100] + "..." if len(task.content) > 100 else task.content
                    
                    writer.writerow({
                        '任务ID': task.id,
                        '邮件主题': task.subject,
                        '发送时间': task.send_time.strftime('%Y-%m-%d %H:%M:%S') if task.send_time else '',
                        '总收件人数': task.total,
                        '成功数量': task.success_count,
                        '失败数量': task.fail_count,
                        '成功率': f"{success_rate}%",
                        '失败率': f"{fail_rate}%",
                        '任务状态': task.status,
                        '账户ID': task.account_id,
                        '邮件内容摘要': content_summary
                    })
                    
            return len(tasks)
        finally:
            self.db_manager.close_session(session)
            
    def export_task_details_to_csv(self, task_id, file_path):
        """
        导出任务详细信息到CSV文件
        
        Args:
            task_id (int): 任务ID
            file_path (str): 导出文件路径
            
        Returns:
            int: 导出的详情数量
        """
        session = self.db_manager.get_session()
        try:
            # 获取任务基本信息
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return 0
                
            details = session.query(TaskDetail).filter(TaskDetail.task_id == task_id).all()
            
            # 写入CSV文件 - 使用UTF-8编码并添加BOM头，确保中文字符正确显示
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # 扩展字段列表，添加更多详细信息
                fieldnames = [
                    '详情ID', '任务ID', '邮件主题', '收件人邮箱', '发送结果', 
                    '错误信息', '发送轮次', '发送时间', '任务状态'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for detail in details:
                    writer.writerow({
                        '详情ID': detail.id,
                        '任务ID': task_id,
                        '邮件主题': task.subject,
                        '收件人邮箱': detail.recipient_email,
                        '发送结果': detail.result,
                        '错误信息': detail.error_msg or '',
                        '发送轮次': detail.send_round,
                        '发送时间': task.send_time.strftime('%Y-%m-%d %H:%M:%S') if task.send_time else '',
                        '任务状态': task.status
                    })
                    
            return len(details)
        finally:
            self.db_manager.close_session(session)
            
    def add_task_detail(self, task_id, recipient_email, success, error_msg=None, send_round=1):
        """
        添加任务详情记录
        
        Args:
            task_id (int): 任务ID
            recipient_email (str): 收件人邮箱
            success (bool): 是否发送成功
            error_msg (str, optional): 错误信息
            send_round (int, optional): 发送轮次，默认为1
            
        Returns:
            int: 新增详情记录ID
        """
        session = self.db_manager.get_session()
        try:
            new_detail = TaskDetail(
                task_id=task_id,
                recipient_email=recipient_email,
                result="成功" if success else "失败",
                error_msg=error_msg,
                send_round=send_round
            )
            
            session.add(new_detail)
            session.commit()
            return new_detail.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def delete_task(self, task_id):
        """
        删除任务记录（包括详情）
        
        Args:
            task_id (int): 任务ID
        """
        session = self.db_manager.get_session()
        try:
            # 先删除任务详情
            session.query(TaskDetail).filter(TaskDetail.task_id == task_id).delete()
            
            # 再删除任务
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                session.delete(task)
                
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def export_to_csv(self, file_path, start_date=None, end_date=None):
        """
        导出任务记录到CSV文件（export_tasks_to_csv的别名）
        
        Args:
            file_path (str): 导出文件路径
            start_date (datetime, optional): 开始日期
            end_date (datetime, optional): 结束日期
            
        Returns:
            int: 导出的任务数量
        """
        return self.export_tasks_to_csv(file_path, start_date, end_date)
        
    def update_task_status(self, task_id, status, success_count, fail_count):
        """
        更新任务状态
        
        Args:
            task_id (int): 任务ID
            status (str): 任务状态
            success_count (int): 成功数量
            fail_count (int): 失败数量
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                task.success_count = success_count
                task.fail_count = fail_count
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def get_statistics(self, start_date=None, end_date=None):
        """
        获取发送统计信息
        
        Args:
            start_date (datetime, optional): 开始日期
            end_date (datetime, optional): 结束日期
            
        Returns:
            dict: 统计信息
        """
        session = self.db_manager.get_session()
        try:
            # 构建查询
            query = session.query(Task)
            if start_date:
                query = query.filter(Task.send_time >= start_date)
            if end_date:
                query = query.filter(Task.send_time <= end_date)
                
            tasks = query.all()
            
            total_tasks = len(tasks)
            total_emails = sum(task.total for task in tasks)
            total_success = sum(task.success_count for task in tasks)
            total_failed = sum(task.fail_count for task in tasks)
            
            # 计算成功率
            success_rate = (total_success / total_emails * 100) if total_emails > 0 else 0
            
            return {
                'total_tasks': total_tasks,
                'total_emails': total_emails,
                'total_success': total_success,
                'total_failed': total_failed,
                'success_rate': round(success_rate, 2)
            }
        finally:
            self.db_manager.close_session(session)