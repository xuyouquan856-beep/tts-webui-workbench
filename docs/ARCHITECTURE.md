# 系统架构

TTS WebUI Workbench 由三个本地进程层组成：

```text
Tauri desktop host
  ├─ React/Vite WebView
  └─ FastAPI sidecar (127.0.0.1)
       ├─ SQLAlchemy / SQLite
       ├─ queue worker
       └─ provider adapters
            ├─ dummy
            ├─ higgs_api
            ├─ local_http
            ├─ local_command
            └─ piper
```

## 前端

React 前端负责模型、声音、文本、翻译、任务历史和播放交互。它只通过本地 HTTP API 与 sidecar 通信，不直接读取数据库或密钥。

## 桌面壳

Tauri 启动并监督编译后的 FastAPI sidecar。sidecar 数据目录由系统应用数据位置提供，不依赖安装目录可写。启动诊断不会输出数据目录或用户密钥。

## 后端

FastAPI 提供 `/api` 路由。SQLAlchemy 保存模型、声音和任务记录；生成文件与参考音频位于受控数据目录。后台队列顺序执行普通生成任务，流式接口按块转发兼容提供商输出。

## 提供商边界

`BaseTTSProvider` 统一接收文本、模型属性、声音配置和参数，返回生成文件及非敏感元数据。云端提供商通过共享 HTTP 客户端调用外部服务；本地 HTTP 调用环回服务；本地命令使用 `shell=False` 并验证受管输出/参考路径，但仍会运行用户配置的程序，因此不是沙箱。

## 数据与隐私

公开发布包不含运行数据。云端请求只在用户选择对应功能时产生。详细边界见 `docs/PRIVACY.md` 和 `SECURITY.md`。
