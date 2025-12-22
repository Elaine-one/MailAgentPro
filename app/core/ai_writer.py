#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI撰写模块
负责接入多种大模型、自动识别Key类型、容错机制等
"""

import json
import os
import logging
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate


# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'llm_errors.log')

# 创建详细的日志配置
logger = logging.getLogger('SmartLLMClient')
logger.setLevel(logging.DEBUG)

# 如果已经有处理器，先清除
if logger.handlers:
    logger.handlers.clear()

# 文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 禁用其他库的日志
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


class SmartLLMClient:
    """智能LLM客户端，支持多模型自动识别与容错"""
    
    _instance = None
    
    def __new__(cls, config_path="config.json"):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path="config.json"):
        """
        初始化智能LLM客户端
        
        Args:
            config_path (str): 配置文件路径
        """
        # 每次初始化都重新加载配置，确保配置持久化
        self.config_path = config_path
        from .config_manager import ConfigManager
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 如果模型未初始化，则进行初始化
        if not hasattr(self, 'llm') or self.llm is None:
            self.llm = self._init_llm_with_fallback()
        if not hasattr(self, 'streaming_llm') or self.streaming_llm is None:
            self.streaming_llm = self._init_streaming_llm()
            
    def refresh_models(self):
        """强制重新从配置初始化模型（用于配置更改或环境修复后）"""
        self.config = self.config_manager.get_config()
        self.llm = self._init_llm_with_fallback()
        self.streaming_llm = self._init_streaming_llm()
        return self.llm is not None
        
    def get_config(self):
        """
        获取当前配置
        
        Returns:
            dict: 当前配置字典
        """
        return self.config.copy()
        
    def _load_config(self):
        """加载配置文件"""
        try:
            from .config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # 确保AI配置存在
            if "ai_config" not in config:
                config["ai_config"] = {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "primary_key": "",
                    "secondary_key": "",
                    "max_tokens": 2048,
                    "temperature": 0.7
                }
            
            # 为了向后兼容，将ai_config中的值复制到顶层
            ai_config = config.get("ai_config", {})
            if "llm_primary_key" not in config and "primary_key" in ai_config:
                config["llm_primary_key"] = ai_config["primary_key"]
            if "llm_secondary_key" not in config and "secondary_key" in ai_config:
                config["llm_secondary_key"] = ai_config["secondary_key"]
            if "provider" not in config and "provider" in ai_config:
                config["provider"] = ai_config["provider"]
            if "model" not in config and "model" in ai_config:
                config["model"] = ai_config["model"]
            if "max_tokens" not in config and "max_tokens" in ai_config:
                config["max_tokens"] = ai_config["max_tokens"]
            if "temperature" not in config and "temperature" in ai_config:
                config["temperature"] = ai_config["temperature"]
            
            return config
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            # 返回默认配置
            return {
                "llm_primary_key": "",
                "llm_secondary_key": "",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "max_tokens": 2048,
                "temperature": 0.7
            }
            
    def _detect_provider(self, key):
        """
        根据API Key前缀识别模型提供商
        
        Args:
            key (str): API Key
            
        Returns:
            str: 提供商名称
        """
        if not key or not isinstance(key, str):
            return "unknown"
            
        # 清理key中的空格
        key = key.strip()
        
        # 更精确的提供商检测
        if key.startswith("sk-") and len(key) > 10:  # OpenAI格式：sk-xxxxxxxx
            return "openai"
        elif key.startswith("ak-") and len(key) > 10:  # 通义千问格式：ak-xxxxxxxx
            return "tongyi"
        elif key.startswith("qwen-") and len(key) > 10:  # 通义千问格式：qwen-xxxxxxxx
            return "tongyi"
        elif key.startswith("moonshot-") and len(key) > 15:  # Moonshot格式：moonshot-xxxxxxxx
            return "moonshot"
        elif key.startswith("ds-") and len(key) > 10:  # DeepSeek格式：ds-xxxxxxxx
            return "deepseek"
        else:
            # 如果无法识别，检查key长度和格式
            if len(key) < 10:
                return "invalid"  # key太短
            elif " " in key:
                return "invalid"  # 包含空格
            else:
                return "unknown"  # 未知格式
            
    def _init_llm_with_fallback(self):
        """
        初始化LLM模型，基于用户手动选择的供应商配置
        
        Returns:
            LLM对象或None
        """
        logger.info("开始初始化LLM模型")
        
        # 检查是否有可用的API密钥
        primary_key = self.config.get("llm_primary_key", "").strip()
        secondary_key = self.config.get("llm_secondary_key", "").strip()
        provider = self.config.get("provider", "openai").strip()
        model = self.config.get("model", "gpt-3.5-turbo").strip()
        
        if not primary_key and not secondary_key:
            logger.error("未配置API密钥，请先在设置中配置主密钥或备用密钥")
            print("未配置API密钥，请先在设置中配置主密钥或备用密钥")
            return None
        
        # 验证用户选择的供应商和模型
        if provider == "auto":
            logger.warning("自动检测已禁用，请手动选择供应商")
            print("自动检测已禁用，请手动选择供应商")
            provider = "openai"  # 默认使用OpenAI
            
        # 基于用户手动选择的供应商进行初始化
        if primary_key:
            try:
                logger.info("尝试使用主密钥初始化模型")
                logger.info(f"用户选择的提供商: {provider}")
                logger.info(f"用户选择的模型: {model}")
                
                # 直接使用用户选择的供应商和模型
                llm = self._create_llm(provider, primary_key, model)
                logger.info("主模型初始化成功 (跳过连接测试)")
                return llm
            except Exception as e:
                logger.error(f"主模型初始化失败: {e}", exc_info=True)
                print(f"主模型初始化失败: {e}")
                
        # 如果主密钥失败，尝试使用备用密钥
        if secondary_key:
            try:
                logger.info("尝试使用备用密钥初始化模型")
                logger.info(f"用户选择的提供商: {provider}")
                logger.info(f"用户选择的模型: {model}")
                
                # 直接使用用户选择的供应商和模型
                llm = self._create_llm(provider, secondary_key, model)
                logger.info("备用模型初始化成功 (跳过连接测试)")
                return llm
            except Exception as e:
                logger.error(f"备用模型初始化失败: {e}", exc_info=True)
                print(f"备用模型初始化失败: {e}")
                
        # 如果都失败，提供详细的错误信息
        error_msg = "所有模型初始化失败，AI功能不可用。请检查：\n"
        error_msg += "1. API密钥是否正确配置\n"
        error_msg += "2. 网络连接是否正常\n"
        error_msg += "3. 密钥是否有足够的额度\n"
        error_msg += "4. 模型服务是否可用"
        
        logger.error(error_msg)
        print(error_msg)
        return None
        
    def _create_llm(self, provider, api_key, model="auto", streaming=False):
        """
        根据提供商创建对应的LLM对象
        
        Args:
            provider (str): 提供商名称
            api_key (str): API密钥
            model (str): 模型名称，默认为auto
            streaming (bool): 是否启用流式输出
            
        Returns:
            LLM对象
        """
        common_params = {
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 2048),
            "streaming": streaming
        }
        
        # 如果指定了具体模型，添加到参数中
        if model != "auto" and model:
            common_params["model"] = model
        
        if provider == "openai":
            # 为OpenAI设置默认模型
            if "model" not in common_params:
                common_params["model"] = "gpt-3.5-turbo"
            return ChatOpenAI(openai_api_key=api_key, **common_params)
        elif provider == "deepseek":
            # 移除deepseek支持，因为deepinfra库的使用方式与预期不符
            raise ValueError("DeepSeek模型暂不支持")
        elif provider == "tongyi":
            # 为通义千问设置默认模型
            if "model" not in common_params:
                common_params["model"] = "qwen-turbo"
            return ChatTongyi(dashscope_api_key=api_key, **common_params)
        elif provider == "moonshot":
            # 为Moonshot设置默认模型
            if "model" not in common_params:
                common_params["model"] = "moonshot-v1-8k"
            return ChatOpenAI(
                openai_api_key=api_key,
                base_url="https://api.moonshot.cn/v1",
                **common_params
            )
        else:
            raise ValueError(f"不支持的模型提供商: {provider}")
            
    def _init_streaming_llm(self):
        """
        初始化流式输出的LLM模型
        
        Returns:
            流式输出的LLM对象或None
        """
        logger.info("开始初始化流式LLM模型")
        
        # 检查是否有可用的API密钥
        primary_key = self.config.get("llm_primary_key", "").strip()
        secondary_key = self.config.get("llm_secondary_key", "").strip()
        provider = self.config.get("provider", "openai").strip()
        model = self.config.get("model", "gpt-3.5-turbo").strip()
        
        if not primary_key and not secondary_key:
            logger.error("未配置API密钥，无法初始化流式LLM")
            return None
        
        # 验证用户选择的供应商和模型
        if provider == "auto":
            logger.warning("自动检测已禁用，请手动选择供应商")
            provider = "openai"  # 默认使用OpenAI
            
        # 基于用户手动选择的供应商进行初始化
        if primary_key:
            try:
                logger.info("尝试使用主密钥初始化流式模型")
                logger.info(f"用户选择的提供商: {provider}")
                logger.info(f"用户选择的模型: {model}")
                
                # 直接使用用户选择的供应商 and 模型，启用流式输出
                llm = self._create_llm(provider, primary_key, model, streaming=True)
                logger.info("主流式模型初始化成功 (跳过连接测试)")
                return llm
            except Exception as e:
                logger.error(f"主流式模型初始化失败: {e}", exc_info=True)
                print(f"主流式模型初始化失败: {e}")
                
        # 如果主密钥失败，尝试使用备用密钥
        if secondary_key:
            try:
                logger.info("尝试使用备用密钥初始化流式模型")
                logger.info(f"用户选择的提供商: {provider}")
                logger.info(f"用户选择的模型: {model}")
                
                # 直接使用用户选择的供应商和模型，启用流式输出
                llm = self._create_llm(provider, secondary_key, model, streaming=True)
                logger.info("备用流式模型初始化成功 (跳过连接测试)")
                return llm
            except Exception as e:
                logger.error(f"备用流式模型初始化失败: {e}", exc_info=True)
                print(f"备用流式模型初始化失败: {e}")
                
        # 如果都失败，提供详细的错误信息
        error_msg = "所有流式模型初始化失败，流式输出功能不可用。请检查：\n"
        error_msg += "1. API密钥是否正确配置\n"
        error_msg += "2. 网络连接是否正常\n"
        error_msg += "3. 密钥是否有足够的额度\n"
        error_msg += "4. 模型服务是否可用"
        
        logger.error(error_msg)
        print(error_msg)
        return None
        
    def update_config(self, primary_key=None, secondary_key=None, provider=None, model=None, 
                     max_tokens=None, temperature=None, preferred_model=None):
        """
        更新配置
        
        Args:
            primary_key (str, optional): 主API密钥
            secondary_key (str, optional): 备用API密钥
            provider (str, optional): 模型供应商
            model (str, optional): 模型名称
            max_tokens (int, optional): 最大token数
            temperature (float, optional): 温度参数
            preferred_model (str, optional): 首选模型
        """
        try:
            from .config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # 更新AI配置
            if "ai_config" not in config:
                config["ai_config"] = {}
            
            ai_config = config["ai_config"]
            
            if primary_key is not None:
                ai_config["primary_key"] = primary_key
                config["llm_primary_key"] = primary_key
            if secondary_key is not None:
                ai_config["secondary_key"] = secondary_key
                config["llm_secondary_key"] = secondary_key
            if provider is not None:
                ai_config["provider"] = provider
                config["provider"] = provider
            if model is not None:
                ai_config["model"] = model
                config["model"] = model
            if max_tokens is not None:
                ai_config["max_tokens"] = max_tokens
                config["max_tokens"] = max_tokens
            if temperature is not None:
                ai_config["temperature"] = temperature
                config["temperature"] = temperature
            if preferred_model is not None:
                ai_config["preferred_model"] = preferred_model
                config["preferred_model"] = preferred_model
            
            # 保存配置
            config_manager.save_config(config)
            
            # 更新本地配置
            self.config = config
            
            # 重新初始化LLM
            self.llm = self._init_llm_with_fallback()
            # 重新初始化流式LLM
            self.streaming_llm = self._init_streaming_llm()
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise
        
    def generate_mail(self, topic, tone="formal", language="zh-CN"):
        """
        生成邮件内容
        
        Args:
            topic (str): 邮件主题
            tone (str): 语气 (formal, casual, friendly, professional)
            language (str): 语言
            
        Returns:
            str: 生成的邮件内容
        """
        if not self.llm:
            return "AI模型不可用，请检查配置或网络连接。"
            
        # 定义语气描述
        tone_descriptions = {
            "formal": "正式、商务",
            "casual": "随意、轻松",
            "friendly": "友好、亲切",
            "professional": "专业、严谨"
        }
        
        tone_desc = tone_descriptions.get(tone, "正式、商务")
        
        prompt_template = """
