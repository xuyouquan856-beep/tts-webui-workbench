# 安装、开发与构建

## 环境

- Windows 10/11 x64
- Python 3.11
- Node.js 18+
- Rust stable 与 Tauri 2 系统依赖（仅桌面构建）

## 源码启动

在项目根目录运行：

```powershell
./install_backend.bat
./install_frontend.bat
./start_all.bat
```

后端默认监听 `127.0.0.1:8000`，前端位于 `http://localhost:5173`。安装脚本会在 `.env` 不存在时从 `.env.example` 创建空模板；密钥必须由用户自行填写。

也可手动启动：

```powershell
backend/venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

## 提供商配置

- Higgs：在 `.env` 设置 `BOSON_API_KEY`，重新启动后端，再在界面启用对应模型。
- 翻译：设置 `TRANSLATION_API_BASE`、`TRANSLATION_API_KEY` 和 `TRANSLATION_MODEL`。
- Piper：准备可信的 Piper 可执行文件、ONNX 模型及对应配置。
- 本地 HTTP：先独立验证本地服务，再填写环回地址和负载模式。
- 本地命令：使用独立环境和明确的绝对可执行路径，例如 `C:\tts-models\venv\Scripts\python.exe`。该能力不是沙箱。

## 检查

```powershell
$env:PYTHONPATH = "$PWD/backend"
backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -p "test_*_unit.py" -v
npm --prefix frontend run build
cargo test --manifest-path src-tauri/Cargo.toml
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_release_scripts.ps1
```

## Windows 便携包

安装 PyInstaller 和 Tauri CLI 后运行：

```powershell
python -m pip install pyinstaller
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_portable_release.ps1
```

产物写入 `artifacts/`，包括版本化 ZIP 和 `.sha256`。打包脚本只复制明确允许的文件，并在压缩前执行隐私审计；它不会复制项目根目录的 `.env` 或 `data` 内容。
