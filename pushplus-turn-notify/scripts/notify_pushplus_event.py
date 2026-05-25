#!/usr/bin/env python3
"""Format a Codex workflow event and send it through PushPlus."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


EVENT_TITLES_EN = {
    "completed": "Codex task completed",
    "review": "Codex result needs review",
    "permission": "Codex needs permission",
    "blocked": "Codex is blocked",
}

EVENT_TITLES_ZH = {
    "completed": "Codex 任务完成",
    "review": "Codex 结果待检查",
    "permission": "Codex 需要确认",
    "blocked": "Codex 任务受阻",
}

EVENT_LABELS_ZH = {
    "completed": "任务完成",
    "review": "结果待检查",
    "permission": "需要确认",
    "blocked": "任务受阻",
}


def _load_send_module() -> Any:
    script_path = Path(__file__).with_name("send_pushplus.py")
    spec = importlib.util.spec_from_file_location("send_pushplus", script_path)
    if not spec or not spec.loader:
        raise SystemExit(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_title(event: str, title: str | None, title_zh: str | None) -> str:
    if title and title_zh:
        return f"{title} / {title_zh}"
    if title:
        return title
    if title_zh:
        return title_zh
    return f"{EVENT_TITLES_EN[event]} / {EVENT_TITLES_ZH[event]}"


def render_content(
    event: str,
    summary: str,
    details: str | None,
    summary_zh: str | None,
    details_zh: str | None,
    pwd: str | None,
) -> str:
    effective_summary_zh = summary_zh or summary
    effective_details_zh = details_zh or details
    effective_pwd = pwd or str(Path.cwd())

    lines = [
        f"**Event / 事件:** `{event}` / {EVENT_LABELS_ZH[event]}",
        f"**Summary / 摘要 (EN):** {summary}",
        f"**摘要 / Summary (ZH):** {effective_summary_zh}",
        f"**Time / 时间:** {datetime.now().isoformat(timespec='seconds')}",
        f"**pwd / 工作目录:** `{effective_pwd}`",
    ]

    if details:
        lines.extend(["**Details / 详情 (EN):**", details])
    if effective_details_zh:
        lines.extend(["**详情 / Details (ZH):**", effective_details_zh])

    return "\n\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a PushPlus notification for a Codex turn event.")
    parser.add_argument("event", choices=sorted(EVENT_TITLES_EN), help="Workflow event type.")
    parser.add_argument("--summary", required=True, help="Short notification summary.")
    parser.add_argument("--summary-zh", help="Chinese notification summary.")
    parser.add_argument("--details", help="Details to include in the notification body.")
    parser.add_argument("--details-zh", help="Chinese details to include in the notification body.")
    parser.add_argument("--title", help="Override notification title.")
    parser.add_argument("--title-zh", help="Chinese title to combine with --title.")
    parser.add_argument("--pwd", help="Codex session working directory. Defaults to the current process directory.")
    parser.add_argument("--token", help="PushPlus token. Prefer config or env for regular use.")
    parser.add_argument("--template", help="PushPlus template, e.g. markdown, html, txt.")
    parser.add_argument("--channel", help="PushPlus channel, e.g. wechat.")
    parser.add_argument("--topic", help="Optional PushPlus topic.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    send_pushplus = _load_send_module()

    title = build_title(args.event, args.title, args.title_zh)
    content = render_content(args.event, args.summary, args.details, args.summary_zh, args.details_zh, args.pwd)
    send_args = argparse.Namespace(
        title=title,
        content=content,
        token=args.token,
        template=args.template,
        channel=args.channel,
        topic=args.topic,
        dry_run=args.dry_run,
    )
    payload = send_pushplus.build_payload(send_args)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "payload": send_pushplus.redact_payload(payload)}, ensure_ascii=False, indent=2))
        return 0

    result = send_pushplus.post_payload(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
