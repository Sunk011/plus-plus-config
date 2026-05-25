# PushPlus Turn Notify Skill 配置说明

本仓库保存 `pushplus-turn-notify` Codex skill 的源码、脚本和配置记录。目标是在 Codex 任务达到需要用户关注的状态时，通过 PushPlus 发送提醒。

本文记录从零部署到可用的完整过程，包括 skill 安装、PushPlus token、脚本验证、跨工作目录规则、权限确认 hook 和故障排查。

## 目标行为

- `completed`: 一轮实质性任务结束，准备最终回复前提醒。
- `review`: 结果或文件已经生成，需要用户检查。
- `permission`: Codex 需要用户批准某个动作。
- `blocked`: Codex 需要用户补充信息，否则无法继续。
- 该能力应在所有 Codex 工作目录中生效，不只在本仓库中生效。
- 真正的 Codex 权限确认弹窗由 `PermissionRequest` hook 兜底通知。
- 每条 PushPlus 正文同时包含英文和中文内容，并包含一行当前 Codex 会话工作目录：`pwd / 工作目录`。

## 仓库结构

```text
pushplus-turn-notify/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── pushplus-api.md
└── scripts/
    ├── notify_claude_hook.js
    ├── notify_pushplus_event.py
    ├── notify_pushplus_hook.ps1
    ├── notify_pushplus_hook.sh
    └── send_pushplus.py
```

辅助文档：

```text
pushplus_turn_notify_skill_deploy.md
```

不要发布或复制运行缓存：

```text
scripts/__pycache__/
*.pyc
```

## 1. 安装 Skill

Codex 自动发现的用户级 skill 目录是：

```text
~/.codex/skills/pushplus-turn-notify/
```

在本仓库根目录运行 PowerShell：

```powershell
$src = Resolve-Path ".\pushplus-turn-notify"
$dst = Join-Path $env:USERPROFILE ".codex\skills\pushplus-turn-notify"

New-Item -ItemType Directory -Force -Path $dst | Out-Null
Get-ChildItem -LiteralPath $src -Force |
  Where-Object { $_.Name -ne "__pycache__" } |
  Copy-Item -Destination $dst -Recurse -Force
```

安装后如果当前 Codex 会话没有看到该 skill，重启 Codex 或重新 resume 会话。

macOS/Linux 可在本仓库根目录运行：

```bash
src="$(pwd)/pushplus-turn-notify"
dst="$HOME/.codex/skills/pushplus-turn-notify"

mkdir -p "$dst"
cp -R "$src"/. "$dst"/
rm -rf "$dst"/scripts/__pycache__
```

## 2. 配置 PushPlus Token

不要把真实 token 写进本仓库、`SKILL.md`、README、部署文档或脚本。

PushPlus 官方地址：

- 官网：`https://www.pushplus.plus/`
- 获取用户 token 接口文档：`https://www.pushplus.plus/api/open/user/token`

推荐使用用户级配置：

```text
~/.config/pushplus-turn-notify/config.json
```

Windows PowerShell 配置命令：

```powershell
$dir = Join-Path $env:USERPROFILE ".config\pushplus-turn-notify"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$token = Read-Host "Paste PushPlus token"

@{
  token = $token
  template = "markdown"
  channel = "wechat"
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir "config.json") -Encoding utf8
```

配置文件格式：

```json
{
  "token": "YOUR_PUSHPLUS_TOKEN",
  "template": "markdown",
  "channel": "wechat"
}
```

脚本读取 token 的顺序：

1. 命令行参数 `--token`
2. 环境变量 `PUSHPLUS_TOKEN`
3. 环境变量 `PUSHPLUS_NOTIFY_TOKEN`
4. `~/.config/pushplus-turn-notify/config.json`
5. `~/.config/pushplus/config.json`

## 3. 验证 Skill 脚本

进入 skill 目录：

```powershell
cd pushplus-turn-notify
```

如果要验证已安装到 Codex 的副本，则进入：

```text
~/.codex/skills/pushplus-turn-notify/
```

