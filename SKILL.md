---
name: zhuque-ai-detector
description: "Playwright + WebSocket 自动调腾讯朱雀 AI 检测，无需手动操作浏览器"
---

# 朱雀 AI 检测

Playwright headless 浏览器自动调用 https://matrix.tencent.com/ai-detect/。

## 前置

```bash
pip install playwright && playwright install chromium
```

需要 `~/.openclaw/workspace/.zhuque-state.json`，含 `aiGenAccessToken`（localStorage 获取，7 天有效）。

首次设置：用户扫码登录朱雀 → F12 Console → `copy(localStorage.getItem("aiGenAccessToken"))` → 写入 state 文件。

## 检测命令

```bash
cd ~/.openclaw/workspace && python3 /tmp/zhuque_full.py
```

自动找最新终稿，打开朱雀，注入文本，点 Detect，打印结果。

自定义文本：
```bash
echo "待检测文本" | python3 /tmp/zhuque_cli.py
```

## 结果字段

- `labels_ratio["2"]` — AI 率
- `labels_ratio["1"]` — 可疑率
- `labels_ratio["0"]` — 人类率
- `segment_labels[].label` — 逐段标记（0=人类 1=可疑 2=AI）
- `availableUses` — 当日剩余次数

## 阈值

< 30% 通过 | 30-50% 改高风险段 | ≥ 50% 大改重测

技术指南类文章朱雀判得偏严，综合判断。

## 后端细节

WebSocket 端点 `wss://matrix.tencent.com/ai_gen_txt_server/getClassify`。握手时序：fp → Invalid request → 滑块 CAPTCHA → ticket+randstr → access_token → 确认 → 发文本 → 收结果。

token 有效期 7 天（`Date.now() + 6048e5`），存 `aiGenAccessToken`。配额服务端独立计数。
