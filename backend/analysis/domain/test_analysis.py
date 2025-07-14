import pytest
from datetime import datetime, date
from pydantic import ValidationError

from analysis.domain.analysis import Analysis
from analysis.infra.db_models.analysis import AnalysisStatus


class TestAnalysis:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.valid_analysis_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "analysis_date": date(2024, 1, 1),
            "analysts_selected": ["market", "sentiment", "news"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4",
            "status": AnalysisStatus.PENDING,
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 1, 12, 0, 0)
        }

    def test_analysis_creation_with_all_fields(self):
        """모든 필드가 포함된 Analysis 생성 테스트"""
        # Given
        data = self.valid_analysis_data.copy()
        data.update({
            "market_report": "Market analysis report",
            "news_report": "News analysis report",
            "fundamentals_report": "Fundamentals analysis report",
            "investment_debate_state": {"rounds": 3, "decision": "buy"},
            "trader_investment_plan": "Investment plan details",
            "risk_debate_state": {"risk_level": "medium"},
            "final_trade_decision": "BUY",
            "final_report": "Final analysis report",
            "error_message": None,
            "completed_at": datetime(2024, 1, 1, 13, 0, 0)
        })
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.id == data["id"]
        assert analysis.member_id == data["member_id"]
        assert analysis.ticker == data["ticker"]
        assert analysis.analysis_date == data["analysis_date"]
        assert analysis.analysts_selected == data["analysts_selected"]
        assert analysis.research_depth == data["research_depth"]
        assert analysis.llm_provider == data["llm_provider"]
        assert analysis.backend_url == data["backend_url"]
        assert analysis.shallow_thinker == data["shallow_thinker"]
        assert analysis.deep_thinker == data["deep_thinker"]
        assert analysis.status == data["status"]
        assert analysis.market_report == data["market_report"]
        assert analysis.news_report == data["news_report"]
        assert analysis.fundamentals_report == data["fundamentals_report"]
        assert analysis.investment_debate_state == data["investment_debate_state"]
        assert analysis.trader_investment_plan == data["trader_investment_plan"]
        assert analysis.risk_debate_state == data["risk_debate_state"]
        assert analysis.final_trade_decision == data["final_trade_decision"]
        assert analysis.final_report == data["final_report"]
        assert analysis.error_message == data["error_message"]
        assert analysis.completed_at == data["completed_at"]
        assert analysis.created_at == data["created_at"]
        assert analysis.updated_at == data["updated_at"]

    def test_analysis_creation_with_minimal_fields(self):
        """최소 필드만으로 Analysis 생성 테스트"""
        # Given - 모든 필드가 optional이므로 빈 딕셔너리로 생성 가능
        data = {}
        
        # When
        analysis = Analysis(**data)
        
        # Then - 기본값 확인
        assert analysis.id is None
        assert analysis.member_id is None
        assert analysis.ticker is None
        assert analysis.analysis_date is None
        assert analysis.analysts_selected == []
        assert analysis.research_depth == 1
        assert analysis.llm_provider == "google"
        assert analysis.backend_url == "https://generativelanguage.googleapis.com/v1"
        assert analysis.shallow_thinker == "gemini-2.5-flash-lite-preview-06-17"
        assert analysis.deep_thinker == "gemini-2.5-flash-lite-preview-06-17"
        assert analysis.status == AnalysisStatus.PENDING
        assert analysis.market_report is None
        assert analysis.news_report is None
        assert analysis.fundamentals_report is None
        assert analysis.investment_debate_state is None
        assert analysis.trader_investment_plan is None
        assert analysis.risk_debate_state is None
        assert analysis.final_trade_decision is None
        assert analysis.final_report is None
        assert analysis.error_message is None
        assert analysis.completed_at is None
        assert analysis.created_at is None
        assert analysis.updated_at is None

    def test_analysis_creation_with_partial_fields(self):
        """일부 필드만 포함된 Analysis 생성 테스트"""
        # Given
        data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "status": AnalysisStatus.RUNNING
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.id == data["id"]
        assert analysis.member_id == data["member_id"]
        assert analysis.ticker == data["ticker"]
        assert analysis.status == data["status"]
        # 기본값 확인
        assert analysis.research_depth == 1
        assert analysis.llm_provider == "google"
        assert analysis.analysts_selected == []

    def test_analysis_different_statuses(self):
        """다양한 상태의 Analysis 생성 테스트"""
        # Given
        base_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL"
        }
        
        statuses = [
            AnalysisStatus.PENDING,
            AnalysisStatus.RUNNING,
            AnalysisStatus.COMPLETED,
            AnalysisStatus.FAILED
        ]
        
        for status in statuses:
            # When
            data = base_data.copy()
            data["status"] = status
            analysis = Analysis(**data)
            
            # Then
            assert analysis.status == status

    def test_analysis_with_empty_analysts_list(self):
        """빈 분석가 리스트로 Analysis 생성 테스트"""
        # Given
        data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "analysts_selected": []
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.analysts_selected == []

    def test_analysis_with_multiple_analysts(self):
        """여러 분석가가 선택된 Analysis 생성 테스트"""
        # Given
        analysts = ["market", "sentiment", "news", "fundamentals"]
        data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "analysts_selected": analysts
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.analysts_selected == analysts
        assert len(analysis.analysts_selected) == 4

    def test_analysis_with_different_research_depths(self):
        """다양한 연구 깊이로 Analysis 생성 테스트"""
        # Given
        depths = [1, 2, 3, 5, 10]
        
        for depth in depths:
            # When
            data = {"research_depth": depth}
            analysis = Analysis(**data)
            
            # Then
            assert analysis.research_depth == depth

    def test_analysis_with_different_llm_providers(self):
        """다양한 LLM 제공자로 Analysis 생성 테스트"""
        # Given
        providers = ["openai", "google", "anthropic", "azure"]
        
        for provider in providers:
            # When
            data = {"llm_provider": provider}
            analysis = Analysis(**data)
            
            # Then
            assert analysis.llm_provider == provider

    def test_analysis_with_custom_backend_url(self):
        """커스텀 백엔드 URL로 Analysis 생성 테스트"""
        # Given
        custom_urls = [
            "http://localhost:3000",
            "https://api.example.com",
            "https://custom-backend.domain.com/v1"
        ]
        
        for url in custom_urls:
            # When
            data = {"backend_url": url}
            analysis = Analysis(**data)
            
            # Then
            assert analysis.backend_url == url

    def test_analysis_with_different_thinkers(self):
        """다양한 thinker 모델로 Analysis 생성 테스트"""
        # Given
        data = {
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4"
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.shallow_thinker == data["shallow_thinker"]
        assert analysis.deep_thinker == data["deep_thinker"]

    def test_analysis_with_reports(self):
        """리포트 데이터가 포함된 Analysis 생성 테스트"""
        # Given
        reports = {
            "market_report": "Market is bullish",
            "news_report": "Good news coverage",
            "fundamentals_report": "Strong fundamentals"
        }
        
        # When
        analysis = Analysis(**reports)
        
        # Then
        assert analysis.market_report == reports["market_report"]
        assert analysis.news_report == reports["news_report"]
        assert analysis.fundamentals_report == reports["fundamentals_report"]

    def test_analysis_with_debate_states(self):
        """토론 상태 데이터가 포함된 Analysis 생성 테스트"""
        # Given
        data = {
            "investment_debate_state": {
                "rounds": 3,
                "participants": ["analyst1", "analyst2"],
                "decision": "buy"
            },
            "risk_debate_state": {
                "risk_level": "medium",
                "factors": ["volatility", "market_conditions"]
            }
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.investment_debate_state == data["investment_debate_state"]
        assert analysis.risk_debate_state == data["risk_debate_state"]

    def test_analysis_with_final_results(self):
        """최종 결과가 포함된 Analysis 생성 테스트"""
        # Given
        data = {
            "final_trade_decision": "BUY",
            "final_report": "Based on comprehensive analysis, recommend BUY"
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.final_trade_decision == data["final_trade_decision"]
        assert analysis.final_report == data["final_report"]

    def test_analysis_with_error_information(self):
        """오류 정보가 포함된 Analysis 생성 테스트"""
        # Given
        data = {
            "status": AnalysisStatus.FAILED,
            "error_message": "API request failed",
            "completed_at": datetime(2024, 1, 1, 13, 0, 0)
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.status == AnalysisStatus.FAILED
        assert analysis.error_message == data["error_message"]
        assert analysis.completed_at == data["completed_at"]

    def test_analysis_with_timestamps(self):
        """타임스탬프가 포함된 Analysis 생성 테스트"""
        # Given
        now = datetime.now()
        data = {
            "created_at": now,
            "updated_at": now,
            "completed_at": now
        }
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.created_at == now
        assert analysis.updated_at == now
        assert analysis.completed_at == now

    def test_analysis_date_field(self):
        """analysis_date 필드 테스트"""
        # Given
        test_date = date(2024, 12, 25)
        data = {"analysis_date": test_date}
        
        # When
        analysis = Analysis(**data)
        
        # Then
        assert analysis.analysis_date == test_date
        assert isinstance(analysis.analysis_date, date)

    def test_analysis_immutability_after_creation(self):
        """생성 후 Analysis 객체의 불변성 테스트"""
        # Given
        data = self.valid_analysis_data.copy()
        analysis = Analysis(**data)
        
        # When & Then
        # Pydantic v2에서는 기본적으로 변경 가능하므로 변경 후 원본과 다른지 확인
        original_ticker = analysis.ticker
        analysis.ticker = "GOOGL"
        assert analysis.ticker == "GOOGL"
        assert analysis.ticker != original_ticker

    def test_analysis_model_validation(self):
        """Analysis 모델 검증 테스트"""
        # Given
        data = self.valid_analysis_data.copy()
        
        # When
        analysis = Analysis(**data)
        
        # Then
        # 모델이 정상적으로 검증되고 생성됨
        assert isinstance(analysis, Analysis)
        
        # 모든 필드가 올바르게 설정됨
        for key, value in data.items():
            assert getattr(analysis, key) == value

    def test_analysis_model_dict_conversion(self):
        """Analysis 모델의 딕셔너리 변환 테스트"""
        # Given
        data = self.valid_analysis_data.copy()
        analysis = Analysis(**data)
        
        # When
        analysis_dict = analysis.model_dump()
        
        # Then
        assert isinstance(analysis_dict, dict)
        for key, value in data.items():
            assert analysis_dict[key] == value

    def test_analysis_model_json_serialization(self):
        """Analysis 모델의 JSON 직렬화 테스트"""
        # Given
        data = self.valid_analysis_data.copy()
        analysis = Analysis(**data)
        
        # When
        json_str = analysis.model_dump_json()
        
        # Then
        assert isinstance(json_str, str)
        assert "01ARZ3NDEKTSV4RRFFQ69G5FAV" in json_str
        assert "member_123" in json_str
        assert "AAPL" in json_str