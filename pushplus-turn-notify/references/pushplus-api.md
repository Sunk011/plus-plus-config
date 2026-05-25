# PushPlus API Notes

The scripts send JSON to:

```text
https://www.pushplus.plus/send
```

Required field:

- `token`: PushPlus token.

Common optional fields:

- `title`: Notification title.
- `content`: Message body.
- `template`: Usually `markdown`, `html`, or `txt`; default is `markdown`.
- `channel`: Delivery channel such as `wechat`.
- `topic`: Optional group topic.

The response is expected to be JSON. Treat HTTP 200 plus PushPlus `code` 200 as success. If HTTP succeeds but `code` is not 200, report the PushPlus message and inspect token, channel, topic, and account status.

Keep scripts conservative:

- Do not log full tokens.
- Support dry-run payload output without token or network.
- Preserve non-200 HTTP responses in error output for troubleshooting.
