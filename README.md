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
pip install flask python-docx PyPDF2

# 2. 生成测试文件（可选）
python generate_test_files.py

# 3. 启动系统
python app.py

# 4. 打开浏览器访问
# http://localhost:5000
```

## 项目结构

```
security-system/
├── app.py                              # Flask 主应用
├── requirements.txt                    # Python 依赖
├── generate_test_files.py              # 测试文件生成器
├── detectors/                          # 核心检测模块
│   ├── __init__.py
│   ├── base_detector.py                # 基类和数据模型
│   ├── file_parser.py                  # 多格式文件解析器
│   ├── classified_mark_detector.py     # 密级标识检测
│   ├── classified_keyword_detector.py  # 涉密关键词检测
│   ├── pii_detector.py                 # 个人隐私信息检测
│   ├── business_sensitive_detector.py  # 商业敏感信息检测
│   ├── restricted_content_detector.py  # 受限使用内容检测
│   ├── credential_detector.py          # 凭证/密钥检测
│   ├── infrastructure_detector.py      # 内部架构信息检测
│   └── detection_orchestrator.py       # 检测调度器
├── config/                             # 规则配置
│   └── classified_keywords.json        # 涉密关键词库
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

## 检测类别

| 层级   | 类别       | 判定       | 颜色   |
|--------|-----------|-----------|--------|
| 第一层 | 涉密信息   | BLOCK     | 🔴 红色 |
| 第二层 | 敏感信息   | WARNING   | 🟠 橙色 |
| 第三层 | 受限内容   | NOTICE    | 🟡 黄色 |
| 第四层 | 风险内容   | NOTICE    | 🔵 蓝色 |
| 通过   | 安全       | PASS      | 🟢 绿色 |

## 环境要求

- Python 3.8+
- 浏览器：Chrome / Edge（最新版）
- 系统：Windows / Linux / macOS
