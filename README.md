# 大模型输入内容安全检测系统 Demo V2.0

## 系统定位

在用户将文件发送给大模型之前，自动检测并拦截所有不应被 AI 看到的内容，包括：

- **涉密信息**（密级标识、军事/国安/外交/核心技术关键词）→ 强制拦截
- **敏感信息**（身份证号、手机号、银行卡号、商业秘密等）→ 建议脱敏
- **受限内容**（内部文件、版权保护、AI使用限制等）→ 风险提示
- **其他风险**（API密钥、数据库连接、内网IP等）→ 提示注意

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

## 双模式检测

系统支持两种检测模式：

| 模式 | 说明 |
|------|------|
| 规则引擎 | 基于正则表达式和关键词库的本地检测，速度快 |
| AI智能体 | 调用 LLM API 进行智能分析，支持 ChatGPT 4o、阿里云通义千问、百度文心一言 |

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
BAIDU_SECRET_KEY=your-baidu-secret-key-here
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
│   ├── classified_mark_detector.py     # 密级标识检测智能体
│   ├── classified_keyword_detector.py  # 涉密关键词检测智能体
│   ├── stamp_ocr_detector.py           # 公章OCR检测智能体
│   ├── pii_detector.py                 # 个人隐私信息检测智能体
│   ├── business_sensitive_detector.py  # 商业敏感信息检测智能体
│   ├── restricted_content_detector.py  # 受限内容检测智能体
│   ├── credential_detector.py          # 凭证密钥检测智能体
│   ├── infrastructure_detector.py      # 内部架构信息检测智能体
│   └── detection_orchestrator.py       # 检测调度器
├── config/                             # 规则配置
│   ├── classified_keywords.json        # 涉密关键词库
│   └── ocr_config.json                 # OCR 配置
├── templates/
│   └── index.html                      # 前端页面
├── uploads/                            # 临时上传目录
└── logs/                               # 检测日志目录
```

## 支持的文件格式

| 格式   | 说明                  |
|--------|----------------------|
| .docx  | Word 文档            |
| .txt   | 纯文本文件           |
| .pdf   | PDF 文档             |

## 检测器列表（8个）

| 层级 | 规则引擎 | AI智能体 |
|------|---------|---------|
| 第一层 | 涉密标识检测智能体处理 | 涉密标识检测智能体处理 |
| 第一层 | 涉密关键词检测智能体处理 | 涉密信息检测智能体处理 |
| 第二层 | 公章OCR检测智能体处理 | 公章OCR检测智能体处理 |
| 第二层 | 个人隐私信息检测智能体处理 | 个人隐私信息检测智能体处理 |
| 第二层 | 商业敏感信息检测智能体处理 | 商业敏感信息检测智能体处理 |
| 第三层 | 受限内容检测智能体处理 | 受限内容检测智能体处理 |
| 第四层 | 凭证密钥检测智能体处理 | 凭证密钥检测智能体处理 |
| 第四层 | 内部架构信息检测智能体处理 | 内部架构信息检测智能体处理 |

## 判定结果

| 层级   | 类别       | 判定       | 颜色   |
|--------|-----------|-----------|--------|
| 第一层 | 涉密信息   | BLOCK     | 🔴 红色 |
| 第二层 | 敏感信息   | WARNING   | 🟠 橙色 |
| 第三层 | 受限内容   | NOTICE    | 🟡 黄色 |
| 第四层 | 风险内容   | NOTICE    | 🔵 蓝色 |
| 通过   | 安全       | PASS      | 🟢 绿色 |

## 功能特性

- ✅ 多文件并发处理
- ✅ 双模式检测（规则引擎 / AI智能体）
- ✅ OCR 公章检测
- ✅ 综合处理建议
- ✅ 检测日志详情
- ✅ 支持多种 LLM 提供商

## 环境要求

- Python 3.8+
- 浏览器：Chrome / Edge（最新版）
- 系统：Windows / Linux / macOS
