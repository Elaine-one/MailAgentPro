#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
收件人管理模块
负责导入CSV文件、管理联系人分组、批量选择等功能
"""

import csv
import pandas as pd
from db.db_manager import get_db_manager, Recipient
from datetime import datetime


class RecipientManager:
    """收件人管理类"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
    def import_from_csv(self, csv_file_path, group_name=None):
        """
        从CSV文件导入收件人
        
        Args:
            csv_file_path (str): CSV文件路径
            group_name (str, optional): 分组名称
            
        Returns:
            int: 成功导入的数量
        """
        try:
            # 使用pandas读取CSV文件
            df = pd.read_csv(csv_file_path)
            
            # 检查必需的列是否存在
            required_columns = ['name', 'email']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV文件必须包含以下列: {required_columns}")
                
            session = self.db_manager.get_session()
            imported_count = 0
            
            try:
                for _, row in df.iterrows():
                    # 检查邮箱是否已存在
                    existing_recipient = session.query(Recipient).filter(
                        Recipient.email == row['email']
                    ).first()
                    
                    if existing_recipient:
                        # 如果已存在，更新信息
                        existing_recipient.name = row['name']
                        if group_name:
                            existing_recipient.group_name = group_name
                    else:
                        # 创建新收件人
                        recipient = Recipient(
                            name=row['name'],
                            email=row['email'],
                            group_name=group_name,
                            created_at=datetime.now()
                        )
                        session.add(recipient)
                        
                    imported_count += 1
                    
                session.commit()
                return imported_count
            except Exception as e:
                session.rollback()
                raise e
            finally:
                self.db_manager.close_session(session)
                
        except Exception as e:
            raise Exception(f"导入CSV文件失败: {str(e)}")
            
    def add_recipient(self, name, email, group_name=None, variables=None):
        """
        添加单个收件人
        
        Args:
            name (str): 收件人姓名
            email (str): 收件人邮箱
            group_name (str, optional): 分组名称
            variables (str, optional): 变量数据
            
        Returns:
            int: 新增收件人的ID
        """
        session = self.db_manager.get_session()
        try:
            # 检查邮箱是否已存在
            existing_recipient = session.query(Recipient).filter(
                Recipient.email == email
            ).first()
            
            if existing_recipient:
                # 如果已存在，更新信息
                existing_recipient.name = name
                if group_name:
                    existing_recipient.group_name = group_name
                if variables is not None:
                    existing_recipient.variables = variables
                recipient_id = existing_recipient.id
            else:
                # 创建新收件人
                recipient = Recipient(
                    name=name,
                    email=email,
                    group_name=group_name,
                    variables=variables,
                    created_at=datetime.now()
                )
                session.add(recipient)
                session.flush()  # 获取ID但不提交
                recipient_id = recipient.id
                
            session.commit()
            return recipient_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def update_recipient(self, recipient_id, name=None, email=None, group_name=None, variables=None):
        """
        更新收件人信息
        
        Args:
            recipient_id (int): 收件人ID
            name (str, optional): 收件人姓名
            email (str, optional): 收件人邮箱
            group_name (str, optional): 分组名称
            variables (str, optional): 变量数据
        """
        session = self.db_manager.get_session()
        try:
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise ValueError(f"收件人ID {recipient_id} 不存在")
                
            if name is not None:
                recipient.name = name
                
            if email is not None:
                recipient.email = email
                
            if group_name is not None:
                recipient.group_name = group_name
                
            if variables is not None:
                recipient.variables = variables
                
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def delete_recipient(self, recipient_id):
        """
        删除收件人
        
        Args:
            recipient_id (int): 收件人ID
        """
        session = self.db_manager.get_session()
        try:
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if recipient:
                session.delete(recipient)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def delete_recipients_by_group(self, group_name):
        """
        删除指定分组的所有收件人
        
        Args:
            group_name (str): 分组名称
        """
        session = self.db_manager.get_session()
        try:
            recipients = session.query(Recipient).filter(Recipient.group_name == group_name).all()
            for recipient in recipients:
                session.delete(recipient)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def get_recipient(self, recipient_id):
        """
        获取指定收件人信息
        
        Args:
            recipient_id (int): 收件人ID
            
        Returns:
            dict: 收件人信息
        """
        session = self.db_manager.get_session()
        try:
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                return None
                
            return {
                'id': recipient.id,
                'name': recipient.name,
                'email': recipient.email,
                'group_name': recipient.group_name,
                'variables': recipient.variables,
                'created_at': recipient.created_at
            }
        finally:
            self.db_manager.close_session(session)
            
    def list_recipients(self, group_name=None):
        """
        获取收件人列表
        
        Args:
            group_name (str, optional): 分组名称，如果指定则只返回该分组的收件人
            
        Returns:
            list: 收件人列表
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(Recipient)
            if group_name:
                query = query.filter(Recipient.group_name == group_name)
            
            # 过滤掉分组占位符记录（邮箱以"group_"开头）
            query = query.filter(~Recipient.email.like("group_%@placeholder.com"))
                
            recipients = query.all()
            return [{
                'id': recipient.id,
                'name': recipient.name,
                'email': recipient.email,
                'group_name': recipient.group_name,
                'variables': recipient.variables,
                'created_at': recipient.created_at
            } for recipient in recipients]
        finally:
            self.db_manager.close_session(session)
            
    def search_recipients(self, keyword):
        """
        搜索收件人（按姓名或邮箱）
        
        Args:
            keyword (str): 搜索关键词
            
        Returns:
            list: 匹配的收件人列表
        """
        session = self.db_manager.get_session()
        try:
            recipients = session.query(Recipient).filter(
                (Recipient.name.contains(keyword)) | 
                (Recipient.email.contains(keyword))
            ).all()
            
            return [{
                'id': recipient.id,
                'name': recipient.name,
                'email': recipient.email,
                'group_name': recipient.group_name,
                'created_at': recipient.created_at
            } for recipient in recipients]
        finally:
            self.db_manager.close_session(session)
            
    def get_groups(self):
        """
        获取所有分组名称
        
        Returns:
            list: 分组名称列表
        """
        session = self.db_manager.get_session()
        try:
            groups = session.query(Recipient.group_name).distinct().all()
            # 过滤掉None值
            return [group[0] for group in groups if group[0]]
        finally:
            self.db_manager.close_session(session)
            
    def add_group(self, group_name):
        """
        添加分组（实际上分组是通过收件人的group_name字段管理的）
        这个方法会创建一个特殊的收件人记录来代表空分组
        
        Args:
            group_name (str): 分组名称
        """
        if not group_name or not group_name.strip():
            raise ValueError("分组名称不能为空")
            
        session = self.db_manager.get_session()
        try:
            # 检查分组是否已存在
            existing_group = session.query(Recipient).filter(
                Recipient.group_name == group_name
            ).first()
            
            if not existing_group:
                # 创建一个特殊的收件人记录来代表空分组
                # 使用特殊的邮箱地址来标识这是一个分组记录
                group_recipient = Recipient(
                    name=f"分组: {group_name}",
                    email=f"group_{group_name}@placeholder.com",
                    group_name=group_name,
                    created_at=datetime.now()
                )
                session.add(group_recipient)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
        
    def get_all_groups(self):
        """
        获取所有分组信息
        
        Returns:
            list: 分组信息列表，每个分组包含name字段
        """
        session = self.db_manager.get_session()
        try:
            groups = session.query(Recipient.group_name).distinct().all()
            return [{'name': group[0]} for group in groups if group[0]]  # 过滤掉None值
        finally:
            self.db_manager.close_session(session)
            
    def update_group_name(self, old_group_name, new_group_name):
        """
        更新分组名称
        
        Args:
            old_group_name (str): 旧分组名称
            new_group_name (str): 新分组名称
        """
        if not old_group_name or not new_group_name:
            raise ValueError("分组名称不能为空")
            
        session = self.db_manager.get_session()
        try:
            # 更新所有属于旧分组的收件人的分组名称
            recipients = session.query(Recipient).filter(Recipient.group_name == old_group_name).all()
            for recipient in recipients:
                recipient.group_name = new_group_name
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)