### Dry-run

dry-run 不发送网络请求，只检查 payload 构造。

```powershell
python scripts/notify_pushplus_event.py completed `
  --summary "PushPlus skill dry run" `
  --summary-zh "PushPlus skill dry-run 验证" `
  --details "This is a local payload check." `
  --details-zh "这是一次本地 payload 检查。" `
  --dry-run
```

预期输出包含：

```json
{
  "ok": true,
  "dry_run": true,
  "payload": {
    "token": "REDACTED"
  }
}
```

如果本机还没有配置 token，dry-run 中 token 可能显示为 `DRY_RUN_TOKEN`。如果已经配置 token，输出必须脱敏为 `REDACTED`。

正文中应同时出现这些字段：

```text
Event / 事件
Summary / 摘要 (EN)
摘要 / Summary (ZH)
Time / 时间
pwd / 工作目录
Details / 详情 (EN)
详情 / Details (ZH)
```

脚本默认用当前进程目录作为 `pwd / 工作目录`。如果是 hook 或外层脚本已经知道更准确的 Codex 工作目录，可以显式传入：

```powershell
python scripts/notify_pushplus_event.py completed `
  --summary "Task completed" `
  --summary-zh "任务已完成" `
  --details "Validation passed." `
  --details-zh "验证已通过。" `
  --pwd (Get-Location).Path `
  --dry-run
```

### 真实发送

```powershell
python scripts/notify_pushplus_event.py completed `
  --summary "PushPlus skill configured" `
  --summary-zh "PushPlus skill 已配置" `
  --details "Codex verified the PushPlus notification skill using the saved user config." `
  --details-zh "Codex 已使用保存的用户配置验证 PushPlus 通知 skill。"
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

如果当前环境没有 `python` 命令，可以改用 `python3`，或使用当前 Python 环境里的解释器路径。

## 4. 配置跨工作目录规则

`pushplus-turn-notify` 是全局通知 skill，不绑定本仓库。

已在 `pushplus-turn-notify/SKILL.md` 中记录规则：

- 在任何 Codex 工作目录中都可以使用该 skill。
- 不要因为当前工作目录不是本仓库而跳过通知。
- 如果当前项目里没有 `scripts/notify_pushplus_event.py`，应调用已安装 skill 的脚本：

```text
~/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_event.py
```

这解决的是普通任务流程中的通知触发问题，例如任务完成、需要 review、阻塞等待用户输入等。

## 5. 配置 PermissionRequest Hook

真正的 Codex 权限确认弹窗不能只依赖模型主动调用 skill。审批请求出现时，Codex 往往已经在等待用户批准，未必还有机会先发 `permission` 事件。

因此需要在 `~/.codex/config.toml` 中配置 `PermissionRequest` hook。

### 推荐配置

Windows 保留已有本机桌面通知 hook 时，可以追加第二个 `PermissionRequest` hook：

```toml
[[hooks.PermissionRequest]]
[[hooks.PermissionRequest.hooks]]
type = "command"
command = '''powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Import-Module BurntToast; New-BurntToastNotification -Text 'Codex', '需要确认以继续' -Sound Reminder"'''
timeout = 30
statusMessage = "Codex 权限确认通知"

[[hooks.PermissionRequest.hooks]]
type = "command"
command = '''powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& (Join-Path $env:USERPROFILE '.codex\skills\pushplus-turn-notify\scripts\notify_pushplus_hook.ps1') -Event permission -Summary 'Codex needs confirmation' -SummaryZh 'Codex 需要确认' -Details 'A Codex session is waiting for your approval to continue.' -DetailsZh 'Codex 会话正在等待你的批准以继续。'"'''
timeout = 30
statusMessage = "Codex PushPlus 权限确认通知"
```

如果不需要 BurntToast，本地桌面通知 hook 可以省略，只保留 PushPlus hook。

macOS/Linux 使用 shell wrapper：

