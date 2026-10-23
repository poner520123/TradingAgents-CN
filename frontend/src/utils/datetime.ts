/**
 * 日期时间工具函数
 * 统一处理时间转换和显示
 *
 * 处理逻辑：
 * 1. 如果时间字符串包含时区信息（+08:00 或 Z），直接使用
 * 2. 🔥 如果时间字符串没有时区信息，假定为 UTC+8 时间（后端已经入库为 UTC+8）
 * 3. 最终统一显示为中国时区（Asia/Shanghai）
 *
 * 注意：后端要求所有入库数据都是 UTC+8 时间，但可能没有时区标志
 */

/** 默认的完整日期时间格式选项。 */
const DEFAULT_DATETIME_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
}

/** 仅日期部分的格式选项。 */
const DATE_ONLY_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
}

/** 仅时间部分的格式选项。 */
const TIME_ONLY_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: 'Asia/Shanghai',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
}

/**
 * 归一化时间字符串，产出可被 `new Date()` 正确解析的 ISO 串。
 *
 * - 数字入参按秒/毫秒时间戳处理（小于 1e10 视为秒）
 * - 修复 "YYYY-MM-DD  HH:MM"（双空格、无秒）等非标准格式
 * - 无时区标识时按 UTC+8 补齐
 *
 * @returns 归一化后的字符串；无法识别时返回 null
 */
function normalizeTimeString(dateStr: string | number | null | undefined): string | null {
  if (dateStr === null || dateStr === undefined || dateStr === '') {
    return null
  }

  let timeStr: string

  // 处理时间戳（秒或毫秒）
  if (typeof dateStr === 'number') {
    // 如果是秒级时间戳（小于 10000000000），转换为毫秒
    const timestamp = dateStr < 10000000000 ? dateStr * 1000 : dateStr
    timeStr = new Date(timestamp).toISOString()
  } else {
    timeStr = String(dateStr).trim()

    // 修复格式：支持各种时间格式
    // 格式1: "YYYY-MM-DD  HH:MM"（两个空格，无秒数）
    // 格式2: "YYYY-MM-DD HH:MM"（一个空格，无秒数）
    // 格式3: "YYYY-MM-DD HH:MM:SS"（带秒数）
    if (timeStr.match(/^\d{4}-\d{2}-\d{2}\s{1,2}\d{2}:\d{2}(:\d{2})?$/)) {
      // 将空格替换为T
      timeStr = timeStr.replace(/\s{1,2}/, 'T')
      // 如果没有秒数，添加秒数
      if (!timeStr.match(/:\d{2}:\d{2}$/)) {
        timeStr += ':00'
      }
      // 添加时区信息
      if (!timeStr.endsWith('Z') && !timeStr.includes('+') && !timeStr.includes('-', 10)) {
        timeStr += '+08:00'
      }
      console.debug('[时间处理] 修复时间格式:', String(dateStr), '->', timeStr)
    }
  }

  // 检查时间字符串是否包含时区信息
  const hasTimezone = timeStr.endsWith('Z') ||
                     timeStr.includes('+') ||
                     timeStr.includes('-', 10) // 日期后面的 - 才是时区标识

  // 🔥 如果没有时区标识，假定为 UTC+8 时间（后端已经入库为 UTC+8），添加 +08:00 后缀
  if (timeStr.match(/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/) && !hasTimezone) {
    console.debug('[时间处理] 检测到不带时区的时间字符串，添加 +08:00:', timeStr)
    timeStr += '+08:00'
  }

  return timeStr
}

/**
 * 按**给定**的格式选项格式化时间（不再与默认选项合并）。
 *
 * 与 {@link formatDateTime} 的区别：这里完全由调用方决定输出哪些字段，
 * 因此 formatDate / formatTime 才能真正只输出日期 / 时间部分。
 */
