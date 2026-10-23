"""
``tradingagents.dataflows.interface.get_reddit_sentiment`` 单元测试。

回归背景
--------
``Toolkit.get_stock_sentiment_unified`` 的美股分支调用
``tradingagents.dataflows.interface.get_reddit_sentiment``，但该函数此前**并不存在**，
导致美股情绪分析永远走到 ``except`` 分支并返回「获取失败」。

本测试锁定：
1. 函数存在且可调用；
2. 数据集缺失时优雅降级（不抛异常）；
3. 情绪打分与标签映射符合预期。
"""

from __future__ import annotations

import pytest

from tradingagents.dataflows import interface


class TestGetRedditSentiment:
    def test_function_exists(self):
        assert hasattr(interface, "get_reddit_sentiment")
        assert callable(interface.get_reddit_sentiment)

    def test_invalid_date_returns_message_instead_of_raising(self):
        result = interface.get_reddit_sentiment("AAPL", "not-a-date")
        assert "无法解析分析日期" in result

    def test_missing_dataset_degrades_gracefully(self, monkeypatch):
        """本地 Reddit 数据集不存在时不应抛异常。"""

        def _boom(*args, **kwargs):
            raise FileNotFoundError("reddit_data/company_news 不存在")

        monkeypatch.setattr(interface, "fetch_top_from_category", _boom)

        result = interface.get_reddit_sentiment("AAPL", "2026-09-01")

        assert "## Reddit情绪分析" in result
        assert "没有可用的 Reddit 讨论数据" in result or "数据获取失败" in result

    def test_returns_summary_when_posts_exist(self, monkeypatch):
        """有帖子时返回包含情绪指标与热门讨论的摘要。"""
        posts = [
            {
                "title": "AAPL beats earnings, stock soars",
                "content": "Strong growth and record profit",
                "upvotes": 320,
            },
            {
                "title": "AAPL downgrade worries",
                "content": "Weak outlook, possible decline",
                "upvotes": 120,
            },
        ]
        monkeypatch.setattr(
            interface, "fetch_top_from_category", lambda *a, **k: list(posts)
        )

        result = interface.get_reddit_sentiment("AAPL", "2026-09-01", look_back_days=1)

        assert "## Reddit情绪分析" in result
        assert "AAPL" in result
        assert "讨论热度: 2 篇相关帖子" in result
        assert "情绪倾向" in result
        assert "热门讨论" in result
        assert "AAPL beats earnings" in result

    def test_empty_posts_reports_no_data(self, monkeypatch):
        monkeypatch.setattr(interface, "fetch_top_from_category", lambda *a, **k: [])

        result = interface.get_reddit_sentiment("AAPL", "2026-09-01", look_back_days=1)

        assert "没有可用的 Reddit 讨论数据" in result


class TestSentimentScoring:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("bullish breakout, huge gain", 3),
            ("crash, fraud, downgrade", -3),
            ("AAPL beats earnings and surges", 2),
            ("Weak outlook, possible decline", -2),
            ("", 0),
            ("completely neutral wording", 0),
        ],
    )
    def test_score_text(self, text, expected):
        assert interface._score_reddit_text(text) == expected

    def test_word_boundary_prevents_double_counting(self):
        """'beat' 不应同时命中 'beats'（子串重复计数）。"""
        assert interface._score_reddit_text("beats") == 1
        assert interface._score_reddit_text("surges") == 1

    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.8, "乐观"),
            (0.2, "中性偏乐观"),
            (0.0, "中性"),
            (-0.2, "中性偏悲观"),
            (-0.8, "悲观"),
        ],
    )
    def test_label_mapping(self, score, expected):
        assert interface._reddit_sentiment_label(score) == expected

    def test_label_is_stable_outside_range(self):
        assert interface._reddit_sentiment_label(5.0) == "乐观"
        assert interface._reddit_sentiment_label(-5.0) == "悲观"


class TestToolkitIntegration:
    def test_unified_sentiment_tool_can_call_reddit_sentiment(self, monkeypatch):
        """
        Toolkit 的美股情绪分支必须能真正取到情绪数据（而非必然的「获取失败」）。

        回归点：``interface.get_reddit_sentiment`` 缺失导致该分支恒定降级。
        """
        from tradingagents.agents.utils.agent_utils import Toolkit

        monkeypatch.setattr(
            interface,
            "fetch_top_from_category",
            lambda *a, **k: [
                {
                    "title": "NVDA record profit, bullish rally",
                    "content": "Strong beat and upgrade",
                    "upvotes": 500,
                }
            ],
        )

        toolkit = Toolkit()
        result = toolkit.get_stock_sentiment_unified.invoke(
            {"ticker": "NVDA", "curr_date": "2026-09-01"}
        )

        assert "美股Reddit情绪" in result
        assert "获取失败" not in result
        assert "情绪倾向" in result