你是一位专业的邮件撰写助手，请根据以下要求生成一封{language}邮件：

主题：{topic}
语气：{tone} ({tone_desc})
要求：
1. 邮件结构完整，包括称呼、正文、结尾
2. 内容符合{tone}语气
3. 语言流畅自然
4. 不要包含任何占位符，直接输出完整的邮件内容

请开始撰写：
""".strip()
        
        prompt = prompt_template.format(
            topic=topic,
            tone=tone,
            tone_desc=tone_desc,
            language="中文" if language.startswith("zh") else "英文"
        )
        
        try:
            messages = [
                SystemMessage(content="You are a professional email writing assistant."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            error_msg = f"邮件生成失败: {str(e)}"
            logging.error(error_msg)
            return f"邮件生成失败，请稍后重试。错误信息：{str(e)}"
            
    def adjust_tone(self, content, target_tone):
        """
        调整邮件语气
        
        Args:
            content (str): 原始内容
            target_tone (str): 目标语气
            
        Returns:
            str: 调整后的内容
        """
        if not self.llm:
            return "AI模型不可用，请检查配置或网络连接。"
            
        tone_descriptions = {
            "formal": "正式、商务",
            "casual": "随意、轻松",
            "friendly": "友好、亲切",
            "professional": "专业、严谨"
        }
        
        target_desc = tone_descriptions.get(target_tone, "正式、商务")
        
        prompt = f"""
