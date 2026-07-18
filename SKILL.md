# 朱雀 AI 检测自动化 Skill

> 通过 Playwright + WebSocket 自动调用腾讯朱雀 AI 检测

## 概要

自动对公众号文章终稿进行朱雀 AI 率检测，无需浏览器手动操作。

- **检测端点**：`wss://matrix.tencent.com/ai_gen_txt_server/getClassify`（WebSocket）
- **身份验证**：localStorage 中的 `access_token`（7 天有效）或 `fp`（浏览器指纹）
- **检测结果字段**：`confidence`（模型置信度）、`labels_ratio`（{0: 人类, 1: 可疑, 2: AI}）、`segment_labels`（逐段标记）

## 前置条件

- `playwright` 已安装：`pip install playwright && playwright install chromium`
- 状态文件 `~/.openclaw/workspace/.zhuque-state.json` 已包含 `aiGenAccessToken`（从用户浏览器 localStorage 获取）
- 每日配额至少 1 次

## 调用方式

### 方式一：全流程（推荐）

```bash
cd /home/admin/.openclaw/workspace && python3 /tmp/zhuque_full.py
```

自动读取最新终稿 → 打开朱雀页面 → 注入文本 → 点击 Detect → 等待结果 → 打印到控制台。

### 方式二：自定义文本

使用 `/tmp/zhuque_cli.py`（见下方脚本区块）：

```bash
echo "待检测文本" | python3 /tmp/zhuque_cli.py
```

## 首次设置

1. 用户访问 `https://matrix.tencent.com/ai-detect/` 并扫码登录
2. 在浏览器 Console 运行：
   ```javascript
   copy(localStorage.getItem("aiGenAccessToken"))
   ```
3. 发送给助手，助手指令写入 `~/.openclaw/workspace/.zhuque-state.json`

## 验证结果解读

API 返回 JSON：

```json
{
  "status": "success",
  "confidence": 1.0,
  "labels_ratio": {"0": 0, "1": 0.136, "2": 0.864},
  "segment_labels": [{"text": "...", "label": 1, "conf": 0.99}, ...],
  "availableUses": 17
}
```

| 字段 | 说明 |
|------|------|
| `labels_ratio["2"]` | **AI 率**（Label 2 = 判为 AI） |
| `labels_ratio["1"]` | 疑似率（Label 1 = 可能 AI） |
| `labels_ratio["0"]` | 人类率（Label 0 = 人类） |
| `segment_labels[].label` | 逐段标记：0=人类 1=可疑 2=AI |
| `availableUses` | 当日剩余检测次数 |

## 判断标准

| AI 率 | 判定 | 处理 |
|-------|------|------|
| < 30% | ✅ 通过 | 继续流程 |
| 30-50% | ⚠️ 警告 | 针对性改写高风险段落 |
| ≥ 50% | ❌ 不通过 | 需要大改后重测 |

**注意**：朱雀对于"技术指南解读"类文章的 AI 率判定较严格，建议结合内容价值综合判断，不完全以 AI 率决定是否发布。

## 背景技术细节

- **WebSocket 握手时序**：`fp` → server 返回 `Invalid request` → 触发滑块 CAPTCHA → 提交 `ticket+randstr` → 通过后获得 `access_token` → 发 `access_token` 确认 → 发送 `text` → 接收检测结果
- **access_token 有效期**：7 天（JS 源码：`Date.now() + 6048e5`），存 localStorage key `aiGenAccessToken`
- **fingerprint 生成**：FingerprintJS → SHA256(visitorId + timestamp + random) → 取 32 位 hex，存 localStorage key `fp`
- **WebSocket 空闲超时**：30 分钟
- **配额限制**：服务端独立计数，不依赖 localStorage
