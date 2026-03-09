"""
LLM 客户端模块 —— 支持 OpenAI ChatGPT、阿里云通义千问、百度文心一言等
"""
import os
import json
from typing import Optional, Dict, List, Any
import requests

# 加载 .env 文件
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass


DETECTION_PROMPTS = {
    "classified": """你是一个内容安全检测专家。请分析以下文本内容，检测是否包含涉密信息：
- 国家秘密（绝密、机密、秘密）
- 涉密文件标识
- 涉密关键词

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "涉密信息类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "classified_mark": """你是一个密级标识检测专家。请分析以下文本内容，检测是否包含密级标识：
- 绝密、机密、秘密
- 内部、公开
- 密级标注文件标题
- 编号中的密级标识

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "密级标识类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "stamp_ocr": """你是一个公章OCR检测专家。请分析以下文本内容，检测是否包含公章或印章相关信息：
- 公章文字
- 印章图案描述
- 签字信息
- 落款日期和单位

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "公章类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "pii": """你是一个隐私保护检测专家。请分析以下文本内容，检测是否包含个人隐私信息：
- 身份证号
- 手机号
- 银行卡号
- 邮箱地址
- 家庭住址
- 其他个人敏感信息

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "隐私信息类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "business": """你是一个商业信息安全检测专家。请分析以下文本内容，检测是否包含商业敏感信息：
- 未公开的财务数据
- 核心算法
- 客户名单
- 薪酬信息
- 商业机密

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "商业敏感类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "restricted_content": """你是一个受限内容检测专家。请分析以下文本内容，检测是否包含受限内容：
- 政治敏感内容
- 暴力血腥内容
- 色情低俗内容
- 赌博相关内容
- 毒品相关推广
- 邪教组织宣传

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "受限内容类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "credential": """你是一个凭证安全检测专家。请分析以下文本内容，检测是否包含凭证密钥信息：
- API Key
- Token
- 密码
- 数据库连接串
- SSH 密钥

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "凭证类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",

    "infrastructure": """你是一个基础设施安全检测专家。请分析以下文本内容，检测是否包含内部架构信息：
- 内网IP地址
- 端口号
- 服务器路径
- 主机名

请返回JSON格式的检测结果：
{{
    "is_sensitive": true/false,
    "category": "基础设施类型",
    "severity": "critical/high/medium/low",
    "reason": "检测理由",
    "suggestion": "处理建议"
}}

要检测的文本：""",
}


class LLMClient:
    """LLM API 客户端 - 从环境变量读取配置"""

    def __init__(self, config_path: str = None):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self._load_config()

    def _load_config(self):
        """从环境变量加载配置"""
        self.config = {
            "provider": self.provider,
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
            },
            "aliyun": {
                "api_key": os.getenv("ALIYUN_API_KEY", ""),
                "model": os.getenv("ALIYUN_MODEL", "qwen-turbo"),
            },
            "baidu": {
                "api_key": os.getenv("BAIDU_API_KEY", ""),
                "secret_key": os.getenv("BAIDU_SECRET_KEY", ""),
            },
            "timeout": int(os.getenv("LLM_TIMEOUT", "60")),
        }

    def detect(self, text: str, category: str = "classified") -> Dict[str, Any]:
        """
        使用 LLM 进行内容检测

        Args:
            text: 待检测文本
            category: 检测类别 (classified/pii/business/credential/infrastructure)

        Returns:
            检测结果字典
        """
        if not text or not text.strip():
            return {"is_sensitive": False, "category": "", "severity": "low", "reason": "", "suggestion": ""}

        prompt = DETECTION_PROMPTS.get(category, DETECTION_PROMPTS["classified"]) + text

        try:
            if self.provider == "openai":
                result = self._call_openai(prompt)
            elif self.provider == "aliyun":
                result = self._call_aliyun(prompt)
            elif self.provider == "baidu":
                result = self._call_baidu(prompt)
            else:
                result = {"is_sensitive": False, "error": f"Unknown provider: {self.provider}"}

            return self._parse_result(result)
        except Exception as e:
            return {
                "is_sensitive": False,
                "error": str(e),
                "category": "",
                "severity": "low",
                "reason": "",
                "suggestion": ""
            }

    def _call_openai(self, prompt: str) -> str:
        """调用 OpenAI API"""
        config = self.config.get("openai", {})
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model", "gpt-4o")
        temperature = config.get("temperature", 0.1)

        if not api_key:
            raise ValueError("OpenAI API key not configured (OPENAI_API_KEY)")

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }

        timeout = self.config.get("timeout", 60)
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_aliyun(self, prompt: str) -> str:
        """调用阿里云通义千问 API"""
        config = self.config.get("aliyun", {})
        api_key = config.get("api_key", "")
        model = config.get("model", "qwen-turbo")

        if not api_key:
            raise ValueError("Aliyun API key not configured (ALIYUN_API_KEY)")

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "disable"
        }

        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "temperature": 0.1,
                "result_format": "message"
            }
        }

        timeout = self.config.get("timeout", 60)
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        result = response.json()
        return result["output"]["choices"]["message"]["content"]

    def _call_baidu(self, prompt: str) -> str:
        """调用百度文心一言 API"""
        config = self.config.get("baidu", {})
        api_key = config.get("api_key", "")
        secret_key = config.get("secret_key", "")

        if not api_key or not secret_key:
            raise ValueError("Baidu API key not configured (BAIDU_API_KEY, BAIDU_SECRET_KEY)")

        access_token = self._get_baidu_token(api_key, secret_key)
        if not access_token:
            raise ValueError("Failed to get Baidu access token")

        url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-lite-8k"
        params = {"access_token": access_token}

        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        timeout = self.config.get("timeout", 60)
        response = requests.post(url, params=params, json=payload, timeout=timeout)
        response.raise_for_status()

        result = response.json()
        return result["result"]

    def _get_baidu_token(self, api_key: str, secret_key: str) -> Optional[str]:
        """获取百度 access_token"""
        try:
            auth_url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key
            }

            response = requests.post(auth_url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get("access_token")
        except Exception:
            pass

        return None

    def _parse_result(self, result_str: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 结果"""
        try:
            import re
            json_match = re.search(r'\{[^{}]*\}', result_str, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "is_sensitive": result.get("is_sensitive", False),
                    "category": result.get("category", ""),
                    "severity": result.get("severity", "low"),
                    "reason": result.get("reason", ""),
                    "suggestion": result.get("suggestion", "")
                }
        except Exception:
            pass

        return {
            "is_sensitive": False,
            "category": "",
            "severity": "low",
            "reason": "",
            "suggestion": ""
        }
