/**
 * 股票名称到代码的映射工具
 * 通过后端API获取股票名称和代码的映射关系
 */

import { ref } from 'vue'

// 定义股票名称到代码的映射类型
export interface StockNameCodeMap {
  [stockName: string]: string
}

// 股票名称到代码的映射对象
const stockNameCodeMap = ref<StockNameCodeMap>({})

// 是否已经加载完成
const isLoaded = ref(false)

/**
 * 从后端API加载股票名称到代码的映射
 */
export const loadStockNameCodeMap = async (): Promise<StockNameCodeMap> => {
  if (isLoaded.value && Object.keys(stockNameCodeMap.value).length > 0) {
    return stockNameCodeMap.value
  }

  try {
    // 通过API获取映射列表，支持分页
    let allMaps: { name: string; code: string }[] = []
    let page = 1
    const pageSize = 1000
    let hasMore = true

    // 循环获取所有映射数据
    while (hasMore) {
      const response = await fetch(`/api/stock-map/maps?skip=${(page - 1) * pageSize}&limit=${pageSize}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch stock map: ${response.status}`)
      }
      
      const data = await response.json()
      const maps = data.data || []
      allMaps = [...allMaps, ...maps]
      
      // 检查是否还有更多数据
      hasMore = allMaps.length < data.total
      page++
    }
    
    // 构建映射对象
    const map: StockNameCodeMap = {}
    allMaps.forEach(item => {
      if (item.name && item.code) {
        map[item.name] = item.code
      }
    })
    
    stockNameCodeMap.value = map
    isLoaded.value = true
    
    console.log(`✅ 成功从API加载股票名称到代码映射，共 ${Object.keys(map).length} 条记录`)
    return map
  } catch (error) {
    console.error('❌ 从API加载股票名称到代码映射失败:', error)
    return {}
  }
}

/**
 * 根据股票名称获取股票代码
 * @param stockName 股票名称
 * @returns 股票代码，如果找不到返回undefined
 */
export const getStockCodeByName = async (stockName: string): Promise<string | undefined> => {
  try {
    // 直接调用API获取单个股票代码
    const response = await fetch(`/api/stock-map/codes?name=${encodeURIComponent(stockName)}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch stock code: ${response.status}`)
    }
    
    const data = await response.json()
    return data.found ? data.code : undefined
  } catch (error) {
    console.error(`❌ 根据股票名称获取股票代码失败: ${error}`)
    return undefined
  }
}

/**
 * 根据股票名称列表批量获取股票代码
 * @param stockNames 股票名称列表
 * @returns 股票名称到代码的映射对象
 */
export const getStockCodesByNames = async (stockNames: string[]): Promise<StockNameCodeMap> => {
  try {
    // 调用API批量获取股票代码
    const response = await fetch('/api/stock-map/codes/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ names: stockNames })
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch stock codes: ${response.status}`)
    }
    
    const data = await response.json()
    return data
  } catch (error) {
    console.error(`❌ 批量获取股票代码失败: ${error}`)
    return {}
  }
}

/**
 * 初始化股票名称到代码的映射
 * 在应用启动时调用，确保映射已加载
 */
export const initStockNameCodeMap = async (): Promise<void> => {
  await loadStockNameCodeMap()
}

// 导出全局映射对象
export { stockNameCodeMap, isLoaded }
