# TTS WebUI Workbench

一个本地优先的 Windows 语音工作台，用统一界面管理云端与本地 TTS、语音配置、翻译预处理、试听和生成历史。

当前公开版本：`0.1.0`。这是首个公开预览版，适合试用和反馈，不代表所有第三方提供商都已预配置。

## 快速开始（Windows 便携版）

1. 从 GitHub Releases 下载 `tts-webui-workbench-v0.1.0-windows-x64.zip` 和同名 `.sha256`。
2. 解压到普通可写目录，保持 `app.exe` 与 `backend_sidecar.exe` 在同一目录，然后运行 `app.exe`。
3. 首次启动只启用离线 `Dummy Beep Generator`，可立即生成一秒测试音确认流程正常。
4. 需要 Higgs、Piper、本地 HTTP 或本地命令时，在界面中自行配置并测试。

便携包不包含作者的 API Key、数据库、生成音频、参考音频、模型权重或声音配置。升级前请备份自己的应用数据。

## 功能与提供商

- Dummy：离线测试音，开箱可用。
- Higgs TTS 3 / Boson AI：需用户自己的 API Key；未配置时默认禁用。
- 本地 HTTP：连接用户自行运行的兼容服务。
- 本地命令：运行用户明确配置的本地程序；默认禁用，启用前请阅读安全说明。
- Piper：连接用户自行安装的 Piper 可执行文件与 ONNX 模型。
- 翻译预处理：可连接 OpenAI-compatible 翻译接口，配置为空时不发送文本。
- 语音配置、参考音频、生成历史、流式播放和自定义声音工作流。

项目不捆绑、不代理也不代表任何第三方模型或服务。第三方服务的价格、许可和数据政策由其提供者决定。

## 从源码运行

要求：Windows 10/11、Python 3.11、Node.js 18+。桌面构建另需 Rust stable 与 Tauri 2 的系统依赖。

```powershell
git clone <your-fork-url>
cd tts-webui-workbench
./install_backend.bat
./install_frontend.bat
./start_all.bat
```

浏览器界面默认位于 `http://localhost:5173`，后端默认只监听 `127.0.0.1:8000`。复制 `.env.example` 为 `.env` 后再填写自己的密钥；不要提交 `.env`。

开发与构建细节见 [设置指南](docs/SETUP_GUIDE.md) 和 [系统架构](docs/ARCHITECTURE.md)。

## 验证

```powershell
$env:PYTHONPATH = "$PWD/backend"
backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -p "test_*_unit.py" -v
npm --prefix frontend run build
cargo test --manifest-path src-tauri/Cargo.toml
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_release_scripts.ps1
```

真实云端合成会产生费用，因此不属于默认离线测试。

## 隐私与安全

- 数据库、参考音频和生成音频默认保存在本机应用数据目录。
- 只有在用户选择并调用云端提供商时，相应文本、参数及必要的参考音频才会发送给该提供商。
- 本地命令提供商拥有启动本机程序的能力，只应配置可信命令和模型。
- 不要在公开 Issue 中粘贴 API Key、私人录音、命令输出或本机绝对路径。

详见 [隐私说明](docs/PRIVACY.md) 与 [安全政策](SECURITY.md)。

## 文档

- [安装与开发](docs/SETUP_GUIDE.md)
- [本地 TTS 接入](docs/LOCAL_TTS_PROVIDERS.md)
- [Higgs API](docs/HIGGS_API.md)
- [桌宠语音接入](docs/DESKTOP_PET_INTEGRATION.md)
- [贡献指南](CONTRIBUTING.md)

## 许可证

本项目原创源代码采用 [Apache License 2.0](LICENSE)。该许可证不自动覆盖第三方模型、服务、声音、录音、角色素材或生成内容，详见 [NOTICE](NOTICE)。
