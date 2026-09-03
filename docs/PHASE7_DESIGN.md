# Phase 7 系统管理设计

日期：2026-09-03  
工作区：`E:\gongjiangban\dingzi-codex`  
状态：设计步骤完成，待用户查看；尚未进入实现或验证步骤。

## 1. 范围与依据

本阶段交付管理员专属的用户管理、日志中心、MES 配置与异步上报、文件策略。遵循本轮用户要求，依次完成设计、实现、验证，每一步完成后停止。Phase 7 完成后不自动进入 Phase 8。

正式依据为 `docs/` 下需求说明书和设计方案 V1.1。本轮明确指令优先；除明确例外外，需求说明书仍优先于设计方案。阶段总结仅作索引和既往证据，不能代替代码或运行验证。

本次直接提取两份 Word 的正文及表格文字核对，主要定位如下（P 为 `word/document.xml` 中段落序号，含表格段落，不是页码）：

| 内容 | 需求说明书 | 设计方案 V1.1 |
| --- | --- | --- |
| 用户功能与邮件重置 | 6.6.1，P491～500 | 3.7，P482～488；5.2，P1518 软删除 |
| 日志与保留周期 | 6.6.2，P505～514 | 3.7，P489～495；6.3，P1548～1552 |
| MES | 6.6.3，P519～526 | 3.7，P496～504；4.2.6，P1083～1118；5.2，P1515～1516 |
| 文件策略 | 6.6.4，P531～536 | 3.7，P505～512 |

已明确的业务口径：

- 角色仅 `admin`、`operator`；所有系统管理接口在后端检查管理员权限。
- 按本轮“按照设计文档设置日志保留周期”：操作日志 180 天、系统日志 90 天；作为需求说明书统一 180 天的本阶段明确例外登记 Q018。
- 原图默认保留 90 天，达到配额 80% 告警，达到配额上限清理最旧文件；每日北京时间 02:00 执行保留期清理。
- 检测完成后由 Celery 上报 MES，失败指数退避，最多重试 3 次。依据设计原文“最多重试 3 次”，解释为首次请求加 3 次重试，最多 4 次请求；不是总计 3 次请求。
- 清理仅删除文件内容，保留检测、缺陷、原始推理 JSON、配置快照和文件清理记录。

## 2. 现有实现检查与复用

本次为代码检查，没有重新运行上一阶段测试。已有通过记录不作为本次新增功能的测试结果。工作区当前没有 `.git`，不能提供 Git 差异基线；实现时仍严格限制改动范围。

| 当前文件/组件 | 已有能力 | 本阶段处理 |
| --- | --- | --- |
| `backend/app/core/deps.py` | 从数据库读取当前用户、检查 active 状态与角色 | 复用 `require_roles("admin")`；补删除状态与凭据版本检查 |
| `models/user.py`、`services/auth.py`、`security/auth.py` | 姓名、邮箱、角色、启停、锁定字段；bcrypt cost=12、密码策略、JWT | 增量实现用户管理与重置，保留现有登录流程 |
| `models/refresh_token.py` | 刷新令牌撤销 | 用户停用、删除、重置和角色修改时复用撤销机制 |
| `models/audit_log.py`、`services/configuration.py` | 操作者、时间、IP、前后值、配置版本与二次确认 | 保留原有配置审计；新增通用系统审计写入，不大规模搬迁旧模块 |
| `api/v1/system.py` | 仅 `/system/admin-check` | 保留接口，挂载系统管理子路由 |
| `services/realtime.py::process_image` | 检测、缺陷、统计事务落库和推送 | 同事务增加文件登记与待投递记录，提交后触发 Celery |
| `models/detection.py` | `mes_status=not_sent`、工单、图片路径、不可变配置快照 | 复用字段，新增投递表和文件表承载详细状态 |
| `tasks/__init__.py` | Celery 应用与统计/导出任务 | 增加 MES、维护任务及 Beat 调度，不新建独立微服务 |
| `models/export.py`、`services/exports.py` | 异步任务、进度、文件路径、有效期 | 复用任务表，增加用途/幂等字段及独立 CSV 生成器，保持 xlsx/pdf 分支 |
| `services/files.py` | 自定义 HMAC 下载地址生成 | 不能认定为完整 MinIO SDK 签名/存储实现；新增真实存储适配器供本阶段使用 |
| `frontend/src/router/index.ts` | `/system` 管理员路由、占位页面 | 改为系统管理容器及四个子页面，复用 Axios、Pinia、Element Plus |
| `views/history/HistoryDetailView.vue` | 详情、标注、原图请求、MES 工单关联 | 增量显示 MES 状态和管理员补报；原图缺失仍显示元数据与缺陷 |
| `docker-compose.yml` | API、Worker、Redis、MySQL、MinIO | 增加单实例 Beat、必要共享存储挂载和配置，保留其他服务拓扑 |

