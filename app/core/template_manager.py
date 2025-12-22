"""
模板管理模块
负责邮件模板的增删改查操作
"""

import json
import os
from datetime import datetime


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_file="templates.json"):
        """
        初始化模板管理器
        
        Args:
            template_file (str): 模板存储文件路径
        """
        # 如果是相对路径，则转换为绝对路径
        if not os.path.isabs(template_file):
            template_file = os.path.abspath(template_file)
        self.template_file = template_file
        self.templates = self._load_templates()
    
    def _load_templates(self):
        """加载模板数据"""
        if os.path.exists(self.template_file):
            try:
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def _save_templates(self):
        """保存模板数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.template_file), exist_ok=True)
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def add_template(self, name, subject, content):
        """
        添加模板
        
        Args:
            name (str): 模板名称
            subject (str): 邮件主题
            content (str): 邮件内容
            
        Returns:
            bool: 是否添加成功
        """
        # 检查模板名称是否已存在
        for template in self.templates:
            if template['name'] == name:
                raise ValueError(f"模板名称 '{name}' 已存在")
        
        # 添加新模板
        template = {
            'id': len(self.templates) + 1,
            'name': name,
            'subject': subject,
            'content': content,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.templates.append(template)
        return self._save_templates()
    
    def list_templates(self):
        """
        获取模板列表
        
        Returns:
            list: 模板列表
        """
        return self.templates
    
    def get_template(self, template_id):
        """
        根据ID获取模板
        
        Args:
            template_id (int): 模板ID
            
        Returns:
            dict or None: 模板信息
        """
        for template in self.templates:
            if template['id'] == template_id:
                return template
        return None
    
    def get_template_by_name(self, name):
        """
        根据名称获取模板
        
        Args:
            name (str): 模板名称
            
        Returns:
            dict or None: 模板信息
        """
        for template in self.templates:
            if template['name'] == name:
                return template
        return None
    
    def update_template(self, template_id, name=None, subject=None, content=None):
        """
        更新模板
        
        Args:
            template_id (int): 模板ID
            name (str, optional): 新模板名称
            subject (str, optional): 新邮件主题
            content (str, optional): 新邮件内容
            
        Returns:
            bool: 是否更新成功
        """
        for template in self.templates:
            if template['id'] == template_id:
                if name is not None:
                    # 检查新名称是否与其他模板冲突
                    for other_template in self.templates:
                        if other_template['id'] != template_id and other_template['name'] == name:
                            raise ValueError(f"模板名称 '{name}' 已存在")
                    template['name'] = name
                
                if subject is not None:
                    template['subject'] = subject
                
                if content is not None:
                    template['content'] = content
                
                template['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return self._save_templates()
        
        raise ValueError(f"模板ID {template_id} 不存在")
    
    def delete_template(self, template_id):
        """
        删除模板
        
        Args:
            template_id (int): 模板ID
            
        Returns:
            bool: 是否删除成功
        """
        for i, template in enumerate(self.templates):
            if template['id'] == template_id:
                self.templates.pop(i)
                return self._save_templates()
        
        raise ValueError(f"模板ID {template_id} 不存在")
    
    def search_templates(self, keyword):
        """
        搜索模板
        
        Args:
            keyword (str): 搜索关键词
            
        Returns:
            list: 匹配的模板列表
        """
        results = []
        for template in self.templates:
            if (keyword.lower() in template['name'].lower() or 
                keyword.lower() in template['subject'].lower() or 
                keyword.lower() in template['content'].lower()):
                results.append(template)
        return results