"""
凭证密钥检测 Skill
"""
import re
from typing import Dict, Any
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class CredentialSkill(BaseSkill):
    """凭证密钥检测 Skill"""

    name = "credential"
    description = "检测 API密钥、密码、数据库连接等凭证信息"
    category = Category.CREDENTIAL

    PATTERNS = {
        "api_key": r'(?:api[_-]?key|apikey|api[_-]?secret)[\s:=]+["\']?([a-zA-Z0-9_\-]{16,})["\']?',
        "password": r'(?:password|passwd|pwd)[\s:=]+["\']?([^\s"\']{6,})["\']?',
        "token": r'(?:token|access[_-]?token)[\s:=]+["\']?([a-zA-Z0-9_\-\.]{16,})["\']?',
        "secret": r'(?:secret|client[_-]?secret)[\s:=]+["\']?([a-zA-Z0-9_\-\.]{16,})["\']?',
    }

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_credentials = []

        for cred_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_credentials.append({"type": cred_type, "count": len(matches)})

        if found_credentials:
            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=Severity.CRITICAL,
                category=self.category,
                reason=f"检测到凭证密钥: {', '.join([c['type'] for c in found_credentials])}",
                suggestion="严禁将凭证密钥发送至外部 AI 平台！请立即脱敏处理",
                evidence={"credentials": found_credentials},
                location="全文",
                matched_rule="credential_pattern"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到凭证密钥",
            suggestion="",
            evidence={}
        )
