"""
应用启动时的定时任务注册。

设计说明
--------
此前这些任务全部内联在 ``app/main.py`` 的 ``lifespan`` 中，约 300 行高度重复的
``add_job`` + 条件 ``pause_job`` + 日志代码，使 ``main.py`` 膨胀到 1000+ 行，
且新增/调整一个数据源的任务需要复制粘贴 15 行样板。

这里把任务定义抽成**声明式任务表**：

* ``CronJobSpec`` 描述一个 CRON 任务（id、名称、CRON 配置项、启用开关、回调）；
* ``register_cron_job`` 是唯一的注册入口，统一处理"注册 → 未启用则暂停 → 日志"；
* ``register_scheduled_jobs`` 是总入口，按数据源分组注册全部任务。

新增一个数据源任务只需在任务表里加一行。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger("app.startup.scheduler")


@dataclass
class CronJobSpec:
    """一个 CRON 型定时任务的声明。"""

    job_id: str
    name: str
    cron_attr: str
    func: Callable
    #: 任务自身的启用开关（settings 属性名）
    enabled_attr: Optional[str] = None
    #: 数据源总开关（settings 属性名）；与 enabled_attr 同时为真才启用
    unified_attr: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)
    #: 暂停/启用时的日志前缀（用于区分不同数据源）
    log_prefix: str = ""


def register_cron_job(scheduler: AsyncIOScheduler, spec: CronJobSpec) -> None:
    """
    注册单个 CRON 任务，并按开关决定是否立即暂停。

    行为与原先内联实现完全一致：
    * 总是注册任务（保证任务列表可见、可被 API 手动触发）；
    * 若开关未全部打开则立即 ``pause_job``；
    * 输出对应的暂停/启用日志。
    """
    cron_expr = getattr(settings, spec.cron_attr)
    scheduler.add_job(
        spec.func,
        CronTrigger.from_crontab(cron_expr, timezone=settings.TIMEZONE),
        id=spec.job_id,
        name=spec.name,
        kwargs=spec.kwargs or None,
    )

    enabled = True
    if spec.unified_attr:
        enabled = enabled and bool(getattr(settings, spec.unified_attr))
    if spec.enabled_attr:
        enabled = enabled and bool(getattr(settings, spec.enabled_attr))

    if not enabled:
        scheduler.pause_job(spec.job_id)
        logger.info(f"⏸️ {spec.log_prefix or spec.name}已添加但暂停: {cron_expr}")
    else:
        logger.info(f"✅ {spec.log_prefix or spec.name}已配置: {cron_expr}")


def _datasource_job_specs() -> List[CronJobSpec]:
    """
    三个数据源（Tushare / AKShare / BaoStock）的统一同步任务表。

    每个数据源的任务集合与开关命名高度一致，因此用循环生成，
    避免 14 段近乎相同的样板代码。
    """
    from app.worker.akshare_sync_service import (
        run_akshare_basic_info_sync,
        run_akshare_financial_sync,
        run_akshare_historical_sync,
        run_akshare_quotes_sync,
        run_akshare_status_check,
    )
    from app.worker.baostock_sync_service import (
        run_baostock_basic_info_sync,
        run_baostock_daily_quotes_sync,
        run_baostock_historical_sync,
        run_baostock_status_check,
    )
    from app.worker.tushare_sync_service import (
        run_tushare_basic_info_sync,
        run_tushare_financial_sync,
        run_tushare_historical_sync,
        run_tushare_quotes_sync,
        run_tushare_status_check,
    )

    specs: List[CronJobSpec] = []

    # ---------------- Tushare ----------------
    specs += [
        CronJobSpec(
            job_id="tushare_basic_info_sync",
            name="股票基础信息同步（Tushare）",
            cron_attr="TUSHARE_BASIC_INFO_SYNC_CRON",
            func=run_tushare_basic_info_sync,
            enabled_attr="TUSHARE_BASIC_INFO_SYNC_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
            kwargs={"force_update": False},
            log_prefix="Tushare基础信息同步",
        ),
        CronJobSpec(
            job_id="tushare_quotes_sync",
            name="实时行情同步（Tushare）",
            cron_attr="TUSHARE_QUOTES_SYNC_CRON",
            func=run_tushare_quotes_sync,
            enabled_attr="TUSHARE_QUOTES_SYNC_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
            log_prefix="Tushare行情同步",
        ),
        CronJobSpec(
            job_id="tushare_historical_sync",
            name="历史数据同步（Tushare）",
            cron_attr="TUSHARE_HISTORICAL_SYNC_CRON",
            func=run_tushare_historical_sync,
            enabled_attr="TUSHARE_HISTORICAL_SYNC_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
            kwargs={"incremental": True},
            log_prefix="Tushare历史数据同步",
        ),
        CronJobSpec(
            job_id="tushare_financial_sync",
            name="财务数据同步（Tushare）",
            cron_attr="TUSHARE_FINANCIAL_SYNC_CRON",
            func=run_tushare_financial_sync,
            enabled_attr="TUSHARE_FINANCIAL_SYNC_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
            log_prefix="Tushare财务数据同步",
        ),
        CronJobSpec(
            job_id="tushare_status_check",
            name="数据源状态检查（Tushare）",
            cron_attr="TUSHARE_STATUS_CHECK_CRON",
            func=run_tushare_status_check,
            enabled_attr="TUSHARE_STATUS_CHECK_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
            log_prefix="Tushare状态检查",
        ),
    ]

    # ---------------- AKShare ----------------
    specs += [
        CronJobSpec(
            job_id="akshare_basic_info_sync",
            name="股票基础信息同步（AKShare）",
            cron_attr="AKSHARE_BASIC_INFO_SYNC_CRON",
            func=run_akshare_basic_info_sync,
            enabled_attr="AKSHARE_BASIC_INFO_SYNC_ENABLED",
            unified_attr="AKSHARE_UNIFIED_ENABLED",
            kwargs={"force_update": False},
            log_prefix="AKShare基础信息同步",
        ),
        CronJobSpec(
            job_id="akshare_quotes_sync",
            name="实时行情同步（AKShare）",
            cron_attr="AKSHARE_QUOTES_SYNC_CRON",
            func=run_akshare_quotes_sync,
            enabled_attr="AKSHARE_QUOTES_SYNC_ENABLED",
            unified_attr="AKSHARE_UNIFIED_ENABLED",
            log_prefix="AKShare行情同步",
        ),
        CronJobSpec(
            job_id="akshare_historical_sync",
            name="历史数据同步（AKShare）",
            cron_attr="AKSHARE_HISTORICAL_SYNC_CRON",
            func=run_akshare_historical_sync,
            enabled_attr="AKSHARE_HISTORICAL_SYNC_ENABLED",
            unified_attr="AKSHARE_UNIFIED_ENABLED",
            kwargs={"incremental": True},
            log_prefix="AKShare历史数据同步",
        ),
        CronJobSpec(
            job_id="akshare_financial_sync",
            name="财务数据同步（AKShare）",
            cron_attr="AKSHARE_FINANCIAL_SYNC_CRON",
            func=run_akshare_financial_sync,
            enabled_attr="AKSHARE_FINANCIAL_SYNC_ENABLED",
            unified_attr="AKSHARE_UNIFIED_ENABLED",
            log_prefix="AKShare财务数据同步",
        ),
        CronJobSpec(
            job_id="akshare_status_check",
            name="数据源状态检查（AKShare）",
            cron_attr="AKSHARE_STATUS_CHECK_CRON",
            func=run_akshare_status_check,
            enabled_attr="AKSHARE_STATUS_CHECK_ENABLED",
            unified_attr="AKSHARE_UNIFIED_ENABLED",
            log_prefix="AKShare状态检查",
        ),
    ]

    # ---------------- BaoStock ----------------
    specs += [
        CronJobSpec(
            job_id="baostock_basic_info_sync",
            name="股票基础信息同步（BaoStock）",
            cron_attr="BAOSTOCK_BASIC_INFO_SYNC_CRON",
            func=run_baostock_basic_info_sync,
            enabled_attr="BAOSTOCK_BASIC_INFO_SYNC_ENABLED",
            unified_attr="BAOSTOCK_UNIFIED_ENABLED",
            log_prefix="BaoStock基础信息同步",
        ),
        CronJobSpec(
            job_id="baostock_daily_quotes_sync",
            name="日K线数据同步（BaoStock）",
            cron_attr="BAOSTOCK_DAILY_QUOTES_SYNC_CRON",
            func=run_baostock_daily_quotes_sync,
            enabled_attr="BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED",
            unified_attr="BAOSTOCK_UNIFIED_ENABLED",
            log_prefix="BaoStock日K线同步",
        ),
        CronJobSpec(
            job_id="baostock_historical_sync",
            name="历史数据同步（BaoStock）",
            cron_attr="BAOSTOCK_HISTORICAL_SYNC_CRON",
            func=run_baostock_historical_sync,
            enabled_attr="BAOSTOCK_HISTORICAL_SYNC_ENABLED",
            unified_attr="BAOSTOCK_UNIFIED_ENABLED",
            log_prefix="BaoStock历史数据同步",
        ),
        CronJobSpec(
            job_id="baostock_status_check",
            name="数据源状态检查（BaoStock）",
            cron_attr="BAOSTOCK_STATUS_CHECK_CRON",
            func=run_baostock_status_check,
            enabled_attr="BAOSTOCK_STATUS_CHECK_ENABLED",
            unified_attr="BAOSTOCK_UNIFIED_ENABLED",
            log_prefix="BaoStock状态检查",
        ),
    ]

    return specs


def _register_news_sync(scheduler: AsyncIOScheduler) -> None:
    """新闻数据同步（AKShare，仅自选股）。"""
    from app.worker.akshare_sync_service import get_akshare_sync_service

    async def run_news_sync():
        """运行新闻同步任务 - 使用AKShare同步自选股新闻"""
        try:
            logger.info("开始新闻数据同步（AKShare - 仅自选股）...")
            service = await get_akshare_sync_service()
            result = await service.sync_news_data(
                symbols=None,  # None + favorites_only=True 表示只同步自选股
                max_news_per_stock=settings.NEWS_SYNC_MAX_PER_SOURCE,
                favorites_only=True,  # 只同步自选股
            )
            logger.info(
                f"新闻同步完成: "
                f"处理{result['total_processed']}只自选股, "
                f"成功{result['success_count']}只, "
                f"失败{result['error_count']}只, "
                f"新闻总数{result['news_count']}条, "
                f"耗时{(datetime.utcnow() - result['start_time']).total_seconds():.2f}秒"
            )
        except Exception as e:
            logger.error(f"新闻同步失败: {e}", exc_info=True)

    scheduler.add_job(
        run_news_sync,
        CronTrigger.from_crontab(settings.NEWS_SYNC_CRON, timezone=settings.TIMEZONE),
        id="news_sync",
        name="新闻数据同步（AKShare - 仅自选股）",
    )
    if not settings.NEWS_SYNC_ENABLED:
        scheduler.pause_job("news_sync")
        logger.info(f"⏸️ 新闻数据同步已添加但暂停: {settings.NEWS_SYNC_CRON}")
    else:
        logger.info(f"📰 新闻数据同步已配置（仅自选股）: {settings.NEWS_SYNC_CRON}")


def _register_stock_basics_sync(scheduler: AsyncIOScheduler) -> None:
    """多数据源股票基础信息同步（支持自动降级）。"""
    from app.services.multi_source_basics_sync_service import MultiSourceBasicsSyncService

    service = MultiSourceBasicsSyncService()

    # 根据 TUSHARE_ENABLED 配置决定优先数据源
    # 如果 Tushare 被禁用，系统会自动使用其他可用数据源（AKShare/BaoStock）
    if settings.TUSHARE_ENABLED:
        preferred_sources = ["tushare", "akshare", "baostock"]
        logger.info("📊 股票基础信息同步优先数据源: Tushare > AKShare > BaoStock")
    else:
        preferred_sources = ["akshare", "baostock"]
        logger.info("📊 股票基础信息同步优先数据源: AKShare > BaoStock (Tushare已禁用)")

    def _run_sync():
        return service.run_full_sync(force=False, preferred_sources=preferred_sources)

    # 立即在启动后尝试一次（不阻塞）
    async def run_sync_with_sources():
        await _run_sync()

    asyncio.create_task(run_sync_with_sources())

    # 配置调度：优先使用 CRON，其次使用 HH:MM
    if not settings.SYNC_STOCK_BASICS_ENABLED:
        return

    if settings.SYNC_STOCK_BASICS_CRON:
        scheduler.add_job(
            _run_sync,
            CronTrigger.from_crontab(settings.SYNC_STOCK_BASICS_CRON, timezone=settings.TIMEZONE),
            id="basics_sync_service",
            name="股票基础信息同步（多数据源）",
        )
        logger.info(
            f"📅 Stock basics sync scheduled by CRON: "
            f"{settings.SYNC_STOCK_BASICS_CRON} ({settings.TIMEZONE})"
        )
    else:
        hh, mm = (settings.SYNC_STOCK_BASICS_TIME or "06:30").split(":")
        scheduler.add_job(
            _run_sync,
            CronTrigger(hour=int(hh), minute=int(mm), timezone=settings.TIMEZONE),
            id="basics_sync_service",
            name="股票基础信息同步（多数据源）",
        )
        logger.info(
            f"📅 Stock basics sync scheduled daily at "
            f"{settings.SYNC_STOCK_BASICS_TIME} ({settings.TIMEZONE})"
        )


def _register_quotes_ingestion(scheduler: AsyncIOScheduler) -> None:
    """实时行情入库（内部自判交易时段）。"""
    from app.services.quotes_ingestion_service import QuotesIngestionService

    if not settings.QUOTES_INGEST_ENABLED:
        return

    quotes_ingestion = QuotesIngestionService()
    scheduler.add_job(
        quotes_ingestion.run_once,  # coroutine function; AsyncIOScheduler will await it
        IntervalTrigger(seconds=settings.QUOTES_INGEST_INTERVAL_SECONDS, timezone=settings.TIMEZONE),
        id="quotes_ingestion_service",
        name="实时行情入库服务",
    )
    logger.info(f"⏱ 实时行情入库任务已启动: 每 {settings.QUOTES_INGEST_INTERVAL_SECONDS}s")


def _register_crawlers(scheduler: AsyncIOScheduler) -> None:
    """
    爬虫任务（178448 复盘 + 东方财富人气/资金流/专家排行）。

    使用**动态间隔**：交易时段每 3 分钟，非交易时段每 10 分钟。
    """
    from app.services.crawler_service import CrawlerService
    from app.services.scrapy_crawler_service import ScrapyCrawlerService
    from app.utils.trading_time import is_active_trading_period

    # 创建服务实例，避免每次执行都创建新的实例
    crawler_service = CrawlerService()
    scrapy_service = ScrapyCrawlerService()

    async def run_all_crawlers():
        """运行所有爬虫任务 - 包括CrawlerService(双模板)和ScrapyCrawlerService"""
        try:
            logger.info("开始执行所有爬虫任务...")

            # 1. CrawlerService - 依次爬 fjzt-1(伏击人) + fjzt-2(专家)，每页 N 页
            # save_data 按 (user_name, stock_name, time) upsert，幂等跳过已入库
            pages_per_run = settings.CRAWLER_PAGES_PER_RUN
            crawler_total = await asyncio.to_thread(crawler_service.crawl_pages, 1, pages_per_run)
            logger.info(
                f"CrawlerService爬虫完成: 伏击人+专家各 {pages_per_run} 页（共 {pages_per_run * 2} 页），"
                f"新增 {crawler_total} 条数据"
            )

            # 2. 运行ScrapyCrawlerService爬虫（东方财富人气/资金流/专家排行）- 独立调度
            scrapy_total = await asyncio.to_thread(scrapy_service.run_all_crawlers)
            logger.info(f"ScrapyCrawlerService爬虫完成: 保存了 {scrapy_total} 条新数据")

            logger.info(f"所有爬虫任务完成: 总共保存了 {crawler_total + scrapy_total} 条新数据")
        except Exception as e:
            logger.error(f"爬虫任务失败: {e}", exc_info=True)
        finally:
            logger.info("爬虫任务执行完成")

    interval_minutes = settings.CRAWLER_INTERVAL_MINUTES
    scheduler.add_job(
        run_all_crawlers,
        IntervalTrigger(minutes=interval_minutes, timezone=settings.TIMEZONE),
        id="all_crawlers_task",
        name="所有爬虫任务",
        replace_existing=True,
        misfire_grace_time=120,  # 间隔 1 分钟，宽容窗口 2 分钟防止积压
    )
    logger.info(
        f"所有爬虫任务已配置: 每 {interval_minutes} 分钟执行一次，"
        f"CrawlerService 爬伏击人+专家各 {settings.CRAWLER_PAGES_PER_RUN} 页，"
        f"Scrapy 爬东方财富人气/资金流/专家排行"
    )

    # 立即执行一次爬虫任务 - 移到后台任务执行，避免阻塞服务器启动
    asyncio.create_task(run_all_crawlers())


def _register_stock_selector(scheduler: AsyncIOScheduler) -> None:
    """股票筛选服务（每 10 分钟）。"""
    from app.services.stock_selector_service import stock_selector_service

    async def run_stock_selector():
        """运行股票筛选服务"""
        try:
            logger.info("开始执行股票筛选...")
            result = stock_selector_service.run_screening()
            if result:
                logger.info("股票筛选服务执行成功")
            else:
                logger.warning("股票筛选服务执行失败")
        except Exception as e:
            logger.error(f"股票筛选服务失败: {e}", exc_info=True)

    scheduler.add_job(
        run_stock_selector,
        IntervalTrigger(minutes=10, timezone=settings.TIMEZONE),
        id="stock_selector_task",
        name="股票筛选服务",
        replace_existing=True,
    )
    logger.info("✅ 股票筛选服务已配置: 每 10 分钟执行一次")

    # 立即执行一次股票筛选 - 移到后台任务执行，避免阻塞服务器启动
    asyncio.create_task(run_stock_selector())


def register_scheduled_jobs(scheduler: AsyncIOScheduler) -> None:
    """
    注册全部定时任务（应用启动时调用一次）。

    任务清单：
    * 多数据源股票基础信息同步
    * 实时行情入库
    * Tushare / AKShare / BaoStock 各自的同步与状态检查任务
    * 新闻数据同步（仅自选股）
    * 爬虫任务（交易时段动态间隔）
    * 股票筛选服务
    * 排行数据调度器
    """
    logger.info("🔧 开始注册定时任务...")

    _register_stock_basics_sync(scheduler)
    _register_quotes_ingestion(scheduler)

    logger.info("🔄 配置数据源统一同步任务...")
    for spec in _datasource_job_specs():
        register_cron_job(scheduler, spec)

    logger.info("配置新闻数据同步任务...")
    _register_news_sync(scheduler)

    logger.info("配置爬虫定时任务...")
    _register_crawlers(scheduler)

    logger.info("配置股票筛选服务定时任务...")
    _register_stock_selector(scheduler)

    logger.info("配置排行数据爬虫...")
    from app.services.ranking_scheduler import ranking_scheduler

    ranking_scheduler.start()
    logger.info("✅ 排行数据定时调度器已启动: 每 10 分钟执行一次")

    # 港股/美股数据采用按需获取+缓存模式，不再配置定时同步任务
    logger.info("🇭🇰 港股数据采用按需获取+缓存模式")
    logger.info("🇺🇸 美股数据采用按需获取+缓存模式")

    logger.info("✅ 定时任务注册完成")
