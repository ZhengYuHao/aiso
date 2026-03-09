"""
商业敏感信息检测器 —— 检测未公开财务数据、核心算法、客户名单、薪酬信息等
采用 "关键词 + 上下文增强词" 策略，降低误报率
"""
import re
import time
from typing import List, Tuple
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class BusinessSensitiveDetector(BaseDetector):
    """商业敏感信息检测器"""

    name = "商业敏感信息检测智能体"
    description = "检测未公开财务数据、核心算法、客户名单、薪酬信息等商业敏感内容"

    # 关键词 + 增强词组合规则
    # 仅当关键词与增强词在同一上下文窗口内同时出现时才判定为敏感
    RULES = [
        {
            "sub_type": "unpublished_financial",
            "name": "未公开财务数据",
            "keywords": ["营收", "收入", "利润", "净利", "毛利", "EBITDA", "现金流",
                        "资产负债", "财务报表", "营业额", "销售额", "GMV"],
            "enhancers": ["未公开", "内部", "仅限", "不得外传", "保密", "未发布",
                         "预测", "预估", "内部预算", "季度", "Q1", "Q2", "Q3", "Q4"],
            "reason": "包含未公开的财务数据，一旦泄露可能影响资本市场或造成商业损失",
            "suggestion": "建议删除具体财务数字或替换为[财务数据已脱敏]后再发送",
        },
        {
            "sub_type": "core_algorithm",
            "name": "核心算法/代码",
            "keywords": ["核心算法", "专利技术", "技术秘密", "源代码", "核心代码",
                        "加密算法", "推荐算法", "风控模型", "定价模型"],
            "enhancers": ["内部", "保密", "专利", "不得外传", "商业秘密", "核心",
                         "自研", "独有", "竞争优势"],
            "reason": "包含核心算法或技术秘密，属于商业秘密，不应被外部 AI 获取",
            "suggestion": "建议删除核心技术细节，仅保留功能描述后再发送",
        },
        {
            "sub_type": "client_list",
            "name": "客户名单/合同",
            "keywords": ["客户名单", "客户清单", "合同金额", "签约金额", "合同价格",
                        "客户联系方式", "客户资料", "供应商名单"],
            "enhancers": ["内部", "保密", "不得外传", "仅限", "内部使用"],
            "reason": "包含客户名单或合同信息，属于商业敏感数据，不应被外部 AI 获取",
            "suggestion": "建议将客户名称替换为[客户A]、[客户B]等代号，删除合同金额后再发送",
        },
        {
            "sub_type": "bidding_info",
            "name": "招投标信息",
            "keywords": ["报价", "投标价", "标底", "评分细则", "投标方案",
                        "竞标", "中标", "招标文件", "投标书"],
            "enhancers": ["内部", "保密", "不得外传", "仅限", "未公开", "秘密"],
            "reason": "包含招投标相关信息，泄露可能影响公平竞争",
            "suggestion": "建议删除报价和评分细则等关键数据后再发送",
        },
        {
            "sub_type": "salary_info",
            "name": "人事薪酬信息",
            "keywords": ["薪资", "工资", "薪酬", "年薪", "月薪", "绩效奖金",
                        "期权", "股权激励", "绩效评分", "晋升名单"],
            "enhancers": ["内部", "保密", "不得外传", "人事", "HR", "员工"],
            "reason": "包含人事薪酬信息，属于员工隐私和商业敏感数据",
            "suggestion": "建议删除具体姓名和薪资数字，或替换为[已脱敏]后再发送",
        },
        {
            "sub_type": "strategy_plan",
            "name": "内部战略规划",
            "keywords": ["战略规划", "发展战略", "业务规划", "扩张计划",
                        "并购计划", "收购目标", "上市计划", "融资计划"],
            "enhancers": ["内部", "保密", "不得外传", "仅限内部", "董事会",
                         "高管", "管理层", "未公开"],
            "reason": "包含内部战略规划，泄露可能影响公司重大决策和市场竞争",
            "suggestion": "建议删除战略细节和具体数据后再发送",
        },
    ]

    # 直接命中规则（无需增强词，关键词本身就足够说明敏感性）
    DIRECT_RULES = [
        {
            "sub_type": "trade_secret_mark",
            "name": "商业秘密标记",
            "patterns": [
                r'商\s*业\s*秘\s*密',
                r'trade\s*secret',
                r'proprietary\s*(?:and\s*)?confidential',
            ],
            "reason": "文件明确标注为商业秘密，不应被外部 AI 获取",
            "suggestion": "该文件被标注为商业秘密，建议不要发送至外部 AI 平台",
        },
    ]

    CONTEXT_WINDOW = 60  # 上下文窗口大小（字符数）

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        for para in paragraphs:
            text = para.text

            # 1. 关键词 + 增强词 检测
            for rule in self.RULES:
                for keyword in rule["keywords"]:
                    kw_pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    for match in kw_pattern.finditer(text):
                        # 提取上下文窗口
                        ctx_start = max(0, match.start() - self.CONTEXT_WINDOW)
                        ctx_end = min(len(text), match.end() + self.CONTEXT_WINDOW)
                        context = text[ctx_start:ctx_end]

                        # 检查增强词
                        found_enhancer = None
                        for enhancer in rule["enhancers"]:
                            if enhancer.lower() in context.lower():
                                found_enhancer = enhancer
                                break

                        if found_enhancer:
                            display = f"…{context}…" if ctx_start > 0 or ctx_end < len(text) else context
                            issues.append(Issue(
                                category=Category.SENSITIVE,
                                sub_type=rule["sub_type"],
                                severity=Severity.HIGH,
                                content=display,
                                content_raw=context,
                                location=self._make_location(para),
                                paragraph_index=para.index,
                                char_offset=match.start(),
                                char_length=len(match.group()),
                                reason=rule["reason"],
                                suggestion=rule["suggestion"],
                                matched_rule=f"商业敏感-{rule['name']}-{keyword}+{found_enhancer}",
                            ))

            # 2. 直接命中检测
            for rule in self.DIRECT_RULES:
                for pattern_str in rule["patterns"]:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    for match in pattern.finditer(text):
                        matched_text = match.group()
                        issues.append(Issue(
                            category=Category.SENSITIVE,
                            sub_type=rule["sub_type"],
                            severity=Severity.HIGH,
                            content=matched_text,
                            content_raw=matched_text,
                            location=self._make_location(para),
                            paragraph_index=para.index,
                            char_offset=match.start(),
                            char_length=len(matched_text),
                            reason=rule["reason"],
                            suggestion=rule["suggestion"],
                            matched_rule=f"商业敏感-{rule['name']}",
                        ))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )
