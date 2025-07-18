from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
from tradingagents.agents.utils.websocket_utils import create_agent_config

def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Use only FinnHub and Search Provider tools for news
        tools = [
            toolkit.get_finnhub_news,
            toolkit.get_stock_news,  # Search provider for stock news
            toolkit.get_global_news,  # Search provider for global news
        ]

        system_message = (
            "**IMPORTANT THING** Respond in Korean(한국어로 대답해주세요)\n\nYou are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Look at news from EODHD, and finnhub to be comprehensive. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Makrdown table at the end of the report to organize key points in the report, organized and easy to read."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)
        
        # Create config with agent metadata
        config = create_agent_config("News Analyst", "뉴스 데이터 수집 및 분석 중")
        
        result = chain.invoke(
            state["messages"],
            config=config,
            tools = [GenAITool(google_search={})]                      
        )


        report = ""

        if len(result.tool_calls) == 0:
            # result.content가 리스트인 경우 문자열로 변환
            if isinstance(result.content, list):
                report = "\n".join(str(item) for item in result.content)
            else:
                report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
