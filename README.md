# 定子冲片表面缺陷检测 Web 可视化系统

Phase 1 基础工程采用前后端分离：Vue 3 + TypeScript 前端、FastAPI + SQLAlchemy Async 后端，并预留实时网关、推理、判定、MES 和维护服务目录。

## 环境要求

- Node.js 22+、npm 10+
- Python 3.11+、uv
- Docker Engine 24+ 与 Docker Compose v2（完整容器启动）
- MySQL 8.0、Redis 7.x、MinIO（本地运行或 Compose）

## 环境变量

复制 `.env.example` 为 `.env`，按现场环境修改数据库、Redis、MinIO、JWT 和 CORS 配置。`JWT_SECRET_KEY` 必须使用至少 32 字节的随机值；缺失、过短或仍为示例占位值时后端会拒绝启动。前端可复制 `frontend/.env.example` 为 `frontend/.env`。

## 后端安装、迁移和启动

```powershell
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

健康检查：`GET http://localhost:8000/api/v1/health`。响应会分别报告 Web API、MySQL 和 Redis 状态；依赖未启动时返回 `degraded`。

## 前端安装和启动

```powershell
cd frontend
npm install
npm run dev
```

前端开发地址为 `http://localhost:5173`，构建命令为 `npm run build`。

## Docker Compose

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up --build -d
```

Nginx 入口为 `http://localhost`，API 通过 `/api/` 反向代理到 web-api。生产环境必须替换示例密码和 JWT 密钥，并接入 HTTPS/WSS。

## 测试与代码质量

```powershell
cd backend
uv run pytest
uv run ruff check app tests

cd ..\frontend
npm run lint
npm run build
npm run test
```

Phase 1 只提供基础元信息接口和依赖健康检查；业务功能按 `docs/REQUIREMENTS_TRACEABILITY.md` 在后续阶段实现。禁止使用 `Base.metadata.create_all()`，正式数据库结构必须通过 Alembic 迁移管理。

## Phase 2 认证与管理员初始化

后端提供 `/api/v1/auth/login`、`/refresh`、`/logout`、`/api/v1/me` 和 `/api/v1/me/menus`。管理员初始化不使用固定密码：

```powershell
$env:INIT_ADMIN_USERNAME = "your-admin"
$env:INIT_ADMIN_PASSWORD = "Use-A-Strong-Password1!"
uv run python scripts/init_admin.py
```

密码必须至少 8 位并同时包含大小写字母、数字和特殊字符。认证使用 HS256 JWT（access 8 小时、refresh 7 天），连续 5 次登录失败锁定 30 分钟。
