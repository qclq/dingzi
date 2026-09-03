# Phase 9：生产部署与最终验收设计

日期：2026-09-03  
状态：设计步骤完成，待用户查看；尚未进入实现或验证步骤。  
工作区：`E:\gongjiangban\dingzi-codex`

## 1. 范围、依据和步骤边界

本阶段是用户指定的最终阶段，合并旧计划中的 Phase 9 联调和 Phase 10 交付内容。目标是将已有业务实现变成可复现部署、可演示、可核验的交付包，不扩展业务范围。

按照“设计 → 用户查看 → 实现 → 用户查看 → 验证 → 用户查看”推进。实现阶段执行必要的定向检查；验证阶段执行全量检查、真实进程和容器联调，修复发现的错误并复测。用户本轮明确要求每一步暂停，不能因为此前授权直接修改而跳过暂停。

依据优先级：正式需求说明书 Word > 不冲突的设计方案 Word > 本轮阶段交付要求与已确认决策 > 总结和状态记录。本轮要求决定阶段安排，不自动豁免正式验收要求。

本次直接读取两份 Word 的正文与表格文本，需求说明书包含 79 个显式 FR。重点复核需求第 7 节和设计第 8、9、11 节；未进行 Word 排版视觉检查。本文件记录静态审查及拟实施方案，不能作为测试通过证据。

## 2. 现有实现审查

| 范围 | 当前文件与发现 | 本阶段处理 |
| --- | --- | --- |
| 部署 | `docker-compose.yml` 已有 nginx、frontend、web-api、mysql、redis、celery-worker、celery-beat、minio；API 单实例，缺少独立网关和推理入口 | 复用 Compose 和两个 Dockerfile，补齐进程入口、双副本、启动依赖、健康检查和数据卷 |
| 镜像 | `backend/Dockerfile` 未复制 scripts；`frontend/Dockerfile` 复制整个构建上下文；未见对应 `.dockerignore` | 补齐初始化脚本、构建依赖及上下文排除；验证安装包内容、中文 PDF 字体和非 root 运行所需权限 |
| Nginx | `deploy/nginx.conf` 只有 `/api/` 和前端代理；`frontend/nginx.conf` 已有 SPA fallback | 保留 SPA，增加 WS Upgrade、两个上游实例、资源缓存及独立 TLS 配置 |
| 实时消息 | `backend/app/services/realtime.py` 发布 Redis，但 WS 只订阅进程内队列；序号与 latest 也在本进程 | 补齐跨进程消费、序号一致性、重连与慢客户端处理；保留测试用本地 broker |
| 网关 | `services/realtime-gateway/app/envelope.py` 只有封装函数 | 增加独立 ASGI 入口，复用后端 WS 路由与认证规则，避免复制业务代码 |
| 推理 | `backend/app/services/inference.py` 已有 Provider、Mock、模型适配入口；独立 services 目录只有另一个 Mock 契约文件 | 以实际被调用的后端 Provider 为主，增加独立运行入口；确认引用后清理重复骨架，保留正式 Mock Adapter |
| 接图 | `backend/app/services/watcher.py` 已有 watchdog 与轮询；watchdog 回调在线程内调用事件循环；演示图片编号重启后重复 | 修复线程调度、完整文件落盘识别、启动积压扫描、失败重试和重启幂等 |
| 页面 | `RealtimeView.vue` 当前显示图片编号占位和缺陷框，没有加载原图；历史详情已有图片 URL 加载 | 补齐原图显示和真实图片标注，复用已存在的图片下载接口 |
| 文件 | `services/files.py` 生成自定义 HMAC URL，但未发现对应验签下载服务或 MinIO SDK 上传链路 | 接通实际存储、授权下载、过期拒绝及浏览器可访问地址；不能把拼接 URL 视作下载成功 |
| 数据库 | 已有 `0001`～`0008_system_management`，模型声明 15 张业务表 | 从空 MySQL 在线迁移并核验完整表、索引、约束；必要修复采用新增迁移，保留既有迁移历史 |
| 管理员 | `scripts/init_admin.py` 可执行，但每次调用都会重设已有用户密码、角色和状态 | 区分首次创建与显式轮换，重复启动不覆盖已有账号；轮换须遵守凭据版本与审计规则 |
| Mock 数据 | `scripts/run_realtime_demo.py` 已有图片生成和接图，尚无完整首次演示初始化流程 | 复用入口，生成有效可见图片、PASS/NG 数据及演示 MES 配置；不绕过正式迁移或判定 |
| MES | 已有 `MesDelivery`、Mock/HTTP Client、发送任务和重试时间字段；自动检测只插入 outbox，Beat 未见 outbox 扫描任务 | 补齐待发/到期重试调度、重复领取保护、结果与历史状态一致性，验证自动上报与人工补报 |
| 维护 | Beat 已配置 Asia/Shanghai 每日 02:00；日志清理分别为 180/90 天 | 保留调度，实测 Worker/Beat；日志期限按 Q018 处理，不能沿用 90 天即宣称合规 |
| 认证 | WS 握手检查 token 与 active，但未与 REST 完整凭据版本/软删除校验对齐 | 复用认证规则，验证停用、删除、角色调整、密码重置后的 WS 拒绝及已连接会话处理 |
| 文档 | 追踪矩阵仍混有规划路径、TODO/TESTED，状态文件阶段名称及清单滞后；性能/安全报告有待填字段 | 实现后逐条核对，验证后填写实际证据，禁止批量将旧 TESTED 转为 DONE |

