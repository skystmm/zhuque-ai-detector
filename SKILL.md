---
name: zhuque-ai-detector
description: "Playwright + WebSocket 自动调腾讯朱雀 AI 检测。触发：朱雀、AI检测、AI率检测、AI率、zhuque、detect"
---

# 朱雀 AI 检测

Playwright headless 自动调用 https://matrix.tencent.com/ai-detect/。

## 前置

```bash
pip install playwright && playwright install chromium
```

需 state 文件 `~/.openclaw/workspace/.zhuque-state.json`，含 `aiGenAccessToken`（localStorage，7 天有效）。

首次：扫码登录朱雀 → F12 → `copy(localStorage.getItem("aiGenAccessToken"))` → 写入 state 文件。

## 命令

```bash
python3 scripts/detect.py
```

自动找最新终稿 → 注入检测 → 打印结果。支持 `echo "文本" | python3 scripts/detect.py` 自定义输入。

## 验证

结果含 `labels_ratio`（AI率/可疑率/人类率）、`segment_labels`（逐段标记）、`availableUses`（当日剩余）。详见 README.md。