```toml
[[hooks.PermissionRequest]]
[[hooks.PermissionRequest.hooks]]
type = "command"
command = '''sh "$HOME/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_hook.sh" --event permission --summary "Codex needs confirmation" --summary-zh "Codex 需要确认" --details "A Codex session is waiting for your approval to continue." --details-zh "Codex 会话正在等待你的批准以继续。"'''
timeout = 30
statusMessage = "Codex PushPlus 权限确认通知"
```

macOS/Linux 可以用下面的 shell 命令追加到 `~/.codex/config.toml`：

```bash
mkdir -p ~/.codex

cat >> ~/.codex/config.toml <<'TOML'

[[hooks.PermissionRequest]]
[[hooks.PermissionRequest.hooks]]
type = "command"
command = '''sh "$HOME/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_hook.sh" --event permission --summary "Codex needs confirmation" --summary-zh "Codex 需要确认" --details "A Codex session is waiting for your approval to continue." --details-zh "Codex 会话正在等待你的批准以继续。"'''
timeout = 30
statusMessage = "Codex PushPlus 权限确认通知"
TOML
```

如果 `~/.codex/config.toml` 中已经有 `[[hooks.PermissionRequest]]`，也可以只把下面这个 hook 追加到现有 `PermissionRequest` 配置块内：

```toml
[[hooks.PermissionRequest.hooks]]
type = "command"
command = '''sh "$HOME/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_hook.sh" --event permission --summary "Codex needs confirmation" --summary-zh "Codex 需要确认" --details "A Codex session is waiting for your approval to continue." --details-zh "Codex 会话正在等待你的批准以继续。"'''
timeout = 30
statusMessage = "Codex PushPlus 权限确认通知"
```

Git Bash 中可直接使用同一个 `.sh` wrapper 测试；实际 Windows Codex hook 仍建议使用上面的 PowerShell 配置。

`notify_pushplus_hook.ps1` 和 `notify_pushplus_hook.sh` 都会自动定位 Python，调用同目录下的：

```text
notify_pushplus_event.py permission
```

并读取第 2 步配置的用户级 token。wrapper 会把当前 shell 位置作为 `pwd / 工作目录` 传给 Python 脚本；Codex 调用 hook 时，这个位置应对应当前会话的工作目录。

### Hook 信任

新增或修改 hook 后，Codex 可能会在首次触发时要求信任该 hook。批准一次后，信任状态会写入：

```text
~/.codex/config.toml
```

位置在：

```toml
[hooks.state]
```

不要手写 `trusted_hash`，让 Codex 在首次批准后自动生成。

## 6. 验证 PermissionRequest Hook

先直接测试 wrapper：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& (Join-Path $env:USERPROFILE '.codex\skills\pushplus-turn-notify\scripts\notify_pushplus_hook.ps1') -Event permission -Summary 'Permission hook manual test' -Details 'Manual PushPlus permission hook verification.'"
```

推荐同时带上中文内容测试：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& (Join-Path $env:USERPROFILE '.codex\skills\pushplus-turn-notify\scripts\notify_pushplus_hook.ps1') -Event permission -Summary 'Permission hook manual test' -SummaryZh '权限 hook 手动测试' -Details 'Manual PushPlus permission hook verification.' -DetailsZh '手动验证 PushPlus 权限 hook。'"
```

PowerShell dry-run：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& (Join-Path $env:USERPROFILE '.codex\skills\pushplus-turn-notify\scripts\notify_pushplus_hook.ps1') -Event permission -Summary 'Permission hook dry run' -SummaryZh '权限 hook dry-run' -Details 'Local payload check.' -DetailsZh '本地 payload 检查。' -DryRun"
```

macOS/Linux dry-run：

```bash
sh ~/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_hook.sh \
  --event permission \
  --summary "Permission hook dry run" \
  --summary-zh "权限 hook dry-run" \
  --details "Local payload check." \
  --details-zh "本地 payload 检查。" \
  --dry-run
