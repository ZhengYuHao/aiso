"""
大模型输入内容安全检测系统 —— Flask 后端服务
"""
import os
import uuid
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, render_template, send_from_directory
from detectors import DetectionOrchestrator
from detectors.logger import logger

app = Flask(__name__,
    template_folder="templates",
    static_folder="static",
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "docx", "pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024

orchestrator = DetectionOrchestrator(config_dir=CONFIG_DIR)

MAX_WORKERS = 4


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename_cn(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    name = name.replace("/", "_").replace("\\", "_").replace("..", "_")
    uid = uuid.uuid4().hex[:8]
    return f"{uid}_{name}{ext}"


def process_single_file(file_obj, detection_mode: str = "rule") -> dict:
    """处理单个文件"""
    original_name = file_obj.filename

    if not allowed_file(original_name):
        ext = original_name.rsplit(".", 1)[-1] if "." in original_name else "未知"
        return {
            "filename": original_name,
            "error": f"不支持的文件格式 .{ext}，仅支持 .docx / .txt / .pdf",
            "overall_verdict": "ERROR",
        }

    safe_name = secure_filename_cn(original_name)
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    try:
        file_obj.save(filepath)

        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            os.remove(filepath)
            return {
                "filename": original_name,
                "error": f"文件大小 {file_size / 1024 / 1024:.1f}MB 超过限制 5MB",
                "overall_verdict": "ERROR",
            }

        if file_size == 0:
            os.remove(filepath)
            return {
                "filename": original_name,
                "error": "文件为空",
                "overall_verdict": "ERROR",
            }

    except Exception as e:
        logger.error(f"文件保存失败: {original_name}, 错误: {str(e)}")
        return {
            "filename": original_name,
            "error": f"文件保存失败: {str(e)}",
            "overall_verdict": "ERROR",
        }

    try:
        report = orchestrator.detect_file(filepath, detection_mode=detection_mode)
        report["filename"] = original_name
        report["detection_mode"] = detection_mode

        log_filename = f"{safe_name}.json"
        log_path = os.path.join(LOG_DIR, log_filename)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    except Exception as e:
        return {
            "filename": original_name,
            "error": f"检测过程异常: {str(e)}",
            "overall_verdict": "ERROR",
        }
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_and_detect():
    if "files" not in request.files:
        logger.warning("未检测到上传文件")
        return jsonify({"error": "未检测到上传文件", "code": 400}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        logger.warning("未选择文件")
        return jsonify({"error": "未选择文件", "code": 400}), 400

    detection_mode = request.form.get("detection_mode", "rule")
    if detection_mode not in ["rule", "llm"]:
        detection_mode = "rule"

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_file, f, detection_mode): f for f in files}

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                logger.info(f"==================== [处理结束] {result.get('filename', 'unknown')} 判定: {result.get('overall_verdict', 'unknown')} ====================")
            except Exception as e:
                file_obj = futures[future]
                results.append({
                    "filename": file_obj.filename,
                    "error": f"处理异常: {str(e)}",
                    "overall_verdict": "ERROR",
                })

    return jsonify({"results": results, "count": len(results)})


if __name__ == "__main__":
    print("=" * 60)
    print("  大模型输入内容安全检测系统 Demo V2.0")
    print("  访问地址: http://localhost:5000")
    print("  检测模式: 支持规则引擎(rule) / AI智能体(llm)")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
