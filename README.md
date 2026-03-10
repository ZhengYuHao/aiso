# 大模型输入内容安全检测系统 Demo V2.0

## 系统定位

在用户将文件发送给大模型之前，自动检测并拦截所有不应被 AI 看到的内容，包括：

- **涉密信息**（密级标识、军事/国安/外交/核心技术关键词）→ 强制拦截
- **敏感信息**（身份证号、手机号、银行卡号、商业秘密等）→ 建议脱敏
- **受限内容**（内部文件、版权保护、AI使用限制等）→ 风险提示
- **凭证密钥**（API Key、Token、密码等）→ 提示注意
- **内部架构**（内网IP、服务器路径、主机名等）→ 提示注意

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM API（可选，使用 AI 智能体模式时需要）
# 编辑 .env 文件，配置你的 API 密钥
# LLM_PROVIDER=openai  # 可选: openai, aliyun, baidu
# OPENAI_API_KEY=your-key-here

# 3. 生成测试文件（可选）
python generate_test_files.py

# 4. 启动系统
python app.py

# 5. 打开浏览器访问
# http://localhost:5000
```

## 三层 Agent 架构

系统采用 **Master Agent → Category Agent → Skill** 三层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                      Master Agent                           │
│                    (总调度智能体)                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Classified  │ │   Sensitive   │ │   Restricted  │
│     Agent     │ │     Agent     │ │     Agent     │
│  (涉密信息)    │ │  (敏感信息)    │ │  (受限内容)    │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
   ┌────┴────┐       ┌────┴────┐       ┌────┴────┐
   │ Skills  │       │ Skills  │       │ Skills  │
   └─────────┘       └─────────┘       └─────────┘
```

### Category Agents（5个分类智能体）

| Agent | 检测类别 | Skills |
|-------|---------|--------|
| ClassifiedAgent | 涉密信息 | ClassifiedMarkSkill, ClassifiedKeywordSkill, StampOCRSkill |
| SensitiveAgent | 敏感信息 | PIISkill, BusinessSensitiveSkill |
| RestrictedAgent | 受限内容 | RestrictedContentSkill |
| CredentialAgent | 凭证密钥 | CredentialSkill |
| InfrastructureAgent | 内部架构 | InfrastructureSkill |

### Skills（细粒度检测技能）

每个 Skill 封装独立的检测逻辑：

- **ClassifiedMarkSkill**: 密级标识检测（绝密/机密/秘密）
- **ClassifiedKeywordSkill**: 涉密关键词检测
- **StampOCRSkill**: 公章 OCR 识别
- **PIISkill**: 个人隐私信息检测（身份证、银行卡、手机号等）
- **BusinessSensitiveSkill**: 商业敏感信息检测
- **RestrictedContentSkill**: 受限内容检测
- **CredentialSkill**: 凭证密钥检测（API Key、Token等）
- **InfrastructureSkill**: 内部架构信息检测

## 双模式检测

| 模式 | 说明 |
|------|------|
| 规则引擎 | 执行所有 Skills，基于正则表达式和关键词库检测 |
| AI智能体 | LLM 智能决策，先分析文本选择需要检测的类别和 Skills |

### LLM 智能决策流程

1. **Master Agent** 分析文本，决定需要检测的 Category
2. **Category Agent** 进一步决定需要调用的 Skills
3. **Skill** 执行细粒度检测，返回结果

### LLM API 配置

编辑 `.env` 文件配置 API：

```env
# 选择提供商: openai, aliyun, baidu
LLM_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 阿里云配置（可选）
ALIYUN_API_KEY=your-aliyun-key-here
ALIYUN_MODEL=qwen-turbo

# 百度配置（可选）
BAIDU_API_KEY=your-baidu-api-key-here

# OCR 配置（可选）
# 可用提供商: openai, aliyun, baidu (默认使用 openai，使用 LLM 的 API 密钥)
OCR_PROVIDER=openai
OPENAI_OCR_MODEL=gpt-4o
```

## 项目结构

