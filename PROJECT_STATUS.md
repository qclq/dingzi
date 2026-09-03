# 项目进度

> 项目：定子冲片表面缺陷检测 Web 可视化系统  
> 更新日期：2026-09-03  
> 状态规则：未构建、未测试或未启动验证的功能不得标记 `DONE`。

## 总览

| 阶段 | 目标 | 状态 |
| --- | --- | --- |
| Phase 0 | 需求分析与项目规划 | DONE |
| Phase 1 | 基础工程与运行底座 | IN_PROGRESS |
| Phase 2 | 登录、JWT 与 RBAC | DONE |
| Phase 3 | 实时检测完整闭环 | DONE |
| Phase 4 | 历史记录、详情、文件与异步导出 | DONE |
| Phase 5 | 统计分析与车间大屏 | IN_PROGRESS |
| Phase 6 | 六类参数配置与版本管理 | TESTED |
| Phase 7 | 用户、日志、MES、文件策略 | IN_PROGRESS |
| Phase 8 | 完整联调、测试与性能优化 | IN_PROGRESS |
| Phase 9 | 生产部署与最终验收（含原 Phase 10 交付范围） | PARTIAL：验证完成；前端 Vitest 与 Docker/真实基础设施验收 BLOCKED |

## Phase 9 当前步骤（2026-09-03）

- 本轮用户指定 Phase 9 为最终阶段，按“设计 → 实现 → 验证”推进，每一步结束后停下供用户查看。
- 已检查现有 Compose/Dockerfile/Nginx、迁移/初始化、推理/实时、文件、MES 与验收文档，形成 `docs/PHASE9_DESIGN.md`。
- 已完成本机验证并形成 `docs/PHASE9_VALIDATION_REPORT.md`：后端 Ruff/pytest 32/32、SQLite 迁移与 Uvicorn API smoke 通过，前端 lint/build 通过。
- 前端 Vitest 被本机缺失 `canvas.node` 阻断；Docker CLI/Engine 不可用，Compose、MySQL、Redis、MinIO、Celery、Nginx 和真实基础设施验证均未执行，不得标记最终交付完成。
- 本轮 PATH、默认安装目录及 Windows 服务探测未发现 Docker；前端 canvas 原生模块缺失。下文旧阶段的环境描述是历史记录，不代表当前可用状态。
- 现有关键交付缺口：API/网关双副本、独立推理入口、跨进程 WS、MinIO 实际文件链路、幂等初始化、MES outbox 调度、真实图片显示及矩阵证据同步。
- 原 Phase 9/10 清单保留供最终核验，统一纳入本轮 Phase 9；未经核验的旧阶段勾选或 DONE 不自动视为生产验收通过。

## Phase 0：需求分析与项目规划

- [x] 定位并原样复制两份正式 Word 到 `docs/`。
- [x] 完整提取并核对需求说明书正文、表格、页眉页脚和 FR。
- [x] 完整提取并核对设计方案正文、表格、REST、WebSocket、数据库、部署和验收章节。
- [x] 读取 `docx/总结文档.md` 作为辅助索引，并以 Word 原文复核。
- [x] 创建 `docs/PROJECT_ANALYSIS.md`。
- [x] 创建 `docs/REQUIREMENTS_TRACEABILITY.md`，收录 79 个显式 FR。
- [x] 创建 `docs/OPEN_QUESTIONS.md`，冲突不做静默裁决。
- [x] 创建 `PROJECT_STATUS.md` 和 Phase 0～9 计划。
- [x] 执行阶段文件结构、FR 唯一性、计数和关键章节完整性检查。
- [x] 完成 Phase 0 交付复核并将本阶段标记 DONE。

## Phase 1：基础工程、数据库、认证与 RBAC

- [x] 建立前后端分离目录、依赖清单、严格 TypeScript、ESLint、Router、Pinia、Axios 和 Element Plus。
- [x] 建立 FastAPI 分层骨架、SQLAlchemy Async、Alembic、JWT 依赖、Celery 应用入口。
- [x] 建立 Docker Compose、Nginx、MySQL、Redis、Celery Worker、MinIO 和环境变量模板。
- [x] 增加 `GET /api/v1/health`，检查 Web API、MySQL 和 Redis。
- [x] 完成前端 lint/build/test、后端 Ruff/pytest、API 根路径/健康端点和 Compose 配置验证。
- [ ] 在 Docker Desktop 启动后运行 Compose 全栈。
- [ ] 在 MySQL/Redis 可用后执行在线 `alembic upgrade head`。

