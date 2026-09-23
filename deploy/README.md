# 自动部署说明

服务器上的 `deploy/deployer.py` 由 ubuntu 用户每分钟运行一次。它从 `siddhartha-yz/funuono` 获取 `main` 的提交，检查该提交的 GitHub Actions `ci.yml` 是否成功，再将两个插件的已提交文件放入 AstrBot 的 `data/plugins/` 并通过只有 `plugin` 权限的 AstrBot API key 热重载。

部署器不读取或覆盖 `data/plugin_data/`、AstrBot 配置、NapCat 登录数据。首次迁移时会把旧插件目录移至 `~/.local/share/funuono/backups/`；后续每次部署也保留旧目录以供回退。

当前服务器依赖：

- `/home/ubuntu/.local/share/funuono/repo.git`：只读 Git 镜像。
- `/home/ubuntu/.config/funuono/astrbot-plugin.key`：仅具有 AstrBot `plugin` scope 的 API key，权限 `0600`。
- `/home/ubuntu/.local/lib/funuono/deployer.py`：部署器的安装副本。
- `/home/ubuntu/.local/share/funuono/deploy.log`：部署日志。
- 用户 crontab：每分钟调用部署器。

部署器自身、CI、Compose 或核心补丁的修改不会自动改变服务器上的部署器或运行中的 AstrBot 镜像。维护这些基础设施时应先检查差异，再单独更新。

手动运行一次检查（不触发容器重启）：

```bash
/usr/bin/python3 /home/ubuntu/.local/lib/funuono/deployer.py sync
```

如果某次部署失败，查看 `deploy.log` 和 AstrBot 日志。部署器会恢复旧目录；修复代码后重新合并即可重试。若需要固定回退到某个提交，在 GitHub 上 revert 相关提交并等待新 CI 通过。

