"""
密级标识检测 Skill
"""
import re
from typing import Dict, Any
from ..base_skill import BaseSkill, SkillResult, Severity, Category


CLASSIFIED_MARKS = {
    "绝密": ["绝密", "最高机密", "国家绝密"],
    "机密": ["机密", "内部机密", "机密文件"],
    "秘密": ["秘密", "内部秘密", "秘密文件"],
    "内部": ["内部资料", "内部文件", "不准复制", "不准翻印", "限国内发行"],
}


class ClassifiedMarkSkill(BaseSkill):
    """密级标识检测 Skill"""

    name = "classified_mark"
    description = "检测文件中的密级标识，如'绝密'、'机密'、'秘密'等"
    category = Category.CLASSIFIED

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_marks = []

        for level, keywords in CLASSIFIED_MARKS.items():
            for keyword in keywords:
                if keyword in text:
                    found_marks.append({"level": level, "keyword": keyword})
                    break

        if found_marks:
            severity = Severity.CRITICAL
            if any(m["level"] == "内部" for m in found_marks):
                severity = Severity.MEDIUM

            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=severity,
                category=self.category,
                reason=f"检测到密级标识: {', '.join([m['keyword'] for m in found_marks])}",
                suggestion="该文件包含涉密标识，严禁发送至外部 AI 平台",
                evidence={"marks": found_marks},
                location="全文",
                matched_rule="classified_mark_keywords"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到密级标识",
            suggestion="",
            evidence={}
        )
