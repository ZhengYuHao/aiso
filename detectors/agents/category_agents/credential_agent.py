"""
凭证密钥检测 Category Agent
"""
from typing import List
from ...agents.base_agent import BaseCategoryAgent
from ...skills.base_skill import BaseSkill, SkillResult, Category
from ...skills.credential import CredentialSkill


class CredentialAgent(BaseCategoryAgent):
    """凭证密钥检测 Category Agent"""

    name = "凭证密钥检测"
    description = "检测 API密钥、密码、数据库连接等凭证信息"
    category = Category.CREDENTIAL

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.skills: List[BaseSkill] = [
            CredentialSkill(),
        ]

    def get_skill_summaries(self) -> str:
        return "\n".join([
            f"- {s.name}: {s.description}"
            for s in self.skills
        ])