请将以下邮件内容调整为{target_tone}语气 ({target_desc})：

原始内容：
{content}

要求：
1. 保持原意不变
2. 调整语言风格和措辞
3. 保持邮件结构完整
4. 直接输出调整后的完整内容，不要添加其他说明

调整后的邮件：
""".strip()
        
        try:
            messages = [
                SystemMessage(content="You are a professional email writing assistant."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            error_msg = f"语气调整失败: {str(e)}"
            logging.error(error_msg)
            return f"语气调整失败，请稍后重试。错误信息：{str(e)}"
            
    def summarize_mail(self, content, max_length=200, summary_type="general", language="zh"):
        """
        生成邮件摘要
        
        Args:
            content (str): 邮件内容
            max_length (int): 最大摘要长度
            summary_type (str): 摘要类型 (general, action_items, key_points, detailed)
            language (str): 摘要语言 (zh, en)
            
        Returns:
            str: 邮件摘要
        """
        if not self.llm:
            return "AI模型不可用，请检查配置或网络连接。"
            
        # 根据摘要类型调整提示词
        type_descriptions = {
            "general": "通用摘要",
            "action_items": "行动项摘要",
            "key_points": "关键点摘要",
            "detailed": "详细摘要"
        }
        
        type_desc = type_descriptions.get(summary_type, "通用摘要")
        lang_desc = "中文" if language == "zh" else "英文"
        
        # 根据摘要类型定制提示词
        if summary_type == "action_items":
            prompt = f"""
请为以下邮件内容生成一个不超过{max_length}字的行动项摘要：

