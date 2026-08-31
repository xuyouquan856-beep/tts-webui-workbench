# Changelog

本项目从 `0.1.0` 起采用语义化版本。

## [0.1.0] - 2026-08-31

首个公开预览版：

- 统一管理 Dummy、Higgs、Piper、本地 HTTP 和本地命令 TTS。
- 语音配置、参考音频、自定义声音、生成历史与流式播放。
- OpenAI-compatible 翻译预处理与标签保护。
- React WebUI、FastAPI 后端和 Tauri 2 Windows 桌面壳。
- 干净首次启动策略：只有 Dummy 默认启用，其他提供商需用户配置。
- Windows 便携包白名单构建、隐私审计与 SHA-256 校验文件。
- 本地命令路径约束、诊断脱敏及 120 秒超时上限。
