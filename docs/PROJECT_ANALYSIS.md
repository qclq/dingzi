# 定子冲片表面缺陷检测 Web 可视化系统项目分析

> 阶段：Phase 0 需求分析与项目规划  
> 正式依据：系统需求说明书 v1.0、Web 可视化系统设计方案 V1.1  
> 规则：需求说明书决定“做什么”，设计方案决定“怎么做”；未决冲突见 `OPEN_QUESTIONS.md`。

## 1. 项目背景

东方电气定子冲片在冲压、转运、叠片过程中可能产生划痕、点蚀等表面缺陷。现有人工目检约为 3～4 片/分钟，存在节拍不足、判断受疲劳和经验影响、纸质记录难追溯、检测数据无法沉淀用于工艺改进等问题。

项目建设一套支持 7×24 小时运行的自动检测系统，将工业相机采图、AI 推理、缺陷分类分级、PASS/NG 判定、数据落库、Web 实时展示、MES 上报、历史追溯和统计分析形成闭环。

## 2. 项目目标

- 对每张检测图片形成可追溯记录：图片编号、检测时间、操作员、原图、缺陷结果、模型版本、配置版本、MES 上报状态。
- 单张推理耗时不超过 5 秒；1 mm 以上缺陷漏检率不超过 0.5%；误判 NG 比例不超过 3%。
- WebSocket 端到端延迟不超过 200 ms，HTTP API P95 不超过 300 ms。
- 10 万条历史记录分页查询不超过 1 秒，支持至少 50 个并发用户。
- 数据不出厂，配置和模型版本可追溯，支持审计、备份恢复及扩展。

## 3. 系统边界

### 3.1 系统内

- 工业相机和光源系统集成及设备适配器接入。
- 图片接入、AI 推理结果处理、缺陷分类分级和 PASS/NG 判定。
- 实时检测、历史记录、详情、导出、统计和车间大屏。
- 缺陷阈值、判定规则、ROI、像素标定、相机/光源方案、模型参数配置。
- 用户、权限、日志、MES、文件策略、监控、备份和运维。

### 3.2 系统外

- 冲压工艺流程控制。
- 厂级生产调度和 ERP/MES 自身业务。
- 定子装配、绕组、绝缘等后续工序。
- 相机、光源底层驱动开发是否在范围内尚未冻结，见 `OPEN_QUESTIONS.md`。

## 4. 用户角色

| 角色 | 系统值 | 职责与权限 |
| --- | --- | --- |
| 管理员 | `admin` | 拥有实时、历史、统计、导出权限，并负责全部参数配置、用户管理、日志审计、MES 和文件策略。 |
| 操作员 | `operator` | 日常检测、实时查看、历史查询、详情查看、统计分析和数据导出；无配置和系统管理权限。 |

权限采用 RBAC。前端按角色生成菜单、路由和按钮，后端逐接口校验；前端隐藏不能替代后端鉴权。

## 5. 完整功能模块

需求说明书定义 6 个一级模块，共拆分为 19 个可交付功能域：

1. 登录与权限：登录、刷新、退出、动态菜单、路由守卫、账号锁定、安全审计。
2. 实时检测：图像与标注、产品信息、设备状态、异常告警。
3. 历史记录与详情：历史列表、检测详情、Excel/PDF/图片/JSON 导出。
4. 数据统计分析：概览卡片、柱状图、趋势图、热力图、饼图、1080p 大屏。
5. 参数配置：缺陷阈值、合格判定、ROI、像素标定、相机/光源方案、模型参数。
6. 系统管理：用户管理、日志中心、MES 配置、文件策略。

所有模块必须同时具备真实后端、持久化或真实服务调用、前端页面和联调测试。

## 6. 核心业务流程

```text
相机拍照
  -> 图片写入共享待检测目录
  -> inference-service 通过 watchdog 发现文件并推理
  -> decision-service 绑定当前配置版本并计算 PASS/NG
  -> 检测主记录、缺陷明细、文件元数据在同一事务落库
  -> 原图/结果图归档到 MinIO 或本地 NAS
  -> realtime-gateway 推送 frame/infer/device/alert
  -> Web 实时展示
  -> mes-adapter 异步、幂等上报 MES
  -> 历史查询、统计聚合、报表导出和审计
```

MES 上报失败不得回滚检测记录；推理服务重启后应继续处理待检测文件；重连 WebSocket 后通过实时快照恢复当前状态而不重放全部历史。

## 7. 缺陷类型

正式需求只允许两类缺陷：

| 中文 | 枚举 | 显示颜色 |
| --- | --- | --- |
| 划痕 | `scratch` | `#FAAD14` 橙色 |
| 点蚀 | `pitted_surface` | `#36CFC9` 青色 |

文档中“麻点腐蚀”“腐蚀”及 CSS 变量 `defect-stain` 的混用不得直接带入代码，待确认统一术语。

## 8. 缺陷等级

