"""
``app.core.startup.scheduler_jobs`` 单元测试。

这些任务原先内联在 ``app/main.py`` 的 lifespan 中（约 300 行高度重复的样板），
现抽为**声明式任务表**。本测试锁定：

1. 全部任务都被注册（数量与 id 不回退）；
2. 开关未打开时任务被**注册但暂停**（保证任务在列表中可见、可被 API 手动触发）；
3. 开关打开时任务处于运行态；
4. CRON 表达式取自正确的配置项；
5. ``register_cron_job`` 的通用逻辑对任意 spec 生效。
"""

from __future__ import annotations

import pytest

from app.core.startup import scheduler_jobs as sj


class FakeJob:
    """APScheduler Job 的最小替身。"""

    def __init__(self, job_id, name, trigger, kwargs=None):
        self.id = job_id
        self.name = name
        self.trigger = trigger
        self.kwargs = kwargs or {}
        self.paused = False

    def pause(self):
        self.paused = True


class FakeScheduler:
    """APScheduler AsyncIOScheduler 的最小替身。"""

    def __init__(self):
        self.jobs: dict = {}
        self.paused_ids: list = []
        self.rescheduled: list = []
        self.started = False

    def add_job(self, func, trigger=None, id=None, name=None, **kwargs):
        self.jobs[id] = FakeJob(id, name, trigger, kwargs.get("kwargs"))
        return self.jobs[id]

    def pause_job(self, job_id):
        self.paused_ids.append(job_id)
        if job_id in self.jobs:
            self.jobs[job_id].paused = True

    def reschedule_job(self, job_id, trigger=None):
        self.rescheduled.append((job_id, trigger))

    def start(self):
        self.started = True


def _noop():
    return None


class TestRegisterCronJob:
    def test_registers_job_with_id_and_name(self):
        scheduler = FakeScheduler()
        spec = sj.CronJobSpec(
            job_id="demo_job",
            name="演示任务",
            cron_attr="NEWS_SYNC_CRON",
            func=_noop,
        )
        sj.register_cron_job(scheduler, spec)

        assert "demo_job" in scheduler.jobs
        job = scheduler.jobs["demo_job"]
        assert job.name == "演示任务"
        assert job.trigger is not None

    def test_pauses_job_when_disabled(self, monkeypatch):
        monkeypatch.setattr(sj.settings, "NEWS_SYNC_ENABLED", False, raising=False)
        scheduler = FakeScheduler()
        spec = sj.CronJobSpec(
            job_id="demo_job",
            name="演示任务",
            cron_attr="NEWS_SYNC_CRON",
            func=_noop,
            enabled_attr="NEWS_SYNC_ENABLED",
        )
        sj.register_cron_job(scheduler, spec)

        assert "demo_job" in scheduler.jobs, "任务必须被注册（保持可见性）"
        assert scheduler.paused_ids == ["demo_job"]

    def test_runs_job_when_enabled(self, monkeypatch):
        monkeypatch.setattr(sj.settings, "NEWS_SYNC_ENABLED", True, raising=False)
        scheduler = FakeScheduler()
        spec = sj.CronJobSpec(
            job_id="demo_job",
            name="演示任务",
            cron_attr="NEWS_SYNC_CRON",
            func=_noop,
            enabled_attr="NEWS_SYNC_ENABLED",
        )
        sj.register_cron_job(scheduler, spec)

        assert scheduler.paused_ids == []

    def test_unified_switch_also_controls_state(self, monkeypatch):
        """数据源总开关关闭时，即使子开关打开也要暂停。"""
        monkeypatch.setattr(sj.settings, "TUSHARE_UNIFIED_ENABLED", False, raising=False)
        monkeypatch.setattr(sj.settings, "TUSHARE_BASIC_INFO_SYNC_ENABLED", True, raising=False)
        scheduler = FakeScheduler()
        spec = sj.CronJobSpec(
            job_id="tushare_basic_info_sync",
            name="股票基础信息同步（Tushare）",
            cron_attr="TUSHARE_BASIC_INFO_SYNC_CRON",
            func=_noop,
            enabled_attr="TUSHARE_BASIC_INFO_SYNC_ENABLED",
            unified_attr="TUSHARE_UNIFIED_ENABLED",
        )
        sj.register_cron_job(scheduler, spec)

        assert scheduler.paused_ids == ["tushare_basic_info_sync"]

    def test_kwargs_are_forwarded(self):
        scheduler = FakeScheduler()
        spec = sj.CronJobSpec(
            job_id="demo_job",
            name="演示任务",
            cron_attr="NEWS_SYNC_CRON",
            func=_noop,
            kwargs={"force_update": False},
        )
        sj.register_cron_job(scheduler, spec)

        assert scheduler.jobs["demo_job"].kwargs == {"force_update": False}


