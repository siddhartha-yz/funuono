# AstrBot latency patch

AstrBot 4.27.3 runs `RateLimitStage` before plugin handlers. With the default
`stall` strategy, busy group traffic can therefore delay both Ostrakon reaction
notices and administrator commands before Ostrakon itself gets a chance to process
them.

`rate_limit_stage.py` is a narrow override of AstrBot's built-in rate-limit stage.
It bypasses chat throttling only for:

- OneBot `group_msg_emoji_like` notices;
- `/ostrakon status`;
- `/ostrakon reset`.

All ordinary messages keep AstrBot's configured rate limit.

## Docker Compose

Set `OSTRAKON_REPO` to the absolute path of this repository and add the example
override when starting AstrBot:

```bash
export OSTRAKON_REPO=/absolute/path/to/ostrakon
docker compose \
  -f compose.yaml \
  -f "$OSTRAKON_REPO/deploy/astrbot/compose.override.example.yaml" \
  up -d --force-recreate astrbot
```

The override bind-mounts the repository copy of the patch directly into the
container, so the running deployment and Git source cannot silently drift apart.

## Compatibility

This override patches an AstrBot internal module and is validated against
**AstrBot 4.27.3**. Before upgrading AstrBot, compare the new upstream
`astrbot/core/pipeline/rate_limit_check/stage.py` with this file and re-run the
test suite. Remove this override if AstrBot gains an upstream mechanism for
excluding moderation/control events from chat throttling.