```

真实发送时去掉 `-DryRun` 或 `--dry-run`。

成功时 PushPlus 返回：

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

再验证 Codex 配置能正常加载：

```powershell
codex doctor --summary --no-color
```

预期结果中 `Configuration` 应显示 `config loaded`，最终汇总没有 `fail`。

如果要校验 skill 结构：

```powershell
$env:PYTHONUTF8 = "1"
python ~/.codex/skills/skill-creator/scripts/quick_validate.py pushplus-turn-notify
python ~/.codex/skills/skill-creator/scripts/quick_validate.py ~/.codex/skills/pushplus-turn-notify
```

Windows 默认 GBK locale 下，`SKILL.md` 含中文时可能需要先设置 `PYTHONUTF8=1`，否则校验脚本读取 UTF-8 文件可能失败。

最后可以在一个需要审批的场景中触发 Codex 权限确认，例如需要 `require_escalated` 的命令。首次触发新增 hook 时，可能先出现 hook 信任确认；批准后应收到 PushPlus 提醒。

## 7. 配置 Claude Code Hook

Claude Code 使用 `~/.claude/settings.json` 的 JSON 配置，不使用 Codex 的 `~/.codex/config.toml`。本仓库新增的 `notify_claude_hook.js` 会读取 Claude Code hook 通过 stdin 传入的 JSON，并复用第 2 步的 PushPlus token 配置。

推荐先启用 `Notification`，用于 Claude Code 需要权限、等待用户输入或需要关注时提醒；如果也希望每轮 Claude Code 停止时提醒，再启用 `Stop`。

### Windows / Git Bash 当前验证配置

本机 Git Bash 环境没有 `python`、`python3`、`py` 和 `powershell.exe` 命令，但有 Node.js，所以 Claude Code hook 使用 Node wrapper。已在 `C:\Users\Sunky\.claude\settings.json` 中加入：

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node \"E:/Projects/wkSpace/plus++_config/pushplus-turn-notify/scripts/notify_claude_hook.js\" --hook Notification",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node \"E:/Projects/wkSpace/plus++_config/pushplus-turn-notify/scripts/notify_claude_hook.js\" --hook Stop",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

如果只想在需要关注时提醒，不想每轮结束都提醒，可以删除 `Stop` 配置块。

### macOS/Linux 示例

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$HOME/.claude/pushplus-turn-notify/scripts/notify_claude_hook.js\" --hook Notification",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

如果把 skill 安装在其他目录，把 `command` 中的脚本路径改成实际绝对路径。不要把 PushPlus token 写进 `settings.json`。

### Claude Code 事件映射

- `Notification`：映射为 `permission` 或 `blocked`。当 hook `message` 包含 permission、approve、approval 时按 `permission` 发送，否则按 `blocked` 发送。
- `Stop`：映射为 `completed`。
- `SubagentStop`：默认不建议配置，否则子代理结束也会提醒，容易过于频繁。

`notify_claude_hook.js` 会把 Claude Code hook JSON 中的 `cwd` 写入正文的 `pwd / 工作目录`，并在存在时附带 `session_id`。

### Claude Code Hook 验证

本地 dry-run：

```bash
node "pushplus-turn-notify/scripts/notify_claude_hook.js" --hook Notification --dry-run <<'JSON'
{"hook_event_name":"Notification","message":"Claude needs your permission to use Bash","cwd":"/e/Projects/wkSpace/plus++_config","session_id":"test-session"}
JSON
```

真实发送测试：

```bash
node "pushplus-turn-notify/scripts/notify_claude_hook.js" --hook Notification <<'JSON'
{"hook_event_name":"Notification","message":"Claude Code PushPlus hook verification from local setup.","cwd":"/e/Projects/wkSpace/plus++_config","session_id":"manual-test"}
JSON
```

成功时 PushPlus 返回 `code: 200`。

### Claude Code 配置问题记录

- `claude doctor --summary --no-color` 在当前 Claude Code 版本中不可用，会报 `unknown option '--summary'`；改用 `claude doctor`。
- 当前 Git Bash PATH 中没有 `claude`，但全局 npm 目录有 `D:\Program Files\nodejs\node_global\claude`，可用 `"/d/Program Files/nodejs/node_global/claude" doctor` 调用。
- 当前 Git Bash 环境没有 Python 和 PowerShell 命令，因此 Codex 用的 `.ps1` / `.sh` wrapper 不适合作为 Claude Code hook 命令；Claude Code 配置改用 Node wrapper。
- JSON 配置中命令路径建议使用正斜杠和双引号包裹，避免 Windows 反斜杠转义和 `plus++_config` 路径解析问题。
- 第一次修改 Claude Code hook 后，Claude Code 可能要求信任新增 hook；批准后通知才会稳定触发。
- 同时启用模型主动通知和 `Stop` hook 时，完成通知可能重复。需要减少噪音时保留 `Notification`，删除 `Stop`。

## 8. 可选 Stop Hook

如果希望 Codex 每次停止时都通过 hook 发送 PushPlus，而不是只依赖 skill 主动发送，可以额外配置 `Stop` hook。

Windows 示例：

```toml
[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = '''powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& (Join-Path $env:USERPROFILE '.codex\skills\pushplus-turn-notify\scripts\notify_pushplus_hook.ps1') -Event completed -Summary 'Codex task completed' -SummaryZh 'Codex 任务完成' -Details 'A Codex task turn has completed.' -DetailsZh '一轮 Codex 任务已经完成。'"'''
timeout = 30
statusMessage = "Codex PushPlus Stop 通知"
```

macOS/Linux 示例：

```toml
[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = '''sh "$HOME/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_hook.sh" --event completed --summary "Codex task completed" --summary-zh "Codex 任务完成" --details "A Codex task turn has completed." --details-zh "一轮 Codex 任务已经完成。"'''
timeout = 30
statusMessage = "Codex PushPlus Stop 通知"
```

注意：如果模型也会在完成前主动调用 `pushplus-turn-notify`，再配置 `Stop` hook 可能导致重复通知。通常建议先只配置 `PermissionRequest` hook，再由 skill 规则处理普通完成、review 和 blocked 事件。

## 9. 使用约定

- 每轮任务最多发送一次提醒，除非用户明确要求再发。
- 不要给普通状态更新、短对话或每一步工具调用发提醒。
- PushPlus 只是提醒渠道，发送后仍然要在 Codex 对话里正常回复。
- 修改通知策略优先编辑 `pushplus-turn-notify/SKILL.md`。
- 修改 PushPlus API 字段或响应解析时，再参考 `pushplus-turn-notify/references/pushplus-api.md`。

## 10. 故障排查

- `python: command not found`: 使用 `python3`，或安装 Python。`notify_pushplus_hook.ps1` 和 `notify_pushplus_hook.sh` 会自动尝试 `python`、`python3`、`py -3` 和 conda 的 `py310` 环境。
- `PushPlus token not found`: 检查用户级配置、环境变量或 `--token` 参数。
- HTTP 200 但 `response.code` 不是 200: PushPlus 接口拒绝请求，检查 token、渠道、topic 或账户状态。
- 没有收到微信提醒: 检查 PushPlus 账号绑定、渠道配置、免打扰设置。
- Codex 看不到 skill: 确认目录位于 `~/.codex/skills/pushplus-turn-notify/`，必要时重启 Codex 会话。
- `PermissionRequest` 没有 PushPlus 提醒: 检查 `~/.codex/config.toml` 是否有 PushPlus hook、是否已经信任新增 hook、wrapper 手动测试是否返回 `code: 200`。
- `conda run` 输出编码报错: 直接调用当前环境里的 Python 解释器，绕过 `conda run` 的输出编码路径。

## 11. 安全注意事项

- 不要提交真实 token。
- 不要把 token 写进 README、部署文档、skill 文件或脚本。
- 不要复制 `scripts/__pycache__/` 或 `*.pyc` 到发布包。
- 对外分发时只分发 skill 源文件和说明文档，token 由每台机器单独配置。
- dry-run 输出必须脱敏真实 token；如果看到真实 token，先修复脚本再继续分发。