class TestDatasourceJobSpecs:
    def test_all_three_datasources_are_covered(self):
        specs = sj._datasource_job_specs()
        job_ids = {s.job_id for s in specs}

        assert "tushare_basic_info_sync" in job_ids
        assert "akshare_basic_info_sync" in job_ids
        assert "baostock_basic_info_sync" in job_ids

    def test_expected_job_count(self):
        """Tushare 5 + AKShare 5 + BaoStock 4 = 14 个数据源任务。"""
        specs = sj._datasource_job_specs()
        assert len(specs) == 14

    def test_job_ids_are_unique(self):
        specs = sj._datasource_job_specs()
        ids = [s.job_id for s in specs]
        assert len(ids) == len(set(ids))

    def test_every_spec_has_cron_attr_enabled_attr_and_unified_attr(self):
        for spec in sj._datasource_job_specs():
            assert spec.cron_attr
            assert spec.enabled_attr
            assert spec.unified_attr
            assert callable(spec.func)

    def test_specs_reference_real_settings(self):
        """所有配置项名必须在 settings 中真实存在（防止改名后静默失效）。"""
        for spec in sj._datasource_job_specs():
            assert hasattr(sj.settings, spec.cron_attr), spec.cron_attr
            assert hasattr(sj.settings, spec.enabled_attr), spec.enabled_attr
            assert hasattr(sj.settings, spec.unified_attr), spec.unified_attr


class TestRegisterScheduledJobs:
    def test_registers_the_full_job_set(self, monkeypatch):
        """
        端到端：注册全部任务。

        这里把三个数据源开关全部打开、新闻同步打开，便于断言"运行态"的任务集合。
        """
        for attr in (
            "TUSHARE_UNIFIED_ENABLED",
            "AKSHARE_UNIFIED_ENABLED",
            "BAOSTOCK_UNIFIED_ENABLED",
            "NEWS_SYNC_ENABLED",
        ):
            monkeypatch.setattr(sj.settings, attr, True, raising=False)
        for attr in (
            "TUSHARE_BASIC_INFO_SYNC_ENABLED",
            "TUSHARE_QUOTES_SYNC_ENABLED",
            "TUSHARE_HISTORICAL_SYNC_ENABLED",
            "TUSHARE_FINANCIAL_SYNC_ENABLED",
            "TUSHARE_STATUS_CHECK_ENABLED",
            "AKSHARE_BASIC_INFO_SYNC_ENABLED",
            "AKSHARE_QUOTES_SYNC_ENABLED",
            "AKSHARE_HISTORICAL_SYNC_ENABLED",
            "AKSHARE_FINANCIAL_SYNC_ENABLED",
            "AKSHARE_STATUS_CHECK_ENABLED",
            "BAOSTOCK_BASIC_INFO_SYNC_ENABLED",
            "BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED",
            "BAOSTOCK_HISTORICAL_SYNC_ENABLED",
            "BAOSTOCK_STATUS_CHECK_ENABLED",
        ):
            monkeypatch.setattr(sj.settings, attr, True, raising=False)

        # 避免真正启动后台任务（爬虫/筛选/排行）
        created = []
        monkeypatch.setattr(sj.asyncio, "create_task", lambda coro: created.append(coro))
        monkeypatch.setattr(
            "app.services.ranking_scheduler.ranking_scheduler.start", lambda: None
        )

        scheduler = FakeScheduler()
        sj.register_scheduled_jobs(scheduler)

        # 关闭被捕获的协程，避免 "never awaited" 警告
        for coro in created:
            coro.close()

        # 14 个数据源任务 + 新闻 + 基础信息同步 + 爬虫 + 筛选
        assert len(scheduler.jobs) >= 16
        for expected in (
            "tushare_basic_info_sync",
            "akshare_quotes_sync",
            "baostock_status_check",
            "news_sync",
            "all_crawlers_task",
            "stock_selector_task",
        ):
            assert expected in scheduler.jobs, expected

        # 全部开关打开 -> 不应有任何任务被暂停
        assert scheduler.paused_ids == []

    def test_disabled_datasource_jobs_are_registered_but_paused(self, monkeypatch):
        """数据源总开关关闭时：任务仍然注册，但处于暂停态。"""
        for attr in ("TUSHARE_UNIFIED_ENABLED", "AKSHARE_UNIFIED_ENABLED", "BAOSTOCK_UNIFIED_ENABLED"):
            monkeypatch.setattr(sj.settings, attr, False, raising=False)
        monkeypatch.setattr(sj.settings, "NEWS_SYNC_ENABLED", False, raising=False)

        created = []
        monkeypatch.setattr(sj.asyncio, "create_task", lambda coro: created.append(coro))
        monkeypatch.setattr(
            "app.services.ranking_scheduler.ranking_scheduler.start", lambda: None
        )

        scheduler = FakeScheduler()
        sj.register_scheduled_jobs(scheduler)

        for coro in created:
            coro.close()

        # 任务依然可见（可被 API 手动触发）
        assert "tushare_basic_info_sync" in scheduler.jobs
        assert "akshare_quotes_sync" in scheduler.jobs
        assert "baostock_status_check" in scheduler.jobs
        # 但都处于暂停态
        assert "tushare_basic_info_sync" in scheduler.paused_ids
        assert "akshare_quotes_sync" in scheduler.paused_ids
        assert "news_sync" in scheduler.paused_ids