- [ ] 冻结 Phase 1 相关开放问题和 OpenAPI 基线。
- [ ] 初始化 Vue 3 + TypeScript + Vite + Element Plus 前端。
- [ ] 初始化 FastAPI + Pydantic v2 + SQLAlchemy Async + Alembic 后端。
- [ ] 建立 MySQL、Redis、MinIO、Nginx 和开发用 Docker Compose。
- [ ] 建立环境配置、密钥占位、健康检查、结构化日志和 trace_id。
- [ ] 建立核心数据库迁移、约束和索引。
- [ ] 实现 JWT 登录、刷新、退出、账号锁定和 bcrypt cost=12。
- [ ] 实现 admin/operator RBAC、动态菜单和前后端路由/接口权限。
- [ ] 编写单元、集成和 E2E 测试。
- [ ] 构建、测试、启动并修复全部错误。

## Phase 2：登录、JWT 与 RBAC

- [x] 实现登录、刷新、退出、`/me` 和动态菜单接口。
- [x] 实现 HS256 JWT（access 8 小时、refresh 7 天）及数据库 refresh token 轮换/撤销。
- [x] 实现 bcrypt cost=12、密码策略、连续 5 次失败锁定 30 分钟。
- [x] 实现 admin/operator 后端 RBAC、管理员接口 403 校验和前端路由/菜单控制。
- [x] 实现 Axios 自动注入、401 单次刷新、刷新失败跳转登录。
- [x] 完成 14 项后端测试、13 项前端测试及前端 lint/build。
- [x] 提供 `backend/scripts/init_admin.py` 环境变量初始化管理员方式。

验证记录：后端 `ruff` 通过，pytest 14/14 通过；前端 lint（0 error）、build、Vitest 13/13 通过。前端测试覆盖匿名路由拦截、RBAC、登录持久化、动态菜单、Authorization 注入和并发 401 单次刷新。
## Phase 3：实时检测闭环

- [ ] 实现共享目录和 watchdog 图片接入。
- [ ] 实现 inference-service 模型加载、推理、超时和热更新骨架。
- [ ] 实现 decision-service 分级、数量规则、PASS/NG 和配置快照。
- [ ] 实现检测、文件、缺陷的事务落库。
- [ ] 实现 realtime-gateway、心跳、序列号、去重和断线恢复。
- [ ] 实现 frame/infer/device/alert 消息和首屏 snapshot。
- [ ] 实现实时图像、Fabric.js 标注、产品信息、设备状态和告警页面。
- [ ] 完成真实后端与前端联调。
- [ ] 构建、测试、启动、故障注入并修复错误。

## Phase 4：历史、详情与文件导出

- [x] 实现历史服务端分页、时间/PASS-NG/操作员/图片编号/产线筛选、倒序排序和索引。
- [x] 实现历史列表、详情、缺陷标注、原始 JSON、模型/配置版本、MES 状态和工单关联。
- [x] 实现图片、JSON 和导出报告的短时签名 URL。
- [x] 实现 Excel/PDF Celery 异步导出、任务进度、失败状态和 24h 下载。
- [x] 实现每批 1,000 条的大数据导出读取并完成多批次测试。
- [x] 完成前后端联调和 10 万条数据库分页索引基准。
- [x] 完成 lint、构建、测试、迁移和真实进程验证并修复错误。

验证记录：后端 Ruff 通过、pytest 22/22 通过；前端 lint 0 error、build 通过、Vitest 14/14 通过。临时 SQLite 在线迁移至 `0005_history_fr_completion`，Uvicorn 实测登录、历史分页、详情、签名 URL 和导出 202 响应；10 万条基准使用复合覆盖索引，50,000 条 NG 结果深分页查询耗时约 3.3ms。

## Phase 5：统计分析与大屏

- [x] 冻结缺陷率口径为 NG 检测记录数/检测总数，记录统计路径与热力图映射决策。
- [x] 实现按小时聚合、Celery 历史回填任务与 Redis 60s 缓存降级。
- [x] 实现概览、类型对比、趋势、类型×等级分布和 360°热力图 API。
- [x] 实现 ECharts 图表、时间筛选、自动刷新、CSV 导出和 1080p 大屏。
- [x] 验证统计口径、空数据、自定义时间范围、UTC/SQLite 时区归一化和聚合查询。
- [x] 完成 Ruff、pytest、Alembic 离线 SQL/SQLite 在线迁移、ESLint、Vitest、Vite build 和 Uvicorn 验证；MySQL/Redis/Celery/MinIO 容器联调仍待基础设施可用后复验。

