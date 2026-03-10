from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import json
import os
import uuid


class RuleType(Enum):
    KEYWORD = "keyword"
    REGEX = "regex"
    PATTERN = "pattern"


class SkillStatus(Enum):
    ACTIVE = "active"
    TESTING = "testing"
    DISCARDED = "discarded"


class SeverityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class LearnedSkill:
    skill_id: str
    name: str
    description: str
    category: str
    rule_type: RuleType
    rules: List[Dict[str, Any]]
    severity: str
    suggestion: str
    created_at: str
    usage_count: int = 0
    accuracy: float = 0.0
    status: SkillStatus = SkillStatus.TESTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "rule_type": self.rule_type.value,
            "rules": self.rules,
            "severity": self.severity,
            "suggestion": self.suggestion,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "accuracy": self.accuracy,
            "status": self.status.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnedSkill":
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            rule_type=RuleType(data["rule_type"]),
            rules=data["rules"],
            severity=data["severity"],
            suggestion=data["suggestion"],
            created_at=data["created_at"],
            usage_count=data.get("usage_count", 0),
            accuracy=data.get("accuracy", 0.0),
            status=SkillStatus(data.get("status", "testing"))
        )

    def detect(self, text: str) -> Dict[str, Any]:
        matched_rules = []
        
        for rule in self.rules:
            rule_type = rule.get("type", "")
            value = rule.get("value", "")
            
            if rule_type == "keyword":
                if value in text:
                    matched_rules.append({
                        "rule": rule,
                        "match": value,
                        "position": text.find(value)
                    })
            
            elif rule_type == "regex":
                import re
                try:
                    pattern = re.compile(value)
                    matches = pattern.findall(text)
                    if matches:
                        matched_rules.append({
                            "rule": rule,
                            "match": matches,
                            "count": len(matches)
                        })
                except re.error:
                    pass
        
        is_triggered = len(matched_rules) > 0
        
        if is_triggered:
            return {
                "is_triggered": True,
                "severity": self.severity,
                "category": self.category,
                "reason": f"检测到学习规则: {self.name}",
                "suggestion": self.suggestion,
                "matched_rules": matched_rules,
                "skill_id": self.skill_id
            }
        
        return {
            "is_triggered": False,
            "severity": "low",
            "category": self.category,
            "reason": "未匹配",
            "suggestion": "",
            "matched_rules": [],
            "skill_id": self.skill_id
        }


@dataclass
class EvaluationMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0
    true_positive_rate: float = 0.0
    true_positives: List[Dict] = field(default_factory=list)
    false_positives: List[Dict] = field(default_factory=list)
    false_negatives: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "false_positive_rate": self.false_positive_rate,
            "true_positive_rate": self.true_positive_rate,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives
        }


@dataclass
class EvaluationReport:
    skill_id: str
    skill_name: str
    metrics: EvaluationMetrics
    status: SkillStatus
    recommendation: str
    evaluated_at: str
    test_case_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "metrics": self.metrics.to_dict(),
            "status": self.status.value,
            "recommendation": self.recommendation,
            "evaluated_at": self.evaluated_at,
            "test_case_count": self.test_case_count
        }


class LearnedSkillManager:
    """管理的学习技能管理器"""
    
    def __init__(self, storage_dir: str = "config/learned_skills"):
        self.storage_dir = storage_dir
        self.metadata_file = os.path.join(storage_dir, "metadata.json")
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _load_metadata(self) -> Dict[str, Any]:
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "version": "1.0",
            "last_updated": "",
            "skills": []
        }
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def save_skill(self, skill: LearnedSkill) -> bool:
        try:
            skill_file = os.path.join(self.storage_dir, f"{skill.skill_id}.json")
            with open(skill_file, "w", encoding="utf-8") as f:
                json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
            
            metadata = self._load_metadata()
            skill_info = {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "category": skill.category,
                "status": skill.status.value,
                "accuracy": skill.accuracy,
                "usage_count": skill.usage_count,
                "created_at": skill.created_at
            }
            
            existing = [s for s in metadata["skills"] if s["skill_id"] != skill.skill_id]
            existing.append(skill_info)
            metadata["skills"] = existing
            self._save_metadata(metadata)
            
            return True
        except Exception as e:
            return False
    
    def load_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        skill_file = os.path.join(self.storage_dir, f"{skill_id}.json")
        if os.path.exists(skill_file):
            with open(skill_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return LearnedSkill.from_dict(data)
        return None
    
    def load_all_skills(self, status: Optional[SkillStatus] = None) -> List[LearnedSkill]:
        skills = []
        metadata = self._load_metadata()
        
        for skill_info in metadata.get("skills", []):
            skill_id = skill_info.get("skill_id")
            if not skill_id:
                continue
            
            skill = self.load_skill(skill_id)
            if skill:
                if status is None or skill.status == status:
                    skills.append(skill)
        
        return skills
    
    def delete_skill(self, skill_id: str) -> bool:
        try:
            skill_file = os.path.join(self.storage_dir, f"{skill_id}.json")
            if os.path.exists(skill_file):
                os.remove(skill_file)
            
            metadata = self._load_metadata()
            metadata["skills"] = [s for s in metadata["skills"] if s["skill_id"] != skill_id]
            self._save_metadata(metadata)
            
            return True
        except Exception as e:
            return False
    
    def skill_exists(self, category: str, name_pattern: str) -> bool:
        metadata = self._load_metadata()
        for skill_info in metadata.get("skills", []):
            if skill_info.get("category") == category:
                skill = self.load_skill(skill_info.get("skill_id"))
                if skill and name_pattern.lower() in skill.name.lower():
                    return True
        return False
