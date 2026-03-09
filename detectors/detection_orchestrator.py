"""
检测调度器 —— 编排所有检测器的执行顺序，汇总结果，生成最终报告
"""
import time
import json
from datetime import datetime
from typing import List, Dict, Any
from .base_detector import (
    Paragraph, Issue, DetectionResult,
    Category, Severity, Verdict, VERDICT_PRIORITY
)
from .logger import logger
from .file_parser import FileParser
from .classified_mark_detector import ClassifiedMarkDetector
from .classified_keyword_detector import ClassifiedKeywordDetector
from .pii_detector import PIIDetector
from .business_sensitive_detector import BusinessSensitiveDetector
from .restricted_content_detector import RestrictedContentDetector
from .credential_detector import CredentialDetector
from .infrastructure_detector import InfrastructureDetector
from .stamp_ocr_detector import StampOCRDetector
from .llm_client import LLMClient
from .agents.master_agent import MasterAgent


LLM_DETECTOR_CATEGORIES = {
    "classified": ["涉密信息", "密级标识"],
    "classified_mark": ["密级标识", "绝密", "机密", "秘密", "内部", "公开"],
    "pii": ["个人隐私", "身份证", "手机号", "银行卡"],
    "business": ["商业敏感", "财务数据", "客户名单"],
    "credential": ["凭证密钥", "API Key", "密码"],
    "infrastructure": ["基础设施", "内网IP", "端口"],
    "restricted_content": ["受限内容", "政治敏感", "暴力", "色情", "赌博", "毒品"],
    "stamp_ocr": ["公章", "印章", "签字"],
}


