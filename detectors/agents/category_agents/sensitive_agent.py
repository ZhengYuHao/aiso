"""
敏感信息检测 Category Agent
"""
from typing import List
from ...agents.base_agent import BaseCategoryAgent
from ...skills.base_skill import BaseSkill, SkillResult, Category
from ...skills.sensitive import PIISkill, BusinessSensitiveSkill


class SensitiveAgent(BaseCategoryAgent):
    """敏感信息检测 Category Agent"""

    name = "敏感信息检测"
    description = "检测个人隐私信息和商业敏感信息"
    category = Category.SENSITIVE

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.skills: List[BaseSkill] = [
            PIISkill(),
            BusinessSensitiveSkill(),
        ]

    def get_skill_summaries(self) -> str:
        return "\n".join([
            f"- {s.name}: {s.description}"
            for s in self.skills
        ])
