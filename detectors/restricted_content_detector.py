"""
受限使用内容检测器 —— 检测内部管理文件标识和版权受限内容
"""
import re
import time
from typing import List
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class RestrictedContentDetector(BaseDetector):
    """受限使用内容检测器"""

    name = "受限内容检测智能体"
    description = "检测内部管理文件标识和版权受限内容"

    # 内部文件标识
    INTERNAL_PATTERNS = [
        {
            "sub_type": "internal_doc",
            "name": "内部文件标识",
            "patterns": [
                r'仅\s*限?\s*内\s*部(?:\s*使用|\s*参考|\s*阅读|\s*传阅|\s*交流)',
                r'不\s*得\s*(?:外\s*传|转\s*发|扩\s*散|对\s*外|泄\s*露|复\s*制)',
                r'内\s*部\s*(?:资料|文件|文档|材料|参考|通报|通知|简报)',
                r'(?:阅\s*后\s*即\s*焚|限\s*定\s*范\s*围\s*阅\s*读)',
                r'(?:禁\s*止\s*外\s*泄|严\s*禁\s*外\s*传)',
            ],
            "reason": "文件包含内部使用限制标识，表明该内容仅限组织内部使用，不应发送至外部 AI 平台",
            "suggestion": "建议删除内部限制性标注部分，或确认内容脱敏后再发送",
        },
        {
            "sub_type": "audit_report",
            "name": "内部审计报告",
            "patterns": [
                r'(?:内部\s*)?审\s*计\s*报\s*告',
                r'内\s*审\s*(?:报告|发现|意见|结论|整改)',
                r'审\s*计\s*整\s*改\s*(?:方案|措施|报告)',
            ],
            "reason": "文件包含内部审计报告内容，属于组织内部管理文件，不应被外部 AI 获取",
            "suggestion": "建议删除审计详细发现和整改措施后再发送",
        },
        {
            "sub_type": "meeting_restricted",
            "name": "限制性会议纪要",
            "patterns": [
                r'(?:仅\s*限\s*)?会\s*议\s*(?:参与人|参加人|出席人)(?:\s*(?:阅读|查看|知悉))',
                r'会\s*议\s*(?:纪要|记录).*?(?:不得外传|仅限内部|内部参考)',
                r'(?:党\s*委|董\s*事\s*会|管\s*理\s*层)\s*(?:会议|决议).*?(?:内部|保密)',
            ],
            "reason": "文件包含限制性会议纪要，会议内容仅限参与人知悉，不应发送至外部 AI",
            "suggestion": "建议删除会议具体讨论内容和决议细节后再发送",
        },
        {
            "sub_type": "exam_material",
            "name": "试题/答案",
            "patterns": [
                r'(?:试卷|试题|考卷|考试题|测试题)',
                r'(?:标准\s*答案|参考\s*答案|评分\s*(?:标准|细则))',
                r'(?:考试\s*用|命题\s*(?:材料|参考))',
            ],
            "reason": "文件包含试题或答案内容，发送至 AI 可能导致泄题",
            "suggestion": "试题和答案属于受限材料，建议不要发送至外部 AI 平台",
        },
    ]

    # 版权受限内容
    COPYRIGHT_PATTERNS = [
        {
            "sub_type": "copyright_notice",
            "name": "版权声明",
            "patterns": [
                r'版\s*权\s*所\s*有',
                r'All\s*Rights?\s*Reserved',
                r'未\s*经\s*(?:授权|许可|书面同意)\s*(?:禁止|不得)\s*(?:转载|复制|传播|使用)',
                r'©\s*\d{4}',
                r'Copyright\s*©?\s*\d{4}',
            ],
            "reason": "文件包含版权声明，将受版权保护的内容发送至 AI 可能涉及版权问题",
            "suggestion": "请确认版权方是否允许 AI 处理该内容，或删除受版权保护的部分后再发送",
        },
        {
            "sub_type": "ai_restriction",
            "name": "AI使用限制",
            "patterns": [
                r'(?:禁止|不得|不允许)\s*(?:用于|使用)\s*(?:AI|人工智能)\s*(?:训练|处理|分析)',
                r'(?:禁止|不得)\s*(?:自动化|机器)\s*(?:处理|分析|抓取|爬取)',
                r'not\s*(?:for|allowed)\s*(?:AI|machine)\s*(?:training|processing)',
            ],
            "reason": "文件明确标注禁止用于 AI 处理，发送至大模型将违反使用条款",
            "suggestion": "该文件明确禁止 AI 处理，请勿发送至任何 AI 平台",
        },
        {
            "sub_type": "paywall_content",
            "name": "付费内容标识",
            "patterns": [
                r'仅\s*限\s*(?:订阅|付费|会员)\s*(?:用户|会员)',
                r'(?:购买|付费)\s*后\s*(?:查看|阅读|下载)',
                r'(?:VIP|会员)\s*(?:专属|专享|独享)\s*(?:内容|资料)',
            ],
            "reason": "文件包含付费内容标识，将付费内容发送至 AI 可能违反服务条款",
            "suggestion": "请确认是否有权将该付费内容用于 AI 处理",
        },
    ]

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        all_rules = self.INTERNAL_PATTERNS + self.COPYRIGHT_PATTERNS

        for para in paragraphs:
            text = para.text
            for rule_group in all_rules:
                for pattern_str in rule_group["patterns"]:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    for match in pattern.finditer(text):
                        matched_text = match.group()
                        # 提取上下文
                        ctx_start = max(0, match.start() - 20)
                        ctx_end = min(len(text), match.end() + 20)
                        context = text[ctx_start:ctx_end]

                        issues.append(Issue(
                            category=Category.RESTRICTED,
                            sub_type=rule_group["sub_type"],
                            severity=Severity.MEDIUM,
                            content=f"…{context}…" if ctx_start > 0 or ctx_end < len(text) else context,
                            content_raw=matched_text,
                            location=self._make_location(para),
                            paragraph_index=para.index,
                            char_offset=match.start(),
                            char_length=len(matched_text),
                            reason=rule_group["reason"],
                            suggestion=rule_group["suggestion"],
                            matched_rule=f"受限内容-{rule_group['name']}",
                        ))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )
