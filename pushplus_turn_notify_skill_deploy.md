# PushPlus Turn Notify Skill Deployment Guide

这份文档给另一个 Codex 或维护者使用，用来把
`pushplus-turn-notify` skill 部署到一台新机器上，并完成最小验证。

## 1. Skill 目标

`pushplus-turn-notify` 用于在 Codex 工作流中发送 PushPlus 提醒。适用场景：

- `completed`: 一轮实质性任务结束，准备给用户最终回复前提醒。
- `review`: 需要用户检查或确认某个结果。
- `permission`: 需要用户批准某个动作。
- `blocked`: 需要用户回答问题，否则无法继续。

不要用于短对话、普通状态更新或每一步工具调用。它应该只在用户可能离开窗口、需要看到结果或需要决策时发送。

## 2. 目录结构

目标目录通常是：

```bash
${CODEX_HOME:-$HOME/.codex}/skills/pushplus-turn-notify
```

最小文件结构：

```text
pushplus-turn-notify/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── pushplus-api.md
└── scripts/
    ├── notify_pushplus_event.py
    └── send_pushplus.py
```

不要复制运行缓存：

```text
scripts/__pycache__/
*.pyc
```

## 3. 从已有机器复制

在已有机器上打包或同步 skill 目录。示例：

```bash
SRC="$HOME/.codex/skills/pushplus-turn-notify"
DST_HOST="user@target-host"

rsync -av \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$SRC/" \
  "$DST_HOST:~/.codex/skills/pushplus-turn-notify/"
```

如果是在目标机器本地安装：

```bash
SRC="/path/to/pushplus-turn-notify"
DST="${CODEX_HOME:-$HOME/.codex}/skills/pushplus-turn-notify"

mkdir -p "$DST"
rsync -av --exclude='__pycache__' --exclude='*.pyc' "$SRC/" "$DST/"
chmod +x "$DST/scripts/"*.py
```

如果 Codex 客户端不会热加载 skill，安装后重新打开 Codex 会话。

## 4. 配置 PushPlus Token

不要把 token 写进 repo、`SKILL.md` 或脚本。推荐放到用户配置文件：

```bash
mkdir -p ~/.config/pushplus-turn-notify
cat > ~/.config/pushplus-turn-notify/config.json <<'JSON'
{
  "token": "YOUR_PUSHPLUS_TOKEN",
  "template": "markdown",
  "channel": "wechat"
}
JSON
chmod 600 ~/.config/pushplus-turn-notify/config.json
```

脚本读取 token 的优先级：

1. 命令行 `--token`
2. 环境变量 `PUSHPLUS_TOKEN`
3. 环境变量 `PUSHPLUS_NOTIFY_TOKEN`
4. `~/.config/pushplus-turn-notify/config.json`
5. `~/.config/pushplus/config.json`

## 5. 验证安装

先 dry-run，确认脚本能正常构造 payload：

```bash
cd "${CODEX_HOME:-$HOME/.codex}/skills/pushplus-turn-notify"

python3 scripts/notify_pushplus_event.py completed \
  --summary "PushPlus skill dry run" \
  --details "This is a local payload check." \
  --dry-run
```

看到 JSON payload 即表示本地脚本正常。

然后发一条真实消息：

```bash
python3 scripts/notify_pushplus_event.py completed \
  --summary "PushPlus skill installed" \
  --details "The Codex notification skill can send messages from this machine."
```

成功响应示例：

```json
{
  "ok": true,
  "http_status": 200,
  "response": {
    "code": 200,
    "msg": "执行成功"
  }
}
```

## 6. Codex 使用约定

当任务触发该 skill 时，Codex 应先读取：

```text
${CODEX_HOME:-$HOME/.codex}/skills/pushplus-turn-notify/SKILL.md
```

常用命令模板：

```bash
python3 scripts/notify_pushplus_event.py completed \
  --summary "R07 eval done" \
  --details "Val AP 0.5450; official test JSON generated."
```

```bash
python3 scripts/notify_pushplus_event.py review \
  --summary "Need review for generated plots" \
  --details "QC plots are ready. Please confirm before adopting corrections."
```

```bash
python3 scripts/notify_pushplus_event.py blocked \
  --summary "Need dataset location" \
  --details "Cannot continue until the target dataset path is provided."
```

事件发送后，Codex 仍然要在对话里给正常回复。PushPlus 只是提醒，不替代最终答复。

## 7. 故障排查

- `python: command not found`: 用 `python3`，或使用当前 conda/env 里的 Python。
- `PushPlus token not found`: 检查配置文件路径、环境变量或 `--token`。
- HTTP 200 但 `code` 不是 200: PushPlus 侧拒绝请求，检查 token、渠道、topic 或账户状态。
- 没有收到微信提醒: 检查 `channel`、PushPlus 账号绑定、免打扰设置。
- Codex 看不到 skill: 确认目录在 `${CODEX_HOME:-$HOME/.codex}/skills/` 下，并重启 Codex 会话。

## 8. 安全和维护

- 不提交真实 token。
- 不复制 `__pycache__` 和 `*.pyc`。
- 修改通知策略时优先改 `SKILL.md`，修改 API 字段时再看 `references/pushplus-api.md`。
- 对外分发时建议压缩整个 `pushplus-turn-notify/` 目录，排除缓存文件。
