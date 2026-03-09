"""
个人隐私信息（PII）检测器 —— 检测身份证号、手机号、银行卡号、邮箱、地址等
"""
import re
import time
from typing import List
from .base_detector import (
    BaseDetector, Paragraph, Issue, DetectionResult,
    Category, Severity
)


class PIIDetector(BaseDetector):
    """个人隐私信息检测器"""

    name = "个人隐私信息检测智能体"
    description = "检测身份证号、手机号、银行卡号、邮箱、住址等个人隐私信息"

    def detect(self, full_text: str, paragraphs: List[Paragraph]) -> DetectionResult:
        start = time.time()
        issues = []

        for para in paragraphs:
            text = para.text
            issues.extend(self._detect_id_card(text, para))
            issues.extend(self._detect_phone(text, para))
            issues.extend(self._detect_bank_card(text, para))
            issues.extend(self._detect_email(text, para))
            issues.extend(self._detect_address(text, para))
            issues.extend(self._detect_passport(text, para))

        elapsed = (time.time() - start) * 1000
        return DetectionResult(
            detector_name=self.name,
            issues=issues,
            scan_time_ms=elapsed,
        )

    # ---- 身份证号检测 ----
    def _detect_id_card(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        # 18位身份证号（末尾可能是X）
        pattern_18 = re.compile(r'(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)')
        # 15位老身份证
        pattern_15 = re.compile(r'(?<!\d)([1-9]\d{5}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})(?!\d)')

        for pattern, length in [(pattern_18, 18), (pattern_15, 15)]:
            for match in pattern.finditer(text):
                id_num = match.group(1)
                # 18位需要校验位验证
                if length == 18 and not self._verify_id_checksum(id_num):
                    continue

                masked = self._mask_number(id_num, 3, 4)
                issues.append(Issue(
                    category=Category.SENSITIVE,
                    sub_type="id_card",
                    severity=Severity.HIGH,
                    content=masked,
                    content_raw=id_num,
                    location=self._make_location(para),
                    paragraph_index=para.index,
                    char_offset=match.start(),
                    char_length=len(id_num),
                    reason="包含公民身份证号码，属于个人隐私信息，不应被大模型读取",
                    suggestion=f"建议将身份证号 {masked} 替换为 [身份证号已脱敏] 或删除后再发送",
                    matched_rule="PII-身份证号",
                ))
        return issues

    def _verify_id_checksum(self, id_num: str) -> bool:
        """GB 11643 标准校验位验证"""
        if len(id_num) != 18:
            return False
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = "10X98765432"
        try:
            total = sum(int(id_num[i]) * weights[i] for i in range(17))
            expected = check_codes[total % 11]
            return id_num[17].upper() == expected
        except (ValueError, IndexError):
            return False

    # ---- 手机号检测 ----
    def _detect_phone(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        # 支持多种格式：13800001111、138-0000-1111、138 0000 1111、+86 138...
        pattern = re.compile(
            r'(?<!\d)(?:\+?86\s*[-.]?\s*)?'
            r'(1[3-9]\d[\s\-.]?\d{4}[\s\-.]?\d{4})'
            r'(?!\d)'
        )
        for match in pattern.finditer(text):
            phone = match.group(1)
            # 去除分隔符后验证
            clean_phone = re.sub(r'[\s\-.]', '', phone)
            if len(clean_phone) != 11:
                continue

            masked = self._mask_number(clean_phone, 3, 4)
            issues.append(Issue(
                category=Category.SENSITIVE,
                sub_type="phone_number",
                severity=Severity.HIGH,
                content=masked,
                content_raw=phone,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(match.group()),
                reason="包含手机号码，属于个人隐私信息，不应被大模型读取",
                suggestion=f"建议将手机号 {masked} 替换为 [手机号已脱敏] 或删除后再发送",
                matched_rule="PII-手机号",
            ))
        return issues

    # ---- 银行卡号检测 ----
    def _detect_bank_card(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        # 16-19位数字，可能含空格或短横线分隔
        pattern = re.compile(
            r'(?<!\d)(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?:[\s\-]?\d{1,3})?)(?!\d)'
        )
        for match in pattern.finditer(text):
            card = match.group(1)
            clean_card = re.sub(r'[\s\-]', '', card)
            if not (16 <= len(clean_card) <= 19):
                continue
            if not clean_card.isdigit():
                continue
            # Luhn 校验
            if not self._luhn_check(clean_card):
                continue

            masked = self._mask_number(clean_card, 4, 4)
            issues.append(Issue(
                category=Category.SENSITIVE,
                sub_type="bank_card",
                severity=Severity.HIGH,
                content=masked,
                content_raw=card,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(card),
                reason="包含银行卡号，属于个人隐私信息和金融敏感数据，不应被大模型读取",
                suggestion=f"建议将银行卡号 {masked} 替换为 [银行卡号已脱敏] 或删除后再发送",
                matched_rule="PII-银行卡号",
            ))
        return issues

    def _luhn_check(self, number: str) -> bool:
        """Luhn 算法校验"""
        digits = [int(d) for d in number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(d * 2, 10))
        return total % 10 == 0

    # ---- 邮箱检测 ----
    def _detect_email(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        pattern = re.compile(
            r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        )
        for match in pattern.finditer(text):
            email = match.group()
            # 排除常见的示例邮箱
            if any(ex in email.lower() for ex in ["example.com", "test.com", "xxx.com", "sample."]):
                continue

            masked = self._mask_content(email, 2, 4)
            issues.append(Issue(
                category=Category.SENSITIVE,
                sub_type="email",
                severity=Severity.HIGH,
                content=masked,
                content_raw=email,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(email),
                reason="包含电子邮箱地址，属于个人隐私信息，不应被大模型读取",
                suggestion=f"建议将邮箱 {masked} 替换为 [邮箱已脱敏] 或删除后再发送",
                matched_rule="PII-邮箱",
            ))
        return issues

    # ---- 家庭住址检测 ----
    def _detect_address(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        # 匹配较完整的地址格式：XX省/市 + XX区/县 + XX路/街 + XX号
        pattern = re.compile(
            r'(?:[\u4e00-\u9fa5]{2,}(?:省|自治区|市))'
            r'(?:[\u4e00-\u9fa5]{2,}(?:市|区|县|旗))?'
            r'(?:[\u4e00-\u9fa5]{2,}(?:区|县|镇|乡))?'
            r'(?:[\u4e00-\u9fa5\d]{2,}(?:路|街|道|巷|弄|胡同|大街|大道))'
            r'(?:[\u4e00-\u9fa5\d]{1,}(?:号|弄|栋|单元|室|楼|幢)[\u4e00-\u9fa5\d]*)*'
        )
        for match in pattern.finditer(text):
            addr = match.group()
            if len(addr) < 8:  # 过短的不算
                continue
            masked = self._mask_content(addr, 4, 0)
            issues.append(Issue(
                category=Category.SENSITIVE,
                sub_type="address",
                severity=Severity.HIGH,
                content=masked,
                content_raw=addr,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(addr),
                reason="包含详细家庭住址，属于个人隐私信息，不应被大模型读取",
                suggestion="建议将详细地址替换为 [地址已脱敏] 或仅保留省市级信息",
                matched_rule="PII-家庭住址",
            ))
        return issues

    # ---- 护照号检测 ----
    def _detect_passport(self, text: str, para: Paragraph) -> List[Issue]:
        issues = []
        # 中国护照号：E/G/D/S/P/H + 8位数字 或 EA/EB等 + 7位数字
        pattern = re.compile(r'(?<![A-Za-z])([EGDSPH][A-Z]?\d{7,8})(?![A-Za-z\d])')
        for match in pattern.finditer(text):
            passport = match.group(1)
            # 排除常见误匹配
            if len(passport) > 10:
                continue
            masked = self._mask_content(passport, 2, 2)
            issues.append(Issue(
                category=Category.SENSITIVE,
                sub_type="passport",
                severity=Severity.HIGH,
                content=masked,
                content_raw=passport,
                location=self._make_location(para),
                paragraph_index=para.index,
                char_offset=match.start(),
                char_length=len(passport),
                reason="疑似包含护照号码，属于个人隐私信息，不应被大模型读取",
                suggestion=f"建议将护照号 {masked} 替换为 [护照号已脱敏] 或删除后再发送",
                matched_rule="PII-护照号",
            ))
        return issues
