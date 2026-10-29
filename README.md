# 清风清理 Breeze Cleaner

一个界面清爽、安全第一的 Windows 智能清理工具。Python + PySide6 打造，苹果官网风格的简洁设计。

> 轻 · 快 · 净 —— 让电脑保持清爽，像刚拆封那天一样。

## ✨ 功能

- **体检**：一键扫描全机，给出「预计可释放空间」总览，系统盘占用一目了然
- **智能清理**：临时文件、浏览器缓存（Chrome / Edge / Firefox / Brave）、缩略图缓存、Windows 更新缓存、DirectX 着色器缓存、回收站……
- **开发垃圾识别**：自动找出 `node_modules`、`__pycache__`、`.venv`、`target`、`build`、`dist` 等可重建目录；笼统的名字会先验证项目标记文件（`package.json` / `Cargo.toml` / `pyvenv.cfg`…）再认定，不误伤
- **文件整理**：把下载文件夹里的散落文件按「图片 / 文档 / 视频 / 音频 / 压缩包…」归类，支持按月份细分，先预览后执行，**一键撤销**
- **工具**：大文件扫描（找占空间的元凶）、空文件夹清理
- **规则引擎**：清理规则全部写在 `rules/*.yaml` 里，你可以给任何软件添加自己的清理规则

## 🛡️ 安全设计（本项目最重要的一节）

清理类工具最大的风险是误删用户文件，清风从第一行代码就定了三条铁律：

1. **扫描可见** —— 默认先扫描预览「将删除什么、能释放多少」，你确认后才执行
2. **删除可逆** —— 所有删除一律进入回收站（`send2trash`），绝不永久删除；唯一例外是「清空回收站」本身，会明确提示
3. **规则可审** —— 只清理白名单规则里的路径；符号链接 / 目录联接一律跳过，防止路径逃逸；`Windows`、`Program Files`、`ProgramData`、桌面、文档、下载等 Critical 路径受最终防线保护

被占用的文件（比如浏览器正在运行时的缓存）会自动跳过，不会中断流程。

清风不联网、不上传任何数据。

## 🚀 快速开始

要求：Windows 10 / 11、Python 3.9+

```bash
pip install -r requirements.txt
python main.py
```

## 📦 打包成 exe

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name BreezeCleaner --add-data "rules;rules" main.py
```

产物在 `dist/BreezeCleaner.exe`。推送到 `v*` 标签时 GitHub Actions 会自动打包并挂到 Releases。

## 🗺️ Roadmap

- [ ] 重复文件检测（大小 → 部分哈希 → 全量哈希三级筛选）
- [ ] 定时自动清理（开机 / 每周静默执行）
- [ ] 系统托盘常驻
- [ ] 清理历史统计图表
- [ ] macOS / Linux 规则支持

## 🤝 贡献

欢迎 PR！最简单的贡献方式：给 `rules/` 添加新的清理规则（参考 `rules/default_rules.yaml` 里的注释），或者改进界面细节。提交前请跑一遍现有功能确认没有回归。

## License

[MIT](LICENSE)