明确缺口：代码及迁移中尚无 `detection_files`、`mes_deliveries`、系统日志表或文件清理任务。文档中的同名表不能视为已实现。Phase 6 配置校验要求恰好六类参数；系统配置另存，不加入检测配置包，不改写历史配置版本。

## 3. 用户管理

页面字段：账号、姓名、邮箱、角色、状态、锁定截止时间、最后登录。支持分页、关键词/角色/状态筛选、新增、编辑、删除、单个/批量启停、角色修改、密码重置、手动解锁。

- 沿用 `active | disabled`，软删除采用 `deleted_at`，不增加第三种角色或把删除混入启停枚举。删除后不可登录/刷新，保留历史审计、导出创建者及账号唯一性。
- 创建账号按设计 3～20 字符校验；已有更长账号仍可查询和管理。姓名、邮箱沿用现有字段。密码复用当前复杂度和 bcrypt，额外验证 bcrypt 字节长度上限，避免多字节密码引发服务异常。
- 编辑默认修改姓名、邮箱、角色及状态，密码变更走专门重置流程；不默认开放更改账号名称。
- 不允许当前管理员删除、停用或降低自己的角色。使用固定守卫行锁串行化管理员集合变更，检查操作后仍有可用管理员，批量操作在同一事务内全部成功或全部失败，避免并发删除最后管理员。
- 手动解锁清空失败次数及锁定截止时间，不改变密码、不自动启用已停用账号。
- 增加用户 `credential_version`（初始 0）及 JWT 对应声明。停用、删除、角色变化、密码重置成功时增加版本并撤销该用户 refresh token，旧 access token 立即失效。兼容缺失声明的旧 token 为版本 0，仅对尚未发生凭据变更的账号有效。
- 审计保留操作对象、操作者、时间、来源 IP 和脱敏前后值，不记录密码、散列、完整 token 或重置链接。

密码重置设计提案（Q016，随本设计审核）：管理员发起向预留邮箱发送一次性链接；链接持有者只能设置自身新密码，不能访问系统管理。令牌只保存散列，建议 30 分钟有效、只能消费一次；新建重置申请使旧申请失效。缺少邮箱时返回明确错误；邮件发送通过 Celery，SMTP 未配置时显示失败，不能宣称邮件已送达，也不在生产响应中返回明文密码或链接。邮件发送失败不修改原密码。重置成功后撤销会话并记录审计。

对应前台 `/reset-password` 和 `POST /api/v1/auth/password-reset/confirm` 是一次性令牌授权的自助入口，不属于管理员管理接口；此例外与 Q016 一并审核。新增/编辑中的任意直接密码覆盖不作为默认替代方案。

## 4. 日志中心

