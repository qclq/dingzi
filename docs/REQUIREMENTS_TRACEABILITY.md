# 需求追踪矩阵

> 状态枚举：`TODO`（未开发）、`IN_PROGRESS`（开发中）、`BLOCKED`（被开放问题阻塞）、`TESTED`（已实现并通过测试）、`DONE`（验收完成）。  
> Phase 0 尚未编写业务代码，因此所有 FR 保持 `TODO` 或 `BLOCKED`。下列实现位置是依据设计方案规划的目标位置，不代表文件已经实现。  
> 共收录需求说明书中的 **79 个显式 FR 编号**。编号 `FR-RT-05` 在原文缺失，记录于 `OPEN_QUESTIONS.md`，不作为已定义 FR 计数。

| 需求编号 | 需求说明 | 所属模块 | 前端实现位置 | 后端实现位置 | API / 协议 | 数据库 | 测试文件 | 开发状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR-AUTH-01 | 账号密码登录并由后端验证 | 登录与权限 | `frontend/src/views/LoginView.vue` | `backend/app/api/v1/auth.py` | `POST /api/v1/auth/login` | `users`; `audit_logs` | `backend/tests/test_auth.py` | TESTED |
| FR-AUTH-02 | 返回 access token（8h）和 refresh token（7d） | 登录与权限 | `frontend/src/stores/auth.ts` | `backend/app/services/auth.py` | `POST /api/v1/auth/login`; `POST /api/v1/auth/refresh` | `refresh_tokens` | `backend/tests/test_auth.py` | TESTED |
| FR-AUTH-03 | Token 持久化并由 Axios 自动注入 Authorization | 登录与权限 | `frontend/src/api/http.ts`; `frontend/src/stores/auth.ts` | `backend/app/core/deps.py` | `Authorization: Bearer`; `POST /api/v1/auth/refresh` | `refresh_tokens` | `backend/tests/test_auth.py`; `frontend/src/api/http.test.ts`; `frontend/src/stores/auth.test.ts` | TESTED |
| FR-AUTH-04 | 登录失败显示密码错误、账号锁定或服务异常 | 登录与权限 | `frontend/src/views/LoginView.vue` | `backend/app/api/v1/auth.py`; `backend/app/services/auth.py` | 统一错误响应 | `users`; `audit_logs` | `backend/tests/test_auth.py` | TESTED |
| FR-AUTH-05 | 记住登录状态后 7 天内自动登录 | 登录与权限 | `frontend/src/stores/auth.ts`; `frontend/src/api/http.ts` | `backend/app/services/auth.py` | `POST /api/v1/auth/refresh` | `refresh_tokens` | `backend/tests/test_auth.py`; `frontend/src/stores/auth.test.ts` | TESTED |
| FR-AUTH-06 | 路由守卫检查角色，越权跳转 `/403` | 登录与权限 | `frontend/src/router/index.ts` | `backend/app/core/deps.py` | 所有受保护接口 | `users` | `backend/tests/test_auth.py`; `frontend/src/router/auth-guard.test.ts` | TESTED |
| FR-AUTH-07 | 后端返回角色菜单，前端动态生成侧栏 | 登录与权限 | `frontend/src/layouts/AppLayout.vue`; `frontend/src/stores/auth.ts` | `backend/app/api/v1/me.py` | `GET /api/v1/me/menus` | `users` | `backend/tests/test_auth.py`; `frontend/src/stores/auth.test.ts` | TESTED |
| FR-AUTH-08 | 顶栏显示头像、姓名、角色和退出按钮 | 登录与权限 | `frontend/src/layouts/AppLayout.vue` | `backend/app/api/v1/me.py` | `GET /api/v1/me` | `users` | `backend/tests/test_auth.py` | TESTED |
| FR-AUTH-09 | 退出清除 Token 并跳转登录页 | 登录与权限 | `frontend/src/layouts/AppLayout.vue`; `frontend/src/stores/auth.ts` | `backend/app/api/v1/auth.py` | `POST /api/v1/auth/logout` | `refresh_tokens`; `audit_logs` | `backend/tests/test_auth.py`; `frontend/src/stores/auth.test.ts` | TESTED |
| FR-RT-01 | WS 原图/URL、Fabric.js 渲染、缩放标注和缺陷详情 | 实时检测-图像区 | `frontend/src/views/realtime/RealtimeView.vue` | `services/realtime-gateway/app/` | WS `frame`; WS `infer` | `detections`; `detection_files`; `defects` | `tests/e2e/realtime_image.spec.ts` | TODO |
| FR-RT-02 | 图片编号输入框 | 实时检测-产品信息 | `frontend/src/views/realtime/components/ProductInfo.vue` | `backend/app/api/v1/realtime.py` | `GET /api/v1/realtime/snapshot`; WS `frame` | `detections.image_id` | `frontend/tests/unit/product_info.spec.ts` | BLOCKED |
| FR-RT-03 | 显示操作员、检测时间和缺陷数 | 实时检测-产品信息 | `frontend/src/views/realtime/components/ProductInfo.vue` | `backend/app/api/v1/realtime.py` | Snapshot; WS `frame/infer` | `detections` | `tests/integration/test_realtime_snapshot.py` | TODO |
| FR-RT-04 | PASS 绿色、NG 红色总判定卡片 | 实时检测-产品信息 | `frontend/src/views/realtime/components/ResultCard.vue` | `services/decision-service/app/` | Snapshot; WS `infer` | `detections.result` | `tests/integration/test_decision_realtime.py` | BLOCKED |
| FR-RT-06 | 设备异常文字标红并弹窗 | 实时检测-告警 | `frontend/src/views/realtime/components/DevicePanel.vue` | `services/realtime-gateway/app/` | WS `device/alert` | `device_status`; `alerts` | `tests/e2e/device_alert.spec.ts` | TODO |
| FR-RT-07 | 弹窗展示异常类型、首次发生时间和建议处理 | 实时检测-告警 | `frontend/src/components/alerts/AlertDialog.vue` | `backend/app/schemas/alert.py` | WS `alert` | `alerts` | `frontend/tests/unit/alert_dialog.spec.ts` | BLOCKED |
| FR-RT-08 | 告警按 warning/error 分级并由 WS 触发 | 实时检测-告警 | `frontend/src/stores/realtime.ts` | `services/realtime-gateway/app/` | WS `alert` | `alerts.level` | `tests/integration/test_ws_alert.py` | BLOCKED |
| FR-RT-09 | 历史告警写入系统日志 | 实时检测-告警 | `frontend/src/views/system/logs/` | `backend/app/services/log_service.py` | WS `alert`; 日志查询 API 待定义 | `alerts`; 系统日志表待定义 | `backend/tests/services/test_alert_logging.py` | TODO |
| FR-RT-10 | 告警推送到外部系统 | 实时检测-告警 | `frontend/src/views/system/integrations/` | `services/mes-adapter/app/alerts.py` | 外部告警 API 待定义 | `alerts`; 集成配置待定义 | `tests/integration/test_external_alert.py` | BLOCKED |
| FR-HIS-01 | 历史表格包含选择、图片编号、时间、操作员、缺陷数、结果、操作 | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/api/v1/detections.py` | `GET /api/v1/detections` | `detections` | `backend/tests/test_history.py` | DONE |
| FR-HIS-02 | 按时间段和 PASS/NG 筛选 | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/repositories/detection.py` | `GET /api/v1/detections` | `detections.captured_at`; `result` | `backend/tests/test_history.py` | DONE |
| FR-HIS-03 | 默认按检测时间倒序 | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/repositories/detection.py` | `GET /api/v1/detections` | `detections.captured_at` 索引 | `backend/tests/test_history.py` | DONE |
| FR-HIS-04 | 默认 20 条，可切换 50/100 | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/api/v1/detections.py` | `page`; `page_size` | `detections` | `backend/tests/test_history.py` | DONE |
| FR-HIS-05 | 多选并批量导出 | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/api/v1/exports.py` | `POST /api/v1/exports` | `export_jobs` | `backend/tests/test_history.py` | DONE |
| FR-HIS-06 | 查看详情、下载图片和 JSON | 历史记录 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/api/v1/detections.py` | 详情、文件签名 URL | `detections`; `defects` | `backend/tests/test_history.py` | DONE |
| FR-HIS-D01 | 大图缩放并展示标注 | 历史详情 | `frontend/src/views/history/HistoryDetailView.vue` | `backend/app/api/v1/detections.py` | `GET /api/v1/detections/{id}` | `detections`; `defects` | `backend/tests/test_history.py` | DONE |
| FR-HIS-D02 | 缺陷列表展示类别、等级、置信度和尺寸 | 历史详情 | `frontend/src/views/history/HistoryDetailView.vue` | `backend/app/schemas/history.py` | `GET /api/v1/detections/{id}` | `defects` | `backend/tests/test_history.py` | DONE |
| FR-HIS-D03 | 展示 AI 推理原始 JSON | 历史详情 | `frontend/src/views/history/HistoryDetailView.vue` | `backend/app/api/v1/detections.py` | `GET /api/v1/detections/{id}` | `detections.raw_output` | `backend/tests/test_history.py` | DONE |
| FR-HIS-D04 | 总判定仅 PASS/NG | 历史详情 | `frontend/src/views/history/HistoryDetailView.vue` | `backend/app/schemas/history.py` | `GET /api/v1/detections/{id}` | `detections.result` | `backend/tests/test_history.py` | DONE |
| FR-HIS-D05 | 导出 PDF、关联 MES 工单 | 历史详情 | `frontend/src/views/history/HistoryDetailView.vue` | `backend/app/api/v1/exports.py`; `backend/app/api/v1/detections.py` | PDF 导出；MES 工单关联 | `export_jobs`; `detections.mes_work_order` | `backend/tests/test_history.py` | DONE |
| FR-HIS-07 | 当前查询结果导出 xlsx | 历史导出 | `frontend/src/views/history/HistoryListView.vue` | `backend/app/tasks/exports.py` | `POST /api/v1/exports`; `GET /api/v1/exports/{id}` | `export_jobs` | `backend/tests/test_history.py` | DONE |
| FR-AN-01 | 今日检测总数、不合格数、缺陷检出率 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `GET /api/v1/analytics/overview` | `analytics_hourly_aggregates` | `backend/tests/test_analytics.py` | TESTED |
| FR-AN-02 | 划痕/点蚀按日周月柱状对比 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `GET /api/v1/analytics/trends`; `GET /api/v1/analytics/defect-trend` | `analytics_hourly_aggregates` | `backend/tests/test_analytics.py` | TESTED |
| FR-AN-03 | 近 7～30 天缺陷率趋势 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `GET /api/v1/analytics/trends` | `analytics_hourly_aggregates` | `backend/tests/test_analytics.py` | TESTED |
| FR-AN-04 | 360° 圆周展开热力图 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `GET /api/v1/analytics/heatmap` | `analytics_heatmap_hourly_buckets` | `backend/tests/test_analytics.py` | TESTED |
| FR-AN-05 | 按类型×等级展示饼图占比 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `GET /api/v1/analytics/defect-distribution` | `analytics_hourly_aggregates` | `backend/tests/test_analytics.py` | TESTED |
| FR-AN-06 | 时间范围筛选，默认 7 天 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | `period`; `start_time`; `end_time` | `analytics_hourly_aggregates` | `frontend/src/api/analytics.test.ts` | TESTED |
| FR-AN-07 | 默认 60 秒自动刷新，可关闭 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | 统计查询接口 | 无直接持久化 | `frontend/src/api/analytics.test.ts` | TESTED |
| FR-AN-08 | 1080p 全屏大屏模式 | 数据统计 | `frontend/src/views/analytics/AnalyticsView.vue` | `backend/app/api/v1/analytics.py` | 统计查询接口 | 无直接持久化 | `frontend/src/router/auth-guard.test.ts` | TESTED |
| FR-CFG-T01 | 仅划痕、点蚀两种缺陷类型 | 参数配置-阈值 | `frontend/src/views/config/thresholds/` | `backend/app/schemas/enums.py` | 配置接口（路径待冻结） | `config_versions` | `backend/tests/schemas/test_defect_type.py` | BLOCKED |
| FR-CFG-T02 | 轻微≤阈值、严重>阈值 | 参数配置-阈值 | `frontend/src/views/config/thresholds/` | `services/decision-service/app/grading.py` | 配置接口 | `config_versions.payload_json` | `services/decision-service/tests/test_grading.py` | BLOCKED |
| FR-CFG-T03 | 阈值表格黑底白字 | 参数配置-阈值 | `frontend/src/views/config/thresholds/ThresholdConfigView.vue` | 无 | 无 | 无 | `frontend/tests/unit/threshold_style.spec.ts` | TODO |
| FR-CFG-T04 | 阈值行级启停 | 参数配置-阈值 | `frontend/src/views/config/thresholds/ThresholdConfigView.vue` | `backend/app/services/config_service.py` | 配置接口 | `config_versions` | `tests/integration/test_threshold_enable.py` | BLOCKED |
| FR-CFG-T05 | 阈值 0～100 mm、两位小数 | 参数配置-阈值 | `frontend/src/views/config/thresholds/ThresholdConfigView.vue` | `backend/app/schemas/config.py` | 配置接口 | `config_versions` | `backend/tests/schemas/test_threshold_validation.py` | TODO |
| FR-CFG-T06 | 轻微绿色、严重红色可视化条 | 参数配置-阈值 | `frontend/src/views/config/thresholds/components/LevelBar.vue` | 无 | 无 | 无 | `frontend/tests/unit/level_bar.spec.ts` | TODO |
| FR-CFG-T07 | 恢复默认并保存配置 | 参数配置-阈值 | `frontend/src/views/config/thresholds/ThresholdConfigView.vue` | `backend/app/services/config_service.py` | 配置更新接口 | `config_versions`; `audit_logs` | `tests/integration/test_threshold_save_reset.py` | BLOCKED |
| FR-CFG-Q01 | 类型×等级四条默认数量规则 | 参数配置-判定 | `frontend/src/views/config/judgement/` | `services/decision-service/app/rules.py` | 配置接口 | `config_versions` | `services/decision-service/tests/test_default_rules.py` | BLOCKED |
| FR-CFG-Q02 | 数量上限和行级启停 | 参数配置-判定 | `frontend/src/views/config/judgement/JudgementConfigView.vue` | `backend/app/schemas/config.py` | 配置接口 | `config_versions` | `tests/integration/test_judgement_config.py` | BLOCKED |
| FR-CFG-Q03 | 恢复默认并保存规则 | 参数配置-判定 | `frontend/src/views/config/judgement/JudgementConfigView.vue` | `backend/app/services/config_service.py` | 配置更新接口 | `config_versions`; `audit_logs` | `tests/integration/test_judgement_reset.py` | BLOCKED |
| FR-CFG-Q04 | 任一启用规则触发即 NG | 参数配置-判定 | `frontend/src/views/config/judgement/JudgementConfigView.vue` | `services/decision-service/app/rules.py` | WS `infer`; 配置接口 | `detections`; `config_versions` | `services/decision-service/tests/test_total_result.py` | BLOCKED |
| FR-CFG-R01 | Fabric.js 绘制矩形 ROI | 参数配置-ROI | `frontend/src/views/config/roi/RoiConfigView.vue` | `backend/app/schemas/config.py` | 配置接口 | `config_versions` | `frontend/tests/unit/roi_canvas.spec.ts` | TODO |
| FR-CFG-R02 | 最多 8 个 ROI | 参数配置-ROI | `frontend/src/views/config/roi/RoiConfigView.vue` | `backend/app/schemas/config.py` | 配置接口 | `config_versions` | `backend/tests/schemas/test_roi_limit.py` | TODO |
| FR-CFG-R03 | 刷新图片、清空、保存 ROI | 参数配置-ROI | `frontend/src/views/config/roi/RoiConfigView.vue` | `backend/app/services/config_service.py` | 参考图/配置接口待定义 | `config_versions`; `detection_files` | `tests/e2e/roi_config.spec.ts` | BLOCKED |
| FR-CFG-R04 | 像素 x/y/w/h 保存并转换 mm | 参数配置-ROI | `frontend/src/views/config/roi/RoiConfigView.vue` | `backend/app/services/calibration_service.py` | 配置接口 | `config_versions` | `backend/tests/services/test_roi_conversion.py` | BLOCKED |
| FR-CFG-CA01 | 输入 1 像素=N mm | 参数配置-标定 | `frontend/src/views/config/calibration/` | `backend/app/services/calibration_service.py` | 配置接口 | `config_versions` | `backend/tests/services/test_calibration.py` | BLOCKED |
| FR-CFG-CA02 | 生成已知尺寸参考物标定图 | 参数配置-标定 | `frontend/src/views/config/calibration/CalibrationView.vue` | `backend/app/api/v1/calibration.py` | 标定图接口待定义 | `detection_files`; `config_versions` | `tests/integration/test_calibration_image.py` | BLOCKED |
| FR-CFG-CA03 | 保存标定参数 | 参数配置-标定 | `frontend/src/views/config/calibration/CalibrationView.vue` | `backend/app/services/config_service.py` | 配置更新接口 | `config_versions`; `audit_logs` | `tests/integration/test_calibration_save.py` | BLOCKED |
| FR-CFG-CM01 | 按定子型号管理多套相机/光源方案 | 参数配置-相机光源 | `frontend/src/views/config/camera/` | `backend/app/services/device_config_service.py` | 相机方案 API 待定义 | 相机方案表/配置载荷待定义 | `tests/integration/test_camera_profiles.py` | BLOCKED |
| FR-CFG-CM02 | 方案含曝光、增益、触发模式、光源亮度 | 参数配置-相机光源 | `frontend/src/views/config/camera/CameraProfileForm.vue` | `backend/app/schemas/device_config.py` | 相机方案 API 待定义 | 相机方案表/配置载荷待定义 | `backend/tests/schemas/test_camera_profile.py` | BLOCKED |
| FR-CFG-CM03 | 新建、加载、编辑、删除方案 | 参数配置-相机光源 | `frontend/src/views/config/camera/CameraConfigView.vue` | `backend/app/api/v1/device_configs.py` | 相机方案 API 待定义 | 相机方案表/配置载荷待定义 | `tests/e2e/camera_profiles.spec.ts` | BLOCKED |
| FR-CFG-M01 | 置信度阈值 0.1～0.99 | 参数配置-模型 | `frontend/src/views/config/model/ModelConfigView.vue` | `services/inference-service/app/config.py` | 配置接口 | `config_versions` | `services/inference-service/tests/test_confidence.py` | TODO |
| FR-CFG-M02 | NMS 阈值 0.1～0.9 | 参数配置-模型 | `frontend/src/views/config/model/ModelConfigView.vue` | `services/inference-service/app/config.py` | 配置接口 | `config_versions` | `services/inference-service/tests/test_nms.py` | TODO |
| FR-CFG-M03 | 推理设备 CPU/GPU | 参数配置-模型 | `frontend/src/views/config/model/ModelConfigView.vue` | `services/inference-service/app/config.py` | 配置接口 | `config_versions` | `services/inference-service/tests/test_device_selection.py` | TODO |
| FR-SYS-U01 | 用户列表含账号、姓名、角色、状态、最后登录 | 系统管理-用户 | `frontend/src/views/system/users/UserListView.vue` | `backend/app/api/v1/users.py` | `GET /api/v1/system/users` | `users` | `backend/tests/api/test_users_list.py` | BLOCKED |
| FR-SYS-U02 | 用户增删改、启停 | 系统管理-用户 | `frontend/src/views/system/users/` | `backend/app/api/v1/users.py` | POST/PUT 已定义；DELETE/启停待定义 | `users`; `audit_logs` | `tests/e2e/user_management.spec.ts` | BLOCKED |
| FR-SYS-U03 | 角色仅管理员和操作员 | 系统管理-用户 | `frontend/src/views/system/users/UserForm.vue` | `backend/app/schemas/enums.py` | 用户创建/更新接口 | `users.role` | `backend/tests/schemas/test_role_enum.py` | TODO |
| FR-SYS-U04 | 重置密码发送到预留邮箱 | 系统管理-用户 | `frontend/src/views/system/users/UserListView.vue` | `backend/app/services/password_reset_service.py` | 密码重置 API 待定义 | `users`; 重置令牌表待定义 | `tests/integration/test_password_reset.py` | BLOCKED |
| FR-SYS-U05 | 错误密码 5 次锁定 30 分钟 | 系统管理-用户 | `frontend/src/views/auth/LoginView.vue` | `backend/app/services/auth_service.py` | `POST /api/v1/auth/login` | `users`; `audit_logs` | `backend/tests/services/test_account_lock.py` | TODO |
| FR-SYS-L01 | 操作日志记录操作者、时间和变更 | 系统管理-日志 | `frontend/src/views/system/logs/AuditLogView.vue` | `backend/app/services/audit_service.py` | `GET /api/v1/system/audit-logs` | `audit_logs` | `backend/tests/services/test_audit_log.py` | TODO |
| FR-SYS-L02 | 系统日志记录相机、推理、磁盘告警 | 系统管理-日志 | `frontend/src/views/system/logs/SystemLogView.vue` | `backend/app/services/log_service.py` | 系统日志 API 待定义 | 系统日志表待定义 | `tests/integration/test_system_logs.py` | BLOCKED |
| FR-SYS-L03 | 按时间、级别、来源筛选 | 系统管理-日志 | `frontend/src/views/system/logs/LogFilters.vue` | `backend/app/api/v1/logs.py` | 日志查询接口（部分定义） | `audit_logs`; 系统日志表 | `backend/tests/api/test_log_filters.py` | BLOCKED |
| FR-SYS-L04 | 导出 CSV | 系统管理-日志 | `frontend/src/views/system/logs/` | `services/worker-maintenance/app/exports.py` | 日志导出 API 待定义 | `audit_logs`; 系统日志表 | `tests/integration/test_log_csv_export.py` | BLOCKED |
| FR-SYS-L05 | 日志保留 180 天并自动清理 | 系统管理-日志 | `frontend/src/views/system/logs/` | `services/worker-maintenance/app/log_cleanup.py` | 无直接接口 | `audit_logs`; 系统日志表 | `services/worker-maintenance/tests/test_log_cleanup.py` | BLOCKED |
| FR-SYS-M01 | 配置 MES URL 和 token | 系统管理-MES | `frontend/src/views/system/mes/MesConfigView.vue` | `services/mes-adapter/app/config.py` | MES 配置 API 待定义 | MES 配置表/配置版本待定义 | `tests/integration/test_mes_config.py` | BLOCKED |
| FR-SYS-M02 | 自动上报开关 | 系统管理-MES | `frontend/src/views/system/mes/MesConfigView.vue` | `services/mes-adapter/app/config.py` | MES 配置 API 待定义 | MES 配置表/配置版本待定义 | `tests/integration/test_mes_auto_report.py` | BLOCKED |
| FR-SYS-M03 | 测试连接并反馈 HTTP 状态码 | 系统管理-MES | `frontend/src/views/system/mes/MesConfigView.vue` | `backend/app/api/v1/mes.py` | `POST /api/v1/system/mes/test-connection` | `audit_logs` | `backend/tests/api/test_mes_connection.py` | TODO |
| FR-SYS-M04 | 上报图片编号、判定、时间、缺陷数 | 系统管理-MES | `frontend/src/views/history/HistoryDetailView.vue` | `services/mes-adapter/app/reporter.py` | MES 外部协议待确认 | `detections`; `mes_deliveries` | `services/mes-adapter/tests/test_payload.py` | BLOCKED |
| FR-SYS-F01 | 原图默认保留 90 天 | 系统管理-文件 | `frontend/src/views/system/files/FilePolicyView.vue` | `services/worker-maintenance/app/file_cleanup.py` | 文件策略 API 待定义 | 文件策略表/配置版本待定义 | `services/worker-maintenance/tests/test_retention.py` | BLOCKED |
| FR-SYS-F02 | 配额达到上限时清理最旧文件 | 系统管理-文件 | `frontend/src/views/system/files/FilePolicyView.vue` | `services/worker-maintenance/app/file_cleanup.py` | 文件策略 API 待定义 | `detection_files`; 文件策略配置 | `services/worker-maintenance/tests/test_quota_cleanup.py` | TODO |
| FR-SYS-F03 | 每日 02:00 自动清理 | 系统管理-文件 | `frontend/src/views/system/files/FilePolicyView.vue` | `services/worker-maintenance/app/schedules.py` | 无直接接口 | `detection_files`; `audit_logs` | `services/worker-maintenance/tests/test_cleanup_schedule.py` | TODO |

## 追踪完整性检查

- AUTH：9 项
- RT：9 项（原文缺少 `FR-RT-05`）
- HIS：12 项（列表/导出 7 项，详情 5 项）
- AN：8 项
- CFG：26 项
- SYS：15 项
- 合计：79 项

每次实现、接口冻结或测试完成后必须同步更新本表。只有实现完成且对应测试实际通过，状态才可改为 `TESTED`；验收完成后才可改为 `DONE`。

