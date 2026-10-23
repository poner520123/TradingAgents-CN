/**
 * 配置管理相关类型定义。
 *
 * ⚠️ 单一真源说明
 * ---------------------------------------------------------------------------
 * 本文件此前**重复定义**了 LLMProvider / LLMConfig / DataSourceConfig /
 * DatabaseConfig / SystemConfig / ConfigTestRequest / ConfigTestResponse，
 * 且与 ``@/api/config`` 中的同名类型**结构已经分叉**
 * （例如 ``LLMProvider.extra_config`` 的形状不同、``api_key`` 字段有无之别），
 * 属于典型的"双份定义 → 静默不一致"隐患。
 *
 * 现在统一以 ``@/api/config``（真正描述后端接口载荷的模块）为唯一真源，
 * 本文件仅做**类型级 re-export**：
 *   - ``export type`` 在编译期被完全擦除，不会产生任何运行时依赖；
 *   - ``from '@/types/config'`` 与 ``from '@/api/config'`` 两条导入路径继续可用；
 *   - 两侧类型从此永远一致。
 */

export type {
  LLMProvider,
  LLMConfig,
  DataSourceConfig,
  MarketCategory,
  DataSourceGrouping,
  DatabaseConfig,
  SystemConfig,
  ConfigTestRequest,
  ConfigTestResponse,
  SettingMeta,
} from '@/api/config'
