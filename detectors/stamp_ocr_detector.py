"""
公章 OCR 检测器 —— 使用 MinerU/PaddleOCR 识别文件中的公章文字，检测是否包含涉密信息
"""
import time
import os
from typing import List
from .base_detector import (
    BaseDetector, DetectionResult, Paragraph, Issue,
    Category, Severity
)
from .file_parser import FileParser


STAMP_CLASSIFIED_KEYWORDS = {
    "绝密": [
        "绝密", "绝密章", "绝密文件", "秘密", "机密", "机密章",
        "秘密文件", "机密文件", "最高机密", "国家机密"
    ],
    "机密": [
        "机密", "机密章", "内部机密", "秘密级", "机密级"
    ],
    "秘密": [
        "秘密", "秘密章", "内部秘密", "涉密", "保密"
    ],
    "公文标识": [
        "发文", "收文", "急件", "特件", "内部资料",
        "不准复制", "不准翻印", "限国内发行"
    ]
}

STAMP_SEVERITY = {
    "绝密": Severity.CRITICAL,
    "机密": Severity.CRITICAL,
    "secret": Severity.HIGH,
    "公文标识": Severity.MEDIUM,
}


class StampOCRDetector(BaseDetector):
    """公章 OCR 检测器"""

    name = "公章OCR检测智能体"
    description = "通过 OCR 技术识别文件中的公章文字，检测是否包含涉密信息"

    def __init__(self, config_path: str = None):
        self.parser = FileParser()

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=0.0
        )

    def detect_from_file(self, filepath: str) -> DetectionResult:
        """直接从文件进行 OCR 检测"""
        start = time.time()
        issues = []

        try:
            ocr_results = self.parser.extract_and_ocr(filepath)

            for ocr_result in ocr_results:
                page = ocr_result.get("page", 0)
                text_lines = ocr_result.get("text_lines", [])
                ocr_text = ocr_result.get("ocr_text", "")

                for level, keywords in STAMP_CLASSIFIED_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in ocr_text:
                            severity = STAMP_SEVERITY.get(level, Severity.HIGH)

                            context_start = max(0, ocr_text.find(keyword) - 10)
                            context_end = min(len(ocr_text), ocr_text.find(keyword) + len(keyword) + 10)
                            context = ocr_text[context_start:context_end]

                            issues.append(Issue(
                                category=Category.CLASSIFIED,
                                sub_type=f"stamp_ocr_{level}",
                                severity=severity,
                                content=f"…{context}…",
                                content_raw=ocr_text,
                                location=f"第{page}页（OCR识别）",
                                paragraph_index=page,
                                char_offset=0,
                                char_length=len(ocr_text),
                                reason=f"OCR识别到公章包含「{keyword}」关键词，该内容涉及国家秘密",
                                suggestion=f"该公章包含涉密标识「{keyword}」，严禁发送至外部 AI 平台",
                                matched_rule=f"公章OCR-{level}-{keyword}",
                            ))
                            break

        except Exception as e:
            pass

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed
        )
