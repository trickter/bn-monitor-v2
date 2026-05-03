# Initial Database Schema

状态：done

## 目标

将 `rules/database-schema.md` 中确认的 MVP 表结构落为 SQLAlchemy models 与 Alembic 初始迁移，为后续采集、指标快照、告警落库和复盘查询提供稳定 schema 基础。

成功标准：

- `monitor.models.Base.metadata` 包含所有核心表。
- 每张表的主键、关键索引、枚举约束和 JSON payload 字段与规则文档一致。
- Alembic 初始迁移可创建 PostgreSQL / TimescaleDB 表结构。
- 大时序表迁移中包含 `create_hypertable(..., if_not_exists => TRUE)`。
- schema 测试覆盖核心表存在、关键列存在、唯一索引存在、hypertable 语句存在。

## 涉及变化

新增文件：

- `monitor/models.py`
- `monitor/db.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/0001_initial.py`
- `docs/database.md`
- `tests/test_schema.py`

依赖变化：

- 在 `pyproject.toml` 中加入 `SQLAlchemy`、`alembic`、`psycopg[binary]`。

## 实施步骤

1. 同步数据库文档，说明当前只提供 schema，不连接真实数据库。
2. 实现 SQLAlchemy declarative models。
3. 实现数据库 engine/session 帮助函数。
4. 新增 Alembic 配置和初始迁移。
5. 新增 schema 测试并运行 `python -m pytest`。

## 测试与验收

- `python -m pytest`
- `python -m monitor.cli healthcheck`

## 不做内容

- 不启动 TimescaleDB 容器。
- 不执行真实数据库迁移。
- 不实现 repository 写入逻辑。
- 不实现数据采集、指标计算、告警生成或查询 API。
