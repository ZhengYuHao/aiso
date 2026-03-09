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


LLM_DETECTOR_CATEGORIES = {
    "classified": ["涉密信息", "密级标识"],
    "pii": ["个人隐私", "身份证", "手机号", "银行卡"],
    "business": ["商业敏感", "财务数据", "客户名单"],
    "credential": ["凭证密钥", "API Key", "密码"],
    "infrastructure": ["基础设施", "内网IP", "端口"],
}


class DetectionOrchestrator:
    """检测调度器"""

    def __init__(self, config_dir: str = None):
        self.parser = FileParser()
        self.llm_client = LLMClient()

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
        except Exception as e:
            report["error"] = f"文件解析失败: {str(e)}"
            report["overall_verdict"] = "ERROR"
            report["risk_level"] = "无法判定"
            return report

        all_issues: List[Issue] = []

        if detection_mode == "llm":
            all_issues = self._detect_with_llm(full_text, paragraphs, report)
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
        all_issues: List[Issue] = []

        for detector in self.detectors:
            try:
                if hasattr(detector, 'detect_from_file'):
                    result: DetectionResult = detector.detect_from_file(filepath)
                else:
                    result: DetectionResult = detector.detect(full_text, paragraphs)
                report["detection_steps"].append(result.to_dict())
                all_issues.extend(result.issues)
            except Exception as e:
                report["detection_steps"].append({
                    "detector_name": detector.name,
                    "error": str(e),
                    "issues_count": 0,
                    "issues": [],
                    "scan_time_ms": 0,
                })

        return all_issues

    def _detect_with_llm(self, full_text: str, paragraphs: List[Paragraph], report: Dict) -> List[Issue]:
        """使用 LLM 进行检测"""
        all_issues: List[Issue] = []

        categories = [
            ("classified", "classified", "涉密信息检测智能体处理"),
            ("pii", "pii", "个人隐私信息检测智能体处理"),
            ("business", "business", "商业敏感信息检测智能体处理"),
            ("credential", "credential", "凭证密钥检测智能体处理"),
            ("infrastructure", "infrastructure", "内部架构信息检测智能体处理"),
        ]

        for category_key, llm_key, detector_name in categories:
            try:
                start_time = time.time()

                text_to_check = full_text[:8000] if len(full_text) > 8000 else full_text

                llm_result = self.llm_client.detect(text_to_check, category_key)

                issues = []
                if llm_result.get("is_sensitive", False):
                    severity_map = {
                        "critical": Severity.CRITICAL,
                        "high": Severity.HIGH,
                        "medium": Severity.MEDIUM,
                        "low": Severity.LOW
                    }
                    severity = severity_map.get(llm_result.get("severity", "low"), Severity.MEDIUM)

                    issues.append(Issue(
                        category=Category.CLASSIFIED if category_key == "classified" else Category.SENSITIVE,
                        sub_type=f"llm_{category_key}",
                        severity=severity,
                        content=llm_result.get("reason", "")[:200],
                        content_raw=text_to_check[:500],
                        location="全文",
                        paragraph_index=0,
                        char_offset=0,
                        char_length=len(text_to_check),
                        reason=llm_result.get("reason", ""),
                        suggestion=llm_result.get("suggestion", ""),
                        matched_rule=f"LLM-{category_key}",
                    ))

                elapsed = (time.time() - start_time) * 1000

                report["detection_steps"].append({
                    "detector_name": detector_name,
                    "issues_count": len(issues),
                    "issues": [i.to_dict() for i in issues],
                    "scan_time_ms": elapsed,
                    "llm_result": llm_result,
                })

                all_issues.extend(issues)

            except Exception as e:
                report["detection_steps"].append({
                    "detector_name": detector_name,
                    "error": str(e),
                    "issues_count": 0,
                    "issues": [],
                    "scan_time_ms": 0,
                })

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
