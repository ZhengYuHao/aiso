"""
凭证信息检测器 —— 检测 API Key、Token、密码、数据库连接串等
"""
import re
import time
from typing import List
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class CredentialDetector(BaseDetector):
    """凭证/密钥信息检测器"""

    name = "凭证密钥检测智能体"
    description = "检测 API Key、Token、密码、数据库连接串、SSH 密钥等凭证信息"

    # 凭证模式定义
    CREDENTIAL_PATTERNS = [
        # ---- API Keys ----
        {
            "sub_type": "aws_access_key",
            "name": "AWS Access Key",
            "pattern": r'(?:AKIA|ASIA)[0-9A-Z]{16}',
            "reason": "包含 AWS 访问密钥，泄露可能导致云服务被非法使用",
            "suggestion": "请立即删除 AWS Access Key，使用环境变量或密钥管理服务替代",
        },
        {
            "sub_type": "aws_secret_key",
            "name": "AWS Secret Key",
            "pattern": r'(?:aws_secret_access_key|AWS_SECRET)\s*[:=]\s*[A-Za-z0-9/+=]{40}',
            "reason": "包含 AWS 密钥，泄露可能导致云服务被非法使用",
            "suggestion": "请立即删除 AWS Secret Key，使用密钥管理服务替代",
        },
        {
            "sub_type": "github_token",
            "name": "GitHub Token",
            "pattern": r'(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}',
            "reason": "包含 GitHub 个人访问令牌，泄露可能导致代码仓库被非法访问",
            "suggestion": "请立即删除 GitHub Token 并在 GitHub 上重新生成",
        },
        {
            "sub_type": "openai_key",
            "name": "OpenAI API Key",
            "pattern": r'sk-[a-zA-Z0-9]{20,}',
            "reason": "包含 OpenAI API 密钥，泄露可能导致 API 额度被盗用",
            "suggestion": "请删除 API Key 并在 OpenAI 平台重新生成",
        },
        {
            "sub_type": "slack_token",
            "name": "Slack Token",
            "pattern": r'xox[boaprs]-[0-9a-zA-Z\-]{10,}',
            "reason": "包含 Slack 令牌，泄露可能导致工作空间被非法访问",
            "suggestion": "请删除 Slack Token 并重新生成",
        },
        {
            "sub_type": "google_api_key",
            "name": "Google API Key",
            "pattern": r'AIza[0-9A-Za-z\-_]{35}',
            "reason": "包含 Google API 密钥，泄露可能导致 Google 服务被非法使用",
            "suggestion": "请删除 Google API Key 并在 Google Cloud Console 重新生成",
        },
        {
            "sub_type": "generic_api_key",
            "name": "通用 API Key",
            "pattern": r'(?:api[_\-]?key|apikey|api[_\-]?secret|app[_\-]?key|app[_\-]?secret|access[_\-]?key)\s*[:=]\s*["\']?[a-zA-Z0-9\-_]{16,}["\']?',
            "reason": "包含 API 密钥配置，泄露可能导致相关服务被非法访问",
            "suggestion": "请删除 API Key，使用环境变量或密钥管理服务替代",
        },
        # ---- Passwords ----
        {
            "sub_type": "password_field",
            "name": "密码字段",
            "pattern": r'(?:password|passwd|密码|口令|pwd)\s*[:=]\s*["\']?(\S{4,})["\']?',
            "reason": "包含密码/口令信息，泄露可能导致系统被非法访问",
            "suggestion": "请删除密码信息，使用占位符 [密码已删除] 替代",
        },
        # ---- Database Connection ----
        {
            "sub_type": "db_connection",
            "name": "数据库连接串",
            "pattern": r'(?:mysql|postgresql|postgres|mongodb|redis|sqlserver|mssql|oracle)://[^\s<>"\']{10,}',
            "reason": "包含数据库连接字符串（含地址、用户名、密码），泄露可能导致数据库被非法访问",
            "suggestion": "请删除数据库连接串，使用占位符 [数据库连接已删除] 替代",
        },
        {
            "sub_type": "jdbc_connection",
            "name": "JDBC 连接串",
            "pattern": r'jdbc:[a-zA-Z]+://[^\s<>"\']{10,}',
            "reason": "包含 JDBC 数据库连接信息",
            "suggestion": "请删除 JDBC 连接串",
        },
        # ---- SSH / Private Keys ----
        {
            "sub_type": "private_key",
            "name": "私钥标识",
            "pattern": r'-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE|EC)\s+KEY-----',
            "reason": "包含私钥内容，泄露将导致严重的安全隐患",
            "suggestion": "请立即删除私钥内容，私钥绝不应出现在发送给 AI 的文件中",
        },
        # ---- Bearer Tokens ----
        {
            "sub_type": "bearer_token",
            "name": "Bearer Token",
            "pattern": r'[Bb]earer\s+[a-zA-Z0-9\-_.~+/]{20,}',
            "reason": "包含 Bearer 认证令牌，泄露可能导致 API 被非法调用",
            "suggestion": "请删除 Bearer Token，使用占位符替代",
        },
        # ---- JWT ----
        {
            "sub_type": "jwt_token",
            "name": "JWT Token",
            "pattern": r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}',
            "reason": "包含 JWT 令牌，可能含有用户身份和权限信息",
            "suggestion": "请删除 JWT Token，使用占位符替代",
        },
    ]

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        for para in paragraphs:
            text = para.text
            for cred in self.CREDENTIAL_PATTERNS:
                pattern = re.compile(cred["pattern"], re.IGNORECASE)
                for match in pattern.finditer(text):
                    matched_text = match.group()
                    masked = self._mask_content(matched_text, 4, 4)

                    issues.append(Issue(
                        category=Category.RISKY,
                        sub_type=cred["sub_type"],
                        severity=Severity.LOW if "password" not in cred["sub_type"] else Severity.MEDIUM,
                        content=masked,
                        content_raw=matched_text,
                        location=self._make_location(para),
                        paragraph_index=para.index,
                        char_offset=match.start(),
                        char_length=len(matched_text),
                        reason=cred["reason"],
                        suggestion=cred["suggestion"],
                        matched_rule=f"凭证-{cred['name']}",
                    ))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )
