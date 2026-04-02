#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
账户管理模块
负责管理发件邮箱账户、SMTP配置、授权码加密存储和连接测试
"""

import os
import smtplib
from cryptography.fernet import Fernet
from db.db_manager import get_db_manager, Account
from datetime import datetime
from core.path_manager import get_path_manager

def _load_or_generate_key():
    """加载或生成加密密钥"""
    # 使用路径管理器获取密钥文件路径
    path_manager = get_path_manager()
    key_file_path = str(path_manager.get_encryption_key_path())
    
    # 确保data目录存在
    key_dir = os.path.dirname(key_file_path)
    if not os.path.exists(key_dir):
        os.makedirs(key_dir)
    
    # 如果密钥文件存在，则加载
    if os.path.exists(key_file_path):
        with open(key_file_path, 'rb') as f:
            return f.read()
    
    # 否则生成新密钥并保存
    new_key = Fernet.generate_key()
    with open(key_file_path, 'wb') as f:
        f.write(new_key)
    return new_key

# 加载或生成加密密钥
ENCRYPTION_KEY = _load_or_generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)


class AccountManager:
    """邮箱账户管理类"""
    
    # 常见邮箱服务商的SMTP配置
    SMTP_CONFIGS = {
        '163.com': {'smtp_server': 'smtp.163.com', 'port': 465},
        '126.com': {'smtp_server': 'smtp.126.com', 'port': 465},
        'qq.com': {'smtp_server': 'smtp.qq.com', 'port': 465},
        'gmail.com': {'smtp_server': 'smtp.gmail.com', 'port': 465},
        'outlook.com': {'smtp_server': 'smtp-mail.outlook.com', 'port': 587},
        'hotmail.com': {'smtp_server': 'smtp-mail.outlook.com', 'port': 587},
        'yahoo.com': {'smtp_server': 'smtp.mail.yahoo.com', 'port': 465},
        'yahoo.co.uk': {'smtp_server': 'smtp.mail.yahoo.co.uk', 'port': 465},
        'yahoo.ca': {'smtp_server': 'smtp.mail.yahoo.ca', 'port': 465},
        'sina.com': {'smtp_server': 'smtp.sina.com', 'port': 465},
        'sina.cn': {'smtp_server': 'smtp.sina.cn', 'port': 465},
        'sohu.com': {'smtp_server': 'smtp.sohu.com', 'port': 465},
        '139.com': {'smtp_server': 'smtp.139.com', 'port': 465},
        'wo.cn': {'smtp_server': 'smtp.wo.cn', 'port': 465},
        '189.cn': {'smtp_server': 'smtp.189.cn', 'port': 465},
        'tom.com': {'smtp_server': 'smtp.tom.com', 'port': 465},
        'aliyun.com': {'smtp_server': 'smtp.aliyun.com', 'port': 465},
        'foxmail.com': {'smtp_server': 'smtp.foxmail.com', 'port': 465},
        'live.com': {'smtp_server': 'smtp-mail.outlook.com', 'port': 587},
        'msn.com': {'smtp_server': 'smtp-mail.outlook.com', 'port': 587},
        'aol.com': {'smtp_server': 'smtp.aol.com', 'port': 587},
        'icloud.com': {'smtp_server': 'smtp.mail.me.com', 'port': 587},
        'me.com': {'smtp_server': 'smtp.mail.me.com', 'port': 587},
        'mac.com': {'smtp_server': 'smtp.mail.me.com', 'port': 587},
        'comcast.net': {'smtp_server': 'smtp.comcast.net', 'port': 587},
        'verizon.net': {'smtp_server': 'smtp.verizon.net', 'port': 465},
        'att.net': {'smtp_server': 'smtp.att.yahoo.com', 'port': 465},
        'earthlink.net': {'smtp_server': 'smtp.earthlink.net', 'port': 587},
        'cox.net': {'smtp_server': 'smtp.cox.net', 'port': 587},
        'charter.net': {'smtp_server': 'smtp.charter.net', 'port': 587},
        'optonline.net': {'smtp_server': 'smtp.optonline.net', 'port': 587},
        'roadrunner.com': {'smtp_server': 'smtp-server.roadrunner.com', 'port': 587},
        'juno.com': {'smtp_server': 'smtp.juno.com', 'port': 465},
        'netzero.com': {'smtp_server': 'smtp.netzero.com', 'port': 465},
        'aim.com': {'smtp_server': 'smtp.aim.com', 'port': 465},
        'rocketmail.com': {'smtp_server': 'smtp.rocketmail.com', 'port': 465},
        'btinternet.com': {'smtp_server': 'mail.btinternet.com', 'port': 465},
        'virginmedia.com': {'smtp_server': 'smtp.virginmedia.com', 'port': 465},
        'sky.com': {'smtp_server': 'smtp.sky.com', 'port': 587},
        'ntlworld.com': {'smtp_server': 'smtp.ntlworld.com', 'port': 587},
        'talktalk.net': {'smtp_server': 'smtp.talktalk.net', 'port': 587},
        'orange.fr': {'smtp_server': 'smtp.orange.fr', 'port': 465},
        'wanadoo.fr': {'smtp_server': 'smtp.wanadoo.fr', 'port': 465},
        'free.fr': {'smtp_server': 'smtp.free.fr', 'port': 587},
        'laposte.net': {'smtp_server': 'smtp.laposte.net', 'port': 465},
        't-online.de': {'smtp_server': 'secure.smtp.t-online.de', 'port': 465},
        'web.de': {'smtp_server': 'smtp.web.de', 'port': 587},
        'gmx.de': {'smtp_server': 'mail.gmx.net', 'port': 587},
        'gmx.com': {'smtp_server': 'mail.gmx.com', 'port': 587},
        'mail.ru': {'smtp_server': 'smtp.mail.ru', 'port': 465},
        'yandex.ru': {'smtp_server': 'smtp.yandex.ru', 'port': 465},
        'rambler.ru': {'smtp_server': 'smtp.rambler.ru', 'port': 465},
        'protonmail.com': {'smtp_server': 'smtp.protonmail.ch', 'port': 587},
        'zoho.com': {'smtp_server': 'smtp.zoho.com', 'port': 465},
        'posteo.de': {'smtp_server': 'posteo.de', 'port': 465},
        'tutanota.com': {'smtp_server': 'smtp.tutanota.com', 'port': 465},
        'fastmail.com': {'smtp_server': 'smtp.fastmail.com', 'port': 465},
        'inbox.com': {'smtp_server': 'smtp.inbox.com', 'port': 465},
        'hushmail.com': {'smtp_server': 'smtp.hushmail.com', 'port': 465},
        'lavabit.com': {'smtp_server': 'smtp.lavabit.com', 'port': 465},
        'runbox.com': {'smtp_server': 'smtp.runbox.com', 'port': 587},
        'countermail.com': {'smtp_server': 'smtp.countermail.com', 'port': 465},
        'disroot.org': {'smtp_server': 'smtp.disroot.org', 'port': 587},
        'riseup.net': {'smtp_server': 'smtp.riseup.net', 'port': 587},
        'autistici.org': {'smtp_server': 'smtp.autistici.org', 'port': 465},
        'systemausfall.org': {'smtp_server': 'smtp.systemausfall.org', 'port': 465},
        'keemail.me': {'smtp_server': 'smtp.keemail.me', 'port': 465},
        'tutamail.com': {'smtp_server': 'smtp.tutamail.com', 'port': 465},
        'mailfence.com': {'smtp_server': 'smtp.mailfence.com', 'port': 465},
        'kolabnow.com': {'smtp_server': 'smtp.kolabnow.com', 'port': 587},
        'startmail.com': {'smtp_server': 'smtp.startmail.com', 'port': 465},
        'pm.me': {'smtp_server': 'smtp.pm.me', 'port': 465},
        'hey.com': {'smtp_server': 'smtp.hey.com', 'port': 587},
        'mail.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'email.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'usa.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'myself.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'consultant.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'post.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'europe.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'asia.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'iname.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'writeme.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'dr.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'engineer.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'cheerful.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'techie.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'linuxmail.org': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'uymail.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'webname.com': {'smtp_server': 'smtp.mail.com', 'port': 587},
        'workmail.com': {'smtp_server': 'smtp.mail.com', 'port': 587}
    }
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
    def _encrypt_auth_code(self, auth_code):
        """加密授权码"""
        return cipher_suite.encrypt(auth_code.encode()).decode()
        
    def _decrypt_auth_code(self, encrypted_auth_code):
        """解密授权码"""
        return cipher_suite.decrypt(encrypted_auth_code.encode()).decode()
        
    def _get_smtp_config(self, email):
        """根据邮箱地址获取SMTP配置"""
        domain = email.split('@')[1]
        return self.SMTP_CONFIGS.get(domain, {'smtp_server': '', 'port': 0})
        
    def add_account(self, email, auth_code, alias=None, smtp_server=None, port=None, use_ssl=None):
        """
        添加邮箱账户
        
        Args:
            email (str): 邮箱地址
            auth_code (str): 授权码
            alias (str, optional): 备注名
            smtp_server (str, optional): SMTP服务器地址
            port (int, optional): 端口号
            use_ssl (bool, optional): 是否使用SSL
            
        Returns:
            int: 新增账户的ID
        """
        # 如果没有提供SMTP配置，则根据邮箱地址获取
        if smtp_server is None or port is None:
            smtp_config = self._get_smtp_config(email)
            if smtp_server is None:
                smtp_server = smtp_config['smtp_server']
            if port is None:
                port = smtp_config['port']
        
        # 加密授权码
        encrypted_auth_code = self._encrypt_auth_code(auth_code)
        
        # 创建账户对象
        account = Account(
            email=email,
            smtp_server=smtp_server,
            port=port,
            auth_code=encrypted_auth_code,
            alias=alias or email,
            use_ssl=use_ssl or False,
            created_at=datetime.now()
        )
        
        # 保存到数据库
        session = self.db_manager.get_session()
        try:
            session.add(account)
            session.commit()
            account_id = account.id
            return account_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def update_account(self, account_id, email=None, auth_code=None, alias=None, smtp_server=None, port=None, use_ssl=None):
        """
        更新邮箱账户信息
        
        Args:
            account_id (int): 账户ID
            email (str, optional): 邮箱地址
            auth_code (str, optional): 授权码
            alias (str, optional): 备注名
            smtp_server (str, optional): SMTP服务器地址
            port (int, optional): 端口号
            use_ssl (bool, optional): 是否使用SSL
        """
        session = self.db_manager.get_session()
        try:
            account = session.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"账户ID {account_id} 不存在")
                
            if email is not None:
                account.email = email
                # 如果邮箱改变，且没有手动指定SMTP配置，则更新SMTP配置
                if smtp_server is None and port is None:
                    smtp_config = self._get_smtp_config(email)
                    account.smtp_server = smtp_config['smtp_server']
                    account.port = smtp_config['port']
                
            if auth_code is not None:
                account.auth_code = self._encrypt_auth_code(auth_code)
                
            if alias is not None:
                account.alias = alias
                
            # 更新SMTP配置（如果提供了的话）
            if smtp_server is not None:
                account.smtp_server = smtp_server
            if port is not None:
                account.port = port
            if use_ssl is not None:
                account.use_ssl = use_ssl
                
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def delete_account(self, account_id):
        """
        删除邮箱账户
        
        Args:
            account_id (int): 账户ID
        """
        session = self.db_manager.get_session()
        try:
            account = session.query(Account).filter(Account.id == account_id).first()
            if account:
                session.delete(account)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
            
    def get_account(self, account_id):
        """
        获取指定账户信息（解密授权码）
        
        Args:
            account_id (int): 账户ID
            
        Returns:
            dict: 账户信息
        """
        session = self.db_manager.get_session()
        try:
            account = session.query(Account).filter(Account.id == account_id).first()
            if not account:
                return None
                
            # 解密授权码
            decrypted_auth_code = self._decrypt_auth_code(account.auth_code)
            
            return {
                'id': account.id,
                'email': account.email,
                'smtp_server': account.smtp_server,
                'port': account.port,
                'auth_code': decrypted_auth_code,
                'alias': account.alias,
                'use_ssl': account.use_ssl,
                'created_at': account.created_at
            }
        finally:
            self.db_manager.close_session(session)
            
    def list_accounts(self):
        """
        获取所有账户列表（不解密授权码）
        
        Returns:
            list: 账户列表
        """
        session = self.db_manager.get_session()
        try:
            accounts = session.query(Account).all()
            return [{
                'id': account.id,
                'email': account.email,
                'smtp_server': account.smtp_server,
                'port': account.port,
                'alias': account.alias,
                'use_ssl': account.use_ssl,
                'created_at': account.created_at
            } for account in accounts]
        finally:
            self.db_manager.close_session(session)
            
    def test_smtp_connection(self, account_id):
        """
        测试SMTP连接
        
        Args:
            account_id (int): 账户ID
            
        Returns:
            tuple: (是否成功, 错误信息)
        """
        account_info = self.get_account(account_id)
        if not account_info:
            return False, "账户不存在"
            
        try:
            # 根据use_ssl字段或端口号选择合适的连接方式
            if account_info['use_ssl'] or account_info['port'] == 465:
                # SSL连接
                server = smtplib.SMTP_SSL(account_info['smtp_server'], account_info['port'])
            else:
                # STARTTLS连接
                server = smtplib.SMTP(account_info['smtp_server'], account_info['port'])
                server.starttls()
                
            # 登录验证
            server.login(account_info['email'], account_info['auth_code'])
            server.quit()
            return True, "连接成功"
        except Exception as e:
            return False, str(e)
            
    def test_smtp_connection_with_params(self, smtp_server, port, email, password, use_ssl=False):
        """
        使用提供的参数测试SMTP连接
        
        Args:
            smtp_server (str): SMTP服务器地址
            port (int): 端口号
            email (str): 邮箱地址
            password (str): 密码或授权码
            use_ssl (bool): 是否使用SSL连接
            
        Returns:
            tuple: (是否成功, 错误信息)
        """
        try:
            # 根据端口号和use_ssl参数选择合适的连接方式
            if use_ssl or port == 465:
                # SSL连接
                server = smtplib.SMTP_SSL(smtp_server, port)
            elif port == 587:
                # STARTTLS连接
                server = smtplib.SMTP(smtp_server, port)
                server.starttls()
            else:
                # 默认连接方式
                server = smtplib.SMTP(smtp_server, port)
                
            # 登录验证
            server.login(email, password)
            server.quit()
            return True, "连接成功"
        except Exception as e:
            return False, str(e)