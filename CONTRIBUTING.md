# Contributing

欢迎提交可复现的问题和范围清晰的改动。

## 环境

- Python 3.11
- Node.js 18+
- Rust stable（桌面端）
- Windows 10/11 为当前主要验证平台

## 本地检查

```powershell
$env:PYTHONPATH = "$PWD/backend"
backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -p "test_*_unit.py" -v
npm --prefix frontend run build
cargo test --manifest-path src-tauri/Cargo.toml
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_release_scripts.ps1
```

新缺陷应先增加最小回归测试。测试必须使用临时目录、合成音频或确定性桩；不要提交真实 API Key、私人声音、个人数据库、模型权重和生成历史。

提交前运行 `git diff --check`，确认没有本机绝对路径和临时构建产物。涉及第三方协议或模型时，请在 PR 中注明来源与许可证，不要把第三方文件直接并入仓库。