- 两个标签页：操作日志、系统日志。统一筛选 `start_time/end_time/level/source/keyword`，级别仅 `INFO | WARNING | ERROR`；操作日志额外支持 `user_id/action_type`。
- 统一分页外层 `{items,total,page,page_size}`，默认 20，可选 50/100；时间倒序并以 id 稳定排序。API 用 UTC ISO 8601，页面显示北京时间。起止范围采用左闭右开，避免相邻区间重复。
- 操作日志保留原表，增量增加级别、来源、操作者名称快照、可搜索文本和 trace_id。旧记录迁移映射：登录失败/账号锁定为 WARNING，其余没有明确级别的记录为 INFO，不伪造历史 trace_id。
- 新建系统日志表存储时间、级别、来源、消息、关联检测/设备、trace_id、脱敏上下文。接入现有相机/推理告警事件，以及 MES 失败、队列异常、磁盘配额和清理异常。新增日志级别不改动既有实时告警协议枚举。
- 关键词搜索覆盖消息、操作、来源、操作者和脱敏变更摘要，使用参数化查询。先保证中文子串检索正确，不把普通 LIKE 宣称为 MySQL FULLTEXT 索引；生产数据量下的索引方案和性能单独验证。
- CSV 是筛选结果全集，后台按批次读取；复用 `ExportJob` 增加 `kind`（历史任务默认 detection）和创建幂等信息，创建返回 202，查询进度后下载。采用 UTF-8 BOM、正确 CSV 转义并处理电子表格公式注入。
- 管理员权限覆盖 CSV 创建、状态与下载；保留原历史 xlsx/pdf 访问规则。文件过期显示不可下载，不能仅隐藏按钮。
- 单实例 Beat 每日 02:00 触发维护任务；操作日志清理早于当前时刻 180 天的记录，系统日志清理早于 90 天的记录。分批清理、记录范围、数量、运行 id 和结果。普通业务接口不能修改/删除日志。
- 设计方案同时规定审计日志只追加与过期清理，解释边界登记 Q029：保留期内不可改删，过期仅由专用维护任务清理并留下新的清理审计；待本设计审核。

## 5. MES 配置与投递

### 5.1 客户端和配置

建立 `MesClient` 抽象、HTTP 实现与 `MockMesClient`。接口至少提供 `test_connection`、`report`，返回 HTTP 状态码、耗时、成功标志及脱敏错误。Mock 支持成功、超时、连续失败、重复键和恢复，用于可重复测试；生产不能自动降级为 Mock 成功。

配置包含 `mes_url`、`auth_token`、`auto_report`、适配器模式和配置修订号。Token 在响应中仅给出“已配置”，省略更新表示保留，清除动作必须显式；存储采用独立环境密钥加密，日志和历史快照仅保存凭据引用。避免把 Token 放入 Phase 6 检测配置快照。

默认关闭自动上报，地址/Token 留空；不生成真实 MES 地址。HTTP 模式使用现有 httpx，默认连接 3 秒、整体请求 10 秒作为可配置运行参数。允许经部署配置登记的厂内 HTTP(S) 目标，禁止任意协议、URL 用户信息与跨目标自动重定向；测试连接不发送生产检测记录。

真实 MES 的鉴权、字段字典、健康检查方法、成功码和幂等支持由 Q027 记录。提案为 Bearer Token、POST JSON、`Idempotency-Key` 请求头；测试连接用独立探测方法（Mock 固定协议，真实默认 GET 同一配置地址，仅表示 HTTP 可达性）。不擅自构造 `/health` 或把 405 当作业务上报成功。配置测试返回 `http_status: null` 表示未取得 HTTP 响应，不能伪造状态码。

### 5.2 事务、幂等、重试与人工补报

1. 检测落库时读取 MES 当前配置；启用自动上报则在同一数据库事务写入检测及 `mes_deliveries` 待投递行。冻结上报 payload：图片编号、后端判定、检测时间、缺陷数量，关联工单仅在协议允许时附加。保持检测快照不变。
2. 提交后异步派发 Celery；待投递表同时承担 outbox。每分钟补扫到期未派发/租约过期任务，修复“数据库已提交但队列发送失败”的窗口。Redis/MES 失败不会回滚已完成的检测。
3. 每条检测只创建一个逻辑投递，`detection_id` 与稳定业务 `idempotency_key` 都有唯一约束。Worker 用短事务抢占、租约及尝试记录，网络请求期间不持有数据库长事务。完成更新校验租约所有者，旧 Worker 不得覆盖新结果。
4. 内部任务状态拟采用 `pending/sending/retry_wait/succeeded/failed`；对设计公开接口映射 `submitted/success/failed`。检测字段保留既有 `not_sent`，新增状态经集中映射同步，前端不能自行推导成功。
5. 失败后最多重试 3 次（首次加重试最多 4 次），建议可配置基数 5 秒，即 5/10/20 秒；用 Celery 调度和数据库 `next_attempt_at`，不在 API/Worker 内 sleep。重投递或 Worker 重启不能把尝试次数归零。HTTP 失败/超时记录状态码和耗时，耗尽后 ERROR 告警并转 failed。
6. 管理员人工补报仅允许失败或尚未上报的记录，必须带请求 `Idempotency-Key`。相同请求键+相同内容返回同一结果，相同键不同内容返回 409。人工补报开启新轮次、保留累计历史，但复用原业务幂等键与 payload；进行中或成功的记录不再次发送。
7. 配置变更不静默改变正在投递的目标；保存配置修订及凭据引用。需要换地址/凭据的失败任务，由管理员明确选择当前配置补报并审计；旧、新目标之间的去重能力仍取决于真实 MES 协议。

