# 定子冲片表面缺陷检测 Web 可视化系统

面向定子冲片表面缺陷检测现场的 Web 系统。项目由 Vue 3 前端、FastAPI 异步 API、MySQL、Redis/Celery、MinIO 和 Nginx 组成，涵盖登录与权限、实时事件、历史追溯、异步导出、统计、配置版本和系统管理/MES Mock。

当前状态为 **Phase 9 / PARTIAL**。Docker 基础服务、MySQL 迁移和 API smoke 已验证通过；真实推理、工业相机、HTTPS/WSS、双 API/实时网关、MinIO 文件闭环、性能压测和备份恢复仍未完成正式验收。以 [Phase 9 验证报告](docs/PHASE9_VALIDATION_REPORT.md) 和 [需求追踪矩阵](docs/REQUIREMENTS_TRACEABILITY.md) 为准。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia、ECharts、Fabric.js
- 后端：FastAPI、SQLAlchemy Async、Alembic、Pydantic Settings、PyJWT
- 基础设施：MySQL 8、Redis 7、Celery、MinIO、Docker Compose、Nginx

## 已实现范围

- JWT 登录、刷新/退出、管理员/操作员 RBAC、账号锁定和审计记录。
- 实时快照与鉴权 WebSocket；开发脚本可以生成 PASS/NG Mock 图片事件。
- 历史分页/筛选/详情、文件签名 URL、MES 工单关联和异步 Excel/PDF 导出。
- 统计概览、趋势、缺陷分布与热力图；配置草稿、发布、回滚和检测配置快照。
- 用户、日志、MES Mock、文件策略和定时维护任务。

## 目录

```text
backend/                 FastAPI、Alembic、Celery 与初始化/Mock 脚本
frontend/                Vue 前端
deploy/nginx.conf        Compose 使用的 Nginx 配置
docs/                    需求、设计、追踪矩阵与验证记录
services/                后续独立服务的预留目录
docker-compose.yml       本地/演示环境 Compose 编排
.env.example             不含真实密钥的环境变量模板
```

## 环境要求

- Docker Desktop（Linux Engine）与 Docker Compose v2
- 宿主机开发时：Node.js 22+、npm 10+、Python 3.11+、uv

当前 Compose 已在 Windows Docker Desktop 4.87.0 / Docker Engine 29.7.2 上构建并启动验证。

## Docker Compose 启动

1. 创建本地环境文件，`.env` 不得提交。

   ```powershell
   Copy-Item .env.example .env
   ```

2. 在 `.env` 中替换所有示例密码，并设置长度至少 32 字节的随机 `JWT_SECRET_KEY`。后端会拒绝示例占位符、缺失或过短的密钥。

3. 检查并启动：

   ```powershell
   docker compose config --quiet
   docker compose up -d --build
   ```

4. 首次部署及每次包含迁移的升级后执行：

   ```powershell
   docker compose run --rm web-api alembic upgrade head
   ```

5. 检查服务和 API：

   ```powershell
   docker compose ps
   Invoke-WebRequest http://localhost/api/v1/health
   ```

| 服务 | 作用 | 访问方式 |
| --- | --- | --- |
| `nginx` | 前端与 `/api/` 反向代理入口 | `http://localhost` |
| `frontend` | Vue 静态站点 | 由 Nginx 转发 |
| `web-api` | FastAPI 应用 | 由 Nginx 转发 |
| `mysql` | 业务数据库 | Compose 内部网络 |
| `redis` | 缓存和 Celery broker/result backend | Compose 内部网络 |
| `celery-worker` | 导出、MES 和维护异步任务 | Compose 内部网络 |
| `celery-beat` | 定时任务调度 | Compose 内部网络 |
| `minio` | 对象存储 | `http://localhost:9000`；控制台 `http://localhost:9001` |

停止服务：

```powershell
docker compose down
```

`docker compose down -v` 会删除 MySQL、Redis 和 MinIO 本地卷，只能在确认无需保留数据时使用。

## 管理员初始化

脚本位于 `backend/scripts/init_admin.py`，没有固定账号或密码。它从环境变量读取管理员信息，重复执行会更新同名管理员。

