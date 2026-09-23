# 当前 AstrBot 部署

`compose.yaml` 是线上 Compose 文件的受版本管理副本，用于审阅与恢复。补丁来源指向本单仓库的 `plugins/ostrakon/deploy/astrbot/rate_limit_stage.py`。修改 Compose 文件不会改变已运行容器的现有挂载；下次重新创建 AstrBot 容器时才采用新路径。

`plugins/ostrakon/deploy/astrbot/rate_limit_stage.py` 是仓库中的补丁源码。AstrBot 核心补丁不能通过插件重载更新。更改 Compose、镜像或补丁时，先核对运行版本并安排单独的维护操作；不要把这些变更当作插件热更新。

线上 `.env`、AstrBot `data/` 和 NapCat QQ 登录数据只保存在服务器，不进 Git。