邮件内容：
{content}

要求：
1. 提取所有需要采取的行动项和待办事项
2. 明确指出每个行动项的负责人（如果有）
3. 突出截止日期和时间节点（如果有）
4. 使用清晰的列表格式呈现
5. 语言简洁明了，不超过{max_length}字
6. 使用{lang_desc}输出

行动项摘要：
""".strip()
        elif summary_type == "key_points":
            prompt = f"""
请为以下邮件内容生成一个不超过{max_length}字的关键点摘要：

邮件内容：
{content}

要求：
1. 提取邮件的核心要点和重要信息
2. 突出关键决策和结论
3. 使用要点列表形式呈现
4. 语言简洁明了，不超过{max_length}字
5. 使用{lang_desc}输出

关键点摘要：
""".strip()
        elif summary_type == "detailed":
            prompt = f"""
请为以下邮件内容生成一个不超过{max_length}字的详细摘要：

邮件内容：
{content}

要求：
1. 包含邮件的主要背景和上下文
2. 详细说明讨论的主要话题
3. 提取重要的决策和结论
4. 包含相关的行动项和时间安排
5. 保持逻辑清晰，层次分明
6. 语言流畅自然，不超过{max_length}字
7. 使用{lang_desc}输出

详细摘要：
""".strip()
        else:  # general
            prompt = f"""
请为以下邮件内容生成一个不超过{max_length}字的通用摘要：

邮件内容：
{content}

要求：
1. 突出核心要点
2. 语言简洁明了
3. 不超过{max_length}字
4. 直接输出摘要内容，不要添加其他说明
5. 使用{lang_desc}输出

摘要：
""".strip()
        
        try:
            messages = [
                SystemMessage(content=f"You are a professional content summarization assistant, skilled in creating {type_desc} in {lang_desc}."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            error_msg = f"邮件摘要生成失败: {str(e)}"
            logging.error(error_msg)
            return f"邮件摘要生成失败，请稍后重试。错误信息：{str(e)}"
            
    def translate_mail(self, content, target_language="en", translation_style="professional", preserve_formatting=True):
        """
        翻译邮件内容
        
        Args:
            content (str): 原始内容
            target_language (str): 目标语言 (en, zh, ja, ko, fr, de, es, ru)
            translation_style (str): 翻译风格 (professional, casual, formal, literal)
            preserve_formatting (bool): 是否保留原始格式
            
        Returns:
            str: 翻译后的内容
        """
        logger.info(f"开始翻译邮件，目标语言: {target_language}, 翻译风格: {translation_style}")
        
        # 检查内容是否为空
        if not content or not content.strip():
            error_msg = "翻译内容为空，请输入需要翻译的邮件内容"
            logger.error(error_msg)
            return error_msg
            
        if not self.llm:
            error_msg = "AI模型不可用，请检查配置或网络连接。"
            logger.error(error_msg)
            return error_msg
            
        # 扩展语言支持
        language_names = {
            "en": "英文",
            "zh": "中文", 
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "ru": "俄文"
        }
        
        # 翻译风格描述
        style_descriptions = {
            "professional": "专业商务风格",
            "casual": "随意轻松风格",
            "formal": "正式礼貌风格",
            "literal": "直译风格"
        }
        
        target_lang_name = language_names.get(target_language, target_language)
        style_desc = style_descriptions.get(translation_style, "专业商务风格")
        format_desc = "保留原始格式和结构" if preserve_formatting else "重新组织格式"
        
        # 根据翻译风格定制提示词
        if translation_style == "professional":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 保持原意不变
2. 使用专业商务术语和表达方式
3. 语言自然流畅，符合商务邮件习惯
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif translation_style == "casual":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 保持原意不变
2. 使用轻松自然的日常表达方式
3. 语言流畅易懂，符合非正式邮件习惯
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif translation_style == "formal":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 保持原意不变
2. 使用正式礼貌的表达方式和敬语
3. 语言严谨规范，符合正式邮件习惯
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif translation_style == "literal":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 尽可能保持原文结构和表达方式
2. 逐句翻译，不添加或删减内容
3. 保持原文的语气和风格
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        else:  # 默认使用专业风格
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}：

原始内容：
{content}

要求：
1. 保持原意不变
2. 保持邮件格式和结构
3. 语言自然流畅
4. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        
        try:
            logger.debug(f"准备翻译内容，长度: {len(content)} 字符")
            messages = [
                SystemMessage(content=f"You are a professional translation assistant, skilled in {style_desc} for {target_lang_name}."),
                HumanMessage(content=prompt)
            ]
            
            logger.debug("开始调用LLM进行翻译")
            response = self.llm.invoke(messages)
            
            if not response or not hasattr(response, 'content'):
                error_msg = "翻译返回结果格式错误"
                logger.error(error_msg)
                return error_msg
                
            result = response.content.strip()
            if not result:
                error_msg = "翻译结果为空，请稍后重试"
                logger.error(error_msg)
                return error_msg
                
            logger.info(f"翻译成功，结果长度: {len(result)} 字符")
            return result
        except Exception as e:
            error_msg = f"邮件翻译失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"邮件翻译失败，请稍后重试。错误信息：{str(e)}"
            

            

            
    def generate_mail_with_subject(self, requirements, tone="formal", language="zh-CN", template_type="general", recipient_type="general"):
        """
        根据需求自动生成邮件主题和内容
        
        Args:
            requirements (str): 邮件需求描述
            tone (str): 语气 (formal, casual, friendly, professional)
            language (str): 语言
            template_type (str): 模板类型 (general, invitation, meeting, follow_up, apology, request, announcement)
            recipient_type (str): 收件人类型 (general, client, colleague, manager, team, external)
            
        Returns:
            dict: 包含主题和内容的字典
                - subject (str): 邮件主题
                - content (str): 邮件内容
        """
        if not self.llm:
            return {"subject": "", "content": "AI模型不可用，请检查配置或网络连接。"}
            
        # 定义语气描述
        tone_descriptions = {
            "formal": "正式、商务",
            "casual": "随意、轻松", 
            "friendly": "友好、亲切",
            "professional": "专业、严谨"
        }
        
        # 定义模板类型描述
        template_descriptions = {
            "general": "通用邮件",
            "invitation": "邀请邮件",
            "meeting": "会议邮件",
            "follow_up": "跟进邮件",
            "apology": "道歉邮件",
            "request": "请求邮件",
            "announcement": "公告邮件"
        }
        
        # 定义收件人类型描述
        recipient_descriptions = {
            "general": "一般收件人",
            "client": "客户",
            "colleague": "同事",
            "manager": "上级",
            "team": "团队成员",
            "external": "外部合作伙伴"
        }
        
        tone_desc = tone_descriptions.get(tone, "正式、商务")
        template_desc = template_descriptions.get(template_type, "通用邮件")
        recipient_desc = recipient_descriptions.get(recipient_type, "一般收件人")
        
        prompt = f"""
