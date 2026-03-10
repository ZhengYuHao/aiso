"""
EvaluationAgent - 测试评估智能体
验证学习到的规则是否有效
"""
import os
import json
import re
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from .learned_skill import LearnedSkill, EvaluationMetrics, EvaluationReport, SkillStatus, LearnedSkillManager
from ...logger import logger


class TestCase:
    """测试用例"""
    
    def __init__(self, text: str, expected_detect: bool, description: str = ""):
        self.text = text
        self.expected_detect = expected_detect
        self.description = description


class EvaluationAgent:
    """测试评估智能体"""

    def __init__(self, storage_dir: str = "config/learned_skills"):
        self.skill_manager = LearnedSkillManager(storage_dir)
        self.reports_dir = os.path.join(storage_dir, "evaluation_reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        self.config = self._load_config()
        logger.info(f"EvaluationAgent 初始化完成")

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config", "learning_config.json"
        )
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "auto_activate_threshold": 0.8,
            "min_test_cases": 10
        }

    def evaluate(self, skill_id: str) -> Optional[EvaluationReport]:
        """
        评估指定的 Skill
        
        Args:
            skill_id: Skill ID
            
        Returns:
            EvaluationReport 或 None
        """
        skill = self.skill_manager.load_skill(skill_id)
        if not skill:
            logger.warning(f"Skill 不存在: {skill_id}")
            return None

        logger.info(f"开始评估 Skill: {skill.name} (ID: {skill_id})")

        test_cases = self._generate_test_cases(skill)
        if len(test_cases) < 5:
            logger.warning(f"测试用例不足: {len(test_cases)}")
            return None

        results = self._run_tests(skill, test_cases)
        metrics = self._calculate_metrics(results)

        status = self._determine_status(metrics)
        
        skill.accuracy = metrics.f1_score
        skill.status = status
        self.skill_manager.save_skill(skill)

        recommendation = self._generate_recommendation(metrics, status)

        report = EvaluationReport(
            skill_id=skill_id,
            skill_name=skill.name,
            metrics=metrics,
            status=status,
            recommendation=recommendation,
            evaluated_at=datetime.now().isoformat(),
            test_case_count=len(test_cases)
        )

        self._save_report(report)
        
        logger.info(f"评估完成: {skill.name}, F1={metrics.f1_score:.2f}, status={status.value}")
        
        return report

    def _generate_test_cases(self, skill: LearnedSkill) -> List[TestCase]:
        """生成测试用例"""
        test_cases = []

        positive_cases = self._generate_positive_cases(skill)
        test_cases.extend(positive_cases)

        negative_cases = self._generate_negative_cases(skill)
        test_cases.extend(negative_cases)

        random.shuffle(test_cases)
        
        return test_cases[:self.config.get("min_test_cases", 10)]

    def _generate_positive_cases(self, skill: LearnedSkill) -> List[TestCase]:
        """生成正例（应该被检测到的）"""
        cases = []

        for rule in skill.rules:
            rule_type = rule.get("type", "")
            value = rule.get("value", "")

            if rule_type == "keyword" and value:
                texts = [
                    f"这是一段包含{value}的测试文本",
                    f"文件中含有{value}信息",
                    f"需要处理{value}相关数据",
                    f"关于{value}的说明",
                    f"涉及{value}的业务"
                ]
                for text in texts:
                    cases.append(TestCase(
                        text=text,
                        expected_detect=True,
                        description=f"正例-关键词:{value}"
                    ))

            elif rule_type == "regex" and value:
                try:
                    pattern = re.compile(value)
                    for _ in range(3):
                        test_text = self._generate_from_pattern(pattern)
                        if test_text:
                            cases.append(TestCase(
                                text=test_text,
                                expected_detect=True,
                                description=f"正例-正则:{value}"
                            ))
                except re.error:
                    pass

        return cases

    def _generate_negative_cases(self, skill: LearnedSkill) -> List[TestCase]:
        """生成负例（不应该被检测到的）"""
        keywords = [r["value"] for r in skill.rules if r.get("type") == "keyword"]
        
        safe_texts = [
            "这是一个正常的测试文件",
            "今天天气很好",
            "项目进度正常推进中",
            "请按时提交工作报告",
            "会议安排在下午三点",
            "文件已保存到指定目录",
            "感谢您的配合",
            "需要进一步确认",
            "请查看附件内容",
            "如有疑问请反馈"
        ]
        
        cases = []
        for text in safe_texts:
            cases.append(TestCase(
                text=text,
                expected_detect=False,
                description="负例-无关文本"
            ))

        if keywords:
            for kw in keywords[:3]:
                variations = [
                    f"不包含{kw}的内容",
                    f"这个{kw}是误报",
                ]
                for text in variations:
                    cases.append(TestCase(
                        text=text,
                        expected_detect=False,
                        description=f"负例-变体:{kw}"
                    ))

        return cases

    def _generate_from_pattern(self, pattern: re.Pattern) -> Optional[str]:
        """根据正则生成匹配文本"""
        return None

    def _run_tests(self, skill: LearnedSkill, test_cases: List[TestCase]) -> List[Dict]:
        """运行测试"""
        results = []

        for case in test_cases:
            detection_result = skill.detect(case.text)
            detected = detection_result.get("is_triggered", False)

            results.append({
                "text": case.text[:50] + "...",
                "expected": case.expected_detect,
                "detected": detected,
                "correct": detected == case.expected_detect,
                "description": case.description
            })

        return results

    def _calculate_metrics(self, results: List[Dict]) -> EvaluationMetrics:
        """计算评估指标"""
        tp = sum(1 for r in results if r["expected"] and r["detected"])
        fp = sum(1 for r in results if not r["expected"] and r["detected"])
        fn = sum(1 for r in results if r["expected"] and not r["detected"])
        tn = sum(1 for r in results if not r["expected"] and not r["detected"])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        metrics = EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            false_positive_rate=fpr,
            true_positive_rate=tpr,
            true_positives=[r for r in results if r["expected"] and r["detected"]],
            false_positives=[r for r in results if not r["expected"] and r["detected"]],
            false_negatives=[r for r in results if r["expected"] and not r["detected"]]
        )

        return metrics

    def _determine_status(self, metrics: EvaluationMetrics) -> SkillStatus:
        """根据指标确定状态"""
        f1 = metrics.f1_score
        
        threshold = self.config.get("auto_activate_threshold", 0.8)
        
        if f1 >= threshold:
            return SkillStatus.ACTIVE
        elif f1 >= 0.5:
            return SkillStatus.TESTING
        else:
            return SkillStatus.DISCARDED

    def _generate_recommendation(self, metrics: EvaluationMetrics, status: SkillStatus) -> str:
        """生成建议"""
        f1 = metrics.f1_score
        
        if status == SkillStatus.ACTIVE:
            return f"规则效果良好（F1={f1:.2f}），已自动激活使用"
        elif status == SkillStatus.TESTING:
            return f"规则效果一般（F1={f1:.2f}），继续测试验证"
        else:
            return f"规则效果较差（F1={f1:.2f}），建议丢弃或重新学习"

    def _save_report(self, report: EvaluationReport):
        """保存评估报告"""
        report_file = os.path.join(self.reports_dir, f"{report.skill_id}_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    def evaluate_all_pending(self) -> List[EvaluationReport]:
        """评估所有待测试的 Skills"""
        pending_skills = self.skill_manager.load_all_skills(SkillStatus.TESTING)
        
        reports = []
        for skill in pending_skills:
            report = self.evaluate(skill.skill_id)
            if report:
                reports.append(report)
        
        return reports

    def get_latest_report(self, skill_id: str) -> Optional[EvaluationReport]:
        """获取最新的评估报告"""
        report_file = os.path.join(self.reports_dir, f"{skill_id}_report.json")
        if os.path.exists(report_file):
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                metrics = EvaluationMetrics(**data["metrics"])
                return EvaluationReport(
                    skill_id=data["skill_id"],
                    skill_name=data["skill_name"],
                    metrics=metrics,
                    status=SkillStatus(data["status"]),
                    recommendation=data["recommendation"],
                    evaluated_at=data["evaluated_at"],
                    test_case_count=data["test_case_count"]
                )
        return None
