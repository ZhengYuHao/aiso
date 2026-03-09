"""
涉密信息检测 Category Agent
"""
from typing import List
from ...agents.base_agent import BaseCategoryAgent
from ...skills.base_skill import BaseSkill, SkillResult, Category
from ...skills.classified import ClassifiedMarkSkill, ClassifiedKeywordSkill, StampOCRSkill


class ClassifiedAgent(BaseCategoryAgent):
    """涉密信息检测 Category Agent"""

    name = "涉密信息检测"
    description = "检测涉密相关信息，包括密级标识、涉密关键词、公章等"
    category = Category.CLASSIFIED

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.skills: List[BaseSkill] = [
            ClassifiedMarkSkill(),
            ClassifiedKeywordSkill(),
            StampOCRSkill(),
        ]

    def get_skill_summaries(self) -> str:
        return "\n".join([
            f"- {s.name}: {s.description}"
            for s in self.skills
        ])