你是一位专业的邮件撰写助手。请根据以下需求生成一封完整的邮件：

需求描述：{requirements}
邮件类型：{template_type} ({template_desc})
收件人类型：{recipient_type} ({recipient_desc})
语气要求：{tone} ({tone_desc})
语言：{'中文' if language.startswith('zh') else '英文'}

请按照以下格式输出：

主题：[生成的邮件主题]

内容：[生成的邮件内容]

要求：
1. 主题要简洁明了，能够准确反映邮件内容
2. 邮件内容结构完整，包括称呼、正文、结尾
3. 语气要符合{recipient_desc}的身份和{tone_desc}的要求
4. 语言流畅自然，不要包含占位符
5. 根据{template_desc}的特点，确保邮件内容符合该类型邮件的常见结构和表达方式
6. 直接输出完整的邮件内容，不要添加其他说明

请开始：
""".strip()
        
        try:
            messages = [
                SystemMessage(content=f"You are a professional email writing assistant, skilled in writing {template_desc} for {recipient_desc} with {tone_desc}."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            
            # 解析响应，提取主题和内容
            response_text = response.content
            
            # 多种格式的解析尝试
            subject = ""
            content = ""
            
            # 尝试格式1：主题：[主题]\n内容：[内容]
            subject_start = response_text.find("主题：")
            content_start = response_text.find("内容：")
            
            if subject_start != -1 and content_start != -1:
                # 提取主题
                subject_end = response_text.find("\n", subject_start)
                if subject_end == -1 or subject_end > content_start:
                    subject_end = content_start
                subject = response_text[subject_start + 3:subject_end].strip()
                
                # 提取内容
                content = response_text[content_start + 3:].strip()
                
            # 尝试格式2：Subject: [主题]\nContent: [内容] (英文格式)
            elif response_text.find("Subject:") != -1 and response_text.find("Content:") != -1:
                subject_start = response_text.find("Subject:")
                content_start = response_text.find("Content:")
                
                subject_end = response_text.find("\n", subject_start)
                if subject_end == -1 or subject_end > content_start:
                    subject_end = content_start
                subject = response_text[subject_start + 8:subject_end].strip()
                
                content = response_text[content_start + 8:].strip()
                
            # 尝试格式3：第一行作为主题，其余作为内容
            else:
                lines = response_text.split('\n')
                if len(lines) >= 2:
                    # 第一行作为主题
                    subject = lines[0].strip()
                    # 移除可能的主题前缀
                    for prefix in ["主题：", "Subject:", "标题：", "Title:"]:
                        if subject.startswith(prefix):
                            subject = subject[len(prefix):].strip()
                            break
                    
                    # 其余作为内容
                    content_lines = []
                    for i, line in enumerate(lines[1:]):
                        # 跳过空行和内容前缀行
                        if line.strip() and not any(line.strip().startswith(prefix) for prefix in ["内容：", "Content:", "正文：", "Body:"]):
                            content_lines.append(line)
                    
                    content = '\n'.join(content_lines).strip()
                else:
                    # 如果只有一行，作为内容，主题为空
                    content = response_text.strip()
            
            # 如果主题为空但内容不为空，尝试从内容中提取第一行作为主题
            if not subject and content:
                content_lines = content.split('\n')
                if len(content_lines) > 0:
                    first_line = content_lines[0].strip()
                    # 如果第一行看起来像主题（长度适中，不含特殊字符）
                    if 5 <= len(first_line) <= 50 and not first_line.startswith('尊敬的') and not first_line.startswith('Dear'):
                        subject = first_line
                        content = '\n'.join(content_lines[1:]).strip()
            
            # 清理内容中的主题行
            if subject and content:
                # 如果内容以主题开头，移除它
                if content.startswith(subject):
                    content = content[len(subject):].strip()
                # 移除内容中可能重复的主题行
                content_lines = content.split('\n')
                if len(content_lines) > 0 and content_lines[0].strip() == subject:
                    content = '\n'.join(content_lines[1:]).strip()
            
            return {"subject": subject, "content": content}
                    
        except Exception as e:
            error_msg = f"邮件生成失败: {str(e)}"
            logging.error(error_msg)
            return {"subject": "", "content": f"邮件生成失败，请稍后重试。错误信息：{str(e)}"}
    
    def generate_mail_stream(self, requirements, tone="formal", language="zh-CN", template_type="general", recipient_type="general"):
        """
        根据需求流式生成邮件内容
        
        Args:
            requirements (str): 邮件需求描述
            tone (str): 语气 (formal, casual, friendly, professional)
            language (str): 语言
            template_type (str): 模板类型 (general, invitation, meeting, follow_up, apology, request, announcement)
            recipient_type (str): 收件人类型 (general, client, colleague, manager, team, external)
            
        Returns:
            generator: 生成器，每次生成一个文本块
        """
        # 初始化流式LLM
        if not self._init_streaming_llm():
            yield "AI模型不可用，请检查配置或网络连接。"
            return
            
        # 定义语气描述
        tone_descriptions = {
            "formal": "正式、商务",
            "casual": "随意、轻松", 
            "friendly": "友好、亲切",
            "professional": "专业、严谨"
        }
        
        # 定义模板类型描述
        template_descriptions = {
            "general": "通用邮件",
            "invitation": "邀请邮件",
            "meeting": "会议邮件",
            "follow_up": "跟进邮件",
            "apology": "道歉邮件",
            "request": "请求邮件",
            "announcement": "公告邮件"
        }
        
        # 定义收件人类型描述
        recipient_descriptions = {
            "general": "一般收件人",
            "client": "客户",
            "colleague": "同事",
            "manager": "上级",
            "team": "团队成员",
            "external": "外部合作伙伴"
        }
        
        tone_desc = tone_descriptions.get(tone, "正式、商务")
        template_desc = template_descriptions.get(template_type, "通用邮件")
        recipient_desc = recipient_descriptions.get(recipient_type, "一般收件人")
        
        prompt = f"""