| 中文 | 枚举 | 含义 |
| --- | --- | --- |
| 轻微 | `minor` | 缺陷尺寸小于或等于已发布阈值。 |
| 严重 | `severe` | 缺陷尺寸大于已发布阈值。 |

阈值单位为 mm，输入范围 0～100，保留两位小数。用于分级的具体尺寸维度（长度、宽度、高度、最大边或面积）尚未明确。

## 9. PASS/NG 判定规则

总结果仅二级，不存在“待复核”：页面/外部接口使用 `PASS | NG`；文档算法内部另出现 `ok | ng`，映射待冻结。

默认业务算法：

1. 收集一张图片的全部 `defects[]`。
2. 按 `(type × level)` 分组计数。
3. 任一启用数量规则触发时判定 NG。
4. 若数量规则未触发但存在任意 `severe` 缺陷，仍判定 NG。
5. 其余判定 PASS。

| 类型 | 等级 | 默认触发数量 |
| --- | --- | ---: |
| 划痕 | 严重 | ≥ 1 |
| 划痕 | 轻微 | ≥ 5 |
| 点蚀 | 严重 | ≥ 4 |
| 点蚀 | 轻微 | ≥ 9 |

“达到上限”与“超过上限”存在冲突；开发前必须确定使用 `count >= max_count` 还是 `count > max_count`。

## 10. REST API 概要

### 10.1 通用约定

- 前缀 `/api/v1`，JSON 使用 `snake_case`，时间使用带时区 ISO 8601。
- 分页结构：`items`、`total`、`page`、`page_size`。
- 错误结构：`code`、`message`、`details`、`trace_id`。
- 配置发布、MES 上报和导出创建使用 `Idempotency-Key`。
- 大文件仅返回 24 小时短时签名 URL，API 不直接传输大文件。

### 10.2 已定义接口域

| 域 | 代表接口（冲突路径以 OPEN_QUESTIONS 为准） |
| --- | --- |
| 认证 | `POST /auth/login`、`POST /auth/refresh`、`POST /auth/logout` |
| 当前用户 | `GET /me`、`GET /me/menus` |
| 实时 | `GET /realtime/snapshot`、`GET /device/status` |
| 历史 | `GET /detections`/`GET /history/records`、详情、文件签名 URL |
| 导出 | `POST /exports`/`POST /history/export/excel`、任务状态查询 |
| 统计 | `GET /analytics/overview`、趋势、分布、热力图 |
| 配置 | `/configs/{type}` 或 `/config/current|update|versions` |
| 系统 | 用户、审计日志、MES 连接测试、人工补报 |

接口总表和详细章节存在多处不一致，在 Q001～Q004 冻结前不得自行选择。

## 11. WebSocket 协议概要

- 连接：`wss://{host}/ws/realtime?line_id={line_id}&access_token={token}`。
- 公共字段：`type`、`event_id`、`sequence`、`occurred_at`、`data`。
- 系统消息：`hello`、`ping`、`pong`、`error`。
- 业务消息：`frame`、`infer`、`device`、`alert`。
- 心跳：客户端每 20 秒发送 `ping`；60 秒未收到心跳，服务端断开。
- 重连：1 秒起步的指数退避，最大 30 秒；重连后调用 `/api/v1/realtime/snapshot`。
- 去重：客户端依据单调递增的 `sequence` 去重，告警另以 `alert_id` 去重。
- 优先级：ERROR/ALERT 最高，DEVICE/INFER 中等，FRAME 最低且弱网可丢弃。
- 目标频率：frame 约 1.5 秒/帧，infer 约 1.7 秒/次，device 约 2 秒/次，alert 触发即发。

告警字段、等级和 DEVICE 指标在不同章节不一致，必须先冻结协议。

## 12. 数据库核心实体

| 实体 | 主要用途 | 核心字段/约束 |
| --- | --- | --- |
| `users` | 用户与角色 | username 唯一，password_hash，role，status |
| `refresh_tokens` | 刷新令牌吊销 | user_id，jti_hash，expires_at |
| `detections` | 检测主记录 | image_id，detected_at，operator_id，result，defect_count，配置/模型版本 |
| `detection_files` | 原图、结果图、报告 | detection_id，kind，uri，sha256，size_bytes |
| `defects` | 缺陷明细 | detection_id，type，level，confidence，bbox，物理尺寸 |
| `device_status` | 设备时序状态 | device_id，sampled_at，相机/曝光/增益等 |
| `alerts` | 告警事件 | device_id，type，level，first_seen_at，status |
| `config_versions` | 不可变配置版本 | config_type + version 唯一，payload_json，published_at |
| `mes_deliveries` | MES 上报 | detection_id，idempotency_key 唯一，status，attempts |
| `audit_logs` | 只追加审计日志 | actor_id，action，resource，before_json，after_json，created_at |

