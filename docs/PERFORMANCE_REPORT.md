# 性能报告

状态：待 Phase 8 验证步骤填写。

## 测试方法

- 本地回归基线：`backend/scripts/benchmark_history.py` 在临时 SQLite 数据库生成 100,000 条检测记录，预热后执行 100 次深分页查询并记录 P50/P95。
- HTTP 与 WebSocket：由 Phase 8 联调测试记录单进程时延；不得将此结果标记为 50 并发或车间网络时延。
- 生产验收：MySQL 8、Redis、50 并发、真实容器网络和对象存储可用后重新测量。

| 指标 | 目标 | 本地结果 | MySQL/容器结果 | 状态 |
| --- | --- | --- | --- | --- |
| HTTP API P95 | ≤300 ms | 待测 | BLOCKED | BLOCKED |
| 100k 历史查询 | ≤1 s | SQLite P50 118.11 ms, P95 129.05 ms | BLOCKED | PARTIAL |
| 并发用户 | ≥50 | BLOCKED | BLOCKED | BLOCKED |
| WebSocket P95 | ≤200 ms | 待测 | BLOCKED | BLOCKED |

2026-09-03 本地结果来自 100 个深分页查询样本。SQLite 内存库不代表 MySQL 8、容器网络、对象存储或 50 并发验收。