“请求已被 MES 接受但响应丢失”不能单靠本地唯一索引保证外部不重复；HTTP 重试始终使用同一业务幂等键，真实端到端去重必须由 MES 验证支持。此项不得用 Mock 通过代替生产验收。

## 6. 文件策略与存储

- 配置字段：`retention_days=90`、`quota_gb`、`warning_percent=80`、修订号。GB 按十进制 `1,000,000,000 bytes` 计算并在页面标注；容量未确认时 `quota_gb=null`，展示“未配置”，不虚构生产容量。
- 配额统计范围为登记且受本系统管理的原图，不是扫描整个磁盘。宿主机卷的真实磁盘使用率另行展示/告警，不误称应用配额利用率为整盘利用率。范围及未配置行为登记 Q028。
- 新建 `detection_files` 记录 `detection_id/kind/storage_backend/uri/size_bytes/created_at/deleted_at/delete_status` 等，关联缺陷检测。新检测原图在受控存储下登记；旧检测通过分批回填任务登记，不在 Alembic 中扫描文件系统。
- 存储接口提供 stat/delete/download，支持本地受控目录和 MinIO。目录/bucket 由部署配置提供，拒绝越界路径、盘符逃逸和符号链接/junction 逃逸；不对任意 `image_path` 直接执行递归删除。相同物理对象被多条记录引用时，检查全部引用的保留要求后再删除。
- Beat 每日北京时间 02:00 清理过期原图；新文件登记和周期容量检查触发配额计算，达到 80% 产生 WARNING，达到 100% 派发最旧优先清理，避免达到配额仍等到次日。告警按越阈值状态去重，恢复后再越限允许再次告警。
- 先清理过期文件，再在超额时按 `(created_at,id)` 删除最旧文件至用量低于上限。配额可能导致提前于 90 天删除，审计明确原因 retention/quota；不把 90 天宣称为容量不足时的最低保证。
- 清理运行加互斥/租约，按批次处理。先持久化清理意图，再删除内容，再登记完成与审计；进程中断后重试时“文件已不存在”可恢复为完成。权限/网络错误不能标记成功或扣减用量。
- 成功、失败、已不存在、拒绝越界均保留单文件结果及汇总审计，含系统任务或操作者、时间、文件标识、释放字节、原因、运行 id。系统任务 actor 可为空，但必须能识别来源。
- 不删除 Detection、Defect、config_snapshot、raw_output 或文件登记行；原图不可用时下载接口返回明确 410，未曾存在的资源返回 404。历史详情捕获原图不可用错误，仍显示判定、配置快照和缺陷列表。缩略图、报告等不自动继承原图清理规则。
- 新存储接口用于本阶段已登记资源的实际下载与删除；旧签名方式不冒充 S3 presign。本地使用经过签名验证的受控下载接口，MinIO 使用 SDK；补做权限与有效期测试。已有历史接口路径保持不变。
- 文件策略采用独立版本记录，提供配置备份下载与恢复；恢复生成新修订并审计，不恢复已删除的文件。配置备份不包含任何 MES 凭据。

## 7. 接口提案

以下均以 `/api/v1` 为前缀；除密码重置令牌兑换外均要求 `require_roles("admin")`。沿用设计已定义路径，新增路径/字段登记 Q017、Q027、Q028，随本设计审核，尚未宣称冻结。