当前环境：目录无 `.git` 元数据；PATH 中未发现 Docker，默认 Docker Desktop 安装路径及 Windows Docker 服务也未发现。仓库后端虚拟环境存在，前端 `canvas.node` 不存在。以上仅是本次只读探测结果，不等同于已穷尽所有自定义安装路径；实施时继续定位运行时。不得覆盖或输出现有 `.env` 的秘密值。

## 3. 拟交付的容器拓扑

```text
浏览器 -- HTTP（本机演示）/ HTTPS（生产） --> nginx
  /              -> frontend（已有 Vue SPA）
  /api/          -> web-api + web-api-2
  /ws/           -> realtime-gateway + realtime-gateway-2
  对象下载路径    -> 受控 MinIO 入口（签名、Host 与路径保持一致）

inference-service（独立容器，mock 无 GPU 依赖）
  图片接入 -> 已有 Provider -> 后端阈值/PASS-NG 判定
          -> MySQL 检测/快照/统计/outbox -> Redis -> 两个实时网关
          -> MinIO 原图/JSON

celery-worker <- Redis <- 导出任务、MES 待发与重试、维护任务
celery-beat（单实例） -> MES outbox 调度、每日 02:00 维护

mysql、redis、minio -> 持久卷
migrate -> bootstrap -> 应用服务（初始化成功后启动）
```

| 服务 | 常驻实例 | 责任 |
| --- | --- | --- |
| nginx | 1 | 唯一业务入口；REST 负载分配、WS 转发、TLS 准备 |
| frontend | 1 | 提供构建后的 SPA；入口 HTML 不长期缓存，带 hash 资源长期缓存 |
| web-api / web-api-2 | 2 | 复用 FastAPI REST 服务，共享数据库、Redis 和对象存储 |
| realtime-gateway / realtime-gateway-2 | 2 | 独立 WS 进程，共享消息源；断线重连可落到另一实例 |
| inference-service | 1 | 独立接图、Provider 推理、已有判定和持久化流程 |
| mysql / redis / minio | 各 1 | 数据库、队列缓存、私有对象存储 |
| celery-worker / celery-beat | 各 1 | 已有任务执行、单一调度器 |
| migrate / bootstrap / minio-init | 一次性任务 | 迁移、幂等管理员/演示初始化、私有桶及最小权限准备 |

采用两个显式 API 和网关服务，保证普通 `docker compose up -d` 就启动所需实例；用 Compose 复用定义减少配置重复。不依赖用户额外指定 `--scale`。具体服务构建入口在实现中与现有 Python 包结构对齐，允许多个容器复用同一后端镜像。

仅增加进程启动边界，不把已测试的判定、历史、配置等模块重写为新的网络微服务。独立推理容器执行已有后端 Python 业务服务，PASS/NG 始终由后端产生。

此拓扑仍有宿主机、入口、数据库等单点，不能证明正式需求“单点故障为 0”。生产 HA 必须另有实际部署与故障切换证据，见 Q028。监控接入采用部署配置或明确记录外部监控平台依赖，不因服务清单未列监控而忽略正式需求。

## 4. 部署与初始化设计

### 4.1 镜像、环境和启动顺序

