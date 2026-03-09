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


class DetectionOrchestrator:
    """检测调度器"""

    def __init__(self, config_dir: str = None):
        self.parser = FileParser()

        # 按优先级顺序注册检测器
        kw_config = f"{config_dir}/classified_keywords.json" if config_dir else None
        self.detectors = [
            # 第一层：涉密信息检测
            ClassifiedMarkDetector(),
            ClassifiedKeywordDetector(config_path=kw_config),
            # 第一层半：公章 OCR 检测
            StampOCRDetector(),
            # 第二层：敏感信息检测
            PIIDetector(),
            BusinessSensitiveDetector(),
            # 第三层：受限使用内容检测
            RestrictedContentDetector(),
            # 第四层：其他风险内容检测
            CredentialDetector(),
            InfrastructureDetector(),
        ]

    def detect_file(self, filepath: str) -> Dict[str, Any]:
        """
        执行完整的文件检测流程
        返回结构化检测报告（JSON 可序列化）
        """
        total_start = time.time()
        report = {
            "detection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_info": {},
            "overall_verdict": Verdict.PASS,
            "risk_level": "无风险",
            "issues_count": 0,
            "issues_by_category": {},
            "issues": [],
            "detection_steps": [],
            "total_time_ms": 0,
            "error": None,
        }

        # Step 1: 文件解析
        try:
            full_text, paragraphs, meta = self.parser.parse(filepath)
            report["file_info"] = meta
        except Exception as e:
            report["error"] = f"文件解析失败: {str(e)}"
            report["overall_verdict"] = "ERROR"
            report["risk_level"] = "无法判定"
            return report

        # Step 2-5: 依次运行所有检测器
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

        # Step 6: 去重和汇总
        unique_issues = self._deduplicate_issues(all_issues)
        report["issues_count"] = len(unique_issues)
        report["issues"] = [i.to_dict() for i in unique_issues]

        # 按类别统计
        category_counts = {}
        for issue in unique_issues:
            cat = issue.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        report["issues_by_category"] = category_counts

        # 确定总体判定
        report["overall_verdict"], report["risk_level"] = self._determine_verdict(unique_issues)

        report["total_time_ms"] = round((time.time() - total_start) * 1000, 2)
        return report

    def _deduplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        """去重：同一位置同一子类型只保留一个"""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.paragraph_index, issue.char_offset, issue.sub_type)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        # 按优先级排序：severity → paragraph_index → char_offset
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
