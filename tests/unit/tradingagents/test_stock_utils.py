"""
``tradingagents.utils.stock_utils`` 单元测试。

覆盖多市场代码识别的核心契约：A股 / 港股 / 美股 / 未知，
以及币种映射、港股代码标准化、数据源推荐。
"""

from __future__ import annotations

import pytest

from tradingagents.utils.stock_utils import (
    StockMarket,
    StockUtils,
    get_stock_market_info,
    is_china_stock,
    is_hk_stock,
    is_us_stock,
)


class TestIdentifyStockMarket:
    """市场识别。"""

    @pytest.mark.parametrize("ticker", ["600519", "000001", "300750", "688981", "830799"])
    def test_identifies_a_shares(self, ticker):
        assert StockUtils.identify_stock_market(ticker) is StockMarket.CHINA_A

    @pytest.mark.parametrize("ticker", ["0700.HK", "00700.HK", "09988.HK", "0700", "9988"])
    def test_identifies_hk_stocks(self, ticker):
        assert StockUtils.identify_stock_market(ticker) is StockMarket.HONG_KONG

    @pytest.mark.parametrize("ticker", ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"])
    def test_identifies_us_stocks(self, ticker):
        assert StockUtils.identify_stock_market(ticker) is StockMarket.US

    @pytest.mark.parametrize("ticker", ["", None, "ABCDEFGHIJK", "1234567", "12345A"])
    def test_unknown_or_invalid_returns_unknown(self, ticker):
        assert StockUtils.identify_stock_market(ticker) is StockMarket.UNKNOWN

    def test_lowercase_us_ticker_is_normalized(self):
        assert StockUtils.identify_stock_market("aapl") is StockMarket.US

    def test_surrounding_whitespace_is_stripped(self):
        assert StockUtils.identify_stock_market("  600519  ") is StockMarket.CHINA_A


class TestCurrency:
    """币种映射。"""

    @pytest.mark.parametrize(
        "ticker,expected",
        [
            ("600519", ("人民币", "¥")),
            ("0700.HK", ("港币", "HK$")),
            ("AAPL", ("美元", "$")),
            ("!!!", ("未知", "?")),
        ],
    )
    def test_currency_info(self, ticker, expected):
        assert StockUtils.get_currency_info(ticker) == expected


class TestDataSource:
    """推荐数据源。"""

    def test_a_share_uses_china_unified(self):
        assert StockUtils.get_data_source("600519") == "china_unified"

    @pytest.mark.parametrize("ticker", ["0700.HK", "AAPL"])
    def test_hk_and_us_use_yahoo_finance(self, ticker):
        assert StockUtils.get_data_source(ticker) == "yahoo_finance"

    def test_unknown_ticker(self):
        assert StockUtils.get_data_source("!!!") == "unknown"


class TestNormalizeHkTicker:
    """港股代码标准化。"""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("0700", "0700.HK"),
            ("09988", "09988.HK"),
            ("0700.HK", "0700.HK"),
            ("00700.hk", "00700.HK"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert StockUtils.normalize_hk_ticker(raw) == expected

    def test_code_shorter_than_four_digits_is_left_untouched(self):
        """规范只覆盖 4-5 位纯数字；3 位数字既不匹配规则也不属于任何市场，原样返回。"""
        assert StockUtils.normalize_hk_ticker("700") == "700"
        assert StockUtils.identify_stock_market("700") is StockMarket.UNKNOWN

    def test_empty_input_returns_empty(self):
        assert StockUtils.normalize_hk_ticker("") == ""

    def test_non_hk_code_untouched(self):
        assert StockUtils.normalize_hk_ticker("600519") == "600519"


class TestMarketInfo:
    """综合市场信息字典。"""

    def test_china_payload(self):
        info = StockUtils.get_market_info("600519")
        assert info["market"] == "china_a"
        assert info["market_name"] == "中国A股"
        assert info["is_china"] is True
        assert info["is_hk"] is False
        assert info["is_us"] is False
        assert info["currency_symbol"] == "¥"
        assert info["ticker"] == "600519"

    def test_us_payload(self):
        info = StockUtils.get_market_info("NVDA")
        assert info["market"] == "us"
        assert info["market_name"] == "美股"
        assert info["is_us"] is True
        assert info["currency_name"] == "美元"

    def test_hk_payload(self):
        info = StockUtils.get_market_info("0700.HK")
        assert info["market"] == "hong_kong"
        assert info["market_name"] == "港股"
        assert info["currency_symbol"] == "HK$"

    def test_unknown_payload(self):
        info = StockUtils.get_market_info("!!!")
        assert info["market"] == "unknown"
        assert info["market_name"] == "未知市场"
        assert info["is_china"] is False


class TestModuleLevelHelpers:
    """向后兼容的模块级函数。"""

    def test_helpers_match_class_methods(self):
        assert is_china_stock("600519") is StockUtils.is_china_stock("600519")
        assert is_hk_stock("0700.HK") is StockUtils.is_hk_stock("0700.HK")
        assert is_us_stock("AAPL") is StockUtils.is_us_stock("AAPL")
        assert get_stock_market_info("600519") == StockUtils.get_market_info("600519")
