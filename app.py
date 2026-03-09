"""
大模型输入内容安全检测系统 —— Flask 后端服务
"""
import os
import uuid
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory

from detectors import DetectionOrchestrator

# ========== 初始化 ==========
app = Flask(__name__,
    template_folder="templates",
    static_folder="static",
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB 请求体上限

# 目录配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 允许的文件格式
ALLOWED_EXTENSIONS = {"txt", "docx", "pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单文件 5MB

# 检测调度器
orchestrator = DetectionOrchestrator(config_dir=CONFIG_DIR)


# ========== 工具函数 ==========
def allowed_file(filename: str) -> bool:
    """检查文件格式是否在白名单"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename_cn(filename: str) -> str:
    """生成安全的文件名（保留原始名 + UUID 前缀防重名）"""
    name, ext = os.path.splitext(filename)
    # 移除路径分隔符防止路径遍历
    name = name.replace("/", "_").replace("\\", "_").replace("..", "_")
    uid = uuid.uuid4().hex[:8]
    return f"{uid}_{name}{ext}"


# ========== 路由 ==========
@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_and_detect():
    """文件上传与检测接口"""
    if "files" not in request.files:
        return jsonify({"error": "未检测到上传文件", "code": 400}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "未选择文件", "code": 400}), 400

    results = []

    for file in files:
        # 基础校验
        if not file or file.filename == "":
            continue

        original_name = file.filename

        if not allowed_file(original_name):
            ext = original_name.rsplit(".", 1)[-1] if "." in original_name else "未知"
            results.append({
                "filename": original_name,
                "error": f"不支持的文件格式 .{ext}，仅支持 .docx / .txt / .pdf",
                "overall_verdict": "ERROR",
            })
            continue

        # 保存到临时目录
        safe_name = secure_filename_cn(original_name)
        filepath = os.path.join(UPLOAD_DIR, safe_name)

        try:
            file.save(filepath)

            # 校验文件大小
            file_size = os.path.getsize(filepath)
            if file_size > MAX_FILE_SIZE:
                os.remove(filepath)
                results.append({
                    "filename": original_name,
                    "error": f"文件大小 {file_size / 1024 / 1024:.1f}MB 超过限制 5MB",
                    "overall_verdict": "ERROR",
                })
                continue

            if file_size == 0:
                os.remove(filepath)
                results.append({
                    "filename": original_name,
                    "error": "文件为空",
                    "overall_verdict": "ERROR",
                })
                continue

        except Exception as e:
            results.append({
                "filename": original_name,
                "error": f"文件保存失败: {str(e)}",
                "overall_verdict": "ERROR",
            })
            continue

        # 执行检测
        try:
            report = orchestrator.detect_file(filepath)
            report["filename"] = original_name
            results.append(report)

            # 保存检测日志
            log_filename = f"{safe_name}.json"
            log_path = os.path.join(LOG_DIR, log_filename)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        except Exception as e:
            results.append({
                "filename": original_name,
                "error": f"检测过程异常: {str(e)}",
                "overall_verdict": "ERROR",
            })
        finally:
            # 清理临时文件
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass

    return jsonify({"results": results, "count": len(results)})


# ========== 启动 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("  大模型输入内容安全检测系统 Demo V2.0")
    print("  访问地址: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
