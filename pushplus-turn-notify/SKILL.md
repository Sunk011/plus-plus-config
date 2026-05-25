---
name: pushplus-turn-notify
description: Send PushPlus notifications from Codex workflows in any working directory when a task turn has a user-visible outcome or requires user attention. Use for completed, review, permission, or blocked events before the final reply or before waiting for user approval; do not use for short chats, routine progress updates, or every tool call.
---

# PushPlus Turn Notify

Use this skill to send a PushPlus reminder when the user may have stepped away from Codex and should be notified that the current turn has reached a meaningful state.

## Workspace Policy

This is a global notification skill. Apply it in every Codex working directory, not only in the repository where the skill was created or tested.

Do not skip a notification because the active workspace is different from `plus++_config`. If a turn reaches `completed`, `review`, `permission`, or `blocked`, use this skill from whatever project is active.

When the active shell is in another workspace, run the script from this skill directory or by using the installed skill path, such as `~/.codex/skills/pushplus-turn-notify/scripts/notify_pushplus_event.py`. Do not assume `scripts/notify_pushplus_event.py` exists in the current project.

Every notification body must include the Codex session working directory. The script adds `pwd / 工作目录` from the current process directory by default; pass `--pwd` when a hook has a more accurate workspace path.

## Event Policy

Send at most one notification for a turn unless the user explicitly asks for another. Choose one event:

- `completed`: Substantive work is finished and you are about to send the final reply.
- `review`: An artifact or result is ready and needs user review.
- `permission`: The workflow needs explicit user approval for an action.
- `blocked`: You need user input before you can continue.

Do not send notifications for normal status messages, trivial answers, quick command output, or internal implementation milestones.

## Quick Start

From this skill directory, run:

```bash
python scripts/notify_pushplus_event.py completed \
  --summary "Task completed" \
  --summary-zh "任务已完成" \
  --details "The requested files were updated and validation passed." \
  --details-zh "请求的文件已更新，验证已通过。"
```

Use `python3` or an environment-specific Python executable when `python` is not available.

For a local payload check without network or token:

```bash
python scripts/notify_pushplus_event.py completed \
  --summary "PushPlus skill dry run" \
  --summary-zh "PushPlus skill dry-run 验证" \
  --details "This is a local payload check." \
  --details-zh "这是一次本地 payload 检查。" \
  --dry-run
```

## Token Configuration

Never write a real PushPlus token into repository files, `SKILL.md`, or scripts.

Token lookup order:

1. `--token`
2. `PUSHPLUS_TOKEN`
3. `PUSHPLUS_NOTIFY_TOKEN`
4. `~/.config/pushplus-turn-notify/config.json`
5. `~/.config/pushplus/config.json`

Supported config file fields:

```json
{
  "token": "YOUR_PUSHPLUS_TOKEN",
  "template": "markdown",
  "channel": "wechat"
}
```

## Command Patterns

```bash
python scripts/notify_pushplus_event.py review \
  --summary "Need review for generated plots" \
  --summary-zh "需要检查生成的图表" \
  --details "QC plots are ready. Please confirm before adopting corrections." \
  --details-zh "QC 图表已准备好，请确认后再采用修正。"
```

```bash
python scripts/notify_pushplus_event.py blocked \
  --summary "Need dataset location" \
  --summary-zh "需要数据集位置" \
  --details "Cannot continue until the target dataset path is provided." \
  --details-zh "需要提供目标数据集路径后才能继续。"
```

After sending a notification, still reply normally in the Codex conversation. PushPlus is only a reminder channel.

## Codex Permission Hook

For Codex approval prompts, configure a `PermissionRequest` hook in `~/.codex/config.toml` to run the platform wrapper:

- Windows PowerShell: `scripts/notify_pushplus_hook.ps1`
- macOS, Linux, and Git Bash: `scripts/notify_pushplus_hook.sh`

This covers cases where Codex is waiting on the approval UI and may not get another chance to call the skill itself.

The hook wrapper locates Python, runs `notify_pushplus_event.py permission`, passes bilingual content plus the current working directory, and reads the same user-level PushPlus token config. Use `--dry-run` (`-DryRun` on PowerShell) to inspect payload construction without sending.

## API Reference

Read `references/pushplus-api.md` when changing request fields, response parsing, or troubleshooting PushPlus responses.
