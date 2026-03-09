"""
受限内容检测 Category Agent
"""
from typing import List
from ...agents.base_agent import BaseCategoryAgent
from ...skills.base_skill import BaseSkill, SkillResult, Category
from ...skills.restricted import RestrictedContentSkill


class RestrictedAgent(BaseCategoryAgent):
    """受限内容检测 Category Agent"""

    name = "受限内容检测"
    description = "检测内部文件、版权内容、AI使用限制等受限内容"
    category = Category.RESTRICTED

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.skills: List[BaseSkill] = [
            RestrictedContentSkill(),
        ]

    def get_skill_summaries(self) -> str:
        return "\n".join([
            f"- {s.name}: {s.description}"
            for s in self.skills
        ])