```
aiso/
├── app.py                              # Flask 主应用
├── requirements.txt                    # Python 依赖
├── .env                                # 环境变量配置
├── generate_test_files.py              # 测试文件生成器
├── detectors/                          # 核心检测模块
│   ├── __init__.py
│   ├── base_detector.py                # 基类和数据模型
│   ├── file_parser.py                  # 多格式文件解析器
│   ├── llm_client.py                   # LLM API 客户端
│   ├── ocr_client.py                   # OCR API 客户端
│   ├── detection_orchestrator.py       # 检测调度器
│   ├── agents/                         # Agent 层
│   │   ├── master_agent.py             # Master Agent（总调度）
│   │   ├── base_agent.py              # Category Agent 基类
│   │   ├── learning/                  # 边学边用模块（新增）
│   │   │   ├── learning_agent.py     # 边学边用智能体
│   │   │   ├── evaluation_agent.py   # 测试评估智能体
│   │   │   └── learned_skill.py       # 学习到的规则数据模型
│   │   └── category_agents/            # 5 个分类 Agent
│   │       ├── classified_agent.py
│   │       ├── sensitive_agent.py
│   │       ├── restricted_agent.py
│   │       ├── credential_agent.py
│   │       └── infrastructure_agent.py
│   └── skills/                         # Skill 层
│       ├── base_skill.py              # Skill 基类
│       ├── classified/                # 涉密检测 Skills
│       ├── sensitive/                 # 敏感检测 Skills
│       ├── restricted/                # 受限检测 Skills
│       ├── credential/                # 凭证检测 Skills
│       └── infrastructure/            # 架构检测 Skills
├── config/                             # 规则配置
│   ├── classified_keywords.json        # 涉密关键词库
│   ├── learning_config.json           # 边学边用配置
│   ├── learned_skills/               # 学习到的规则存储
│   │   ├── metadata.json             # 规则索引
│   │   └── evaluation_reports/       # 评估报告
│   └── ocr_config.json                 # OCR 配置
├── templates/
│   └── index.html                      # 前端页面
├── uploads/                            # 临时上传目录
└── logs/                               # 检测日志目录
```

## 边学边用系统

系统支持**边学边用**功能，能够从 LLM 检测结果中自动学习新的检测规则。

### 工作原理

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  LLM 检测   │ →  │ Learning   │ →  │ Evaluation │ →  │ 规则存储   │
│  发现问题   │    │   Agent    │    │   Agent    │    │ 复用      │
│             │    │  学习规则   │    │  测试评估   │    │           │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 规则状态

| 状态 | 说明 | 阈值 |
|------|------|------|
| testing | 待测试 | F1 < 0.8 |
| active | 已激活 | F1 >= 0.8 |
| discarded | 已丢弃 | F1 < 0.3 |

### 配置选项

编辑 `config/learning_config.json`:

```json
{
    "learning_enabled": true,
    "auto_activate_threshold": 0.8,
    "min_samples_for_learning": 1,
    "max_learned_skills": 100,
    "evaluation_interval_hours": 24,
    "min_test_cases": 10
}
```

### 查看学习结果

学习到的规则保存在 `config/learned_skills/` 目录，评估报告保存在 `evaluation_reports/` 子目录。

## 支持的文件格式

| 格式   | 说明                  |
|--------|----------------------|
| .docx  | Word 文档            |
| .txt   | 纯文本文件           |
| .pdf   | PDF 文档             |

## 判定结果

| 类别       | 判定       | 颜色   |
|-----------|-----------|--------|
| 涉密信息   | BLOCK     | 🔴 红色 |
| 敏感信息   | WARNING   | 🟠 橙色 |
| 受限内容   | NOTICE    | 🟡 黄色 |
| 凭证/架构  | NOTICE    | 🔵 蓝色 |
| 通过       | PASS      | 🟢 绿色 |

## 功能特性

- ✅ 三层 Agent 架构（Master → Category → Skill）
- ✅ LLM 智能决策选择检测类别和 Skills
- ✅ 边学边用（从 LLM 检测结果自动学习新规则）
- ✅ 规则自动评估（F1 分数阈值激活/丢弃）
- ✅ 多文件并发处理
- ✅ 双模式检测（规则引擎 / AI智能体）
- ✅ OCR 公章检测
- ✅ 综合处理建议
- ✅ 检测日志详情
- ✅ 支持多种 LLM 提供商
- ✅ 模块化设计，便于扩展新的检测技能

## 环境要求

- Python 3.8+
- 浏览器：Chrome / Edge（最新版）
- 系统：Windows / Linux / macOS