- 保留 `backend/Dockerfile`、`frontend/Dockerfile`，无需增加内容重复的根 Dockerfile。添加 `.dockerignore`，排除 `.env`、虚拟环境、node_modules、缓存、测试输出及 IDE 文件，防止本机二进制和密钥进入镜像。
- 核验并固定镜像/依赖版本；避免 `latest`。不在设计步骤随意指定未经构建验证的新版本。后端镜像安装导出所需系统库和中文字体，运行身份、卷属主及写权限一起验证。
- `.env.example` 只保留占位、说明和非秘密默认值；补齐 APP_ENV、数据库/Redis、JWT、存储、INFERENCE_MODE、接图目录、演示开关、初始化和对外地址等配置。真实模式禁止因配置缺失而静默回退 Mock。
- 首次部署先通过本地初始化脚本生成随机密钥及管理员凭据或读取用户提供的值，再执行 `docker compose up -d`。该准备是首次配置步骤；容器启动后不再要求手工逐个启动服务。脚本不得覆盖已有 `.env`，秘密文件不提交、不进入日志；模板不能内置固定演示密码。
- 默认演示环境可设置 `INFERENCE_MODE=mock`、演示图片源开启、MES 使用已有 `mock://` Adapter。生产必须显式关闭演示源并完成环境校验。
- MySQL/Redis/MinIO 就绪后运行单独的迁移任务，再进行管理员和演示数据初始化；失败应阻止依赖服务就绪，不能被启动脚本吞掉。
- 容器健康检查区分存活与就绪：数据库、Redis 或必需依赖失败时，就绪返回非成功状态。修复当前仅检查 HTTP 200 而忽略 `degraded` 的探针。
- 业务端口只经 Nginx 暴露，管理端口不默认向局域网开放；TLS 证书独立挂载，缺证书不影响本机 HTTP Mock 演示。生产证书、域名、KMS 等见 Q027。

### 4.2 数据迁移和管理员

- `alembic upgrade head` 是新库建库后创建完整业务结构的唯一正式入口，检查单一 head、全部模型、索引、外键和默认值；SQLite 只作快速兼容回归，必须补真实 MySQL 证据。
- 初始化脚本复用密码校验、hash 和 User 模型。首次创建管理员；再次运行不改密码、角色或状态，不复活被删除/停用用户。账号轮换必须显式执行并让旧凭据失效。
- Mock 初始化只在演示模式执行，使用稳定种子键保证重复启动不重复造历史；实时产生的新图片使用唯一编号。生产启动不注入 Mock 用户、业务配置或检测记录。
- 不为演示重建数据库、不使用生产 `create_all()`，不清空用户已有数据。

## 5. 联调必须补齐的最小改动

### 5.1 实时与独立推理

- 复用 Provider 和判定服务，推理从 Web 请求进程移出；接图线程通过线程安全调度进入异步处理，确认完整落盘后处理，启动时扫描积压，异常可重试且数据库写入幂等。
- Redis 实际承载跨进程消息；网关负责订阅/重连/退订。生产 Redis 失败不能静默进入互相隔离的本地通道。
- 保留现有事件外壳 `type/event_id/sequence/occurred_at/data` 和业务事件 FRAME/INFER/DEVICE/ALERT、控制消息 HELLO/PING/PONG/ERROR。明确业务事件序号与连接控制消息的关系，避免 HELLO/PONG 提升前端水位而丢弃后续检测。
- 为跨实例事件提供统一排序依据与去重；测试断线补 snapshot、进程重启、Redis 恢复、慢客户端、旧连接回调和两网关切换。Redis Pub/Sub 本身没有持久重放能力，不能宣称不丢历史事件；历史事实必须可从 MySQL 恢复，事件重放缺口应保留验收限制。
- 对齐 WS 与 REST 凭据校验，避免旧 token 在网关继续可用。Nginx 日志不得记录 WS 查询参数中的 access_token 或签名下载秘密。
- 演示图片必须有效且可见，实时页面通过受控地址加载原图、显示缺陷框；PASS/NG 两条链路都要可演示，不能只显示文字与空画布。

### 5.2 文件、导出和 MES

- 在已有文件服务边界接入 MinIO 上传和标准签名下载，保存稳定对象键；Web API、推理和 Worker 对对象路径有一致理解，浏览器不使用容器内部主机名或 Windows 本地路径。
- 私有桶、短期授权、过期拒绝、路径隔离、下载权限及报告属主一起测试。通过 Nginx 的签名访问保持签名相关 Host、路径与查询参数一致。
- 原图、JSON、PDF/XLSX 可实际下载；复用当前异步导出任务。对文件清理的本地路径做受控根目录校验，对对象使用明确键空间，不删除检测元数据或配置快照。
- MES outbox 接通扫描和到期重试；网络调用不持有长事务，重复调度不会并发重复领取，worker 崩溃后可恢复，发送结果回写历史状态。保留 MockMesClient 和 HttpMesClient，不把 Mock 回执作为真实 MES 验收。
- 日志 CSV 的同步大查询、SMTP 未发送、外部告警缺协议等已知限制逐项登记。优先修复部署/演示阻断；未经实现和实测的功能保留 PARTIAL/BLOCKED，不为增加完成数扩大功能。

