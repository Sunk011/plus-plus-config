#!/usr/bin/env python3
"""Send a PushPlus message.

This script intentionally uses only the Python standard library so the skill can
run in minimal Codex environments.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_URL = "https://www.pushplus.plus/send"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config at {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Invalid config at {path}: expected a JSON object")
    return data


def load_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    for path in (
        Path.home() / ".config" / "pushplus-turn-notify" / "config.json",
        Path.home() / ".config" / "pushplus" / "config.json",
    ):
        file_config = _read_json(path)
        if file_config:
            config.update(file_config)
            break

    env_token = os.environ.get("PUSHPLUS_TOKEN") or os.environ.get("PUSHPLUS_NOTIFY_TOKEN")
    if env_token:
        config["token"] = env_token
    return config


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config()
    token = args.token or config.get("token")
    if not token and not args.dry_run:
        raise SystemExit(
            "PushPlus token not found. Provide --token, PUSHPLUS_TOKEN, "
            "PUSHPLUS_NOTIFY_TOKEN, or ~/.config/pushplus-turn-notify/config.json."
        )

    payload: dict[str, Any] = {
        "token": token or "DRY_RUN_TOKEN",
        "title": args.title,
        "content": args.content,
        "template": args.template or config.get("template") or "markdown",
    }

    channel = args.channel or config.get("channel")
    topic = args.topic or config.get("topic")
    if channel:
        payload["channel"] = channel
    if topic:
        payload["topic"] = topic
    return payload


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    token = redacted.get("token")
    if token and token != "DRY_RUN_TOKEN":
        redacted["token"] = "REDACTED"
    return redacted


def post_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            try:
                response_json: Any = json.loads(response_body)
            except json.JSONDecodeError:
                response_json = response_body
            return {
                "ok": response.status == 200
                and isinstance(response_json, dict)
                and response_json.get("code") == 200,
                "http_status": response.status,
                "response": response_json,
            }
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "http_status": exc.code, "response": error_body}
    except urllib.error.URLError as exc:
        return {"ok": False, "http_status": None, "response": str(exc.reason)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a PushPlus notification.")
    parser.add_argument("--title", required=True, help="Notification title.")
    parser.add_argument("--content", required=True, help="Notification body.")
    parser.add_argument("--token", help="PushPlus token. Prefer config or env for regular use.")
    parser.add_argument("--template", help="PushPlus template, e.g. markdown, html, txt.")
    parser.add_argument("--channel", help="PushPlus channel, e.g. wechat.")
    parser.add_argument("--topic", help="Optional PushPlus topic.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload = build_payload(args)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "payload": redact_payload(payload)}, ensure_ascii=False, indent=2))
        return 0

    result = post_payload(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
