# 🐦 朱雀 AI 检测自动化 (zhuque-ai-detector)

Playwright + WebSocket 自动调用[腾讯朱雀 AI 检测](https://matrix.tencent.com/ai-detect/)，无需手动打开浏览器、粘贴文本、点击按钮。

## 适用场景

如果你需要频繁检测公众号文章、博客、论文的 **AI 生成率**，手动操作朱雀网页太慢——这个脚本帮你全自动化：

1. 打开朱雀页面
2. 注入待检测文本
3. 点击 Detect
4. 等待结果
5. 输出结构化的 AI 率/可疑率/逐段标记

整个过程在 Playwright headless 浏览器中完成，不依赖任何第三方 API Key。

## 功能

- ✅ **全自动检测** — 读取本地文件或传入文本，一步输出结果
- ✅ **无 API Key** — 复用朱雀 Web 端身份（扫码一次，7 天有效）
- ✅ **逐段标记** — 返回每个段落是 AI/可疑/人类，定位风险段
- ✅ **配额管理** — 自动检测并提示当日剩余次数
- ✅ **自定义文本** — 支持 stdin 管道输入

## 前置条件

- Python 3.9+
- Playwright + Chromium

```bash
pip install playwright
playwright install chromium
```

## 安装

```bash
git clone https://github.com/skystmm/zhuque-ai-detector.git
cd zhuque-ai-detector
# 脚本默认状态文件位置：~/.openclaw/workspace/.zhuque-state.json
# 如果你在不同目录使用，修改 detect.py 中的 STATE_PATH
```

## 配置（首次使用）

脚本复用你在朱雀网页的登录态，首次需要**手动获取一次 access_token**：

1. 浏览器打开 https://matrix.tencent.com/ai-detect/
2. 使用手机微信扫码登录
3. 打开浏览器开发者工具（F12）→ Console
4. 粘贴以下代码，回车：

```javascript
copy(localStorage.getItem("aiGenAccessToken"))
```

5. 剪贴板会得到一串 JWT token（类似 `eyJhbGciOiJIUzI1NiIs...`）
6. 运行下面命令保存状态文件：

```bash
mkdir -p ~/.openclaw/workspace
cat > ~/.openclaw/workspace/.zhuque-state.json << 'EOF'
{
  "aiGenAccessToken": {
    "value": "粘贴你得到的JWT字符串"
  }
}
EOF
```

**access_token 有效期 7 天**，过期后重新执行以上步骤即可。

> 补充说明：除了 access_token，朱雀还会生成一个浏览器指纹（fp）用于首次握手。脚本内置了自动获取逻辑，首次运行时会自动补充 fp 到状态文件中，无需手动配置。

## 使用

### 方式一：检测最新终稿（推荐）

```bash
python3 /tmp/zhuque_full.py
```

自动在 `my_document` 目录下找到最新 `终稿-*.md` 文件进行检测。

### 方式二：自定义文本

```bash
echo "待检测文本内容" | python3 /tmp/zhuque_cli.py
```

### 方式三：检测指定文件

```bash
python3 -c "
from detect import detect_via_page
import asyncio, json

text = open('你的文件.md').read()
result = asyncio.run(detect_via_page(text))
print(json.dumps(result, ensure_ascii=False, indent=2))
"
```

## 输出解读

检测结果 JSON 示例：

```json
{
  "status": "success",
  "confidence": 0.99,
  "labels_ratio": {"0": 0.0, "1": 0.136, "2": 0.864},
  "segment_labels": [
    {"text": "少写废话...", "label": 2, "conf": 0.937},
    {"text": "旧范式...", "label": 1, "conf": 0.995},
    {"text": "新范式...", "label": 2, "conf": 0.948}
  ],
  "availableUses": 17
}
```

| 字段 | 说明 |
|------|------|
| `labels_ratio["2"]` | **AI 率** — Label 2（判定为 AI 生成）的文本占比 |
| `labels_ratio["1"]` | **可疑率** — Label 1（可能 AI）的文本占比 |
| `labels_ratio["0"]` | **人类率** — Label 0（人类书写）的文本占比 |
| `segment_labels[].label` | 每个段落的判定结果：0=人类 / 1=可疑 / 2=AI |
| `segment_labels[].conf` | 该判定的置信度 |
| `availableUses` | 当日剩余检测次数 |

### 判断标准参考

| AI 率 | 判定 | 处理建议 |
|-------|------|----------|
| < 30% | ✅ 通过 | 可直接发布 |
| 30-50% | ⚠️ 警告 | 针对性改写高风险段落 |
| ≥ 50% | ❌ 不通过 | 需要大改后重测 |

> **注意**：朱雀对"技术指南/趋势解读"类文章的 AI 率判定较严格，建议结合内容质量综合判断，不完全以 AI 率决定是否发布。

## 技术原理

朱雀 AI 检测通过 WebSocket 端点 `wss://matrix.tencent.com/ai_gen_txt_server/getClassify` 实现：

1. **首次握手**：发送浏览器指纹 fp → 触发滑块 CAPTCHA
2. **授权验证**：提交 `ticket + randstr` 通过验证 → 获得 `access_token`
3. **正式检测**：发送 `access_token` 确认 → 发送文本 → 接收分段落判定结果

脚本通过 Playwright 在浏览器同源环境下复现全部流程，包括自动处理 CAPTCHA 握手。

## 配额

- 每日约 10-30 次检测（腾讯官网分配，非固定）
- 服务端独立计数，不依赖 localStorage
- 脚本会在结束时打印剩余次数

## 项目结构

```
zhuque-ai-detector/
├── README.md          ← 本文档
├── SKILL.md           ← OpenClaw 技能定义（SOP 集成用）
├── detect.py          ← 核心检测函数（detect_via_page）
├── .gitignore         ← 排除 state 文件、截图、缓存
└── .zhuque-state.json ← （本地配置，不上传）
```

## License

MIT
