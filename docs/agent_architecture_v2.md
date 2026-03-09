# Agent 架构设计方案 B：多层级 Skills Orchestrator

## 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        输入: 文件                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Master Agent (总调度)                         │
│  职责: 分析文件内容 → 决策调用哪些 Category Orchestrator        │
│  LLM调用: 1次 (判断需要检测哪些大类)                            │
└─────────────────────────────────────────────────────────────────┘
                                │
           ┌────────────────────┼────────────────────┐
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Category Agent 1  │ │ Category Agent 2  │ │ Category Agent N  │
│ 涉密信息检测      │ │ 敏感信息检测      │ │ 其他类别...       │
│ (3 Skills)       │ │ (4 Skills)        │ │                   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │ Skill: 密级  │      │ Skill: PII  │      │   Skill    │
    │ Skill: 关键词│      │ Skill: 商业  │      │             │
    │ Skill: 公章 │      │ Skill: ...   │      │             │
    └─────────────┘      └─────────────┘      └─────────────┘
```

## 二、层级设计

### 层级1: Master Agent (总调度)
- **位置**: `detection_orchestrator.py`
- **职责**: 
  - 接收文件文本
  - 调用 LLM 判断需要检测的大类
  - 调度各个 Category Agent

### 层级2: Category Agent (分类调度)
- **位置**: `detectors/agents/category_agents/`
- **8个分类**:
  1. `classified_agent.py` - 涉密信息检测
  2. `sensitive_agent.py` - 敏感信息检测
  3. `restricted_agent.py` - 受限内容检测
  4. `credential_agent.py` - 凭证密钥检测
  5. `infrastructure_agent.py` - 内部架构检测

- **职责**:
  - 分析文件内容，决定调用哪些 Skills
  - 并行执行选定的 Skills
  - 汇总结果

### 层级3: Skill (具体检测能力)
- **位置**: `detectors/skills/` (重构现有检测器)
- **已有 Skills (8个)**:
  1. `classified_mark_skill.py` - 密级标识检测
  2. `classified_keyword_skill.py` - 涉密关键词检测
  3. `stamp_ocr_skill.py` - 公章OCR检测
  4. `pii_skill.py` - 个人隐私信息检测
  5. `business_sensitive_skill.py` - 商业敏感检测
  6. `restricted_content_skill.py` - 受限内容检测
  7. `credential_skill.py` - 凭证密钥检测
  8. `infrastructure_skill.py` - 内部架构检测

## 三、目录结构

```
detectors/
├── __init__.py
├── base_detector.py          # 基础数据模型
├── file_parser.py            # 文件解析
├── llm_client.py             # LLM 调用
├── ocr_client.py             # OCR 调用
├── logger.py                  # 日志
├── detection_orchestrator.py # Master Agent (总调度)
│
├── agents/                    # Agent 层
│   ├── __init__.py
│   ├── base_agent.py         # Agent 基类
│   ├── master_agent.py       # Master Agent (总调度)
│   │
│   └── category_agents/       # 8个 Category Agents
│       ├── __init__.py
│       ├── classified_agent.py      # 涉密信息
│       ├── sensitive_agent.py        # 敏感信息
│       ├── restricted_agent.py      # 受限内容
│       ├── credential_agent.py      # 凭证密钥
│       └── infrastructure_agent.py  # 内部架构
│
├── skills/                    # Skill 层 (重构现有检测器)
│   ├── __init__.py
│   ├── base_skill.py         # Skill 基类
│   │
│   ├── classified/           # 涉密相关 Skills
│   │   ├── __init__.py
│   │   ├── classified_mark_skill.py
│   │   ├── classified_keyword_skill.py
│   │   └── stamp_ocr_skill.py
│   │
│   ├── sensitive/           # 敏感信息 Skills
│   │   ├── __init__.py
│   │   ├── pii_skill.py
│   │   └── business_sensitive_skill.py
│   │
│   ├── restricted/          # 受限内容 Skills
│   │   ├── __init__.py
│   │   └── restricted_content_skill.py
│   │
│   ├── credential/          # 凭证 Skills
│   │   ├── __init__.py
│   │   └── credential_skill.py
│   │
│   └── infrastructure/      # 架构信息 Skills
│       ├── __init__.py
│       └── infrastructure_skill.py
│
└── utils/                   # 工具层
    ├── __init__.py
    ├── prompt_templates.py  # Prompt 模板
    └── result_merger.py    # 结果合并
