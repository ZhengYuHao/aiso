"""
涉密关键词检测 Skill
"""
import json
import os
from typing import Dict, Any, List
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class ClassifiedKeywordSkill(BaseSkill):
    """涉密关键词检测 Skill"""

    name = "classified_keyword"
    description = "检测文件中是否包含涉密关键词，如军事、国安、外交等"
    category = Category.CLASSIFIED

    def __init__(self):
        self.keywords = self._load_keywords()

    def _load_keywords(self) -> Dict[str, List[str]]:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", "classified_keywords.json"
        )
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "military": ["军事", "部队", "军区", "军工", "武器", "导弹"],
            "state_security": ["国安", "国家安全", "情报", "间谍"],
            "diplomatic": ["外交", "使馆", "领事", "外事"],
            "core_tech": ["核心技术", "源代码", "算法", "专利"],
        }

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_keywords = []

        for level, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found_keywords.append({"level": level, "keyword": keyword})

        if found_keywords:
            severity = Severity.CRITICAL
            high_levels = ["military", "state_security", "diplomatic"]
            if any(k["level"] not in high_levels for k in found_keywords):
                severity = Severity.HIGH

            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=severity,
                category=self.category,
                reason=f"检测到涉密关键词: {', '.join([k['keyword'] for k in found_keywords[:5]])}",
                suggestion="该文件包含涉密关键词，严禁发送至外部 AI 平台",
                evidence={"keywords": found_keywords[:10]},
                location="全文",
                matched_rule="classified_keyword"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到涉密关键词",
            suggestion="",
            evidence={}
        )