验证记录：后端 Ruff 通过、pytest 25/25 通过；Alembic 离线 SQL 和临时 SQLite 在线迁移均到达
`0006_analytics_aggregates`。前端 ESLint 为 0 error（保留既有模板格式 warning）、Vitest 16/16
通过、Vite build 通过。Uvicorn 实测服务启动，OpenAPI 暴露全部统计接口。

## Phase 6：参数配置与版本管理

- [x] 实现缺陷阈值配置。
- [x] 实现图片合格判定规则配置。
- [x] 实现最多 8 个 ROI 及像素/mm 转换。
- [x] 实现像素标定和参考图验证。
- [x] 实现相机/光源多方案及热切换。
- [x] 实现模型置信度、NMS 和 CPU/GPU 配置。
- [x] 实现草稿、校验、发布、恢复默认、回滚和不可变版本。
- [x] 实现写操作二次确认及完整审计。
- [x] 构建、测试、启动并验证历史结果可重现。

验证记录：后端 Ruff 通过、pytest 28/28 通过（含配置版本不可变、历史检测快照、RBAC、审计、幂等与回滚）；临时 SQLite 从空库在线迁移至 `0007_configuration_versions`，并验证配置表/检测快照/审计版本列。前端 Vitest 16/16、ESLint 0 error、Vite build 通过。Uvicorn 实测启动，`/api/v1/health` 数据库状态正常，OpenAPI 暴露全部配置接口；Redis 未启动时健康状态为 degraded，属于本地基础设施未配置而非应用错误。

## Phase 7：系统管理与 MES

- [ ] 实现用户增删改、启停、解锁和密码重置。
- [ ] 实现操作日志、系统日志、筛选、全文搜索和 CSV 导出。
- [ ] 实现 MES 配置、连接测试、异步上报、幂等、重试和人工补报。
- [ ] 实现外部告警渠道（待确认）。
- [ ] 实现文件保留、配额、02:00 清理、预警和清理审计。
- [ ] 构建、测试、启动并完成 MES 模拟联调。

## Phase 8：安全、监控、备份与运维

- [ ] 配置 HTTPS/WSS、TLS 1.2+ 和内网证书。
- [ ] 完成 JWT/数据库/MES 等密钥管理和仓库泄漏扫描。
- [ ] 完成 SQL 注入、XSS、CSRF、限流、上传和逐接口权限测试。
- [ ] 配置 Prometheus、Grafana、ELK/日志采集和告警规则。
- [ ] 实现存活/就绪检查、优雅停机和服务故障摘除。
- [ ] 配置 MySQL 5 分钟增量、每日全量及文件/配置备份。
- [ ] 编写并验证恢复 SOP，完成备份恢复演练。

## Phase 9：全链路验证

- [ ] 执行全部单元、集成、契约和 E2E 测试。
- [ ] 执行 50 并发、API P95、WS 延迟、实时页 FPS 和 10 万条查询压测。
- [ ] 执行连续 100 张推理测试及 AI 独立验收集评测。
- [ ] 演练断网、相机断开、推理超时、MES 失败、服务重启和磁盘满。
- [ ] 验证 RTO≤30 分钟、RPO≤5 分钟和关键服务冗余。
- [ ] 修复全部阻断/严重缺陷并形成测试报告。

## Phase 10：验收与交付

- [ ] 逐项关闭或形成书面豁免的开放问题。
- [ ] 逐项核对 79 个 FR 的实现、接口、数据库和测试证据。
- [ ] 生成 OpenAPI、ER 图、配置字典、协议和部署文件。
- [ ] 完成运维手册、备份恢复、故障处理、用户手册和 FAQ。
- [ ] 完成培训材料和操作演示。
- [ ] 完成客户验收、版本冻结、归档和投产检查。

## 当前阻塞项

- 本机 Docker CLI 可用但 Docker Desktop Linux 引擎未运行，`docker compose up --build -d` 无法连接 daemon。
- 本机 MySQL/Redis 未提供可用运行时；健康检查正确返回 `degraded`，在线迁移无法完成。
- 当前环境为 32 位 Python 3.14；已将 `python-jose[cryptography]` 替换为 PyJWT，避免无法构建 cryptography。

- `docs/OPEN_QUESTIONS.md` 中的接口、判定边界、枚举、阈值结构和安全策略问题必须在对应开发前冻结。
- AI 漏检率/误检率缺少可执行验收方案。
- 文档视觉渲染工具缺少 LibreOffice/soffice；本阶段已完成结构化全文核对，但未完成 DOCX 逐页 PNG 视觉 QA。




