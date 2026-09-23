# 当前 AstrBot 部署

`compose.yaml` 是 2026-09-23 运行中 Compose 配置的快照，用于审阅与灾难恢复。它仍引用服务器上原 Ostrakon 仓库中的限流补丁；当前容器已经把该文件挂载进来。

`plugins/ostrakon/deploy/astrbot/rate_limit_stage.py` 是仓库中的补丁源码。AstrBot 核心补丁不能通过插件重载更新。更改 Compose、镜像或补丁时，先核对运行版本并安排单独的维护操作；不要把这些变更当作插件热更新。

线上 `.env`、AstrBot `data/` 和 NapCat QQ 登录数据只保存在服务器，不进 Git。