```

## 四、核心类设计

### 4.1 Skill 基类

```python
# detectors/skills/base_skill.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class SkillResult:
    skill_name: str
    is_triggered: bool
    severity: Severity
    reason: str
    suggestion: str
    evidence: Dict[str, Any]  # 具体证据

class BaseSkill(ABC):
    """Skill 基类"""
    
    name: str           # Skill 名称
    description: str   # Skill 描述
    category: str       # 所属大类
    
    @abstractmethod
    def detect(self, text: str, **kwargs) -> SkillResult:
        """执行检测"""
        pass
    
    @abstractmethod
    def should_use(self, context: str) -> bool:
        """
        判断是否应该使用此 Skill
        由 Category Agent 调用，用于决策
        """
        pass
    
    def get_prompt(self) -> str:
        """获取检测 Prompt"""
        return f"检测内容: {self.description}"
```

### 4.2 Skill 实现示例

```python
# detectors/skills/classified/classified_mark_skill.py
from ..base_skill import BaseSkill, SkillResult, Severity

class ClassifiedMarkSkill(BaseSkill):
    """密级标识检测 Skill"""
    
    name = "classified_mark_detector"
    description = "检测文件中的密级标识，如'绝密'、'机密'、'秘密'等"
    category = "classified"
    
    KEYWORDS = ["绝密", "机密", "秘密", "内部资料", "密级"]
    
    def should_use(self, context: str) -> bool:
        """判断是否需要使用此 Skill"""
        # 简单规则：如果文本中包含可能的风险词
        return any(kw in context for kw in ["密", "秘密", "机密", "绝密"])
    
    def detect(self, text: str, **kwargs) -> SkillResult:
        """执行检测"""
        found = []
        for keyword in self.KEYWORDS:
            if keyword in text:
                found.append(keyword)
        
        if found:
            return SkillResult(
                skill_name=self.name,
                is_triggered=True,
                severity=Severity.CRITICAL,
                reason=f"检测到密级标识: {', '.join(found)}",
                suggestion="该文件包含涉密标识，严禁发送至外部 AI 平台",
                evidence={"keywords": found}
            )
        
        return SkillResult(
            skill_name=self.name,
            is_triggered=False,
            severity=Severity.LOW,
            reason="未检测到密级标识",
            suggestion="",
            evidence={}
        )
```

### 4.3 Category Agent

```python
# detectors/agents/category_agents/classified_agent.py
from typing import List
from ...skills.base_skill import BaseSkill, SkillResult
from ..base_agent import BaseCategoryAgent

class ClassifiedAgent(BaseCategoryAgent):
    """涉密信息检测 Category Agent"""
    
    name = "涉密信息检测"
    description = "检测涉密相关信息，包括密级标识、涉密关键词、公章等"
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.skills: List[BaseSkill] = [
            ClassifiedMarkSkill(),
            ClassifiedKeywordSkill(),
            StampOCRSkill(),
        ]
    
    async def select_skills(self, text: str) -> List[BaseSkill]:
        """
        使用 LLM 决策需要调用哪些 Skills
        """
        skill_descriptions = "\n".join([
            f"- {s.name}: {s.description}" 
            for s in self.skills
        ])
        
        prompt = f"""
你是一个安全检测专家。需要检测以下文本中的涉密信息。

可选的检测技能:
{skill_descriptions}

请分析文本内容，判断需要使用哪些技能进行检测。
返回 JSON 格式:
{{
    "selected_skills": ["skill_name1", "skill_name2"],
    "reason": "选择理由"
}}

待检测文本: {text[:2000]}
"""
        
        result = await self.llm_client.chat(prompt)
        selected_names = self._parse_llm_result(result)
        
        return [s for s in self.skills if s.name in selected_names]
    
    async def execute(self, text: str) -> List[SkillResult]:
        """执行检测"""
        # 1. 决策使用哪些 Skills
        selected_skills = await self.select_skills(text)
        
        # 2. 并行执行
        results = await asyncio.gather(*[
            skill.detect(text) for skill in selected_skills
        ])
        
        # 3. 过滤触发检测的
        return [r for r in results if r.is_triggered]
