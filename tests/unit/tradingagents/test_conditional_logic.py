"""
``tradingagents.graph.conditional_logic`` 单元测试。

这是多智能体工作流的**路由中枢**：所有条件边都依赖本模块的判定结果。
重点验证：
- 分析师节点的工具调用计数防死循环机制；
- 辩论轮次计数（投资辩论 / 风险辩论）的终止条件；
- 下一个发言人的轮转顺序。
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from tradingagents.graph.conditional_logic import ConditionalLogic


def _state(**overrides):
    """构造一个最小可用的 AgentState 字典。"""
    base = {
        "messages": [HumanMessage(content="分析 600519")],
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "market_tool_call_count": 0,
        "sentiment_tool_call_count": 0,
        "news_tool_call_count": 0,
        "fundamentals_tool_call_count": 0,
        "investment_debate_state": {
            "history": "",
            "current_response": "",
            "count": 0,
        },
        "risk_debate_state": {
            "history": "",
            "latest_speaker": "",
            "count": 0,
        },
    }
    base.update(overrides)
    return base


class TestAnalystToolLoop:
    """分析师节点的继续/结束判定。"""

    def test_no_tool_calls_ends_immediately(self):
        logic = ConditionalLogic()
        state = _state(messages=[AIMessage(content="我已经分析完成")])
        assert logic.should_continue_market(state) == "Msg Clear Market"

    def test_tool_calls_route_to_tool_node(self):
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_market_data_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(messages=[message])
        assert logic.should_continue_market(state) == "tools_market"

    def test_report_longer_than_100_chars_wins_over_tool_calls(self):
        """报告已产出时，即使模型仍请求工具也应结束 —— 这是防死循环的关键分支。"""
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_market_data_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(messages=[message], market_report="x" * 101)
        assert logic.should_continue_market(state) == "Msg Clear Market"

    def test_report_exactly_100_chars_does_not_trigger_shortcut(self):
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_market_data_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(messages=[message], market_report="x" * 100)
        assert logic.should_continue_market(state) == "tools_market"

    @pytest.mark.parametrize("count,expected", [(3, "Msg Clear Market"), (5, "Msg Clear Market")])
    def test_tool_call_count_limit_forces_exit(self, count, expected):
        """达到最大工具调用次数必须强制退出，即使仍有 tool_calls。"""
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_market_data_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(messages=[message], market_tool_call_count=count)
        assert logic.should_continue_market(state) == expected


class TestPerAnalystCounters:
    """每个分析师使用各自独立的计数器与报告字段。"""

    @pytest.mark.parametrize(
        "method,counter,report_key,tool_node,clear_node",
        [
            ("should_continue_market", "market_tool_call_count", "market_report", "tools_market", "Msg Clear Market"),
            ("should_continue_social", "sentiment_tool_call_count", "sentiment_report", "tools_social", "Msg Clear Social"),
            ("should_continue_news", "news_tool_call_count", "news_report", "tools_news", "Msg Clear News"),
            (
                "should_continue_fundamentals",
                "fundamentals_tool_call_count",
                "fundamentals_report",
                "tools_fundamentals",
                "Msg Clear Fundamentals",
            ),
        ],
    )
    def test_counter_isolated_per_analyst(
        self, method, counter, report_key, tool_node, clear_node
    ):
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "tool", "args": {}, "id": "call_1"}],
        )
        # 计数器已超限 → 强制结束
        state = _state(messages=[message], **{counter: 3})
        assert getattr(logic, method)(state) == clear_node

        # 计数器未超限且有报告 → 报告分支优先
        state = _state(messages=[message], **{counter: 0, report_key: "y" * 101})
        assert getattr(logic, method)(state) == clear_node

        # 计数器未超限、无报告、有 tool_calls → 执行工具
        state = _state(messages=[message], **{counter: 0})
        assert getattr(logic, method)(state) == tool_node


class TestFundamentalsSpecialCase:
    """基本面分析师：一次工具调用即可拿全量数据，上限为 1。"""

    def test_fundamentals_limit_is_one(self):
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_fundamentals_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(messages=[message], fundamentals_tool_call_count=1)
        assert logic.should_continue_fundamentals(state) == "Msg Clear Fundamentals"

        state = _state(messages=[message], fundamentals_tool_call_count=0)
        assert logic.should_continue_fundamentals(state) == "tools_fundamentals"

    def test_fundamentals_report_has_priority_over_counter(self):
        """报告优先级高于工具调用计数（与其它分析师相反）。"""
        logic = ConditionalLogic()
        message = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_fundamentals_unified", "args": {}, "id": "call_1"}],
        )
        state = _state(
            messages=[message],
            fundamentals_tool_call_count=1,
            fundamentals_report="z" * 101,
        )
        assert logic.should_continue_fundamentals(state) == "Msg Clear Fundamentals"


class TestInvestmentDebate:
    """投资辩论（多空研究员）的轮转控制。"""

    def test_first_speaker_is_bull(self):
        logic = ConditionalLogic(max_debate_rounds=1)
        state = _state(
            investment_debate_state={"history": "", "current_response": "", "count": 0}
        )
        assert logic.should_continue_debate(state) == "Bull Researcher"

    def test_alternates_between_bull_and_bear(self):
        logic = ConditionalLogic(max_debate_rounds=3)
        state = _state(
            investment_debate_state={"history": "", "current_response": "Bull ...", "count": 1}
        )
        assert logic.should_continue_debate(state) == "Bear Researcher"

        state = _state(
            investment_debate_state={"history": "", "current_response": "Bear ...", "count": 2}
        )
        assert logic.should_continue_debate(state) == "Bull Researcher"

    def test_reaches_manager_when_count_exhausted(self):
        """max_debate_rounds=1 → 上限 2 次发言（多头 + 空头）。"""
        logic = ConditionalLogic(max_debate_rounds=1)
        state = _state(
            investment_debate_state={"history": "", "current_response": "Bear ...", "count": 2}
        )
        assert logic.should_continue_debate(state) == "Research Manager"

    def test_limit_scales_with_rounds(self):
        """max_debate_rounds=3 → 上限 6 次发言。"""
        logic = ConditionalLogic(max_debate_rounds=3)
        state = _state(
            investment_debate_state={"history": "", "current_response": "Bull ...", "count": 6}
        )
        assert logic.should_continue_debate(state) == "Research Manager"

    def test_just_below_limit_still_continues(self):
        logic = ConditionalLogic(max_debate_rounds=3)
        state = _state(
            investment_debate_state={"history": "", "current_response": "Bull ...", "count": 5}
        )
        assert logic.should_continue_debate(state) == "Bear Researcher"


class TestRiskDebate:
    """风险辩论（激进/保守/中性）的轮转控制。"""

    def test_first_speaker_is_risky(self):
        logic = ConditionalLogic(max_risk_discuss_rounds=1)
        state = _state(
            risk_debate_state={"history": "", "latest_speaker": "", "count": 0}
        )
        assert logic.should_continue_risk_analysis(state) == "Risky Analyst"

    @pytest.mark.parametrize(
        "latest,expected",
        [
            ("Risky Analyst", "Safe Analyst"),
            ("Safe Analyst", "Neutral Analyst"),
            ("Neutral Analyst", "Risky Analyst"),
        ],
    )
    def test_rotation_order(self, latest, expected):
        logic = ConditionalLogic(max_risk_discuss_rounds=2)
        state = _state(
            risk_debate_state={"history": "", "latest_speaker": latest, "count": 1}
        )
        assert logic.should_continue_risk_analysis(state) == expected

    def test_reaches_judge_when_count_exhausted(self):
        """max_risk_discuss_rounds=1 → 上限 3 次发言。"""
        logic = ConditionalLogic(max_risk_discuss_rounds=1)
        state = _state(
            risk_debate_state={"history": "", "latest_speaker": "Neutral Analyst", "count": 3}
        )
        assert logic.should_continue_risk_analysis(state) == "Risk Judge"

    def test_limit_scales_with_rounds(self):
        logic = ConditionalLogic(max_risk_discuss_rounds=2)
        state = _state(
            risk_debate_state={"history": "", "latest_speaker": "Neutral Analyst", "count": 6}
        )
        assert logic.should_continue_risk_analysis(state) == "Risk Judge"


class TestToolMessageHandling:
    """工具执行结果（ToolMessage）不应被误判为需要再次调用工具。"""

    def test_tool_message_ends_analyst_loop(self):
        logic = ConditionalLogic()
        state = _state(
            messages=[
                AIMessage(
                    content="",
                    tool_calls=[{"name": "tool", "args": {}, "id": "call_1"}],
                ),
                ToolMessage(content="data", tool_call_id="call_1"),
            ]
        )
        assert logic.should_continue_market(state) == "Msg Clear Market"
