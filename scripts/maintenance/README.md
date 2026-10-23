# scripts/maintenance

一次性运维脚本与维护工具。

这些脚本**不被任何业务代码 import**，仅供人工排查问题 / 数据修复时按需执行。

## 分类

| 前缀 | 用途 |
|---|---|
| `check_*.py` | 数据一致性检查（重复项、缺失代码、时间格式、字段完整性等） |
| `fix_*.py` | 数据修复（补齐股票代码、清理空值等） |
| `verify_*.py` | 导入/同步结果校验 |
| `test_*.py` | 手工联调脚本（需后端服务已启动） |
| `create_admin.py` / `reset_admin_password.py` | 管理员账号初始化与密码重置 |
| `batch_import_stock_mappings.py` | 批量导入股票名称↔代码映射 |
| `generate_complete_stock_map*.py` | 生成完整股票映射表 |
| `*_stock_mappings.py` | 映射表补充 / 重同步 |
| `lazy_db_init_refactor.py` | 一次性 AST 重构脚本（已执行完毕，保留以备追溯） |

## 注意

- 脚本内含历史逻辑，**不保证随主代码演进保持同步**，使用前请阅读源码确认。
- 执行前建议先备份数据库（`POST /api/system/database/backup`）。
- 部分脚本会直接连接 MongoDB，请确保 `.env` 中的连接配置正确。

## 正式测试套件

项目已有正式的自动化测试，**不需要**依赖这些一次性脚本：

```bash
pytest                                  # 后端（tests/）
cd frontend && npm test                 # 前端（frontend/src/__tests__/）
```

详见 `tests/README.md` 与 `frontend/src/__tests__/README.md`。
