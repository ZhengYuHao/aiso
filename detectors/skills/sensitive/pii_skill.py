"""
个人隐私信息检测 Skill (PII)
"""
import re
from typing import Dict, Any
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class PIISkill(BaseSkill):
    """个人隐私信息检测 Skill"""

    name = "pii"
    description = "检测身份证号、手机号、银行卡号等个人隐私信息"
    category = Category.SENSITIVE

    PATTERNS = {
        "id_card": r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b',
        "phone": r'\b1[3-9]\d{9}\b',
        "bank_card": r'\b(?:6217|6222|6235|6282|6229|6226|6210|6225|6228|6010|6220)\d{10,13}\b',
    }

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_pii = []

        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                if pii_type == "id_card":
                    found_pii.append({"type": "身份证号", "count": len(matches)})
                elif pii_type == "phone":
                    found_pii.append({"type": "手机号", "count": len(matches)})
                elif pii_type == "bank_card":
                    found_pii.append({"type": "银行卡号", "count": len(matches)})

        if found_pii:
            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=Severity.HIGH,
                category=self.category,
                reason=f"检测到个人隐私信息: {', '.join([p['type'] for p in found_pii])}",
                suggestion="建议对个人隐私信息进行脱敏处理后再发送至 AI 平台",
                evidence={"pii": found_pii},
                location="全文",
                matched_rule="pii_pattern"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到个人隐私信息",
            suggestion="",
            evidence={}
        )
