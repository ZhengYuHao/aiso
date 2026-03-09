"""
受限内容检测 Skill
"""
from typing import Dict, Any
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class RestrictedContentSkill(BaseSkill):
    """受限内容检测 Skill"""

    name = "restricted_content"
    description = "检测内部文件、版权内容、AI使用限制等受限内容"
    category = Category.RESTRICTED

    KEYWORDS = [
        "内部文件", "内部资料", "机密", "秘密",
        "版权", "著作权", "专利", "商业秘密",
        "不准外传", "不准复制", "限内部", "限部门",
        "AI使用限制", "禁止AI", "不适用于AI",
    ]

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_keywords = []

        for keyword in self.KEYWORDS:
            if keyword in text:
                found_keywords.append(keyword)

        if found_keywords:
            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=Severity.MEDIUM,
                category=self.category,
                reason=f"检测到受限内容: {', '.join(found_keywords[:5])}",
                suggestion="该文件包含受限内容，请确认是否允许发送至外部 AI 平台",
                evidence={"keywords": found_keywords},
                location="全文",
                matched_rule="restricted_content"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到受限内容",
            suggestion="",
            evidence={}
        )
