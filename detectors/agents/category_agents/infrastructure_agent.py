"""
内部架构信息检测 Category Agent
"""
from typing import List
from ...agents.base_agent import BaseCategoryAgent
from ...skills.base_skill import BaseSkill, SkillResult, Category
from ...skills.infrastructure import InfrastructureSkill


class InfrastructureAgent(BaseCategoryAgent):
    """内部架构信息检测 Category Agent"""

    name = "内部架构检测"
    description = "检测内网IP、服务器地址、拓扑结构等内部架构信息"
    category = Category.INFRASTRUCTURE

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.skills: List[BaseSkill] = [
            InfrastructureSkill(),
        ]

    def get_skill_summaries(self) -> str:
        return "\n".join([
            f"- {s.name}: {s.description}"
            for s in self.skills
        ])
