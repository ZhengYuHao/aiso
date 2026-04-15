"""
OCR API 调用模块 —— 支持阿里云、百度OCR等多种服务商
"""
import base64
import json
import os
from typing import List, Dict, Optional
import requests
from .logger import logger

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass


class OCRClient:
    """OCR API 客户端"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.provider = self.config.get("provider", "aliyun")

    def _load_config(self, config_path: str) -> Dict:
        """加载 OCR 配置 - 从环境变量读取"""
        self.provider = os.getenv("OCR_PROVIDER", "openai").lower()

        config = {
            "provider": self.provider,
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_OCR_MODEL", "gpt-4o"),
            },
            "aliyun": {
                "access_key_id": os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
                "access_key_secret": os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
                "endpoint": os.getenv("ALIYUN_OCR_ENDPOINT", "ocr-api.cn-hangzhou.aliyuncs.com"),
                "scene": os.getenv("ALIYUN_OCR_SCENE", "general"),
            },
            "baidu": {
                "api_key": os.getenv("BAIDU_OCR_API_KEY", ""),
                "secret_key": os.getenv("BAIDU_OCR_SECRET_KEY", ""),
            }
        }

        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)

        return config

    def recognize_image(self, image_data: bytes) -> List[str]:
        """识别图片中的文字"""
        if self.provider == "openai":
            return self._recognize_openai(image_data)
        elif self.provider == "aliyun":
            return self._recognize_aliyun(image_data)
        elif self.provider == "baidu":
            return self._recognize_baidu(image_data)
        else:
            return []

    def recognize_pdf(self, pdf_path: str) -> List[Dict]:
        """识别 PDF 中的文字（逐页转图片后识别）"""
        logger.debug(f"开始 OCR 识别 PDF: {pdf_path}, provider: {self.provider}")
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.warning("pdf2image 未安装，无法识别 PDF")
            return []

        results = []
        try:
            images = convert_from_path(pdf_path)
            logger.debug(f"PDF 转换完成，共 {len(images)} 页")
            for page_num, image in enumerate(images, 1):
                import io
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()

                text_lines = self.recognize_image(img_bytes)
                if text_lines:
                    results.append({
                        "page": page_num,
                        "ocr_text": "\n".join(text_lines),
                        "text_lines": text_lines,
                        "source": f"pdf_{self.provider}_ocr"
                    })
                    logger.debug(f"第 {page_num} 页 OCR 识别完成，文字数: {len(text_lines)}")
        except Exception as e:
            logger.error(f"PDF OCR 识别异常: {str(e)}")

        logger.debug(f"PDF OCR 识别完成，识别页数: {len(results)}")
        return results

    def recognize_docx_images(self, docx_path: str) -> List[Dict]:
        """识别 DOCX 中的图片文字"""
        results = []

        try:
            from docx import Document
            import io
            from PIL import Image
        except ImportError:
            return results

        try:
            doc = Document(docx_path)

            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    image_part = rel.target_part
                    image = Image.open(io.BytesIO(image_part.blob))

                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()

                    text_lines = self.recognize_image(img_bytes)
                    if text_lines:
                        results.append({
                            "page": 1,
                            "ocr_text": "\n".join(text_lines),
                            "text_lines": text_lines,
                            "source": f"docx_{self.provider}_ocr"
                        })
        except Exception:
            pass

        return results

    def _recognize_aliyun(self, image_data: bytes) -> List[str]:
        """阿里云通用文字识别 API"""
        config = self.config.get("aliyun", {})
        access_key_id = config.get("access_key_id", "")
        access_key_secret = config.get("access_key_secret", "")

        if not access_key_id or not access_key_secret:
            return []

        try:
            import hashlib
            import hmac
            import time
            from datetime import datetime

            endpoint = config.get("endpoint", "ocr-api.cn-hangzhou.aliyuncs.com")
            action = "RecognizeAdvanced"
            format_type = "PNG"
            image_type = "local_file"
            scene = config.get("scene", "general")

            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            params = {
                "Format": "JSON",
                "Version": "2021-11-11",
                "AccessKeyId": access_key_id,
                "SignatureMethod": "HMAC-SHA1",
                "Timestamp": timestamp,
                "SignatureVersion": "1.0",
                "SignatureNonce": str(time.time()),
                "Action": action,
                "ImageType": image_type,
                "FormatType": format_type,
                "Scene": scene,
            }

            sorted_params = sorted(params.items())
            query_string = "&".join([f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in sorted_params])

            string_to_sign = f"GET&%2F&{requests.utils.quote(query_string, safe='')}"
            signature = base64.b64encode(
                hmac.new(
                    (access_key_secret + "&").encode("utf-8"),
                    string_to_sign.encode("utf-8"),
                    hashlib.sha1
                ).digest()
            ).decode("utf-8")

            params["Signature"] = signature

            image_base64 = base64.b64encode(image_data).decode("utf-8")
            params["ImageBase64"] = image_base64

            url = f"https://{endpoint}/"
            response = requests.post(url, data=params, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return self._parse_aliyun_result(result)

        except Exception:
            pass

        return []

    def _parse_aliyun_result(self, result: Dict) -> List[str]:
        """解析阿里云 OCR 返回结果"""
        text_lines = []

        try:
            data = result.get("Data", {})
            results_list = data.get("results", [])

            for item in results_list:
                text = item.get("text", "")
                if text:
                    text_lines.append(text)
        except Exception:
            pass

        return text_lines

    def _recognize_openai(self, image_data: bytes) -> List[str]:
        """OpenAI Vision API (GPT-4o) 识别图片文字"""
        logger.debug("调用 OpenAI Vision API 进行 OCR 识别")
        config = self.config.get("openai", {})
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model", "gpt-4o")

        if not api_key:
            logger.warning("OpenAI API Key 未配置")
            return []

        try:
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            logger.debug(f"图片已编码为 Base64，长度: {len(image_base64)}")

            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请识别图片中的所有文字，按原格式返回。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64[:50]}..." if len(image_base64) > 50 else f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096
            }

            logger.debug(f"发送 OCR 请求到 OpenAI API, model: {model}")
            response = requests.post(url, headers=headers, json=payload, timeout=360)
            logger.debug(f"OpenAI API 响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"OpenAI API 返回结果: {json.dumps(result, ensure_ascii=False)[:500]}")
                text = result["choices"][0]["message"]["content"]
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                logger.debug(f"OCR 识别完成，识别到 {len(lines)} 行文字")
                return lines
            else:
                pass

        except Exception:
            pass

        return []

    def _recognize_baidu(self, image_data: bytes) -> List[str]:
        """百度OCR API"""
        config = self.config.get("baidu", {})
        api_key = config.get("api_key", "")
        secret_key = config.get("secret_key", "")

        if not api_key or not secret_key:
            return []

        try:
            access_token = self._get_baidu_token(api_key, secret_key)
            if not access_token:
                return []

            image_base64 = base64.b64encode(image_data).decode("utf-8")

            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"

            payload = {"image": image_base64}
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = requests.post(url, data=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return self._parse_baidu_result(result)

        except Exception:
            pass

        return []

    def _get_baidu_token(self, api_key: str, secret_key: str) -> Optional[str]:
        """获取百度 API Access Token"""
        try:
            auth_url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key
            }

            response = requests.post(auth_url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get("access_token")
        except Exception:
            pass

        return None

    def _parse_baidu_result(self, result: Dict) -> List[str]:
        """解析百度 OCR 返回结果"""
        text_lines = []

        try:
            words_result = result.get("words_result", {})
            for item in words_result:
                text = item.get("words", "")
                if text:
                    text_lines.append(text)
        except Exception:
            pass

        return text_lines
