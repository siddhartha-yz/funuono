# MaiBot 群聊部署

这是 2026-10-26 从运行中的部署导出的脱敏配置快照；2026-10-27 已同步主名和人格自称“弗糯糯”。MaiBot 负责指定群的聊天，复用已有 NapCat QQ 登录；AstrBot 继续管理入群验证和投票禁言。MaiBot 配置不属于现有插件自动部署器的更新范围。

## 已配置能力

- MaiBot v1.3.15、官方统一 QQ 适配器 v1.1.9，镜像摘要和源码提交见 `PROVENANCE.json`。
- 主名“弗糯糯”，保留“大肥鱼 / 小鲸鱼”别名的基础人设，保留上游群聊与回复模板。这是自定义人设，不是“大肥鱼官方人格卡”。
- DeepSeek Flash 文本与图片理解、原生 `web_search` 和 `web_fetch`。
- A_Memorix 长期记忆、人物信息、聊天摘要、表达及黑话学习；未配置 embedding，向量检索不可用。
- 快照时启发式记忆已开启，跨聊天记忆关闭。群聊发言频率 0.4，私聊暂停回复。
- QQ 只允许配置的一个群，其他群和私聊被适配器策略拦截。管理操作、电脑控制、自动偷表情未启用。

`templates/` 保留完整设置和注释，只将账号、群号与凭据替换成变量。模型内部名称 `deepseek-v4-flash` 是任务引用名，实际 API 标识为 `deepseek-flash`。模板中的价格字段是统计配置，不保证等于供应商实时账单。

## 在新目录恢复

需要 Python 3.11+、Git、Docker Compose，以及已有的 NapCat 正向 WebSocket 服务。Compose 默认接入 `ostrakon_default` 网络，通过 `napcat:3001` 连接。先核对实际网络、服务名和端口；已有其他部署使用 `maibot-qq` 容器名时不要重复启动。

在仓库根目录运行：

```bash
python3 deploy/maibot/prepare.py /path/to/new-maibot --bot-qq BOT_QQ --group-id GROUP_ID
```

替换两个号码参数，脚本会隐藏输入 DeepSeek API key。也可通过 `DEEPSEEK_API_KEY` 环境变量提供；NapCat 有 token 时通过 `NAPCAT_TOKEN` 环境变量提供。不要把真实凭据写进仓库或命令行参数。

脚本拒绝覆盖任何已有目录，固定适配器提交，生成权限为 0600 的配置，不启动容器。`--config-only` 只用于离线配置检查，缺少适配器源码，不能直接运行 QQ bot。

审阅新目录中的配置、上游用户协议与隐私条款，再执行：

```bash
cd /path/to/new-maibot
docker compose config --quiet
docker compose build
docker compose up -d
```

Compose 保留当前部署的协议确认标记；实际启动代表你接受对应版本的条款。启动前关闭旧聊天框架在同一个群的 LLM 回复，避免双方重复回复。不要关闭仍在使用的群管理插件或 NapCat。

## 后台和维护

WebUI 仅发布到服务器回环地址。使用自己的 SSH 配置连接服务器：

```bash
ssh -N -L 18001:127.0.0.1:18001 SERVER
```

本机打开 <http://127.0.0.1:18001>。管理员登录令牌由运行时生成，保存在部署目录 `data/webui.json`；它不在本仓库内。

在部署目录使用 `docker compose ps` 查看状态、`docker compose logs --tail=100 maibot` 排障、`docker compose restart` 重启。日志可能包含群聊内容，不要公开上传。

后台修改只写入服务器，**不会自动同步到 GitHub**。需要备份新配置时，脱敏后更新本目录并走 PR；不要直接提交服务器的 `config/`、`data/`、`plugins/` 或日志。`data/` 包含记忆与数据库，必须另做私有备份，本仓库不能恢复历史记忆。

恢复配置前先私下备份现有配置和数据。若回退到 AstrBot 聊天，应先停止 MaiBot，再恢复原群配置；不要同时让两个聊天引擎处理该群。

## 验证边界

部署当天已验证真实 QQ 文本收发、记忆写入后重启仍可检索、真实视觉 API 与 WebUI 图片回复、原生联网搜索与网页读取。QQ 图片下载链路未单独完成端到端测试。此次 GitHub 同步仅归档部署，未重启或覆盖运行中的 MaiBot。

本目录的离线检查会验证模板可解析、凭据变量替换及转义、目录覆盖保护、白名单和 WebUI 绑定。它不调用付费 API，也不向 QQ 群发消息。

## 上游来源

配置模板派生自 [MaiBot](https://github.com/Mai-with-u/MaiBot) v1.3.15，遵循上游 GPL-3.0，许可证副本为 `LICENSE-MaiBot`。QQ 适配器从 [MaiBot-SnowLuma-Adapter](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter) 的固定提交下载，保留其上游许可文件；此仓库不复制适配器源码。
