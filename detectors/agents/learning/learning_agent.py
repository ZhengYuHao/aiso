"""
LearningAgent - 边学边用智能体
从 LLM 检测结果中学习新的检测规则
"""
import os
import json
import re
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from .learned_skill import LearnedSkill, LearnedSkillManager, RuleType, SkillStatus
from ...logger import logger


class LearningAgent:
    """边学边用智能体 - 从 LLM 检测结果中学习新规则"""

    def __init__(self, llm_client=None, storage_dir: str = "config/learned_skills"):
        self.llm_client = llm_client
        self.skill_manager = LearnedSkillManager(storage_dir)
        self.config = self._load_config()
        logger.info(f"LearningAgent 初始化完成，存储目录: {storage_dir}")

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", "learning_config.json"
        )
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "learning_enabled": True,
            "auto_activate_threshold": 0.8,
            "min_samples_for_learning": 1,
            "max_learned_skills": 100
        }

    def analyze_and_learn(self, text: str, llm_result: Dict[str, Any]) -> Optional[LearnedSkill]:
        """
        分析 LLM 检测结果，学习新规则
        
        Args:
            text: 原始文本
            llm_result: LLM 检测结果
            
        Returns:
            LearnedSkill 或 None
        """
        if not self.config.get("learning_enabled", True):
            logger.debug("学习功能已禁用")
            return None

        category = llm_result.get("category", "")
        reason = llm_result.get("reason", "")
        is_sensitive = llm_result.get("is_sensitive", False)

        if not is_sensitive:
            return None

        logger.info(f"LearningAgent 开始学习: category={category}, reason={reason[:50]}...")

        if self._skill_exists(category, reason):
            logger.info(f"已存在相似规则，跳过学习")
            return None

        rules = self._generate_rules(text, llm_result)
        if not rules:
            logger.warning("未能生成有效规则，跳过学习")
            return None

        skill = self._build_skill(llm_result, rules)
        if not skill:
            return None

        if self.skill_manager.save_skill(skill):
            logger.info(f"成功保存学习到的 Skill: {skill.name} (ID: {skill.skill_id})")
            return skill
        else:
            logger.error(f"保存 Skill 失败: {skill.name}")
            return None

    def _skill_exists(self, category: str, reason: str) -> bool:
        """检查是否已存在相似规则"""
        keywords = self._extract_keywords(reason)
        for keyword in keywords:
            if self.skill_manager.skill_exists(category, keyword):
                return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', text)
        return [w for w in words if len(w) >= 2][:5]

    def _generate_rules(self, text: str, llm_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 LLM 生成检测规则"""
        if not self.llm_client:
            return self._generate_rules_from_text(text, llm_result)

        prompt = self._build_rule_generation_prompt(text, llm_result)
        
        try:
            result = self.llm_client._call_openai(prompt)
            return self._parse_llm_response(result)
        except Exception as e:
            logger.warning(f"LLM 生成规则失败: {e}，使用本地规则提取")
            return self._generate_rules_from_text(text, llm_result)

    def _build_rule_generation_prompt(self, text: str, llm_result: Dict[str, Any]) -> str:
        """构建规则生成提示词"""
        reason = llm_result.get("reason", "")
        category = llm_result.get("category", "")
        severity = llm_result.get("severity", "medium")

        return f"""分析以下文本和 LLM 检测结果，生成可复用的检测规则。

LLM检测结果:
- 类别: {category}
- 严重程度: {severity}
- 检测理由: {reason}

原始文本片段:
{text[:2000]}

请返回 JSON 格式的规则:
{{
    "rules": [
        {{"type": "keyword", "value": "关键词1", "description": "说明"}},
        {{"type": "keyword", "value": "关键词2", "description": "说明"}},
        {{"type": "regex", "value": "正则表达式", "description": "说明"}}
    ]
}}

要求:
1. keywords: 提取 3-10 个关键中文关键词
2. regex: 生成一个或多个正则表达式（如果适用）
3. 只返回 JSON，不要其他内容"""

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的规则"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("rules", [])
        except json.JSONDecodeError as e:
            logger.warning(f"解析 LLM 响应失败: {e}")
        return []

    def _generate_rules_from_text(self, text: str, llm_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从文本本地提取规则（无 LLM 时使用）"""
        reason = llm_result.get("reason", "")
        
        keywords = self._extract_keywords(reason)
        
        rules = []
        for kw in keywords[:8]:
            rules.append({
                "type": "keyword",
                "value": kw,
                "description": f"从理由提取: {reason[:30]}"
            })

        patterns = self._extract_patterns(text)
        for pattern in patterns[:2]:
            rules.append({
                "type": "regex",
                "value": pattern,
                "description": "从文本提取的模式"
            })

        return rules

    def _extract_patterns(self, text: str) -> List[str]:
        """从文本中提取可能的模式"""
        patterns = []
        
        chinese_nums = re.findall(r'[\u4e00-\u9fa5]{1,5}\s*[\d,，.]+', text)
        for p in chinese_nums[:3]:
            clean = p.replace(" ", "").replace(",", "").replace("，", ".")
            if len(clean) >= 3:
                patterns.append(f".*{re.escape(clean[:6])}.*")
        
        codes = re.findall(r'[A-Za-z0-9_-]{4,20}', text)
        for code in codes[:2]:
            if any(c.isdigit() for c in code):
                patterns.append(f".*{code}.*")
        
        return patterns

    def _build_skill(self, llm_result: Dict[str, Any], rules: List[Dict[str, Any]]) -> Optional[LearnedSkill]:
        """构建 LearnedSkill 对象"""
        category = llm_result.get("category", "unknown")
        reason = llm_result.get("reason", "")
        
        rule_type = RuleType.KEYWORD
        if any(r.get("type") == "regex" for r in rules):
            rule_type = RuleType.PATTERN

        skill_name = self._generate_skill_name(category, reason)
        
        skill = LearnedSkill(
            skill_id=self._generate_id(),
            name=skill_name,
            description=reason[:100],
            category=category,
            rule_type=rule_type,
            rules=rules,
            severity=llm_result.get("severity", "medium"),
            suggestion=llm_result.get("suggestion", "建议手动处理"),
            created_at=datetime.now().isoformat(),
            status=SkillStatus.TESTING
        )
        
        return skill

    def _generate_skill_name(self, category: str, reason: str) -> str:
        """生成 Skill 名称"""
        category_names = {
            "涉密信息": "涉密内容",
            "敏感信息": "敏感内容",
            "受限内容": "受限内容",
            "凭证密钥": "凭证信息",
            "内部架构": "架构信息"
        }
        
        base = category_names.get(category, category)
        keywords = self._extract_keywords(reason)
        
        if keywords:
            return f"{base}_{keywords[0]}"
        return f"{base}_learned"

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return f"learned_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

    def get_all_learned_skills(self, status: Optional[SkillStatus] = None) -> List[LearnedSkill]:
        """获取所有学习到的 Skills"""
        return self.skill_manager.load_all_skills(status)

    def get_active_skills(self) -> List[LearnedSkill]:
        """获取已激活的 Skills"""
        return self.skill_manager.load_all_skills(SkillStatus.ACTIVE)

    def delete_skill(self, skill_id: str) -> bool:
        """删除 Skill"""
        return self.skill_manager.delete_skill(skill_id)
