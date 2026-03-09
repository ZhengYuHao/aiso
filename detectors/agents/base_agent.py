"""
Category Agent 基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..skills.base_skill import BaseSkill, SkillResult, Category


class BaseCategoryAgent(ABC):
    """Category Agent 抽象基类"""

    name: str = ""
    description: str = ""
    category: Category = Category.SENSITIVE
    skills: List[BaseSkill] = []

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    @abstractmethod
    def get_skill_summaries(self) -> str:
        """获取 Skills 描述，用于 LLM 决策"""
        pass

    def execute_all(self, text: str, **kwargs) -> List[SkillResult]:
        """执行所有 Skills（不使用 LLM 决策）"""
        results = []
        for skill in self.skills:
            try:
                result = skill.detect(text, **kwargs)
                results.append(result)
            except Exception as e:
                from ..logger import logger
                logger.error(f"Skill {skill.name} 执行失败: {str(e)}")
        return results

    def execute_triggered_only(self, text: str, **kwargs) -> List[SkillResult]:
        """只返回触发检测的 Skills 结果"""
        results = self.execute_all(text, **kwargs)
        return [r for r in results if r.is_triggered]
