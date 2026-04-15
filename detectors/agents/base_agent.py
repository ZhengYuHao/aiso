"""
Category Agent 基类
"""
import json
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..skills.base_skill import BaseSkill, SkillResult, Category


SKILL_DECISION_PROMPT = """分析以下文本内容，决定需要调用哪些检测技能。

技能列表：
{skills}

文本内容：
{text_sample}

请返回 JSON 格式的决策结果：
{{
    "skills": ["skill1", "skill2"] - 需要调用的技能名称列表
    "reason": "决策原因"
}}

只返回 JSON，不要其他内容。
"""


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
        from ..logger import logger
        logger.debug(f"{self.name} - 开始执行 {len(self.skills)} 个 Skills...")
        
        results = []
        for skill in self.skills:
            try:
                logger.debug(f"{self.name} - 执行 Skill: {skill.name}")
                result = skill.detect(text, **kwargs)
                results.append(result)
                if result.is_triggered:
                    logger.debug(f"{self.name} - Skill[{skill.name}] 触发检测! severity={result.severity.value}, reason={result.reason[:50]}...")
                else:
                    logger.debug(f"{self.name} - Skill[{skill.name}] 未触发")
            except Exception as e:
                logger.error(f"{self.name} - Skill {skill.name} 执行失败: {str(e)}")
        
        triggered_count = sum(1 for r in results if r.is_triggered)
        logger.debug(f"{self.name} - Skills 执行完成，共 {len(self.skills)} 个，触发 {triggered_count} 个")
        return results

    def execute_triggered_only(self, text: str, **kwargs) -> List[SkillResult]:
        """只返回触发检测的 Skills 结果"""
        results = self.execute_all(text, **kwargs)
        return [r for r in results if r.is_triggered]

    def execute_with_llm(self, text: str, llm_client, **kwargs) -> List[SkillResult]:
        """使用 LLM 决策选择并执行 Skills"""
        from ..logger import logger

        if not llm_client:
            return self.execute_triggered_only(text, **kwargs)

        skills_str = self.get_skill_summaries()
        text_sample = text[:1500] if len(text) > 1500 else text

        prompt = SKILL_DECISION_PROMPT.format(
            skills=skills_str,
            text_sample=text_sample
        )

        try:
            result = llm_client._call_openai(prompt)
            logger.debug(f"{self.name} - LLM 技能选择返回: {result[:300]}")

            match = re.search(r'\{[\s\S]*\}', result)
            if match:
                decision = json.loads(match.group())
                selected_skills = decision.get("skills", [])
                logger.debug(f"{self.name} - LLM 选择的技能: {selected_skills}")

                results = []
                for skill in self.skills:
                    if skill.name in selected_skills:
                        try:
                            r = skill.detect(text, **kwargs)
                            results.append(r)
                        except Exception as e:
                            logger.error(f"Skill {skill.name} 执行失败: {str(e)}")
                return [r for r in results if r.is_triggered]
        except Exception as e:
            logger.error(f"{self.name} - LLM 决策失败，回退到规则: {str(e)}")

        return self.execute_triggered_only(text, **kwargs)