| 方法与路径 | 输入/输出要点 |
| --- | --- |
| GET `/system/users` | 分页、关键词、角色、状态；返回 user_id、姓名、邮箱、锁定信息等 |
| POST `/system/users` | username/password/display_name/email/role；新增并审计 |
| PUT `/system/users/{user_id}` | 修改姓名、邮箱、角色、状态；携带 revision 防丢失更新 |
| DELETE `/system/users/{user_id}` | 软删除、撤销会话；返回删除结果 |
| POST `/system/users/{user_id}/status` | active/disabled，复用批量服务 |
| POST `/system/users/batch-status` | user_ids + status，原子批量修改 |
| POST `/system/users/{user_id}/unlock` | 清空锁定及失败次数 |
| POST `/system/users/{user_id}/password-reset` | 创建邮件任务，202；需要请求幂等键 |
| POST `/auth/password-reset/confirm` | 一次性 token + 新密码；仅限令牌指定账号 |
| GET `/system/audit-logs`、`/system/system-logs` | 分页、时间、级别、来源、关键词 |
| POST `/system/log-exports` | 日志类型与筛选快照 + Idempotency-Key，202 |
| GET `/system/log-exports/{id}`、`/{id}/download` | 管理员任务状态、受保护下载地址 |
| GET/PUT `/system/mes/config` | URL、Token 写入/已配置标志、自动上报、修订号 |
| POST `/system/mes/test-connection` | mes_url/auth_token 或当前配置引用；状态码、耗时、错误 |
| GET `/system/mes/deliveries`、`/{id}` | 投递状态、尝试历史、失败原因 |
| POST `/system/mes/manual-report` | 沿用 record_id 和 Idempotency-Key，202/重复返回已有结果 |
| GET/PUT `/system/file-policy` | 保留天数、配额、告警阈值、修订号 |
| GET `/system/file-policy/usage` | 字节量、配额占比、原图数量和清理状态 |
| GET `/system/file-policy/backup` | 策略 JSON 与版本，不含密钥 |
| POST `/system/file-policy/restore` | 校验备份后写新修订，幂等与审计 |

写操作遵循现有前端确认框及后端 `X-Confirm-Action` 约定；PUT 配置保存同时验证修订号。每个写接口失败也返回明确原因；权限校验先于业务动作。邮件/导出/人工补报创建与策略恢复强制请求幂等键，键冲突必须比较请求内容，不能仅按键返回不相干结果。

公开新增响应采用现有列表分页惯例；设计方案中用户 `users` 包装与工程 `{items,total,page,page_size}`、string ID 与现有整数 ID 的差异在 Q017 明示：提案沿用本工程整数 ID 和分页格式，以 DTO 提供 user_id 等外部字段名，不重构旧接口响应。

## 8. 数据迁移与落点

计划增量迁移 `0008_system_management`，父版本 `0007_configuration_versions`。不得在生产代码使用 `Base.metadata.create_all()`。

| 数据对象 | 计划变更 |
| --- | --- |
| users | deleted_at、credential_version、revision；复用既有业务字段 |
| audit_logs | level、source、actor_name、message/search_text、trace_id 及查询索引，历史值兼容回填 |
| system_logs | 级别、来源、消息、上下文、trace_id、时间与组合索引 |
| system_settings / system_setting_versions | MES 与文件策略的当前指针和修订记录、管理员变更守卫行；独立于检测配置包 |
| mes_deliveries / mes_delivery_attempts | 检测唯一、业务幂等键唯一、冻结 payload、轮次、次数、状态、下次时间、租约及 HTTP 结果 |
| system_request_keys | 请求范围、调用者、幂等键、内容摘要、结果引用；唯一约束防重放冲突 |
| password_reset_requests | user_id、token_hash、有效期、消费时间、邮件任务状态 |
| detection_files | 文件定位、字节数、类型、登记/删除状态、检测外键，保留元数据 |
| maintenance_runs / file_cleanup_items | 清理任务、租约、逐文件意图与结果、汇总审计 |
| export_jobs | kind 默认 detection、幂等字段；旧任务和历史导出分支保持兼容 |

新增代码以 `backend/app/{api/v1,schemas,services,models,tasks}` 内系统管理文件为主；存储/MES/邮件适配器放入 services 子包。前端新增 `views/system/{UsersView,LogsView,MesView,FilePolicyView}.vue`、`api/system.ts` 与 `types/system.ts`，主页面复用现有布局。

