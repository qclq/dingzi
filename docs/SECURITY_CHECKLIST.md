# 安全检查清单

状态：待 Phase 8 验证步骤填写。

| 检查项 | 验证方式 | 状态 |
| --- | --- | --- |
| JWT Secret 不使用占位符 | Settings 校验 | PASS |
| 数据库/MES/MinIO 密钥不出现在响应或日志 | API 与日志/CSV 检查 | 待测 |
| SQL 注入 | ORM 参数化及恶意关键词 API 测试 | 待测 |
| XSS | 用户名/日志消息 Vue 转义检查 | 待测 |
| 越权访问 | 系统管理/配置 operator 403，统计/历史 operator 可访问 | PASS |
| 文件越权 | 签名 URL、检测归属与过期验证 | 待测 |
| 敏感字段 | MES 配置响应不返回 Token 的定向测试 | PARTIAL |
