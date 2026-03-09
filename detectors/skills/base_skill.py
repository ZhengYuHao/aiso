"""
Skill 基类 - 所有检测 Skill 的抽象基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    CLASSIFIED = "classified"       # 涉密信息
    SENSITIVE = "sensitive"         # 敏感信息
    RESTRICTED = "restricted"       # 受限内容
    CREDENTIAL = "credential"      # 凭证密钥
    INFRASTRUCTURE = "infrastructure"  # 内部架构


@dataclass
class SkillResult:
    """Skill 检测结果"""
    skill_name: str
    is_triggered: bool
    severity: Severity
    category: Category
    reason: str
    suggestion: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    location: str = ""
    matched_rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "is_triggered": self.is_triggered,
            "severity": self.severity.value,
            "category": self.category.value,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
            "location": self.location,
            "matched_rule": self.matched_rule,
        }


class BaseSkill(ABC):
    """Skill 抽象基类"""

    name: str = ""
    description: str = ""
    category: Category = Category.SENSITIVE

    @abstractmethod
    def detect(self, text: str, **kwargs) -> SkillResult:
        """执行检测"""
        pass

    def should_use_llm(self) -> bool:
        """判断是否需要使用 LLM 进行智能检测"""
        return False

    def get_llm_prompt(self, text: str) -> str:
        """获取 LLM 检测 Prompt"""
        return ""

    def parse_llm_result(self, llm_response: str) -> SkillResult:
        """解析 LLM 返回结果"""
        pass