你是一位专业的邮件撰写助手。请根据以下需求生成一封完整的邮件：

需求描述：{requirements}
邮件类型：{template_type} ({template_desc})
收件人类型：{recipient_type} ({recipient_desc})
语气要求：{tone} ({tone_desc})
语言：{'中文' if language.startswith('zh') else '英文'}

请按照以下格式输出：

主题：[生成的邮件主题]

内容：[生成的邮件内容]

要求：
1. 主题要简洁明了，能够准确反映邮件内容
2. 邮件内容结构完整，包括称呼、正文、结尾
3. 语气要符合{recipient_desc}的身份和{tone_desc}的要求
4. 语言流畅自然，不要包含占位符
5. 根据{template_desc}的特点，确保邮件内容符合该类型邮件的常见结构和表达方式
6. 直接输出完整的邮件内容，不要添加其他说明

请开始：
""".strip()
        
        try:
            messages = [
                SystemMessage(content=f"You are a professional email writing assistant, skilled in writing {template_desc} for {recipient_desc} with {tone_desc}."),
                HumanMessage(content=prompt)
            ]
            
            # 使用流式输出
            for chunk in self.streaming_llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            error_msg = f"流式邮件生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"流式邮件生成失败，请稍后重试。错误信息：{str(e)}"
    
    def generate_subject_stream(self, requirements, tone="formal", language="zh-CN", template_type="general", recipient_type="general"):
        """
        根据需求流式生成邮件主题
        
        Args:
            requirements (str): 邮件需求描述
            tone (str): 语气 (formal, casual, friendly, professional)
            language (str): 语言
            template_type (str): 模板类型 (general, invitation, meeting, follow_up, apology, request, announcement)
            recipient_type (str): 收件人类型 (general, client, colleague, manager, team, external)
            
        Returns:
            generator: 生成器，每次生成一个文本块
        """
        # 初始化流式LLM
        if not self._init_streaming_llm():
            yield "AI模型不可用，请检查配置或网络连接。"
            return
            
        # 定义语气描述
        tone_descriptions = {
            "formal": "正式、商务",
            "casual": "随意、轻松", 
            "friendly": "友好、亲切",
            "professional": "专业、严谨"
        }
        
        # 定义模板类型描述
        template_descriptions = {
            "general": "通用邮件",
            "invitation": "邀请邮件",
            "meeting": "会议邮件",
            "follow_up": "跟进邮件",
            "apology": "道歉邮件",
            "request": "请求邮件",
            "announcement": "公告邮件"
        }
        
        # 定义收件人类型描述
        recipient_descriptions = {
            "general": "一般收件人",
            "client": "客户",
            "colleague": "同事",
            "manager": "上级",
            "team": "团队成员",
            "external": "外部合作伙伴"
        }
        
        tone_desc = tone_descriptions.get(tone, "正式、商务")
        template_desc = template_descriptions.get(template_type, "通用邮件")
        recipient_desc = recipient_descriptions.get(recipient_type, "一般收件人")
        
        prompt = f"""
你是一位专业的邮件撰写助手。请根据以下需求生成一个简洁明了的邮件主题：