检测主记录、缺陷明细和文件元数据必须同事务写入；检测记录绑定模型和配置版本。导出任务、系统日志、统计汇总等实体在设计方案中被功能引用但未列入核心表，列为待确认数据模型。

## 13. 微服务职责

| 服务 | 职责 |
| --- | --- |
| `web-api` | JWT/RBAC、历史查询、统计、配置、用户、审计、导出任务和签名 URL。 |
| `realtime-gateway` | WebSocket 会话、Redis Pub/Sub、心跳、实时推送和断线恢复。 |
| `inference-service` | 监控共享目录，加载模型并输出缺陷框、置信度和物理尺寸。 |
| `decision-service` | 使用检测时刻的配置版本计算 PASS/NG，保证历史可复现。 |
| `mes-adapter` | 异步 MES 上报、重试、幂等、失败告警和人工补报。 |
| `worker/maintenance` | Excel/PDF、统计聚合、文件清理、日志归档、备份校验。 |

FastAPI 不承担图像推理和大文件传输。

## 14. 性能指标

| 指标 | 目标 | 验证方式 |
| --- | ---: | --- |
| 单张推理 | ≤ 5.0 s | 连续 100 张测试；起止口径待冻结 |
| 1 mm 以上缺陷漏检率 | ≤ 0.5% | AI 验收样本与计算口径待补充 |
| 误判 NG 比例 | ≤ 3% | AI 验收样本与计算口径待补充 |
| WebSocket 端到端延迟 | ≤ 200 ms | 事件时间戳至前端渲染 |
| HTTP API P95 | ≤ 300 ms | 50 并发 Locust/k6 |
| 实时页 | ≥ 24 FPS | Chrome DevTools |
| 10 万条历史查询 | ≤ 1 s | 服务端分页查询 |
| 并发用户 | ≥ 50 | 稳定性压测 |

## 15. 安全要求

- JWT HS256，密钥至少 256 位；access 8 小时，refresh 7 天。
- 密码至少 8 位并含大小写、数字、特殊字符；bcrypt cost=12。
- 连续 5 次错误锁定 30 分钟；管理员可选 TOTP。
- HTTPS/WSS，TLS 1.2+；密钥、数据库密码和 MES token 不入库。
- ORM/参数化查询、XSS 白名单、CSRF 防护、Redis 令牌桶限流。
- 后端逐接口授权；敏感写操作二次确认。
- 所有写操作记录操作者、IP、时间和变更前后值；审计日志只追加。
- 数据本地化，所有业务数据留在客户内网。

## 16. 部署要求

首期采用工业服务器 + Docker Compose：Nginx、Vue 静态站点、FastAPI×2、WebSocket 网关×2、GPU 推理服务、Celery Worker、Redis、MySQL、MinIO、Prometheus 和 Grafana。

推荐硬件：8 核 16 线程以上 CPU、64 GB 内存、RTX 3060 12 GB 以上 GPU、500 GB 系统盘、2 TB 数据盘或 NAS。数据库和文件存储使用独立磁盘；配置、模型和业务数据挂载持久卷；外部仅开放 443；支持健康检查、优雅停机、备份和快速回滚。多产线时可迁移 Kubernetes。

## 17. 非功能要求

- 可用性：7×24，月度非计划停机 ≤0.5%，RTO ≤30 分钟，RPO ≤5 分钟。
- 可靠性：关键服务双副本、故障摘除、断网重连、待检测文件可恢复处理。
- 可维护性：结构化 JSON 日志、ELK、Prometheus/Grafana、慢查询和健康检查。
- 可扩展性：模型热更新、配置版本化、缺陷类型可扩展、多产线水平扩容。
- 数据管理：原图默认保留 90 天但至少 3 周；配额清理每日 02:00 执行。
- 合规：数据不出厂，不涉及个人敏感信息；模型与代码知识产权归东方电气所有。
- 可测试性：每个 FR 必须映射前端、后端、API、数据库和测试；未通过测试不得标记 DONE。

## 18. 建议工程目录

```text
dingzi-codex/
├── docs/
│   ├── 定子冲片表面缺陷数据预处理及模型开发技术服务项目系统需求说明书.docx
│   ├── 定子冲片表面缺陷检测Web可视化系统设计方案V1.1.docx
│   ├── PROJECT_ANALYSIS.md
│   ├── REQUIREMENTS_TRACEABILITY.md
│   └── OPEN_QUESTIONS.md
├── frontend/                 # Vue 3 + TS + Vite
├── backend/                  # FastAPI web-api
├── services/
│   ├── realtime-gateway/
│   ├── inference-service/
│   ├── decision-service/
│   ├── mes-adapter/
│   └── worker-maintenance/
├── deploy/
│   ├── nginx/
│   ├── monitoring/
│   └── scripts/
├── tests/
│   ├── integration/
│   ├── e2e/
│   └── performance/
├── docker-compose.yml
├── PROJECT_STATUS.md
└── README.md
```
