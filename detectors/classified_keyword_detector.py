"""
涉密关键词检测器 —— 通过分级关键词库检测涉密内容
"""
import re
import os
import json
import time
from typing import List, Dict
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


# 默认关键词库（当配置文件不存在时使用）
DEFAULT_CLASSIFIED_KEYWORDS = {
    "绝密": {
        "军事国防": [
            "核武器参数", "核弹头", "洲际导弹", "弹道导弹射程",
            "战略武器", "核打击", "核反击", "战略核潜艇",
            "核密码", "核按钮", "发射密码", "作战指挥密码",
        ],
        "情报安全": [
            "绝密情报", "特工名单", "间谍网络", "情报来源",
            "线人信息", "卧底身份", "秘密行动代号",
        ],
        "核心技术": [
            "核武器设计图", "导弹制导算法", "卫星加密算法",
            "量子密钥分发参数", "核心芯片设计源码",
        ],
    },
    "机密": {
        "军事部署": [
            "部队番号", "军事部署", "作战计划", "兵力配置",
            "军事演习方案", "装备列装计划", "武器型号参数",
            "军事调动", "战备等级", "国防工程坐标",
        ],
        "国家安全": [
            "反间谍行动", "国家安全审查", "侦查手段",
            "监听记录", "技术侦察", "安全防范部署",
            "反恐行动方案", "边防部署",
        ],
        "外交密级": [
            "外交电报", "领事机密", "对外谈判策略",
            "大使密电", "外交斡旋方案", "条约草案",
        ],
    },
    "秘密": {
        "政府内部": [
            "内部参考", "内部通报", "阅后即焚",
            "不得扩散", "限定范围阅读", "内部讨论稿",
        ],
        "经济安全": [
            "国家经济战略", "外汇储备详情", "战略储备数据",
            "关键矿产储量", "能源战略部署",
        ],
        "科研机密": [
            "涉密科研项目", "国防科研", "军工研究",
            "保密专利", "涉密实验数据",
        ],
    },
}


class ClassifiedKeywordDetector(BaseDetector):
    """涉密关键词检测器"""

    name = "涉密关键词检测智能体"
    description = "通过分级关键词库检测涉密内容"

    LEVEL_SEVERITY = {
        "绝密": Severity.CRITICAL,
        "机密": Severity.CRITICAL,
        "秘密": Severity.CRITICAL,
    }

    def __init__(self, config_path: str = None):
        self.keywords = self._load_keywords(config_path)

    def _load_keywords(self, config_path: str = None) -> Dict:
        """加载关键词配置"""
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_CLASSIFIED_KEYWORDS

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        # 按优先级：绝密 → 机密 → 秘密
        for level in ["绝密", "机密", "秘密"]:
            if level not in self.keywords:
                continue
            categories = self.keywords[level]
            for cat_name, keyword_list in categories.items():
                for keyword in keyword_list:
                    # 在每个段落中搜索关键词
                    for para in paragraphs:
                        text = para.text
                        # 使用正则支持关键词中间可能有空格
                        escaped = re.escape(keyword)
                        flexible = r'\s*'.join(escaped)
                        pattern = re.compile(flexible, re.IGNORECASE)

                        for match in pattern.finditer(text):
                            matched_text = match.group()

                            # 提取上下文窗口（前后30字）
                            ctx_start = max(0, match.start() - 30)
                            ctx_end = min(len(text), match.end() + 30)
                            context = text[ctx_start:ctx_end]

                            issues.append(Issue(
                                category=Category.CLASSIFIED,
                                sub_type=f"classified_keyword_{cat_name}",
                                severity=self.LEVEL_SEVERITY[level],
                                content=f"…{context}…" if ctx_start > 0 or ctx_end < len(text) else context,
                                content_raw=matched_text,
                                location=self._make_location(para),
                                paragraph_index=para.index,
                                char_offset=match.start(),
                                char_length=len(matched_text),
                                reason=f"包含{level}级涉密关键词「{keyword}」（类别：{cat_name}），该内容涉及国家秘密",
                                suggestion=f"该内容涉及{level}级国家秘密，严禁发送至外部 AI 平台，请删除相关内容或在涉密环境下处理",
                                matched_rule=f"涉密关键词-{level}-{cat_name}-{keyword}",
                            ))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )
