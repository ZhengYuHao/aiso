"""
Master Agent - 总调度 Agent
支持 LLM 智能决策选择合适的 Skills
支持边学边用：自动加载学习到的规则
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
from .learning import LearnedSkillManager, SkillStatus
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
        
        self.learned_skill_manager = LearnedSkillManager()
        self.learned_skills = self._load_learned_skills()
        
    def _load_learned_skills(self) -> List[Any]:
        """加载已激活的学习到的规则"""
        from ..logger import logger
        skills = self.learned_skill_manager.load_all_skills(SkillStatus.ACTIVE)
        if skills:
            logger.info(f"边学边用: 加载 {len(skills)} 个已激活的规则")
            for skill in skills:
                logger.info(f"  - {skill.name} (category={skill.category}, rules={len(skill.rules)})")
        return skills

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
        logger.debug(f"========== Master Agent 开始检测 ==========")
        logger.debug(f"文本长度: {len(text)}, LLM决策: {use_llm_decision}")

        all_results = []

        if use_llm_decision and self.llm_client:
            logger.debug(">>> 使用 LLM 智能决策模式 <<<")
            all_results = self._detect_with_llm(text, **kwargs)
        else:
            logger.debug(">>> 使用规则引擎模式 <<<")
            for agent in self.category_agents:
                try:
                    logger.debug(f"--- 调度 Category Agent: {agent.name} ---")
                    logger.debug(f"该分类包含 {len(agent.skills)} 个 Skills: {[s.name for s in agent.skills]}")
                    results = agent.execute_triggered_only(text, **kwargs)
                    if results:
                        logger.debug(f"[{agent.name}] 发现问题: {len(results)} 个")
                        for r in results:
                            logger.debug(f"  >>> Skill[{r.skill_name}] 触发! category={r.category.value}, severity={r.severity.value}")
                            logger.debug(f"  >>> reason: {r.reason[:80]}...")
                        all_results.extend(results)
                    else:
                        logger.debug(f"[{agent.name}] 未发现问题")
                except Exception as e:
                    logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        all_results.extend(self._detect_with_learned_skills(text, **kwargs))

        logger.debug(f"========== Master Agent 检测完成，总发现问题: {len(all_results)} 个 ==========")
        return all_results

    def _detect_with_learned_skills(self, text: str, **kwargs) -> List[SkillResult]:
        """使用边学边用规则进行检测"""
        from ..logger import logger
        
        if not self.learned_skills:
            return []
        
        logger.debug(f"========== 边学边用: 使用 {len(self.learned_skills)} 个已学习规则 ==========")
        
        results = []
        for skill in self.learned_skills:
            try:
                logger.debug(f"边学边用: 执行规则 {skill.name}")
                detection_result = skill.detect(text)
                
                if detection_result.get("is_triggered"):
                    logger.debug(f"边学边用: 规则[{skill.name}] 触发! category={skill.category}")
                    
                    from ..skills.base_skill import Severity
                    severity_map = {"critical": Severity.CRITICAL, "high": Severity.HIGH, "medium": Severity.MEDIUM, "low": Severity.LOW}
                    
                    skill_result = SkillResult(
                        skill_name=f"learned_{skill.skill_id}",
                        is_triggered=True,
                        severity=severity_map.get(skill.severity, Severity.MEDIUM),
                        category=Category(skill.category),
                        reason=detection_result.get("reason", ""),
                        suggestion=skill.suggestion,
                        evidence={"matched_rules": detection_result.get("matched_rules", [])},
                        location="全文",
                        matched_rule=skill.skill_id
                    )
                    results.append(skill_result)
            except Exception as e:
                logger.error(f"边学边用: 规则 {skill.name} 执行失败: {str(e)}")
        
        logger.debug(f"边学边用: 检测完成，发现 {len(results)} 个问题")
        return results

    def _detect_with_llm(self, text: str, **kwargs) -> List[SkillResult]:
        """使用 LLM 决策进行检测"""
        from ..logger import logger
        logger.debug("使用 LLM 智能决策检测...")

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
            logger.debug(f"LLM 决策返回: {result[:500]}")

            decision = self._parse_llm_decision(result)
            logger.debug(f"LLM 决策结果: {decision}")

            if not decision.get("need_detect", True):
                logger.debug("LLM 决策：无需检测")
                return []

            selected_categories = decision.get("categories", [])
            logger.debug(f"LLM 选择的检测类别: {selected_categories}")

        except Exception as e:
            logger.error(f"LLM 决策失败，回退到规则检测: {str(e)}")
            selected_categories = None

        all_results = []
        for agent in self.category_agents:
            category_key = agent.category.value
            if selected_categories is None or category_key in selected_categories:
                try:
                    logger.debug(f"执行 Category Agent: {agent.name}")
                    if selected_categories:
                        results = agent.execute_with_llm(text, self.llm_client, **kwargs)
                    else:
                        results = agent.execute_triggered_only(text, **kwargs)
                    if results:
                        logger.debug(f"{agent.name} 发现问题: {len(results)} 个")
                        all_results.extend(results)
                    else:
                        logger.debug(f"{agent.name} 未发现问题")
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
        logger.debug("Master Agent 开始全量检测...")

        all_results = []

        for agent in self.category_agents:
            try:
                results = agent.execute_all(text, **kwargs)
                all_results.extend(results)
            except Exception as e:
                from ..logger import logger
                logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        return all_results
