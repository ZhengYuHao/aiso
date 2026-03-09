"""
商业敏感信息检测 Skill
"""
from typing import Dict, Any, List
from ..base_skill import BaseSkill, SkillResult, Severity, Category


class BusinessSensitiveSkill(BaseSkill):
    """商业敏感信息检测 Skill"""

    name = "business_sensitive"
    description = "检测客户名单、薪资待遇、报价、合同金额等商业敏感信息"
    category = Category.SENSITIVE

    KEYWORDS = {
        "customer": ["客户名单", "客户信息", "供应商", "合作伙伴", "联系人"],
        "price": ["报价", "价格", "成本", "利润", "预算", "金额"],
        "salary": ["薪资", "工资", "薪酬", "奖金", "期权", "股票"],
        "contract": ["合同", "协议", "条款", "违约金", "赔偿"],
        "strategy": ["战略", "规划", "商业计划", "市场策略", "竞争对手"],
    }

    def detect(self, text: str, **kwargs) -> SkillResult:
        found_info = []

        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    found_info.append({"category": category, "keyword": keyword})
                    break

        if found_info:
            severity = Severity.HIGH
            if any(info["category"] in ["salary", "strategy"] for info in found_info):
                severity = Severity.MEDIUM

            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=severity,
                category=self.category,
                reason=f"检测到商业敏感信息: {', '.join([info['keyword'] for info in found_info[:5]])}",
                suggestion="建议对商业敏感信息进行脱敏处理后再发送至 AI 平台",
                evidence={"sensitive_info": found_info},
                location="全文",
                matched_rule="business_sensitive"
            )

        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            category=self.category,
            reason="未检测到商业敏感信息",
            suggestion="",
            evidence={}
        )
