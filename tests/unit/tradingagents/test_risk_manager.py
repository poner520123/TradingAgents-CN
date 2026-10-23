"""
``tradingagents.agents.managers.risk_manager`` 单元测试。

风险委员会主席（Risk Judge）负责综合风险辩论与交易员计划给出最终决策。
它依赖「当前市场情境」从 ChromaDB 记忆库检索历史教训，因此
**四份分析师报告必须都正确进入检索键**。

回归用例覆盖曾经的复制粘贴缺陷：``fundamentals_report`` 曾被误取为
``state["news_report"]``，导致基本面报告从未参与记忆检索。
"""

from __future__ import annotations

import pytest

from tradingagents.agents.managers.risk_manager import create_risk_manager


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.response_metadata = {}


class FakeLLM:
    """记录 prompt，便于断言节点读取了哪些报告。"""

    def __init__(self, content: str = "最终交易建议: **买入**") -> None:
        self.content = content
        self.prompts: list[str] = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return _FakeResponse(self.content)


class FakeMemory:
    """记录记忆检索使用的情境串。"""

    def __init__(self) -> None:
        self.situations: list[str] = []

    def get_memories(self, curr_situation: str, n_matches: int = 2):
        self.situations.append(curr_situation)
        return []

    def add_situations(self, situations) -> None:
        pass


MARKET_REPORT = "MARKET_REPORT_MARKER 技术面分析"
NEWS_REPORT = "NEWS_REPORT_MARKER 新闻面分析"
FUNDAMENTALS_REPORT = "FUNDAMENTALS_REPORT_MARKER 基本面分析"
SENTIMENT_REPORT = "SENTIMENT_REPORT_MARKER 情绪面分析"
TRADER_PLAN = "TRADER_PLAN_MARKER 交易计划"


def _state() -> dict:
    return {
        "company_of_interest": "600519",
        "market_report": MARKET_REPORT,
        "news_report": NEWS_REPORT,
        "fundamentals_report": FUNDAMENTALS_REPORT,
        "sentiment_report": SENTIMENT_REPORT,
        "investment_plan": TRADER_PLAN,
        "risk_debate_state": {
            "history": "辩论历史",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "latest_speaker": "Neutral Analyst",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 3,
        },
    }


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def memory():
    return FakeMemory()


@pytest.mark.contract
class TestRiskManagerReadsAllReports:
    def test_memory_retrieval_contains_fundamentals_report(self, llm, memory):
        """记忆检索键必须包含基本面报告（回归用例）。"""
        node = create_risk_manager(llm, memory)
        node(_state())

        assert len(memory.situations) == 1
        situation = memory.situations[0]
        assert FUNDAMENTALS_REPORT in situation, "基本面报告未进入记忆检索键"

    def test_memory_retrieval_contains_all_four_reports(self, llm, memory):
        node = create_risk_manager(llm, memory)
        node(_state())

        situation = memory.situations[0]
        assert MARKET_REPORT in situation
        assert SENTIMENT_REPORT in situation
        assert NEWS_REPORT in situation
        assert FUNDAMENTALS_REPORT in situation

    def test_news_report_is_not_duplicated(self, llm, memory):
        """新闻报告不应在检索键中出现两次（曾因复制粘贴导致）。"""
        node = create_risk_manager(llm, memory)
        node(_state())

        situation = memory.situations[0]
        assert situation.count(NEWS_REPORT) == 1


@pytest.mark.contract
class TestRiskManagerOutput:
    def test_returns_final_trade_decision(self, llm, memory):
        node = create_risk_manager(llm, memory)
        result = node(_state())

        assert "final_trade_decision" in result
        assert "买入" in result["final_trade_decision"]
        assert result["risk_debate_state"]["latest_speaker"] == "Judge"

    def test_trader_plan_is_passed_to_prompt(self, llm, memory):
        node = create_risk_manager(llm, memory)
        node(_state())

        assert llm.prompts, "未调用 LLM"
        assert TRADER_PLAN in llm.prompts[0]

    def test_memory_none_is_tolerated(self, llm):
        """memory 为 None 时应跳过检索而不是抛异常。"""
        node = create_risk_manager(llm, None)
        result = node(_state())

        assert "final_trade_decision" in result

    def test_llm_failure_falls_back_to_default_decision(self, memory):
        """LLM 连续失败时回退到默认「持有」建议。"""
        import time

        class BrokenLLM:
            def invoke(self, prompt):
                raise RuntimeError("LLM 不可用")

        node = create_risk_manager(BrokenLLM(), memory)
        # 跳过重试等待
        original_sleep = time.sleep
        time.sleep = lambda *_args, **_kwargs: None
        try:
            result = node(_state())
        finally:
            time.sleep = original_sleep

        assert "持有" in result["final_trade_decision"]
