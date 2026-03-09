"""
Master Agent - 总调度 Agent
支持 LLM 智能决策选择合适的 Skills
"""
import json
from typing import List, Dict, Any
from .base_agent import BaseCategoryAgent
from .category_agents import (
    ClassifiedAgent,
    SensitiveAgent,
    RestrictedAgent,
    CredentialAgent,
    InfrastructureAgent,
)
from ..skills.base_skill import SkillResult, Category


LLM_DECISION_PROMPT = """你是一个安全检测 Agent，需要分析文本内容并决定调用哪些检测技能。

可用的检测类别：
{categories}

技能列表：
{skills}

请分析以下文本内容（长度：{text_len} 字符）：
{text_sample}

请返回 JSON 格式的决策结果：
{{
    "need_detect": true/false - 是否需要检测
    "categories": ["category1", "category2"] - 需要检测的类别列表
    "reason": "决策原因" - 简要说明为什么选择这些类别
}}

只返回 JSON，不要其他内容。
"""


class MasterAgent:
    """总调度 Agent"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.category_agents: List[BaseCategoryAgent] = [
            ClassifiedAgent(llm_client),
            SensitiveAgent(llm_client),
            RestrictedAgent(llm_client),
            CredentialAgent(llm_client),
            InfrastructureAgent(llm_client),
        ]

    def get_category_summaries(self) -> str:
        """获取所有 Category Agent 描述"""
        return "\n".join([
            f"- {agent.name}: {agent.description}"
            for agent in self.category_agents
        ])

    def detect(self, text: str, use_llm_decision: bool = False, **kwargs) -> List[SkillResult]:
        """
        执行检测
        
        Args:
            text: 待检测文本
            use_llm_decision: 是否使用 LLM 决策
        """
        from ..logger import logger
        logger.info(f"========== Master Agent 开始检测 ==========")
        logger.info(f"文本长度: {len(text)}, LLM决策: {use_llm_decision}")

        all_results = []

        if use_llm_decision and self.llm_client:
            logger.info(">>> 使用 LLM 智能决策模式 <<<")
            all_results = self._detect_with_llm(text, **kwargs)
        else:
            logger.info(">>> 使用规则引擎模式 <<<")
            for agent in self.category_agents:
                try:
                    logger.info(f"--- 调度 Category Agent: {agent.name} ---")
                    logger.info(f"该分类包含 {len(agent.skills)} 个 Skills: {[s.name for s in agent.skills]}")
                    results = agent.execute_triggered_only(text, **kwargs)
                    if results:
                        logger.info(f"[{agent.name}] 发现问题: {len(results)} 个")
                        for r in results:
                            logger.info(f"  >>> Skill[{r.skill_name}] 触发! category={r.category.value}, severity={r.severity.value}")
                            logger.info(f"  >>> reason: {r.reason[:80]}...")
                        all_results.extend(results)
                    else:
                        logger.info(f"[{agent.name}] 未发现问题")
                except Exception as e:
                    logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        logger.info(f"========== Master Agent 检测完成，总发现问题: {len(all_results)} 个 ==========")
        return all_results

    def _detect_with_llm(self, text: str, **kwargs) -> List[SkillResult]:
        """使用 LLM 决策进行检测"""
        from ..logger import logger
        logger.info("使用 LLM 智能决策检测...")

        categories_str = self.get_category_summaries()
        skills_str = self._get_all_skills_summaries()
        text_sample = text[:2000] if len(text) > 2000 else text

        prompt = LLM_DECISION_PROMPT.format(
            categories=categories_str,
            skills=skills_str,
            text_len=len(text),
            text_sample=text_sample
        )

        try:
            result = self.llm_client._call_openai(prompt)
            logger.info(f"LLM 决策返回: {result[:500]}")

            decision = self._parse_llm_decision(result)
            logger.info(f"LLM 决策结果: {decision}")

            if not decision.get("need_detect", True):
                logger.info("LLM 决策：无需检测")
                return []

            selected_categories = decision.get("categories", [])
            logger.info(f"LLM 选择的检测类别: {selected_categories}")

        except Exception as e:
            logger.error(f"LLM 决策失败，回退到规则检测: {str(e)}")
            selected_categories = None

        all_results = []
        for agent in self.category_agents:
            category_key = agent.category.value
            if selected_categories is None or category_key in selected_categories:
                try:
                    logger.info(f"执行 Category Agent: {agent.name}")
                    if selected_categories:
                        results = agent.execute_with_llm(text, self.llm_client, **kwargs)
                    else:
                        results = agent.execute_triggered_only(text, **kwargs)
                    if results:
                        logger.info(f"{agent.name} 发现问题: {len(results)} 个")
                        all_results.extend(results)
                    else:
                        logger.info(f"{agent.name} 未发现问题")
                except Exception as e:
                    logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        return all_results

    def _get_all_skills_summaries(self) -> str:
        """获取所有 Skills 描述"""
        lines = []
        for agent in self.category_agents:
            lines.append(f"\n{agent.name} ({agent.category.value}):")
            for skill in agent.skills:
                lines.append(f"  - {skill.name}: {skill.description}")
        return "\n".join(lines)

    def _parse_llm_decision(self, result: str) -> Dict[str, Any]:
        """解析 LLM 返回的决策结果"""
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            from ..logger import logger
            logger.error(f"解析 LLM 决策失败: {str(e)}")
        return {"need_detect": True, "categories": [], "reason": "解析失败，使用默认策略"}

    def detect_all_skills(self, text: str, **kwargs) -> List[SkillResult]:
        """执行所有 Skills（不做决策，全部执行）"""
        from ..logger import logger
        logger.info("Master Agent 开始全量检测...")

        all_results = []

        for agent in self.category_agents:
            try:
                results = agent.execute_all(text, **kwargs)
                all_results.extend(results)
            except Exception as e:
                from ..logger import logger
                logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        return all_results
