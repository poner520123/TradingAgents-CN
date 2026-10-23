/**
 * 测试辅助：Pinia 实例管理。
 */
import { createPinia, setActivePinia, type Pinia } from 'pinia'

/** 为单个用例创建并激活一个全新的 Pinia 实例。 */
export function setupPinia(): Pinia {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}