需求描述：{requirements}
邮件类型：{template_type} ({template_desc})
收件人类型：{recipient_type} ({recipient_desc})
语气要求：{tone} ({tone_desc})
语言：{'中文' if language.startswith('zh') else '英文'}

要求：
1. 主题要简洁明了，能够准确反映邮件内容
2. 主题长度控制在20个字符以内
3. 语气要符合{recipient_desc}的身份和{tone_desc}的要求
4. 语言流畅自然，不要包含占位符
5. 直接输出主题，不要添加其他说明

请开始：
""".strip()
        
        try:
            messages = [
                SystemMessage(content=f"You are a professional email writing assistant, skilled in writing {template_desc} for {recipient_desc} with {tone_desc}."),
                HumanMessage(content=prompt)
            ]
            
            # 使用流式输出
            for chunk in self.streaming_llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            error_msg = f"流式主题生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"流式主题生成失败，请稍后重试。错误信息：{str(e)}"
    
    def summarize_mail_stream(self, mail_text, summary_type="general"):
        """
        流式生成邮件摘要
        
        Args:
            mail_text (str): 邮件内容
            summary_type (str): 摘要类型 (general, action_items, key_points, detailed)
            
        Returns:
            generator: 生成器，每次生成一个文本块
        """
        # 初始化流式LLM
        if not self._init_streaming_llm():
            yield "AI模型不可用，请检查配置或网络连接。"
            return
            
        # 根据摘要类型调整提示词
        type_descriptions = {
            "general": "通用摘要",
            "action_items": "行动项摘要",
            "key_points": "关键点摘要",
            "detailed": "详细摘要"
        }
        
        type_desc = type_descriptions.get(summary_type, "通用摘要")
        
        # 根据摘要类型定制提示词
        if summary_type == "action_items":
            prompt = f"""
请为以下邮件内容生成一个行动项摘要：

邮件内容：
{mail_text}

要求：
1. 提取所有需要采取的行动项和待办事项
2. 明确指出每个行动项的负责人（如果有）
3. 突出截止日期和时间节点（如果有）
4. 使用清晰的列表格式呈现
5. 语言简洁明了
6. 直接输出摘要内容

行动项摘要：
""".strip()
        elif summary_type == "key_points":
            prompt = f"""
请为以下邮件内容生成一个关键点摘要：

邮件内容：
{mail_text}

要求：
1. 提取邮件的核心要点和重要信息
2. 突出关键决策和结论
3. 使用要点列表形式呈现
4. 语言简洁明了
5. 直接输出摘要内容

关键点摘要：
""".strip()
        else:  # general
            prompt = f"""
请为以下邮件内容生成一个通用摘要：

邮件内容：
{mail_text}

要求：
1. 突出核心要点
2. 语言简洁明了
3. 直接输出摘要内容，不要添加其他说明

摘要：
""".strip()
        
        try:
            messages = [
                SystemMessage(content=f"You are a professional content summarization assistant, skilled in creating {type_desc}."),
                HumanMessage(content=prompt)
            ]
            
            # 使用流式输出
            for chunk in self.streaming_llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            error_msg = f"流式摘要生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"流式摘要生成失败，请稍后重试。错误信息：{str(e)}"
    
    def translate_mail_stream(self, content, target_language="en", style="professional", preserve_formatting=True):
        """
        流式翻译邮件内容
        
        Args:
            content (str): 邮件内容
            target_language (str): 目标语言 (en, zh, ja, fr, de, es, ru, ko)
            style (str): 翻译风格 (professional, casual, formal, literal)
            preserve_formatting (bool): 是否保留格式
            
        Returns:
            generator: 生成器，每次生成一个文本块
        """
        # 初始化流式LLM
        if not self._init_streaming_llm():
            yield "AI模型不可用，请检查配置或网络连接。"
            return
            
        # 语言映射
        language_map = {
            "en": "英文",
            "zh": "中文",
            "ja": "日文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "ru": "俄文",
            "ko": "韩文"
        }
        
        # 风格映射
        style_map = {
            "professional": "专业商务风格",
            "casual": "随意轻松风格",
            "formal": "正式严谨风格",
            "literal": "直译风格"
        }
        
        target_lang_name = language_map.get(target_language, "英文")
        style_desc = style_map.get(style, "专业商务风格")
        format_desc = "保留原始格式和结构" if preserve_formatting else "不保留原始格式"
        
        # 根据风格构建不同的提示词
        if style == "professional":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 使用{target_lang_name}的{style_desc}
2. 保持邮件的专业性和商务感
3. 确保术语准确，表达地道
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif style == "casual":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 使用{target_lang_name}的{style_desc}
2. 语言自然流畅，贴近日常交流
3. 适当使用口语化表达
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif style == "formal":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 使用{target_lang_name}的{style_desc}
2. 语言庄重得体，符合正式场合
3. 使用敬语和礼貌表达
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        elif style == "literal":
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}，使用{style_desc}：

原始内容：
{content}

要求：
1. 尽可能保持原文结构和表达方式
2. 逐句翻译，不添加或删减内容
3. 保持原文的语气和风格
4. {format_desc}
5. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        else:  # 默认使用专业风格
            prompt = f"""
请将以下邮件内容翻译为{target_lang_name}：

原始内容：
{content}

要求：
1. 保持原意不变
2. 保持邮件格式和结构
3. 语言自然流畅
4. 直接输出翻译后的内容，不要添加其他说明

