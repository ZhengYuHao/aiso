"""
内部架构信息检测器 —— 检测内网IP、服务器路径、端口号等基础设施信息
"""
import re
import time
from typing import List
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class InfrastructureDetector(BaseDetector):
    """内部架构信息检测器"""

    name = "内部架构信息检测智能体"
    description = "检测内网IP、端口、服务器路径、主机名等内部基础设施信息"

    # 内网IP段
    PRIVATE_IP_PATTERN = re.compile(
        r'(?<!\d)'
        r'(?:'
        r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}'       # 10.0.0.0/8
        r'|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'  # 172.16.0.0/12
        r'|192\.168\.\d{1,3}\.\d{1,3}'          # 192.168.0.0/16
        r')'
        r'(?::\d{2,5})?'                         # 可选端口
        r'(?!\d)'
    )

    # 排除的IP（示例/文档用途）
    EXAMPLE_IPS = {
        "192.168.1.1", "192.168.0.1", "10.0.0.1",
        "192.168.1.100", "192.168.0.100",
        "10.0.0.0", "172.16.0.0", "192.168.0.0",
    }

    # 服务器路径模式
    SERVER_PATH_PATTERNS = [
        {
            "sub_type": "linux_path",
            "name": "Linux 服务器路径",
            "pattern": r'(?:/(?:home|var|opt|etc|srv|usr|data|app|deploy|www|nginx|apache|tomcat)/[a-zA-Z0-9_\-./]{5,})',
        },
        {
            "sub_type": "windows_path",
            "name": "Windows 服务器路径",
            "pattern": r'(?:[A-Z]:\\(?:Users|Program Files|Windows|inetpub|wwwroot|data|deploy|app)(?:\\[a-zA-Z0-9_\-. ]+){2,})',
        },
    ]

    # 内部主机名模式
    HOSTNAME_PATTERNS = [
        {
            "sub_type": "internal_hostname",
            "name": "内部主机名",
            "pattern": r'(?:(?:prod|staging|dev|test|uat|pre|gray)\s*[-_.]?\s*(?:server|host|node|db|redis|mysql|mongo|web|api|app|gateway|nginx)\s*[-_.]?\s*\d*)',
        },
    ]

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        for para in paragraphs:
            text = para.text
            issues.extend(self._detect_private_ip(text, para))
            issues.extend(self._detect_server_paths(text, para))
            issues.extend(self._detect_hostnames(text, para))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )

    def _detect_private_ip(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        for match in self.PRIVATE_IP_PATTERN.finditer(text):
            ip = match.group()
            # 提取纯 IP（不含端口）
            pure_ip = ip.split(":")[0] if ":" in ip else ip
            # 排除示例 IP
            if pure_ip in self.EXAMPLE_IPS:
                continue
            # 排除出现在明显代码示例上下文中的
            ctx_start = max(0, match.start() - 30)
            context_before = text[ctx_start:match.start()].lower()
            if any(word in context_before for word in ["例如", "示例", "example", "如：", "比如"]):
                continue

            masked = self._mask_content(ip, 4, 0)
            issues.append(Issue(
                category=Category.RISKY,
                sub_type="private_ip",
                severity=Severity.LOW,
                content=masked,
                content_raw=ip,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(ip),
                reason="包含内网 IP 地址，泄露可能暴露内部网络架构",
                suggestion=f"建议将内网 IP {masked} 替换为 [内网IP已脱敏] 或删除后再发送",
                matched_rule="架构-内网IP",
            ))
        return issues

    def _detect_server_paths(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        for path_rule in self.SERVER_PATH_PATTERNS:
            pattern = re.compile(path_rule["pattern"])
            for match in pattern.finditer(text):
                path = match.group()
                masked = self._mask_content(path, 5, 0)
                issues.append(Issue(
                    category=Category.RISKY,
                    sub_type=path_rule["sub_type"],
                    severity=Severity.LOW,
                    content=masked,
                    content_raw=path,
                    location=self._make_location(para),
                    paragraph_index=para.index,
                    char_offset=match.start(),
                    char_length=len(path),
                    reason="包含服务器文件路径，泄露可能暴露内部系统部署结构",
                    suggestion="建议将服务器路径替换为 [路径已脱敏] 或删除后再发送",
                    matched_rule=f"架构-{path_rule['name']}",
                ))
        return issues

    def _detect_hostnames(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        for host_rule in self.HOSTNAME_PATTERNS:
            pattern = re.compile(host_rule["pattern"], re.IGNORECASE)
            for match in pattern.finditer(text):
                hostname = match.group()
                if len(hostname) < 5:
                    continue
                masked = self._mask_content(hostname, 3, 0)
                issues.append(Issue(
                    category=Category.RISKY,
                    sub_type=host_rule["sub_type"],
                    severity=Severity.LOW,
                    content=masked,
                    content_raw=hostname,
                    location=self._make_location(para),
                    paragraph_index=para.index,
                    char_offset=match.start(),
                    char_length=len(hostname),
                    reason="包含内部主机名/服务器名称，泄露可能暴露内部系统架构",
                    suggestion="建议将主机名替换为 [主机名已脱敏] 或删除后再发送",
                    matched_rule=f"架构-{host_rule['name']}",
                ))
        return issues