## 6. 备份恢复与运维交付

建立 `docs/BACKUP_RESTORE.md`：

1. MySQL：一致性全量备份、binlog/增量位置、每天全量与最多 5 分钟间隔的异地增量归档、凭据保护、保留策略和完整恢复命令。只开启 binlog 或保留同机卷不能证明 RPO。
2. MinIO/文件：对象备份、图片接入积压、导出目录和数据关联；校验清单、对象数与 hash；数据库与文件一致性恢复点。
3. 配置：全部配置版本/快照、Compose、Nginx、证书和部署版本；应用回滚与数据库回退条件分开说明。
4. 模型：模型文件、版本、hash、依赖和挂载路径；生产模型及标定数据缺失时注明无法验证。
5. 环境配置：`.env`、KMS/密钥引用和访问权限，独立加密备份，禁止明文打包进普通交付归档。
6. 恢复演练：在隔离目录/新卷恢复，不覆盖当前数据；核对管理员登录、历史、图片、配置、MES 待发和导出。记录开始/完成时间、最后可恢复事务时间及 RTO/RPO；未演练不得宣称达标。

建立 `docs/DEPLOYMENT.md`，包含服务器环境、Docker 安装与版本检查、环境变量、首次启动、数据库初始化、管理员创建、日志、监控、备份、升级、停止和恢复。Docker 安装与操作命令在实现时查官方文档并按目标平台核验。

运维边界：健康端点不等同 Prometheus/Grafana/ELK；监控必须检查采集、面板和告警。单机 Compose 不等同高可用。停止说明默认保留数据卷，删除卷只作为明确标注的独立破坏性操作，不进入常规停机/升级流程。

## 7. 最终需求矩阵及清理规则

实现步骤重新逐项核验 `docs/REQUIREMENTS_TRACEABILITY.md` 的 79 个显式 FR。最终每项只允许：

| 状态 | 判定规则 |
| --- | --- |
| DONE | 对应功能完整，相关检查及要求的运行/验收证据通过，无未完成子项 |
| PARTIAL | 已有可用部分，但实现、UI、测试或目标环境证据不完整；写明缺哪一项及下一步 |
| BLOCKED | 受正式协议、硬件、外部环境、权责方决策等阻断，写明原因、所需输入和解除条件 |

矩阵保留实际前后端文件、API/WS、表及测试/报告路径，新增原因与证据栏。不存在的规划路径必须替换或注明未实现；不能仅凭测试文件存在标记 DONE。FR-RT-05 不补造。

79 个 FR 不包含全部非功能验收；另设非功能表检查性能、TLS/WSS、KMS、结构化日志/监控、备份恢复和冗余。历史测试结果注明阶段和环境，不能直接继承为本轮通过。

代码清理先查引用再删：缓存/临时产物、调试输出、无效 TODO、重复未接入骨架和硬编码凭据。保留正式 Mock Adapter、测试 fixture、基准脚本与必要 CLI 输出。当前 `print` 命中主要为管理员脚本结果及基准报告，不应一律删除。未发现具体缺陷的已通过模块不重构。

## 8. 验证计划和完成门槛

