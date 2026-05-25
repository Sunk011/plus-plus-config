#!/usr/bin/env sh
set -eu

event="permission"
summary="Codex needs confirmation"
summary_zh="Codex 需要确认"
details="A Codex session is waiting for user approval to continue."
details_zh="Codex 会话正在等待用户批准以继续。"
working_directory=$(pwd)
dry_run=0

usage() {
  cat <<'EOF'
Usage: notify_pushplus_hook.sh [options]

Options:
  --event VALUE              completed, review, permission, or blocked
  --summary VALUE            English summary
  --summary-zh VALUE         Chinese summary
  --details VALUE            English details
  --details-zh VALUE         Chinese details
  --pwd VALUE                Codex session working directory
  --working-directory VALUE  Alias for --pwd
  --dry-run                  Print payload without sending
  -h, --help                 Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --event)
      if [ "$#" -lt 2 ]; then echo "--event requires a value" >&2; exit 2; fi
      event=$2
      shift 2
      ;;
    --summary)
      if [ "$#" -lt 2 ]; then echo "--summary requires a value" >&2; exit 2; fi
      summary=$2
      shift 2
      ;;
    --summary-zh|--summaryZh)
      if [ "$#" -lt 2 ]; then echo "--summary-zh requires a value" >&2; exit 2; fi
      summary_zh=$2
      shift 2
      ;;
    --details)
      if [ "$#" -lt 2 ]; then echo "--details requires a value" >&2; exit 2; fi
      details=$2
      shift 2
      ;;
    --details-zh|--detailsZh)
      if [ "$#" -lt 2 ]; then echo "--details-zh requires a value" >&2; exit 2; fi
      details_zh=$2
      shift 2
      ;;
    --pwd|--working-directory)
      if [ "$#" -lt 2 ]; then echo "$1 requires a value" >&2; exit 2; fi
      working_directory=$2
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    completed|review|permission|blocked)
      event=$1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$event" in
  completed|review|permission|blocked)
    ;;
  *)
    echo "Invalid event: $event" >&2
    exit 2
    ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
notify_script="$script_dir/notify_pushplus_event.py"

if [ ! -f "$notify_script" ]; then
  echo "notify_pushplus_event.py not found at $notify_script" >&2
  exit 1
fi

run_notify() {
  if [ "$dry_run" -eq 1 ]; then
    "$@" "$notify_script" "$event" \
      --summary "$summary" \
      --summary-zh "$summary_zh" \
      --details "$details" \
      --details-zh "$details_zh" \
      --pwd "$working_directory" \
      --dry-run
  else
    "$@" "$notify_script" "$event" \
      --summary "$summary" \
      --summary-zh "$summary_zh" \
      --details "$details" \
      --details-zh "$details_zh" \
      --pwd "$working_directory"
  fi
}

if [ "${PYTHON:-}" ]; then
  if run_notify "$PYTHON"; then
    exit 0
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  if run_notify python3; then
    exit 0
  fi
fi

if command -v python >/dev/null 2>&1; then
  if run_notify python; then
    exit 0
  fi
fi

if command -v py >/dev/null 2>&1; then
  if run_notify py -3; then
    exit 0
  fi
fi

if command -v conda >/dev/null 2>&1; then
  if run_notify conda run -n py310 python; then
    exit 0
  fi
fi

echo "No usable Python interpreter found for PushPlus notification hook." >&2
exit 1