```

### 4.4 Master Agent

```python
# detectors/agents/master_agent.py
from typing import List, Dict
from .category_agents import (
    ClassifiedAgent,
    SensitiveAgent,
    RestrictedAgent,
    CredentialAgent,
    InfrastructureAgent
)

class MasterAgent:
    """总调度 Agent"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.category_agents = [
            ClassifiedAgent(llm_client),
            SensitiveAgent(llm_client),
            RestrictedAgent(llm_client),
            CredentialAgent(llm_client),
            InfrastructureAgent(llm_client),
        ]
    
    async def detect(self, text: str) -> Dict:
        """
        主检测流程
        """
        # 1. 分析文件，决定检测哪些大类
        selected_categories = await self._select_categories(text)
        
        # 2. 并行执行各类别检测
        all_results = []
        for agent in self.category_agents:
            if agent.name in selected_categories:
                results = await agent.execute(text)
                all_results.extend(results)
        
        # 3. 汇总结果
        return self._merge_results(all_results)
    
    async def _select_categories(self, text: str) -> List[str]:
        """使用 LLM 判断需要检测的大类"""
        categories = "\n".join([
            f"- {agent.name}: {agent.description}"
            for agent in self.category_agents
        ])
        
        prompt = f"""
你是一个安全检测专家。分析以下文本，判断需要检测哪些安全类别。

可选类别:
{categories}

返回 JSON 格式:
{{
    "selected_categories": ["类别1", "类别2"],
    "reason": "判断理由"
}}

文本内容: {text[:3000]}
"""
        
        result = await self.llm_client.chat(prompt)
        return self._parse_categories(result)
```

## 五、调用流程

```
1. 用户上传文件
       │
       ▼
2. file_parser.parse() 提取文本
       │
       ▼
3. MasterAgent.detect(text)
       │
       ├── 3.1 MasterAgent._select_categories(text)
       │     └── LLM 判断需要检测的大类
       │
       ▼
4. for each selected_category:
       │
       ├── CategoryAgent.execute(text)
       │     │
       │     ├── 4.1 select_skills(text)
       │     │     └── LLM 判断需要使用的 Skills
       │     │
       │     └── 4.2 并行执行 Skills
       │           └── Skill.detect(text)
       │
       ▼
5. 汇总所有结果 → 最终报告
```

## 六、LLM 调用次数优化

| 场景 | 当前架构 | 新架构 |
|------|---------|--------|
| 普通文件(无风险) | 8次 | 1次 (Master) + 0次 (无风险类别) |
| 敏感文件 | 8次 | 1次 + N次 (涉及的Category) + M次 (涉及的Skills) |
| 最佳情况 | 8次 | 1-2次 |

## 七、扩展性

新增 Skill 只需：
1. 在对应目录下创建 Skill 类
2. 注册到 Category Agent 的 skills 列表

无需修改核心调度逻辑。

---

## 总结

此方案优势：
- ✅ 层级清晰 (Master → Category → Skill)
- ✅ 职责明确
- ✅ LLM 调用按需，减少成本
- ✅ 便于扩展和维护
- ✅ 与现有代码兼容 (Skill 可复用现有检测器逻辑)

需要审核请反馈，我可以开始实现！