```powershell
cd backend
$env:INIT_ADMIN_USERNAME = "admin"
$env:INIT_ADMIN_PASSWORD = "Change-This-Strong-Password1!"
$env:INIT_ADMIN_DISPLAY_NAME = "系统管理员"
$env:INIT_ADMIN_EMAIL = "admin@example.invalid"
uv run python scripts/init_admin.py
```

脚本必须在能够连接目标数据库的后端运行环境中执行。密码至少 8 位，并同时含大写字母、小写字母、数字和特殊字符。

## 本地开发

后端：

```powershell
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

开发前端地址为 `http://localhost:5173`，本地 OpenAPI 文档为 `http://localhost:8000/docs`。容器入口下 API 为 `http://localhost/api/`。

## Mock 实时演示

开发脚本会生成 1×1 PNG 模拟图片：每四张为一张 NG，其余为 PASS；随后监听待处理目录、走 Mock 推理/判定路径、写入数据库并发布实时事件。

```powershell
cd backend
$env:INFERENCE_MODE = "mock"
$env:IMAGE_PENDING_DIR = "E:\\dingzi-demo\\pending"
$env:MOCK_IMAGE_INTERVAL_SECONDS = "3"
uv run python scripts/run_realtime_demo.py
```

该脚本不是独立推理容器或真实工业相机集成。真实模型、相机和 MES 的接口、阈值、设备协议与安全策略应先按 [开放问题](docs/OPEN_QUESTIONS.md) 冻结。

## API 与 WebSocket

OpenAPI 是完整契约来源：本地为 `/docs`，容器入口为 `http://localhost/api/docs`。

| 模块 | 路径 | 说明 |
| --- | --- | --- |
| 健康检查 | `GET /api/v1/health` | API、数据库与 Redis 状态 |
| 认证 | `/api/v1/auth/*` | 登录、刷新、退出、密码重置确认 |
| 当前用户 | `/api/v1/me`、`/api/v1/me/menus` | 用户信息和角色菜单 |
| 实时 | `GET /api/v1/realtime/snapshot`、`/ws/realtime` | 快照和鉴权 WebSocket |
| 检测/导出 | `/api/v1/detections/*`、`/api/v1/exports/*` | 历史、详情、文件 URL、MES 工单和导出 |
| 分析 | `/api/v1/analytics/*` | 概览、趋势、分布和热力图 |
| 配置 | `/api/v1/configs/*` | 草稿、校验、发布、版本和回滚 |
| 系统管理 | `/api/v1/system/*` | 用户、日志、MES Mock 和文件策略 |

实时连接需要 `access_token` 查询参数：

```text
ws://localhost/ws/realtime?line_id=line-1&access_token=<access-token>
```

客户端可发送 `PING`，服务端回复 `PONG`；连接成功后服务端先发送 `HELLO` 与实时快照。生产 WSS 尚未验收。

## 验证命令

```powershell
# 后端
cd backend
uv run ruff check app tests scripts alembic
uv run pytest

# 前端
cd ..\\frontend
npm run lint
npm run build
npm run test

# Compose
cd ..
docker compose config --quiet
```

已通过：后端 Ruff、`pytest`（32 passed）、前端 lint/build、SQLite 与 Docker MySQL Alembic 升级、Docker 镜像构建、容器 Redis PING、Nginx 前端响应及 `/api/v1/health`。本机前端 Vitest 因缺少 `canvas.node` 仍被阻断，不能标记为通过。

## 配置与安全

- `.env.example` 只含占位符；不要提交 `.env`、数据库密码、JWT、MES 凭据或生产对象存储密钥。
- 数据库结构只由 Alembic 管理；生产路径禁止使用 `Base.metadata.create_all()`。
- 部署前替换 MySQL、MinIO 和 JWT 示例值，并限制数据库与 MinIO 控制台网络访问。
- Nginx 当前提供 HTTP 和 `/api/` 代理；TLS 证书、HTTPS 与 WebSocket Upgrade 属于待完成的生产部署项。

## 文档

- [项目状态](PROJECT_STATUS.md)
- [Phase 9 设计](docs/PHASE9_DESIGN.md)
- [Phase 9 验证报告](docs/PHASE9_VALIDATION_REPORT.md)
- [需求追踪矩阵](docs/REQUIREMENTS_TRACEABILITY.md)
- [开放问题](docs/OPEN_QUESTIONS.md)
- [性能报告](docs/PERFORMANCE_REPORT.md)
