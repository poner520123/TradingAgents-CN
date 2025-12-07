// 市场参数规范化：只支持A股
export const normalizeMarketForAnalysis = (market: any): 'A股' => {
  return 'A股'
}

/**
 * 将交易所代码转换为市场类型
 * @param exchangeCode 交易所代码（如 "sz", "sh", "bj", "sse", "szse", "bse"）
 * @returns 市场类型（"A股"）
 */
export const exchangeCodeToMarket = (exchangeCode: string): 'A股' => {
  return 'A股'
}

/**
 * 根据股票代码判断市场类型
 * @param stockCode 股票代码
 * @returns 市场类型（"A股"）
 */
export const getMarketByStockCode = (stockCode: string): 'A股' => {
  return 'A股'
}

export default {
  normalizeMarketForAnalysis,
  exchangeCodeToMarket,
  getMarketByStockCode
}

