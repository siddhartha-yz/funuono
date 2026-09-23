# 弗糯糯

QQ 群机器人维护仓库。NapCat 保持 QQ 登录，AstrBot 负责连接和插件生命周期；本仓库管理两个自研插件与部署流程。

| 目录 | 功能 |
| --- | --- |
| `plugins/nju_join_verifier` | 入群申请验证与自动通过 |
| `plugins/ostrakon` | reaction 投票触发群禁言 |
| `deploy/deployer.py` | 检查主分支 CI，更新插件并调用 AstrBot 热重载 |
| `deploy/astrbot` | 当前 AstrBot 部署文件与限流补丁的参考副本 |

## 修改和上线

1. 从 `main` 创建分支，修改插件并提交 Pull Request。
2. CI 检查两个插件。通过后合并到 `main`。
3. 服务器每分钟检查一次 `main`。只有提交来自已合并到 `main` 的 Pull Request，且该提交的 CI 成功后，部署器才更新插件并调用 AstrBot 的插件重载接口。
4. 部署失败时恢复旧插件目录并再次重载旧版本。部署记录留在服务器。

通常合并后约 1–3 分钟生效。插件重载期间对应插件可能短暂暂停处理事件；NapCat 不退出 QQ，两个容器不重启。

**不要把凭据、QQ群消息、学号、SQLite 数据库或 `.env` 提交到仓库。** 线上数据保留在 AstrBot 的 `data/` 中。仓库维护者提交的插件代码会在生产服务器执行，应只授予可信任的人写入权限。公开仓库的 `main` 已启用分支保护：必须通过 Pull Request 和 CI 才能合并；服务器也会验证部署提交对应已合并的 PR。

## 变更范围

`plugins/` 中的 Python 插件代码支持热更新。AstrBot 镜像、NapCat、Docker Compose、依赖安装和 `deploy/astrbot/rate_limit_stage.py` 的变更不自动上线；这些改动需要单独安排维护，部分改动可能需要重启 AstrBot。当前运行的限流补丁对应 AstrBot 4.27.3。

## 本地检查

```bash
python -m pip install 'pytest>=8,<9' 'pytest-asyncio>=0.24,<1' 'aiohttp>=3.9,<4' 'ruff==0.16.3'
cd plugins/ostrakon && ruff check main.py ostrakon tests deploy/astrbot/rate_limit_stage.py && python -m pytest -q
cd ../nju_join_verifier && ruff check main.py nju_join_verifier tests runtime_checks && python -m pytest -q
```

部署细节见 [`deploy/README.md`](deploy/README.md)。