| 验证 | 计划命令或场景 | 通过证据 |
| --- | --- | --- |
| 前端 | `npm ci`、`npm run lint`、`npm run build`、`npm test` | 类型/构建无错误、单测全部通过；修复 canvas 环境，不能跳过失败套件 |
| 后端 | `python -m ruff check app tests scripts alembic`、`python -m pytest` | 原有回归和针对部署缺口的测试全部通过 |
| Compose | `docker compose config --quiet`、各环境覆盖配置校验、`docker compose build` | 模板、真实本地配置和 TLS 配置可解析；输出不泄露渲染后的秘密 |
| 空库迁移 | 新 MySQL 库 `alembic upgrade head`，再执行一次；检查 head/表/索引 | 结构完整、重复执行无损、应用可使用；SQLite 不替代 MySQL |
| 容器运行 | 首次 `docker compose up -d`、健康检查、停止与重启 | 两 API、两网关、独立推理及基础服务实际运行；初始化退出成功 |
| REST smoke | 通过 Nginx 登录→me→配置→历史/详情→统计→系统→MES→导出/下载 | 真实 HTTP 状态及内容断言，匿名/操作员/管理员权限负例 |
| WS smoke | Nginx Upgrade、HELLO/PING/PONG、另一容器生成 FRAME/INFER | PASS/NG 入库与页面一致；两网关、重连和旧 token 拒绝 |
| 存储/任务 | MinIO 写读、签名过期/越权、Worker 导出、Beat/MES 重试 | 实际对象和任务状态，不能仅断言任务已创建 |
| UI 演示 | 浏览器走完整用户链路，检查图片、标注、历史详情及角色菜单 | 浏览器观察与必要截图；无浏览器环境则单列限制 |
| 恢复/故障 | API/网关重启、Redis 短断、MES 失败、独立卷恢复 | 检测不重复、任务可恢复、数据/对象一致；记录 RTO/RPO |

最后必须再次执行用户指定的五项：frontend build、backend tests、docker compose config、database migration、API smoke tests。命令、时间、版本、环境、退出码和失败修复写入 `docs/PHASE9_VALIDATION_REPORT.md`。

性能：MySQL 100,000 条记录、50 并发实际 HTTP 请求，分别记录历史含分页 ≤1s、HTTP P95 ≤300ms；WS 正式口径为采集帧时间至浏览器渲染 ≤200ms，broker 到接收时间只作为诊断；实时页 ≥24 FPS，连续 100 张单图推理 ≤5s。保留本地 SQLite 基线，不能当生产结果。真实 AI 准确率必须使用真实模型和独立验收集。

五项终检全部通过只是必要条件。存在阻断性的 FR、非功能项或真实运行失败时，项目仍不能标记完成。基础设施不可用时继续完成可独立执行的工作并记录 BLOCKED，不能以跳过检查、Mock 或静态配置解析替代运行证据。

## 9. 最终交付内容索引（验证后填写）

最终报告 `docs/PHASE9_FINAL_REPORT.md` 按用户要求输出下列 14 项；设计步骤不预填完成结论。

| 序号 | 内容 | 证据来源/交付位置 |
| --- | --- | --- |
| 1 | 项目最终目录 | 过滤缓存/依赖/秘密后的真实目录清单 |
| 2 | 已完成功能 | 需求矩阵 DONE 与对应测试证据 |
| 3 | 未完成功能 | PARTIAL/BLOCKED 原因、开放问题、非功能缺口 |
| 4 | Docker 服务 | Compose 服务、镜像、入口、端口、卷及健康状态 |
| 5 | 数据库表 | Alembic head、实际数据库表及模型对应，含 alembic_version |
| 6 | REST API | 运行时导出的 OpenAPI 和权限清单，避免手写遗漏 |
| 7 | WebSocket 协议 | 实际路径、鉴权、消息外壳/示例、心跳、重连和序号语义 |
| 8 | 测试情况 | PHASE9_VALIDATION_REPORT、日志/退出码及限制 |
| 9 | 性能测试 | PERFORMANCE_REPORT，明确数据库、样本、并发和硬件 |
| 10 | 部署步骤 | DEPLOYMENT 与 BACKUP_RESTORE |
| 11 | 默认 Mock 演示方法 | 首次安全配置、compose up、登录、图片/判定/历史/详情/统计/配置/MES Mock/系统管理 |
| 12 | 接入真实 AI 模型 | 现有 Provider 入口、输入输出契约、版本/模型卷、运行依赖及实测要求 |
| 13 | 接入真实相机 | 共享目录/接图入口、文件完整性、命名幂等、相机 SDK/光源/ROI/标定待提供项 |
| 14 | 接入真实 MES | 现有 HttpMesClient、配置/鉴权、幂等重试、协议映射与失败验证 |

## 10. 本步骤结束状态

- 已检查当前部署、推理/实时、文件、初始化、MES/任务、前端显示及现有文档的关键实现。
- 已形成最小必要改动、服务拓扑、交付清单和验证门槛。
- 已记录环境与正式验收缺口；未读取或输出真实 `.env` 内容。
- 本步骤只修改设计、阶段状态和开放问题文档；没有修改业务代码、启动容器或执行最终测试。
- 用户查看本设计后再进入实现；实现完成后再次暂停，随后进行完整验证。
