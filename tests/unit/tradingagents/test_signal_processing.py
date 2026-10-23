"""
``tradingagents.graph.signal_processing`` 单元测试。

``SignalProcessor`` 把风险委员会输出的自由文本转成结构化决策
（action / target_price / confidence / risk_score / reasoning），
是分析结果落库前的最后一道标准化关卡。

测试用 FakeLLM 替代真实模型，避免任何网络调用。
"""

from __future__ import annotations

import json

import pytest

from tradingagents.graph.signal_processing import SignalProcessor


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    """最小 LLM 替身：返回预置文本，并记录调用参数。"""

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list = []

    def invoke(self, messages):
        self.calls.append(messages)
        return _FakeResponse(self.content)


def _processor(content: str):
    llm = FakeLLM(content)
    return SignalProcessor(llm), llm


DECISION_KEYS = {"action", "target_price", "confidence", "risk_score", "reasoning"}


class TestInvalidInput:
    """无效输入的降级行为。"""

    @pytest.mark.parametrize("bad", ["", "   ", None, 123])
    def test_empty_signal_returns_default_hold(self, bad):
        processor, llm = _processor("{}")
        result = processor.process_signal(bad, "600519")
        assert set(result) == DECISION_KEYS
        assert result["action"] == "持有"
        assert result["target_price"] is None
        assert result["confidence"] == 0.5
        assert result["risk_score"] == 0.5
        # 无效输入不应触发 LLM 调用
        assert llm.calls == []


class TestJsonParsing:
    """JSON 解析路径。"""

    def test_parses_well_formed_json(self):
        payload = json.dumps(
            {
                "action": "买入",
                "target_price": 1850.5,
                "confidence": 0.82,
                "risk_score": 0.35,
                "reasoning": "技术面与基本面共振",
            },
            ensure_ascii=False,
        )
        processor, _ = _processor(payload)
        result = processor.process_signal("分析报告正文", "600519")
        assert result["action"] == "买入"
        assert result["target_price"] == 1850.5
        assert result["confidence"] == 0.82
        assert result["risk_score"] == 0.35
        assert result["reasoning"] == "技术面与基本面共振"

    def test_extracts_json_embedded_in_prose(self):
        payload = "好的，这是结论：\n```json\n" + json.dumps(
            {"action": "卖出", "target_price": 1500, "confidence": 0.6, "risk_score": 0.8},
            ensure_ascii=False,
        ) + "\n```\n以上。"
        processor, _ = _processor(payload)
        result = processor.process_signal("正文", "600519")
        assert result["action"] == "卖出"
        assert result["target_price"] == 1500.0

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("buy", "买入"),
            ("BUY", "买入"),
            ("sell", "卖出"),
            ("hold", "持有"),
            ("购买", "买入"),
            ("保持", "持有"),
            ("出售", "卖出"),
            ("purchase", "买入"),
            ("unknown-action", "持有"),
        ],
    )
    def test_normalizes_action_variants(self, raw, expected):
        payload = json.dumps({"action": raw, "target_price": 100}, ensure_ascii=False)
        processor, _ = _processor(payload)
        assert processor.process_signal("正文", "600519")["action"] == expected

    def test_applies_default_confidence_and_risk(self):
        payload = json.dumps({"action": "买入", "target_price": 100}, ensure_ascii=False)
        processor, _ = _processor(payload)
        result = processor.process_signal("正文", "600519")
        assert result["confidence"] == 0.7
        assert result["risk_score"] == 0.5
        assert result["reasoning"] == "基于综合分析的投资建议"

    def test_numeric_string_price_is_converted(self):
        payload = json.dumps({"action": "买入", "target_price": "1850.5"}, ensure_ascii=False)
        processor, _ = _processor(payload)
        assert processor.process_signal("正文", "600519")["target_price"] == 1850.5

    def test_currency_prefixed_string_price_is_converted(self):
        payload = json.dumps({"action": "买入", "target_price": "¥1850.5"}, ensure_ascii=False)
        processor, _ = _processor(payload)
        assert processor.process_signal("正文", "600519")["target_price"] == 1850.5

    def test_null_target_price_is_recovered_from_reasoning(self):
        payload = json.dumps(
            {
                "action": "买入",
                "target_price": None,
                "reasoning": "综合判断，目标价：1750.00 元较为合理",
            },
            ensure_ascii=False,
        )
        processor, _ = _processor(payload)
        result = processor.process_signal("正文", "600519")
        assert result["target_price"] == 1750.0


class TestFallbackExtraction:
    """非 JSON 响应走简单文本提取分支。"""

    def test_extracts_action_and_price_from_plain_text(self):
        processor, _ = _processor("综合来看建议买入，目标价 1900")
        result = processor.process_signal("正文", "600519")
        assert result["action"] == "买入"
        assert result["target_price"] == 1900.0

    def test_defaults_to_hold_when_no_signal_found(self):
        processor, _ = _processor("信息不足，无法判断")
        result = processor.process_signal("正文", "600519")
        assert result["action"] == "持有"
        assert result["confidence"] == 0.7
        assert result["risk_score"] == 0.5

    def test_llm_exception_falls_back_to_text_extraction(self):
        class ExplodingLLM:
            def invoke(self, messages):
                raise RuntimeError("LLM 服务不可用")

        processor = SignalProcessor(ExplodingLLM())
        result = processor.process_signal("建议买入，目标价 1234", "600519")
        assert result["action"] == "买入"
        assert result["target_price"] == 1234.0


class TestCurrencyAwareness:
    """货币感知：提示词必须带上对应市场的币种。"""

    def test_a_share_prompt_uses_cny(self):
        processor, llm = _processor(json.dumps({"action": "买入", "target_price": 100}))
        processor.process_signal("正文", "600519")
        system_prompt = llm.calls[0][0][1]
        assert "人民币" in system_prompt
        assert "¥" in system_prompt
        assert "中国A股" in system_prompt

    def test_us_prompt_uses_usd(self):
        processor, llm = _processor(json.dumps({"action": "买入", "target_price": 100}))
        processor.process_signal("body", "AAPL")
        system_prompt = llm.calls[0][0][1]
        assert "美元" in system_prompt
        assert "美股" in system_prompt

    def test_hk_prompt_uses_hkd(self):
        processor, llm = _processor(json.dumps({"action": "买入", "target_price": 100}))
        processor.process_signal("正文", "0700.HK")
        system_prompt = llm.calls[0][0][1]
        assert "港币" in system_prompt
        assert "HK$" in system_prompt