新依赖仅按实现需要加入：MinIO SDK、独立密钥加密支持；邮件优先复用 Python 标准 SMTP。安装或版本兼容问题在实现步骤验证，不在设计阶段宣称已解决。

## 9. 实现顺序

1. 迁移与 schema、管理员路由、用户管理和审计基础；复用认证并做凭据撤销增量修改。
2. 日志查询、CSV 任务、邮件重置与状态处理。
3. MES 客户端、outbox、重试、幂等、人工补报和检测落库接入。
4. 文件登记、存储适配器、策略、清理和 Beat；处理历史原图不可用的显示。
5. 四个管理页面、接口对接和权限反馈；同步追踪矩阵。

实现步骤结束先供用户查看，再进入集中验证步骤；实现中仍执行必要的语法和针对性检查以避免累积错误，不据此提前标记本阶段 TESTED。

## 10. 验证方案与完成条件

| 范围 | 必须验证的行为 |
| --- | --- |
| 用户/RBAC | 全部管理接口匿名 401、operator 403；增删改、角色、启停、批量事务、解锁；并发最后管理员保护；旧 access/refresh 撤销；越权直接调用 |
| 密码重置 | 邮件内容使用测试收件箱；令牌过期、重复消费、新申请覆盖旧申请、发信失败、账号停用；不泄露密码/Token；真实 SMTP 单列 |
| 日志 | 两类日志筛选组合与中文关键词、级别映射、审计前后值脱敏、分页；CSV 全筛选集/转义/权限/过期；180/90 天精确边界和维护审计 |
| MES | Mock 成功、500、连接失败、超时；首次+3次重试上限；重复 API、重复 Worker、响应丢失、租约恢复、Redis 不可用后恢复；人工补报保留历史与业务键；检测不回滚 |
| 文件 | 临时受控目录与测试 bucket；90 天边界、80% 告警、满配额最旧优先、并发清理、缺失文件、删除失败、重复执行与路径逃逸；检测元数据/快照不变；详情继续可读 |
| 调度 | Asia/Shanghai 每日 02:00；单 Beat、多 Worker 不重复处理；周期 outbox/配额补扫；不通过等待到凌晨验证，用注入时钟与真实任务触发 |
| 迁移 | 空 SQLite 升级 head、已有 0007 数据增量升级且原记录保留、MySQL 在线升级；唯一约束及索引；不把 SQLite 当 MySQL 实证 |
| 回归 | 后端 Ruff/pytest，前端 ESLint/Vitest/TypeScript/Vite；Phase 2～6 登录、检测、统计、历史导出和配置快照回归 |
| 运行 | Uvicorn 真实进程、管理员/操作员接口链路；真实 Redis+Celery Worker+Beat 对本机 Mock MES HTTP 服务的完整上报、重试、人工补报；CSV 下载和文件清理后详情 |

验证步骤执行项目现有命令：后端 `python -m ruff check .`、`python -m pytest`、`python -m alembic upgrade head`；前端按 package.json 运行 lint/test/build。使用项目虚拟环境与可用 Node 运行时。生产数据清理不得用作测试，只用专用临时文件、测试数据库和测试 bucket。

真实 Compose 应验证 MySQL、Redis、Worker、Beat、API、前端、Nginx、MinIO。Docker CLI/引擎、真实 SMTP、真实 MES、真实存储当前仅有旧记录，尚未本轮探测；环境不可用时记录具体失败和替代验证边界，不能用 Mock 或 eager mode 宣称真实容器联调通过。

完成条件：本阶段功能实现、必要回归通过、迁移与运行证据齐全；更新 `PROJECT_STATUS.md`、`REQUIREMENTS_TRACEABILITY.md`、`OPEN_QUESTIONS.md` 和阶段验证记录。真实外部环境未验证项逐条列明，不将阶段直接标记为生产验收 DONE。

## 11. 本次设计检查结果

- 已对照全部 15 项 FR-SYS，并补充本轮明确要求的手动解锁、批量启停、关键词、耗时、人工补报与文件审计。
- 已登记正式文档冲突与新增接口/协议缺口；设计提案不冒充已获确认的需求裁决。
- 本步骤只新增/更新设计和状态文档，没有改业务代码、数据库、运行环境或执行真实清理/邮件/MES 上报。
- 等待用户查看设计后进入实现。