function formatWithOptions(
  dateStr: string | number | null | undefined,
  options: Intl.DateTimeFormatOptions
): string {
  if (dateStr === null || dateStr === undefined || dateStr === '') {
    return '-'
  }

  try {
    const timeStr = normalizeTimeString(dateStr)
    if (!timeStr) {
      return '-'
    }

    const date = new Date(timeStr)
    if (isNaN(date.getTime())) {
      console.warn('无效的时间格式:', dateStr)
      return String(dateStr)
    }

    return date.toLocaleString('zh-CN', options)
  } catch (e) {
    console.error('时间格式化错误:', e, dateStr)
    return String(dateStr)
  }
}

/**
 * 格式化时间字符串，自动处理时区转换
 * @param dateStr - 时间字符串或时间戳
 * @param options - 格式化选项（会与默认选项合并）
 * @returns 格式化后的时间字符串
 */
export function formatDateTime(
  dateStr: string | number | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateStr) return '-'
  return formatWithOptions(dateStr, { ...DEFAULT_DATETIME_OPTIONS, ...options })
}

/**
 * 仅格式化日期部分（不含时间）
 * @param dateStr - 时间字符串或时间戳
 * @returns 格式化后的日期字符串
 */
export function formatDate(dateStr: string | number | null | undefined): string {
  return formatWithOptions(dateStr, DATE_ONLY_OPTIONS)
}

/**
 * 仅格式化时间部分（不含日期）
 * @param dateStr - 时间字符串或时间戳
 * @returns 格式化后的时间字符串
 */
export function formatTime(dateStr: string | number | null | undefined): string {
  return formatWithOptions(dateStr, TIME_ONLY_OPTIONS)
}

/**
 * 格式化时间并添加相对时间描述
 * @param dateStr - 时间字符串或时间戳
 * @returns 格式化后的时间字符串 + 相对时间
 */
export function formatDateTimeWithRelative(dateStr: string | number | null | undefined): string {
  if (!dateStr) return '-'

  try {
    const timeStr = normalizeTimeString(dateStr)
    if (!timeStr) {
      return '-'
    }

    const utcDate = new Date(timeStr)
    if (isNaN(utcDate.getTime())) {
      console.warn('无效的时间格式:', dateStr)
      return String(dateStr)
    }

    // 计算时间差
    const diff = Date.now() - utcDate.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor(diff / (1000 * 60))

    // 格式化为中国本地时间
    const formatted = utcDate.toLocaleString('zh-CN', DEFAULT_DATETIME_OPTIONS)

    // 添加相对时间
    let relative = ''
    if (days > 0) {
      relative = `（${days}天前）`
    } else if (hours > 0) {
      relative = `（${hours}小时前）`
    } else if (minutes > 0) {
      relative = `（${minutes}分钟前）`
    } else {
      relative = '（刚刚）'
    }

    return formatted + ' ' + relative
  } catch (e) {
    console.error('时间格式化错误:', e, dateStr)
    return String(dateStr)
  }
}

/**
 * 格式化相对时间（距离现在多久）
 * @param dateStr - 时间字符串或时间戳
 * @returns 相对时间描述
 */
export function formatRelativeTime(dateStr: string | number | null | undefined): string {
  if (!dateStr) return '-'

  try {
    const timeStr = normalizeTimeString(dateStr)
    if (!timeStr) {
      return '-'
    }

    const targetDate = new Date(timeStr)
    if (isNaN(targetDate.getTime())) {
      console.warn('无效的时间格式:', dateStr)
      return String(dateStr)
    }

    // 计算时间差（毫秒）
    const diff = targetDate.getTime() - Date.now()
    const absDiff = Math.abs(diff)

    // 转换为各种时间单位
    const seconds = Math.floor(absDiff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    // 判断是过去还是将来
    const isPast = diff < 0

    if (days > 0) {
      return isPast ? `${days}天前` : `${days}天后`
    } else if (hours > 0) {
      return isPast ? `${hours}小时前` : `${hours}小时后`
    } else if (minutes > 0) {
      return isPast ? `${minutes}分钟前` : `${minutes}分钟后`
    } else if (seconds > 10) {
      return isPast ? `${seconds}秒前` : `${seconds}秒后`
    } else {
      return isPast ? '刚刚' : '即将执行'
    }
  } catch (e) {
    console.error('相对时间格式化错误:', e, dateStr)
    return String(dateStr)
  }
}
