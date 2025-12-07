/**
 * 股票名称代码映射管理工具
 * 用于管理股票名称和代码的映射关系，并提供快速查询功能
 */

// 本地存储键名
const STOCK_NAME_MAP_KEY = 'stock_name_map'
const STOCK_CODE_MAP_KEY = 'stock_code_map'
const STOCK_MAP_UPDATE_TIME_KEY = 'stock_map_update_time'

// 映射更新间隔（毫秒） - 7天
const UPDATE_INTERVAL = 7 * 24 * 60 * 60 * 1000

/**
 * 获取股票名称（通过股票代码）
 * @param code 股票代码
 * @returns 股票名称，如果未找到则返回代码
 */
export function getStockNameByCode(code: string): string {
  if (!code) return code
  
  const codeMap = getCodeMap()
  return codeMap[code] || code
}

/**
 * 获取股票代码（通过股票名称）
 * @param name 股票名称
 * @returns 股票代码，如果未找到则返回名称
 */
export function getStockCodeByName(name: string): string {
  if (!name) return name
  
  const nameMap = getNameMap()
  return nameMap[name] || name
}

/**
 * 获取名称到代码的映射表
 * @returns 名称到代码的映射表
 */
export function getNameMap(): Record<string, string> {
  try {
    const data = localStorage.getItem(STOCK_NAME_MAP_KEY)
    return data ? JSON.parse(data) : {}
  } catch (error) {
    console.error('获取名称映射表失败:', error)
    return {}
  }
}

/**
 * 获取代码到名称的映射表
 * @returns 代码到名称的映射表
 */
export function getCodeMap(): Record<string, string> {
  try {
    const data = localStorage.getItem(STOCK_CODE_MAP_KEY)
    return data ? JSON.parse(data) : {}
  } catch (error) {
    console.error('获取代码映射表失败:', error)
    return {}
  }
}

/**
 * 更新股票名称代码映射表
 * @param stocks 股票列表数据
 */
export function updateStockMaps(stocks: Array<{ code: string; name: string }>) {
  if (!stocks || stocks.length === 0) return
  
  // 创建映射表
  const nameMap: Record<string, string> = {}
  const codeMap: Record<string, string> = {}
  
  stocks.forEach(stock => {
    if (stock.code && stock.name) {
      nameMap[stock.name] = stock.code
      codeMap[stock.code] = stock.name
    }
  })
  
  // 保存到localStorage
  try {
    localStorage.setItem(STOCK_NAME_MAP_KEY, JSON.stringify(nameMap))
    localStorage.setItem(STOCK_CODE_MAP_KEY, JSON.stringify(codeMap))
    localStorage.setItem(STOCK_MAP_UPDATE_TIME_KEY, Date.now().toString())
    console.log(`✅ 股票映射表已更新，共 ${stocks.length} 条数据`)
  } catch (error) {
    console.error('保存股票映射表失败:', error)
  }
}

/**
 * 检查是否需要更新映射表
 * @returns 是否需要更新
 */
export function shouldUpdateStockMaps(): boolean {
  try {
    const lastUpdateTime = localStorage.getItem(STOCK_MAP_UPDATE_TIME_KEY)
    if (!lastUpdateTime) return true
    
    const now = Date.now()
    const lastUpdate = parseInt(lastUpdateTime, 10)
    return now - lastUpdate > UPDATE_INTERVAL
  } catch (error) {
    console.error('检查映射表更新时间失败:', error)
    return true
  }
}

/**
 * 清除股票映射表
 */
export function clearStockMaps() {
  try {
    localStorage.removeItem(STOCK_NAME_MAP_KEY)
    localStorage.removeItem(STOCK_CODE_MAP_KEY)
    localStorage.removeItem(STOCK_MAP_UPDATE_TIME_KEY)
    console.log('✅ 股票映射表已清除')
  } catch (error) {
    console.error('清除股票映射表失败:', error)
  }
}