翻译结果：
""".strip()
        
        try:
            # 检查流式LLM是否可用
            if not self.streaming_llm:
                logger.error("流式LLM未初始化，尝试重新初始化")
                self.streaming_llm = self._init_streaming_llm()
                
                # 如果仍然不可用，回退到非流式方式
                if not self.streaming_llm:
                    logger.warning("流式LLM不可用，回退到非流式方式")
                    result = self.translate_mail(content, target_lang, style)
                    for word in result.split():
                        yield word + " "
                    return
            
            messages = [
                SystemMessage(content=f"You are a professional translation assistant, skilled in {style_desc} for {target_lang_name}."),
                HumanMessage(content=prompt)
            ]
            
            # 使用流式输出
            for chunk in self.streaming_llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            error_msg = f"流式翻译失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"流式翻译失败，请稍后重试。错误信息：{str(e)}"

    def test_connection(self):
        """
        测试LLM连接，基于用户配置的供应商和模型
        
        Returns:
            dict: 包含测试结果的字典
                - success (bool): 是否成功
                - model (str): 使用的模型
                - error (str): 错误信息（如果有的话）
                - response_time (float): 响应时间（毫秒）
        """
        import threading
        import time
        import queue
        
        # 测试连接的函数
        def test_llm_connection(result_queue, provider, primary_key, model, config):
            try:
                # 创建临时的LLM实例进行测试，避免影响主实例
                temp_llm = self._create_llm(provider, primary_key, model)
                
                # 测试连接
                test_msg = [
                    SystemMessage(content="You are a helpful assistant."),
                    HumanMessage(content="Hello")
                ]
                response = temp_llm.invoke(test_msg)
                
                # 获取实际使用的模型名称
                actual_model = model if model != "auto" else f"{provider}-default"
                
                # 将结果放入队列
                result_queue.put({
                    'success': True,
                    'model': actual_model,
                    'error': None
                })
            except Exception as e:
                # 将错误放入队列
                result_queue.put({
                    'success': False,
                    'model': None,
                    'error': str(e)
                })
        
        try:
            # 获取用户配置的供应商和模型信息
            config = self.config
            provider = config.get("provider", "openai")
            model = config.get("model", "gpt-3.5-turbo")
            
            # 尝试从ai_config获取配置
            ai_config = config.get("ai_config", {})
            if not provider and "provider" in ai_config:
                provider = ai_config["provider"]
            if not model and "model" in ai_config:
                model = ai_config["model"]
            
            # 获取API密钥
            primary_key = config.get("llm_primary_key", "").strip()
            if not primary_key and "primary_key" in ai_config:
                primary_key = ai_config["primary_key"].strip()
            
            if not primary_key:
                return {
                    'success': False,
                    'model': None,
                    'error': '请先配置API密钥',
                    'response_time': 0
                }
            
            # 如果用户配置为auto，则警告并强制使用openai
            if provider == "auto":
                logger.warning("自动检测已禁用，强制使用openai供应商")
                provider = "openai"
            
            # 设置超时时间（30秒）
            timeout_seconds = 30
            
            # 记录开始时间
            start_time = time.time()
            
            # 创建队列用于线程间通信
            result_queue = queue.Queue()
            
            # 创建并启动线程
            test_thread = threading.Thread(
                target=test_llm_connection,
                args=(result_queue, provider, primary_key, model, config)
            )
            test_thread.daemon = True  # 设置为守护线程，主线程退出时自动结束
            test_thread.start()
            
            # 等待线程完成或超时
            test_thread.join(timeout_seconds)
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 检查线程是否仍在运行（超时）
            if test_thread.is_alive():
                return {
                    'success': False,
                    'model': None,
                    'error': f'连接测试超时（{timeout_seconds}秒），可能是网络问题或API服务不可用\n\n建议：\n1. 检查网络连接是否正常\n2. 尝试切换到其他模型供应商\n3. 检查防火墙设置是否阻止了API请求',
                    'response_time': round(response_time, 2)
                }
            
            # 从队列获取结果
            try:
                result = result_queue.get_nowait()
                result['response_time'] = round(response_time, 2)
                return result
            except queue.Empty:
                return {
                    'success': False,
                    'model': None,
                    'error': '无法获取测试结果',
                    'response_time': round(response_time, 2)
                }
        except Exception as e:
            # 提供更详细的错误信息
            error_msg = f"连接测试失败: {str(e)}"
            
            # 根据错误类型提供更具体的建议
            if "timeout" in str(e).lower():
                error_msg += "\n\n建议：\n1. 检查网络连接是否正常\n2. 尝试切换到其他模型供应商\n3. 检查防火墙设置是否阻止了API请求"
            elif "api" in str(e).lower() and "key" in str(e).lower():
                error_msg += "\n\n建议：\n1. 检查API密钥是否正确\n2. 确认API密钥是否有效\n3. 检查API密钥是否有足够的额度"
            elif "connection" in str(e).lower():
                error_msg += "\n\n建议：\n1. 检查网络连接是否正常\n2. 确认API服务是否可用\n3. 尝试使用其他网络环境"
            elif "rate" in str(e).lower() and "limit" in str(e).lower():
                error_msg += "\n\n建议：\n1. 稍后重试\n2. 检查API使用配额\n3. 考虑升级API计划"
            
            logger.error(error_msg)
            return {
                'success': False,
                'model': None,
                'error': error_msg,
                'response_time': 0
            }
