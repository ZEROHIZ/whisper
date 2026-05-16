# Bug Log

## 2026-05-16: CUDA Library Not Found
**问题描述**: 运行 `test_medium_model.py` 时报错 `Library cublas64_12.dll is not found or cannot be loaded`。
**原因分析**: `faster-whisper` (CTranslate2) 在 Windows 上使用 GPU (CUDA) 时，需要系统中存在 `cublas64_12.dll` 等 NVIDIA 相关库。即便安装了 CUDA 驱动，有时也需要手动将这些 DLL 放到 PATH 中或项目目录下。
**解决方案**:
1. (临时/快速) 在脚本中使用 `device="cpu"`。
2. (长期) 从 [Purfview's whisper-standalone-win](https://github.com/Purfview/whisper-standalone-win/releases/tag/libs) 下载对应的 CUDA 12 库文件并放入系统 PATH。

## 2026-05-16: Invalid Format Specifier in Test Script
**问题描述**: `test_medium_model.py` 报错 `Invalid format specifier`。
**原因分析**: 在 f-string 中使用了 `:.2fs`，导致 Python 将 `s` 误认为格式化字符。应改为 `{value:.2f}s`。
**解决方案**: 已将 `print` 语句中的格式化占位符从 `:.2fs` 修正为 `:.2f}s`。
