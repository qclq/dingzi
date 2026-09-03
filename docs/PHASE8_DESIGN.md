# Phase 8 完整联调、测试与性能优化设计

日期：2026-09-03  
状态：设计步骤完成，待用户查看；未进入实现或验证步骤。

## 范围

本阶段按照本轮指令，目标是把已有功能联调、测试、性能测量和安全检查串成可复现的验证闭环，不新增业务功能。用户本轮命名为 Phase 8，覆盖原计划中部分 Phase 9 联调内容；`PROJECT_STATUS.md` 的阶段描述在实现完成后统一更新，不以旧计划编号限制本轮范围。

联调主路径如下：

```text
管理员登录 → 配置发布 → Mock 图片 → 推理/判定 → 数据库 → WS → 历史/详情
→ Excel/PDF → 统计 → MES → 日志
```

并行验证 operator 能访问实时检测、历史、导出与统计，且对配置、用户、MES、日志写操作得到后端 403。前端路由隐藏不是权限验证的替代品。

## 现有实现与复用点

| 能力 | 已有实现 | Phase 8 验证方式 |
| --- | --- | --- |
| 认证/RBAC | `core/deps.py`、`services/auth.py`、`api/v1/me.py` | API 直接调用与路由守卫测试；admin/operator 各一组 |
| 配置版本 | `api/v1/configs.py`、`services/configuration.py` | 管理员草稿、校验、幂等发布；operator 403；检测快照冻结 |
| Mock 检测/WS | `services/realtime.py`、`api/v1/realtime.py`、`scripts/run_realtime_demo.py` | 临时图片触发、Snapshot、WS HELLO/FRAME/INFER/PONG、重复图片幂等 |
| 历史/导出 | detections、exports、`services/exports.py` | 过滤/详情、PDF/XLSX 生成、签名下载契约、导出权限 |
| 统计 | analytics 聚合、Redis 缓存降级 | API 口径、空数据、缓存可用/不可用、页面调用 |
| MES/日志/文件 | `models/system.py`、system API、tasks | MockMesClient 成功/失败/重试、审计脱敏、文件保留/配额；不把 Mock 当真实 MES 证明 |

已有 Phase 7 实现需要在本阶段重点复核的风险：密码重置接口当前仅创建令牌而未实际发送 SMTP 邮件；日志 CSV 当前同步生成而不是异步 `ExportJob`；Beat 调度是每 86400 秒，不是严格 Asia/Shanghai 02:00。它们会作为缺陷或限制由验证证据决定是否修复。

## 实现步骤

1. 新增可复用的端到端测试夹具：临时 SQLite、临时图片/导出目录、Mock MES HTTP 服务、受控 Redis 缺失降级。测试通过 HTTP 与 WebSocket 公共接口驱动，避免绕过 API 直接写库。
2. 补齐测试覆盖：用户操作、文件清理、MES 幂等/重试、日志 CSV、operator 越权、WS 完整消息流、XLSX/PDF 内容与历史/统计一致性。
3. 增加独立性能脚本：在临时 SQLite 生成 100,000 条数据，测量历史查询、统计查询和本进程 HTTP 延迟，输出 P50/P95、样本量、机器/数据库/并发信息。只有真实 MySQL + 50 并发结果才可判断正式性能目标是否达标。
4. 修复验证发现的具体问题，避免无关重构。
5. 生成 `docs/PERFORMANCE_REPORT.md` 和 `docs/SECURITY_CHECKLIST.md`；文档每个结论标记 `PASS`、`FAIL`、`PARTIAL` 或 `BLOCKED`，并给出命令、环境和证据边界。

## 验证矩阵

| 范围 | 目标 | 最低证据 |
| --- | --- | --- |
| 后端 | auth、RBAC、decision、history、analytics、config、MES、WS、exports、files | Ruff、全量 pytest、Phase 8 定向 pytest、迁移、Uvicorn API/WS 实测 |
| 前端 | typecheck、lint、build、unit tests | `vue-tsc -b`、ESLint 0 error、Vite build、Vitest；canvas 原生模块问题必须修复或明确阻断 |
| 性能 | API P95 ≤300ms、100k 历史 ≤1s、50 并发、WS ≤200ms | 单机 SQLite 仅作回归基线；真实 MySQL/Redis/容器结果才可标记 PASS |
| 安全 | 密钥、SQL/XSS、越权、日志与文件访问 | 仓库扫描、参数化 ORM、敏感字段响应检查、admin/operator/匿名直接 API 断言、签名 URL 与过期检查 |
| 基础设施 | MySQL、Redis、MinIO、Celery Worker/Beat、Nginx | Docker Compose 健康、在线 Alembic、真实队列/对象写入与权限；当前无 Docker CLI/运行时，标记 BLOCKED 直到环境可用 |

## 性能测量口径

- HTTP：预热后至少 100 次请求，P95 使用排序样本第 `ceil(n*0.95)` 位；分开记录应用进程内、SQLite、MySQL 容器、单用户和 50 并发。
- 历史：100,000 条检测数据，按真实页面索引和时间/result 过滤查询第 1 页及深页；记录总数、数据库、索引、连接池和序列化开销。
- WS：从服务端 broker 发布 FRAME/INFER 到客户端收到的单调时钟差，至少 100 条，记录 P95；本进程结果不能外推网络车间环境。
- 不在测试环境发送真实图片或 MES 请求；图片使用最小 mock 文件。

## 安全检查口径

- 扫描受版本管理文本中的 JWT、DB、MES、MinIO 凭据模式；`.env` 不输出、不读取到日志。
- 检查所有 SQL 使用 SQLAlchemy 参数化表达式，筛选关键词不拼接 SQL；对典型注入字符串进行 API 测试。
- 验证所有 Phase 7 写接口和配置/MES/日志接口的匿名 401、operator 403、admin 成功；验证被停用或凭据版本过期 token 被拒绝。
- 验证 MES Token 不出现在 GET 配置、审计、日志、CSV、错误响应或检测快照。
- 验证文件 URL 不接受跨检测路径替换；存储/MinIO 的真实签名及过期验证依赖可用基础设施。
- Vue 默认转义仍需针对日志/用户名/错误消息的渲染测试；不引入不可信 `v-html`。

## 当前环境阻断项

本机当前未发现 `docker`、`redis-cli` 或 MySQL/MinIO/MES 环境变量，故不能启动真实 Compose、执行 MySQL P95、50 并发容器压测、真实 Redis Pub/Sub、Celery Worker/Beat、MinIO 写入/签名或真实 SMTP/MES 联调。实现和验证阶段会继续探测安全可用路径；若未恢复，报告按 BLOCKED 记录，不用 SQLite、Mock 或单进程结果替代。

## 完成条件

修复发现的代码问题后，所有本地可执行后端/前端检查通过；性能和安全两份报告存在且结果可复现；真实基础设施每项有 PASS 证据或 BLOCKED 原因。完成本轮验证后停止，不自动进入下一阶段。
