"""
基础检测器和数据模型定义
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional
import json


class Category(str, Enum):
    """检测类别"""
    CLASSIFIED = "classified"       # 涉密信息
    SENSITIVE = "sensitive"         # 敏感信息
    RESTRICTED = "restricted"       # 受限使用内容
    CREDENTIAL = "credential"       # 凭证密钥
    INFRASTRUCTURE = "infrastructure"  # 内部架构
    RISKY = "risky"                # 其他风险内容


class Severity(str, Enum):
    """严重程度"""
    CRITICAL = "critical"   # 极高 —— 涉密
    HIGH = "high"           # 高 —— 敏感
    MEDIUM = "medium"       # 中 —— 受限
    LOW = "low"             # 低 —— 风险提示


class Verdict(str, Enum):
    """总体判定"""
    BLOCK = "BLOCK"         # 禁止发送
    WARNING = "WARNING"     # 建议脱敏
    NOTICE = "NOTICE"       # 提示注意
    PASS = "PASS"           # 安全通过


VERDICT_PRIORITY = {
    Verdict.BLOCK: 0,
    Verdict.WARNING: 1,
    Verdict.NOTICE: 2,
    Verdict.PASS: 3,
}


@dataclass
class Paragraph:
    """段落信息"""
    index: int              # 段落编号（从1开始）
    page: Optional[int]     # 所在页码（PDF有效）
    text: str               # 文本内容
    start_char: int         # 起始字符位置（全文偏移）


@dataclass
class Issue:
    """单个检测问题"""
    category: str           # 检测类别
    sub_type: str           # 子类型
    severity: str           # 严重程度
    content: str            # 命中的具体内容（敏感部分打码）
    content_raw: str        # 命中的原始内容（仅日志使用，前端打码）
    location: str           # 位置信息
    paragraph_index: int    # 段落编号
    char_offset: int        # 在段落中的字符偏移
    char_length: int        # 命中内容长度
    reason: str             # 原因说明
    suggestion: str         # 处理建议
    matched_rule: str = ""  # 命中的规则名称

    def to_dict(self):
        return {
            "category": self.category,
            "sub_type": self.sub_type,
            "severity": self.severity,
            "content": self.content,
            "location": self.location,
            "paragraph_index": self.paragraph_index,
            "char_offset": self.char_offset,
            "char_length": self.char_length,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "matched_rule": self.matched_rule,
        }


@dataclass
class DetectionResult:
    """单个检测器的检测结果"""
    detector_name: str
    issues: List[Issue] = field(default_factory=list)
    scan_time_ms: float = 0.0

    def to_dict(self):
        return {
            "detector_name": self.detector_name,
            "issues_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
            "scan_time_ms": round(self.scan_time_ms, 2),
        }


class BaseDetector:
    """检测器基类，所有检测器需继承此类"""

    name: str = "base"
    description: str = ""

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        """
        执行检测
        :param full_text: 完整纯文本
        :param paragraphs: 段落列表（含位置信息）
        :return: DetectionResult
        """
        raise NotImplementedError

    def _make_location(self, para: Paragraph) -> str:
        """生成位置描述"""
        loc = f"第{para.index}段"
        if para.page is not None:
            loc = f"第{para.page}页 {loc}"
        return loc

    def _mask_content(self, text: str, keep_start: int = 2, keep_end: int = 2) -> str:
        """内容打码：保留前后几个字符，中间用***替代"""
        if len(text) <= keep_start + keep_end + 2:
            return text[:1] + "***" + text[-1:] if len(text) > 2 else "***"
        return text[:keep_start] + "***" + text[-keep_end:]

    def _mask_number(self, text: str, keep_start: int = 3, keep_end: int = 4) -> str:
        """数字打码"""
        if len(text) <= keep_start + keep_end:
            return "***"
        masked_len = len(text) - keep_start - keep_end
        return text[:keep_start] + "*" * masked_len + text[-keep_end:]
