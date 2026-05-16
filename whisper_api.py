from faster_whisper import WhisperModel
import os
import sys
import argparse
import subprocess
import tempfile
import shutil
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

app = FastAPI(title="Faster Whisper API Server")

# 全局模型缓存
model_cache = {}

def get_model(model_id, device, compute_type, cache_dir):
    key = f"{model_id}_{device}_{compute_type}"
    if key not in model_cache:
        print(f"正在加载模型: {model_id} (设备: {device})...")
        model_cache[key] = WhisperModel(
            model_id, 
            device=device, 
            compute_type=compute_type,
            download_root=cache_dir
        )
    return model_cache[key]

def convert_to_mp3(input_path):
    output_path = input_path + ".mp3"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path, 
            "-vn", "-acodec", "libmp3lame", "-q:a", "2", 
            output_path
        ], check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg 转换失败: {e.stderr.decode()}")

def group_segments(segments, max_duration):
    grouped = []
    current_text = ""
    current_start = None
    
    for s in segments:
        if current_start is None:
            current_start = s.start
        current_text += s.text
        if s.end - current_start >= max_duration:
            grouped.append({
                "start": round(current_start, 2),
                "end": round(s.end, 2),
                "text": current_text.strip()
            })
            current_text = ""
            current_start = None
            
    if current_text:
        last_end = segments[-1].end if segments else 0
        grouped.append({"start": round(current_start, 2), "end": round(last_end, 2), "text": current_text.strip()})
    return grouped

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Faster Whisper 转录站</title>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; background: #f4f7f6; }
            .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h2 { color: #2c3e50; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="file"], input[type="text"], select, input[type="number"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            button { background: #3498db; color: white; border: none; padding: 12px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; transition: background 0.3s; width: 100%; }
            button:hover { background: #2980b9; }
            #result { margin-top: 30px; white-space: pre-wrap; background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 4px; max-height: 500px; overflow-y: auto; }
            .loading { color: #f39c12; font-weight: bold; display: none; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🎙️ Faster Whisper 智能转录</h2>
            <div class="form-group">
                <label>选择文件 (MP3/MP4/WAV):</label>
                <input type="file" id="audioFile">
            </div>
            <div class="form-group">
                <label>选择模型:</label>
                <select id="modelSelect">
                    <option value="medium">medium (默认)</option>
                    <option value="deepdml/faster-whisper-large-v3-turbo-ct2">large-v3-turbo (推荐)</option>
                    <option value="small">small (快速)</option>
                    <option value="large-v3">large-v3 (极准)</option>
                </select>
            </div>
            <div class="form-group">
                <label>上下文提示 (Initial Prompt):</label>
                <input type="text" id="promptInput" placeholder="提供视频背景或专业词汇，例如：增肌、减脂、积酸...">
            </div>
            <div class="form-group">
                <label>合并秒数 (0 为不合并):</label>
                <input type="number" id="durationInput" value="0" step="1">
            </div>
            <button onclick="startTranscribe()" id="mainBtn">开始转录</button>
            
            <div id="loading" class="loading">正在处理中，请稍候 (如果是第一次使用该模型，可能正在下载)...</div>
            <div id="result">转录结果将显示在这里...</div>
        </div>

        <script>
            async function startTranscribe() {
                const fileInput = document.getElementById('audioFile');
                if (fileInput.files.length === 0) return alert('请先选择文件');
                
                const btn = document.getElementById('mainBtn');
                const loading = document.getElementById('loading');
                const resultDiv = document.getElementById('result');
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('model', document.getElementById('modelSelect').value);
                formData.append('initial_prompt', document.getElementById('promptInput').value);
                formData.append('max_duration', document.getElementById('durationInput').value);

                btn.disabled = true;
                loading.style.display = 'block';
                resultDiv.innerText = '正在上传并转录...';

                try {
                    const response = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (response.ok) {
                        let text = `检测到语言: ${data.language}\\n\\n`;
                        data.segments.forEach(s => {
                            text += `[${s.start}s -> ${s.end}s] ${s.text}\\n`;
                        });
                        resultDiv.innerText = text;
                    } else {
                        resultDiv.innerText = '错误: ' + (data.detail || '未知错误');
                    }
                } catch (e) {
                    resultDiv.innerText = '请求失败: ' + e.message;
                } finally {
                    btn.disabled = false;
                    loading.style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form("medium"),
    device: str = Form("auto"),
    initial_prompt: str = Form(None),
    max_duration: float = Form(0),
    cpu: bool = Form(False)
):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        working_file = tmp_path
        if suffix.lower() == ".mp4":
            working_file = convert_to_mp3(tmp_path)

        run_device = "cpu" if cpu else device
        compute_type = "int8" if run_device == "cpu" else "default"
        whisper = get_model(model, run_device, compute_type, os.getenv("WHISPER_MODEL_CACHE"))

        # 执行转录，initial_prompt 非常有用，可以引导模型识别生僻词或维持术语一致性
        segments_gen, info = whisper.transcribe(working_file, beam_size=5, initial_prompt=initial_prompt)
        segments = list(segments_gen)

        if max_duration > 0:
            result_segments = group_segments(segments, max_duration)
        else:
            result_segments = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]

        return {"language": info.language, "segments": result_segments}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        if 'working_file' in locals() and working_file != tmp_path and os.path.exists(working_file): os.remove(working_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    os.makedirs(os.getenv("WHISPER_MODEL_CACHE", "/app/models"), exist_ok=True)
    uvicorn.run(app, host=args.host, port=args.port)
