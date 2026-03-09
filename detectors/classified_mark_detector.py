"""
密级标识检测器 —— 检测文件中的密级标识（绝密★、机密★、秘密★等）
"""
import re
import time
from typing import List
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class ClassifiedMarkDetector(BaseDetector):
    """密级标识检测器"""

    name = "涉密标识检测智能体"
    description = "检测密级标识（绝密★、机密★、秘密★及其变体）"

    # 密级标识正则模式
    MARK_PATTERNS = [
        # 绝密级
        {
            "level": "绝密",
            "patterns": [
                r'绝\s*密\s*[★\*✡✦※☆⭐＊✳✲]',
                r'绝\s*密\s*级',
                r'(?<![a-zA-Z])TOP\s+SECRET(?![a-zA-Z])',
            ],
            "severity": Severity.CRITICAL,
        },
        # 机密级
        {
            "level": "机密",
            "patterns": [
                r'机\s*密\s*[★\*✡✦※☆⭐＊✳✲]',
                r'机\s*密\s*级',
                r'(?<![a-zA-Z_\-])SECRET(?!\s*(?:KEY|TOKEN|PASSWORD|API|_|:|\d))(?![a-zA-Z])',
            ],
            "severity": Severity.CRITICAL,
        },
        # 秘密级
        {
            "level": "秘密",
            "patterns": [
                r'秘\s*密\s*[★\*✡✦※☆⭐＊✳✲]',
                r'秘\s*密\s*级',
                r'(?<![a-zA-Z_\-])CONFIDENTIAL(?![a-zA-Z])',
            ],
            "severity": Severity.CRITICAL,
        },
    ]

    # 保密期限 / 发文字号模式
    AUX_PATTERNS = [
        {
            "name": "保密期限",
            "pattern": r'保密期限\s*[:：]?\s*\d+\s*年',
            "sub_type": "secret_period",
        },
        {
            "name": "解密时间",
            "pattern": r'解密时间\s*[:：]?\s*\d{4}\s*年',
            "sub_type": "declassify_date",
        },
        {
            "name": "涉密发文字号",
            "pattern": r'[\u4e00-\u9fa5]*密发\s*[\[【\(]?\s*\d{4}\s*[\]】\)]?\s*\d+\s*号',
            "sub_type": "secret_doc_number",
        },
    ]

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        for para in paragraphs:
            text = para.text

            # 检测密级标识
            for mark_config in self.MARK_PATTERNS:
                for pattern_str in mark_config["patterns"]:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    for match in pattern.finditer(text):
                        matched_text = match.group()
                        issues.append(Issue(
                            category=Category.CLASSIFIED,
                            sub_type="secret_mark",
                            severity=mark_config["severity"],
                            content=matched_text,
                            content_raw=matched_text,
                            location=self._make_location(para),
                            paragraph_index=para.index,
                            char_offset=match.start(),
                            char_length=len(matched_text),
                            reason=f"包含{mark_config['level']}级密级标识「{matched_text}」，属于国家秘密",
                            suggestion=f"该文件标注为{mark_config['level']}级，严禁发送至任何外部 AI 平台，请在涉密网络环境下处理",
                            matched_rule=f"密级标识-{mark_config['level']}",
                        ))

            # 检测辅助标识
            for aux in self.AUX_PATTERNS:
                pattern = re.compile(aux["pattern"])
                for match in pattern.finditer(text):
                    matched_text = match.group()
                    issues.append(Issue(
                        category=Category.CLASSIFIED,
                        sub_type=aux["sub_type"],
                        severity=Severity.CRITICAL,
                        content=matched_text,
                        content_raw=matched_text,
                        location=self._make_location(para),
                        paragraph_index=para.index,
                        char_offset=match.start(),
                        char_length=len(matched_text),
                        reason=f"包含涉密辅助标识「{matched_text}」，表明文件具有涉密属性",
                        suggestion="该文件含涉密标注，严禁发送至外部 AI 平台",
                        matched_rule=f"辅助标识-{aux['name']}",
                    ))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )
