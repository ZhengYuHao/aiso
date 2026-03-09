"""
公章 OCR 检测 Skill
"""
from typing import Dict, Any, List
from ..base_skill import BaseSkill, SkillResult, Severity, Category


STAMP_CLASSIFIED_KEYWORDS = {
    "绝密": ["绝密", "机密", "秘密"],
    "公文标识": ["发文", "收文", "急件", "特件", "内部资料"],
}


class StampOCRSkill(BaseSkill):
    """公章 OCR 检测 Skill"""

    name = "stamp_ocr"
    description = "通过 OCR 识别公章中的文字，检测是否包含涉密信息"
    category = Category.CLASSIFIED

    def detect(self, text: str, ocr_text: str = "", **kwargs) -> SkillResult:
        if not ocr_text:
            return SkillResult(
                skill_name=self.name,
                is_triggered=False,
                severity=Severity.LOW,
                category=self.category,
                reason="无 OCR 结果",
                suggestion="",
                evidence={}
            )

        found_stamps = []
        for level, keywords in STAMP_CLASSIFIED_KEYWORDS.items():
            for keyword in keywords:
                if keyword in ocr_text:
                    found_stamps.append({"level": level, "keyword": keyword})
                    break

        if found_stamps:
            severity = Severity.CRITICAL if any(s["level"] == "绝密" for s in found_stamps) else Severity.HIGH

            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=severity,
                category=self.category,
                reason=f"OCR 识别到公章包含涉密标识: {', '.join([s['keyword'] for s in found_stamps])}",
                suggestion="该公章包含涉密标识，严禁发送至外部 AI 平台",
                evidence={"stamps": found_stamps, "ocr_text": ocr_text[:500]},
                location="图片/公章区域",
                matched_rule="stamp_ocr"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到公章涉密标识",
            suggestion="",
            evidence={}
        )
