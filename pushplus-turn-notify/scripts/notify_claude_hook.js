#!/usr/bin/env node

const fs = require('fs');
const https = require('https');
const os = require('os');
const path = require('path');

const API_URL = 'https://www.pushplus.plus/send';

const EVENT_TITLES_EN = {
  completed: 'Claude Code task completed',
  review: 'Claude Code result needs review',
  permission: 'Claude Code needs permission',
  blocked: 'Claude Code needs attention',
};

const EVENT_TITLES_ZH = {
  completed: 'Claude Code 任务完成',
  review: 'Claude Code 结果待检查',
  permission: 'Claude Code 需要确认',
  blocked: 'Claude Code 需要关注',
};

const EVENT_LABELS_ZH = {
  completed: '任务完成',
  review: '结果待检查',
  permission: '需要确认',
  blocked: '需要关注',
};

function parseArgs(argv) {
  const args = { dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      args.dryRun = true;
      continue;
    }
    if (!arg.startsWith('--')) {
      throw new Error(`Unknown argument: ${arg}`);
    }
    if (i + 1 >= argv.length) {
      throw new Error(`${arg} requires a value`);
    }
    const key = arg.slice(2).replace(/-([a-z])/g, (_, char) => char.toUpperCase());
    args[key] = argv[i + 1];
    i += 1;
  }
  return args;
}

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8').trim();
  } catch {
    return '';
  }
}

function parseHookInput(raw) {
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch {
    return { message: raw };
  }
}

function readJsonIfExists(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') {
      return {};
    }
    throw new Error(`Invalid JSON config at ${filePath}: ${error.message}`);
  }
}

function loadConfig() {
  const configPaths = [
    path.join(os.homedir(), '.config', 'pushplus-turn-notify', 'config.json'),
    path.join(os.homedir(), '.config', 'pushplus', 'config.json'),
  ];
  let config = {};
  for (const configPath of configPaths) {
    const fileConfig = readJsonIfExists(configPath);
    if (Object.keys(fileConfig).length > 0) {
      config = fileConfig;
      break;
    }
  }
  if (process.env.PUSHPLUS_NOTIFY_TOKEN) {
    config.token = process.env.PUSHPLUS_NOTIFY_TOKEN;
  }
  if (process.env.PUSHPLUS_TOKEN) {
    config.token = process.env.PUSHPLUS_TOKEN;
  }
  return config;
}

function inferEvent(args, hookInput) {
  if (args.event) {
    return args.event;
  }
  const hookEventName = args.hook || hookInput.hook_event_name || '';
  if (hookEventName === 'Stop') {
    return 'completed';
  }
  if (hookEventName === 'Notification') {
    const message = String(hookInput.message || '').toLowerCase();
    if (message.includes('permission') || message.includes('approve') || message.includes('approval')) {
      return 'permission';
    }
    return 'blocked';
  }
  return 'blocked';
}

function buildContent(event, args, hookInput) {
  const cwd = args.pwd || hookInput.cwd || process.cwd();
  const message = hookInput.message || '';
  const summary = args.summary || EVENT_TITLES_EN[event];
  const summaryZh = args.summaryZh || EVENT_TITLES_ZH[event];
  const details = args.details || message || `Claude Code hook event: ${hookInput.hook_event_name || args.hook || event}`;
  const detailsZh = args.detailsZh || (event === 'completed' ? 'Claude Code 当前轮次已经结束。' : 'Claude Code 会话需要你的关注。');

  const lines = [
    `**Event / 事件:** \`${event}\` / ${EVENT_LABELS_ZH[event]}`,
    `**Hook / 钩子:** \`${hookInput.hook_event_name || args.hook || 'unknown'}\``,
    `**Summary / 摘要 (EN):** ${summary}`,
    `**摘要 / Summary (ZH):** ${summaryZh}`,
    `**Time / 时间:** ${new Date().toISOString().slice(0, 19)}`,
    `**pwd / 工作目录:** \`${cwd}\``,
  ];

  if (hookInput.session_id) {
    lines.push(`**Session / 会话:** \`${hookInput.session_id}\``);
  }
  if (details) {
    lines.push('**Details / 详情 (EN):**', details);
  }
  if (detailsZh) {
    lines.push('**详情 / Details (ZH):**', detailsZh);
  }
  return lines.join('\n\n');
}

function redactPayload(payload) {
  return { ...payload, token: payload.token && payload.token !== 'DRY_RUN_TOKEN' ? 'REDACTED' : payload.token };
}

function postPayload(payload) {
  const body = Buffer.from(JSON.stringify(payload), 'utf8');
  return new Promise((resolve) => {
    const request = https.request(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': body.length,
      },
      timeout: 20000,
    }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let data = text;
        try {
          data = JSON.parse(text);
        } catch {}
        resolve({
          ok: response.statusCode === 200 && data && typeof data === 'object' && data.code === 200,
          http_status: response.statusCode,
          response: data,
        });
      });
    });
    request.on('timeout', () => request.destroy(new Error('request timed out')));
    request.on('error', (error) => resolve({ ok: false, http_status: null, response: error.message }));
    request.write(body);
    request.end();
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const hookInput = parseHookInput(readStdin());
  const event = inferEvent(args, hookInput);
  if (!Object.prototype.hasOwnProperty.call(EVENT_TITLES_EN, event)) {
    throw new Error(`Invalid event: ${event}`);
  }

  const config = loadConfig();
  const token = args.token || config.token;
  if (!token && !args.dryRun) {
    throw new Error('PushPlus token not found. Configure PUSHPLUS_TOKEN, PUSHPLUS_NOTIFY_TOKEN, or ~/.config/pushplus-turn-notify/config.json.');
  }

  const payload = {
    token: token || 'DRY_RUN_TOKEN',
    title: args.title || `${EVENT_TITLES_EN[event]} / ${EVENT_TITLES_ZH[event]}`,
    content: buildContent(event, args, hookInput),
    template: args.template || config.template || 'markdown',
  };
  const channel = args.channel || config.channel;
  const topic = args.topic || config.topic;
  if (channel) {
    payload.channel = channel;
  }
  if (topic) {
    payload.topic = topic;
  }

  if (args.dryRun) {
    console.log(JSON.stringify({ ok: true, dry_run: true, payload: redactPayload(payload) }, null, 2));
    return;
  }

  const result = await postPayload(payload);
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
