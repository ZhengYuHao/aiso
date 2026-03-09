"""
内部架构信息检测 Skill
"""
import re
from typing import Dict, Any
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class InfrastructureSkill(BaseSkill):
    """内部架构信息检测 Skill"""

    name = "infrastructure"
    description = "检测内网IP、服务器地址、拓扑结构等内部架构信息"
    category = Category.INFRASTRUCTURE

    PATTERNS = {
        "ip": r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b',
        "domain": r'\b(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+)(?:com|net|org|edu|gov|cn|com\.cn)\b',
    }

    KEYWORDS = [
        "内网", "私网", "VPN", "防火墙", "负载均衡",
        "服务器", "数据库", "Redis", "MongoDB", "MySQL",
        "拓扑", "架构", "网络", "交换机", "路由器",
    ]

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_info = []

        for info_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found_info.append({"type": info_type, "count": len(matches), "samples": matches[:3]})

        for keyword in self.KEYWORDS:
            if keyword in text:
                found_info.append({"type": "keyword", "keyword": keyword})

        if found_info:
            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=Severity.MEDIUM,
                category=self.category,
                reason=f"检测到内部架构信息: {len(found_info)} 处",
                suggestion="建议对内部架构信息进行脱敏处理后再发送至 AI 平台",
                evidence={"infrastructure": found_info},
                location="全文",
                matched_rule="infrastructure"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到内部架构信息",
            suggestion="",
            evidence={}
        )
