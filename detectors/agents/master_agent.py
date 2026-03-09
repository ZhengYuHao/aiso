"""
Master Agent - 总调度 Agent
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
from ..skills.base_skill import SkillResult


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
            use_llm_decision: 是否使用 LLM 决策（暂未实现）
        """
        from ..logger import logger
        logger.info("Master Agent 开始检测...")

        all_results = []

        for agent in self.category_agents:
            try:
                logger.info(f"执行 Category Agent: {agent.name}")
                results = agent.execute_triggered_only(text, **kwargs)
                if results:
                    logger.info(f"{agent.name} 发现问题: {len(results)} 个")
                    all_results.extend(results)
                else:
                    logger.info(f"{agent.name} 未发现问题")
            except Exception as e:
                logger.error(f"Category Agent {agent.name} 执行失败: {str(e)}")

        logger.info(f"Master Agent 检测完成，总发现问题: {len(all_results)} 个")
        return all_results

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