class DetectionOrchestrator:
    """检测调度器"""

    def __init__(self, config_dir: str = None):
        self.parser = FileParser()
        self.llm_client = LLMClient()
        self.master_agent = MasterAgent(llm_client=self.llm_client)

        kw_config = f"{config_dir}/classified_keywords.json" if config_dir else None
        self.detectors = [
            ClassifiedMarkDetector(),
            ClassifiedKeywordDetector(config_path=kw_config),
            StampOCRDetector(),
            PIIDetector(),
            BusinessSensitiveDetector(),
            RestrictedContentDetector(),
            CredentialDetector(),
            InfrastructureDetector(),
        ]

    def detect_file(self, filepath: str, detection_mode: str = "rule") -> Dict[str, Any]:
        """
        执行完整的文件检测流程
        detection_mode: "rule" (规则引擎) 或 "llm" (AI智能体)
        """
        logger.info(f"开始检测文件: {filepath}, 检测模式: {detection_mode}")
        total_start = time.time()
        report = {
            "detection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "detection_mode": detection_mode,
            "file_info": {},
            "overall_verdict": Verdict.PASS,
            "risk_level": "无风险",
            "issues_count": 0,
            "issues_by_category": {},
            "issues": [],
            "detection_steps": [],
            "total_time_ms": 0,
            "comprehensive_suggestion": "",
            "error": None,
        }

        try:
            full_text, paragraphs, meta = self.parser.parse(filepath)
            report["file_info"] = meta
            logger.debug(f"文件解析完成: {filepath}, 字符数: {len(full_text)}")
        except Exception as e:
            logger.error(f"文件解析失败: {filepath}, 错误: {str(e)}")
            report["error"] = f"文件解析失败: {str(e)}"
            report["overall_verdict"] = "ERROR"
            report["risk_level"] = "无法判定"
            return report

        all_issues: List[Issue] = []

        if detection_mode == "llm":
            all_issues = self._detect_with_agent(full_text, paragraphs, report)
        else:
            all_issues = self._detect_with_rules(filepath, full_text, paragraphs, report)

        unique_issues = self._deduplicate_issues(all_issues)
        report["issues_count"] = len(unique_issues)
        report["issues"] = [i.to_dict() for i in unique_issues]

        category_counts = {}
        for issue in unique_issues:
            cat = issue.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        report["issues_by_category"] = category_counts

        report["overall_verdict"], report["risk_level"] = self._determine_verdict(unique_issues)

        report["comprehensive_suggestion"] = self._generate_comprehensive_suggestion(unique_issues)

        report["total_time_ms"] = round((time.time() - total_start) * 1000, 2)
        return report

    def _detect_with_rules(self, filepath: str, full_text: str, paragraphs: List[Paragraph], report: Dict) -> List[Issue]:
        """使用规则引擎检测"""
        logger.info("开始规则引擎检测...")
        all_issues: List[Issue] = []

        for detector in self.detectors:
            try:
                logger.debug(f"运行检测器: {detector.name}")
                if hasattr(detector, 'detect_from_file'):
                    result: DetectionResult = detector.detect_from_file(filepath)
                else:
                    result: DetectionResult = detector.detect(full_text, paragraphs)
                report["detection_steps"].append(result.to_dict())
                all_issues.extend(result.issues)
                logger.info(f"检测器 {detector.name} 完成，发现问题: {len(result.issues)}")
            except Exception as e:
                logger.error(f"检测器 {detector.name} 执行失败: {str(e)}")
                report["detection_steps"].append({
                    "detector_name": detector.name,
                    "error": str(e),
                    "issues_count": 0,
                    "issues": [],
                    "scan_time_ms": 0,
                })

        return all_issues

    def _detect_with_agent(self, full_text: str, paragraphs: List[Paragraph], report: Dict, use_llm_decision: bool = False) -> List[Issue]:
        """使用 Agent 架构进行检测"""
        logger.info(f"========== 开始 Agent 智能体检测 ==========")
        logger.info(f"文本长度: {len(full_text)}, LLM决策: {use_llm_decision}")

        text_to_check = full_text[:8000] if len(full_text) > 8000 else full_text

        skill_results = self.master_agent.detect(text_to_check, use_llm_decision=True)

        logger.info(f">>> Agent 返回 {len(skill_results)} 个 SkillResult")
        
        all_issues = []
        for skill_result in skill_results:
            logger.info(f"--- 转换 SkillResult -> Issue ---")
            logger.info(f"skill_name: {skill_result.skill_name}")
            logger.info(f"category: {skill_result.category.value}")
            logger.info(f"severity: {skill_result.severity.value}")
            logger.info(f"is_triggered: {skill_result.is_triggered}")
            logger.info(f"reason: {skill_result.reason[:100]}...")
            
            category_map = {
                "classified": Category.CLASSIFIED,
                "sensitive": Category.SENSITIVE,
                "restricted": Category.RESTRICTED,
                "credential": Category.CREDENTIAL,
                "infrastructure": Category.INFRASTRUCTURE,
            }

            severity_map = {
                "critical": Severity.CRITICAL,
                "high": Severity.HIGH,
                "medium": Severity.MEDIUM,
                "low": Severity.LOW,
            }

            issue = Issue(
                category=category_map.get(skill_result.category.value, Category.SENSITIVE),
                sub_type=skill_result.skill_name,
                severity=severity_map.get(skill_result.severity.value, Severity.MEDIUM),
                content=skill_result.reason[:200],
                content_raw=text_to_check[:500],
                location=skill_result.location or "全文",
                paragraph_index=0,
                char_offset=0,
                char_length=len(text_to_check),
                reason=skill_result.reason,
                suggestion=skill_result.suggestion,
                matched_rule=skill_result.matched_rule or f"agent_{skill_result.skill_name}",
            )
            all_issues.append(issue)

            report["detection_steps"].append({
                "detector_name": skill_result.skill_name,
                "issues_count": 1,
                "issues": [skill_result.to_dict()],
                "scan_time_ms": 0,
                "skill_result": skill_result.to_dict(),
            })

            logger.info(f">>> Issue 创建成功: category={issue.category.value}, severity={issue.severity.value}")

        logger.info(f"========== Agent 检测完成，发现问题: {len(all_issues)} 个 ==========")
        return all_issues

    def _deduplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        """去重"""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.paragraph_index, issue.char_offset, issue.sub_type)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        unique.sort(key=lambda i: (
            severity_order.get(i.severity, 99),
            i.paragraph_index,
            i.char_offset,
        ))
        return unique

    def _determine_verdict(self, issues: List[Issue]) -> tuple:
        """根据所有问题确定总体判定"""
        if not issues:
            return Verdict.PASS, "无风险"

        has_classified = any(i.category == Category.CLASSIFIED for i in issues)
        has_sensitive = any(i.category == Category.SENSITIVE for i in issues)
        has_restricted = any(i.category == Category.RESTRICTED for i in issues)
        has_risky = any(i.category == Category.RISKY for i in issues)

        if has_classified:
            return Verdict.BLOCK, "极高"
        elif has_sensitive:
            return Verdict.WARNING, "高"
        elif has_restricted:
            return Verdict.NOTICE, "中"
        elif has_risky:
            return Verdict.NOTICE, "低"
        else:
            return Verdict.PASS, "无风险"

    def _generate_comprehensive_suggestion(self, issues: List[Issue]) -> str:
        """综合所有检测器的建议，生成最终处理建议"""
        if not issues:
            return "检测通过，文件未发现安全风险，可以正常发送至AI平台处理。"

        critical_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        high_issues = [i for i in issues if i.severity == Severity.HIGH]
        medium_issues = [i for i in issues if i.severity == Severity.MEDIUM]
        low_issues = [i for i in issues if i.severity == Severity.LOW]

        suggestions = []

        if critical_issues:
            suggestions.append("【禁止发送】文件包含严重涉密或敏感信息，严禁发送至任何外部AI平台。")
            suggestions.append("建议：立即删除涉密内容，或使用内部脱敏工具处理后重新检测。")

        if high_issues:
            high_categories = set(i.category for i in high_issues)
            category_names = {
                Category.CLASSIFIED: "涉密信息",
                Category.SENSITIVE: "敏感信息",
                Category.RESTRICTED: "受限内容",
                Category.RISKY: "风险内容"
            }
            categories_str = "、".join([category_names.get(c, str(c)) for c in high_categories])
            suggestions.append(f"【高风险】检测到{categories_str}，强烈建议脱敏处理后再发送。")

        if medium_issues:
            suggestions.append("【中风险】检测到部分敏感信息，建议查看具体问题并酌情处理。")

        if low_issues:
            suggestions.append("【低风险】存在少量提示性信息，可根据实际情况选择处理。")

        all_suggestions = [i.suggestion for i in issues if i.suggestion]
        if all_suggestions:
            unique_suggestions = list(set(all_suggestions))[:3]
            suggestions.append("各检测项建议：")
            for s in unique_suggestions:
                suggestions.append(f"  • {s}")

        return "\n".join(suggestions) if suggestions else "检测完成，请查看详细报告。"
