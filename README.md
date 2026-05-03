# bn-monitor-v2

币安 USD-M Futures 二级市场 altcoin 异动监控告警系统。

当前实现进度：

- 工程骨架
- 显式 `.env` 配置校验
- Discord 投递资格判断
- `healthcheck` / `config-dump` CLI

## 本地验证

```bash
python -m pytest
python -m monitor.cli healthcheck
python -m monitor.cli config-dump
```

配置说明见 `docs/configuration.md`。

