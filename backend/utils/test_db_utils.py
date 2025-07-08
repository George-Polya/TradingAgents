import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy import inspect

from utils.db_utils import row_to_dict


class TestDbUtils:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        # Mock database row object
        self.mock_row = Mock()
        
        # Mock inspector
        self.mock_inspector = Mock()
        
        # Test data
        self.test_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "email": "test@example.com",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:00:00",
            "role": "USER"
        }

    def test_row_to_dict_basic_conversion(self):
        """기본 행 to 딕셔너리 변환 테스트"""
        # Given
        mock_attrs = Mock()
        mock_attrs.keys.return_value = self.test_data.keys()
        
        self.mock_inspector.attrs = mock_attrs
        
        # Set up getattr behavior for each attribute
        for key, value in self.test_data.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == self.test_data
        assert isinstance(result, dict)

    def test_row_to_dict_empty_row(self):
        """빈 행 변환 테스트"""
        # Given
        mock_attrs = Mock()
        mock_attrs.keys.return_value = []
        self.mock_inspector.attrs = mock_attrs
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == {}
        assert isinstance(result, dict)

    def test_row_to_dict_with_none_values(self):
        """None 값이 포함된 행 변환 테스트"""
        # Given
        test_data_with_nones = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "email": "test@example.com",
            "optional_field": None,
            "another_optional": None
        }
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = test_data_with_nones.keys()
        self.mock_inspector.attrs = mock_attrs
        
        for key, value in test_data_with_nones.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == test_data_with_nones
        assert result["optional_field"] is None
        assert result["another_optional"] is None

    def test_row_to_dict_with_complex_data_types(self):
        """복잡한 데이터 타입이 포함된 행 변환 테스트"""
        # Given
        from datetime import datetime, date
        import json
        
        complex_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "name": "홍길동",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "birth_date": date(1990, 5, 15),
            "metadata": {"key": "value", "nested": {"data": 123}},
            "tags": ["tag1", "tag2", "tag3"],
            "score": 95.5,
            "is_active": True,
            "count": 42
        }
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = complex_data.keys()
        self.mock_inspector.attrs = mock_attrs
        
        for key, value in complex_data.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == complex_data
        assert isinstance(result["created_at"], datetime)
        assert isinstance(result["birth_date"], date)
        assert isinstance(result["metadata"], dict)
        assert isinstance(result["tags"], list)
        assert isinstance(result["score"], float)
        assert isinstance(result["is_active"], bool)
        assert isinstance(result["count"], int)

    def test_row_to_dict_with_special_characters(self):
        """특수 문자가 포함된 데이터 변환 테스트"""
        # Given
        special_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "korean_name": "김철수",
            "japanese_name": "田中太郎",
            "chinese_name": "李小明",
            "emoji_field": "😀🎉🚀",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "unicode_text": "Ñoël Müller Åse Øyvind",
            "json_string": '{"test": "데이터", "number": 123}',
            "multiline": "Line 1\nLine 2\nLine 3",
            "tabs_and_spaces": "\t  spaced  \t"
        }
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = special_data.keys()
        self.mock_inspector.attrs = mock_attrs
        
        for key, value in special_data.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == special_data
        assert result["korean_name"] == "김철수"
        assert result["emoji_field"] == "😀🎉🚀"
        assert result["unicode_text"] == "Ñoël Müller Åse Øyvind"

    def test_row_to_dict_with_large_dataset(self):
        """대용량 데이터셋 변환 테스트"""
        # Given
        large_data = {}
        for i in range(100):
            large_data[f"field_{i:03d}"] = f"value_{i:03d}"
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = large_data.keys()
        self.mock_inspector.attrs = mock_attrs
        
        for key, value in large_data.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == large_data
        assert len(result) == 100
        assert result["field_000"] == "value_000"
        assert result["field_099"] == "value_099"

    def test_row_to_dict_inspect_called_correctly(self):
        """inspect 함수가 올바르게 호출되는지 테스트"""
        # Given
        mock_attrs = Mock()
        mock_attrs.keys.return_value = ["id", "name"]
        self.mock_inspector.attrs = mock_attrs
        
        setattr(self.mock_row, "id", "test_id")
        setattr(self.mock_row, "name", "test_name")
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector) as mock_inspect:
            result = row_to_dict(self.mock_row)
        
        # Then
        mock_inspect.assert_called_once_with(self.mock_row)
        assert result == {"id": "test_id", "name": "test_name"}

    def test_row_to_dict_getattr_behavior(self):
        """getattr 동작 테스트"""
        # Given
        test_attributes = {
            "simple_attr": "simple_value",
            "numeric_attr": 42,
            "boolean_attr": True
        }
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = test_attributes.keys()
        self.mock_inspector.attrs = mock_attrs
        
        # Mock getattr behavior
        def mock_getattr(obj, attr):
            return test_attributes.get(attr)
        
        for key, value in test_attributes.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == test_attributes

    def test_row_to_dict_with_property_attributes(self):
        """프로퍼티 어트리뷰트가 있는 행 변환 테스트"""
        # Given
        class MockRowWithProperties:
            def __init__(self):
                self._id = "test_id"
                self._name = "test_name"
            
            @property
            def id(self):
                return self._id
            
            @property
            def name(self):
                return self._name
            
            @property
            def computed_field(self):
                return f"{self._name}_{self._id}"
        
        mock_row_with_props = MockRowWithProperties()
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = ["id", "name", "computed_field"]
        self.mock_inspector.attrs = mock_attrs
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(mock_row_with_props)
        
        # Then
        expected = {
            "id": "test_id",
            "name": "test_name",
            "computed_field": "test_name_test_id"
        }
        assert result == expected

    def test_row_to_dict_error_handling(self):
        """에러 처리 테스트"""
        # Given
        mock_attrs = Mock()
        mock_attrs.keys.return_value = ["id", "problematic_attr"]
        self.mock_inspector.attrs = mock_attrs
        
        # Set up normal attribute
        setattr(self.mock_row, "id", "test_id")
        
        # Set up problematic attribute that raises exception
        def problematic_getattr(obj, attr):
            if attr == "problematic_attr":
                raise AttributeError("Attribute access failed")
            return getattr(obj, attr)
        
        # When & Then
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            with pytest.mock.patch('builtins.getattr', side_effect=problematic_getattr):
                with pytest.raises(AttributeError):
                    row_to_dict(self.mock_row)

    def test_row_to_dict_return_type(self):
        """반환 타입 확인 테스트"""
        # Given
        mock_attrs = Mock()
        mock_attrs.keys.return_value = ["test_field"]
        self.mock_inspector.attrs = mock_attrs
        
        setattr(self.mock_row, "test_field", "test_value")
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert isinstance(result, dict)
        assert not isinstance(result, list)
        assert not isinstance(result, tuple)
        assert not isinstance(result, set)

    def test_row_to_dict_key_order_preservation(self):
        """키 순서 보존 테스트"""
        # Given
        ordered_keys = ["field_1", "field_2", "field_3", "field_4", "field_5"]
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = ordered_keys
        self.mock_inspector.attrs = mock_attrs
        
        for i, key in enumerate(ordered_keys):
            setattr(self.mock_row, key, f"value_{i+1}")
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        result_keys = list(result.keys())
        assert result_keys == ordered_keys

    def test_row_to_dict_comprehensive_integration(self):
        """종합 통합 테스트"""
        # Given - Real-world like data
        from datetime import datetime
        
        realistic_data = {
            "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "member_id": "member_123",
            "ticker": "AAPL",
            "analysis_date": "2024-01-01",
            "analysts_selected": ["market", "news", "fundamentals"],
            "research_depth": 3,
            "llm_provider": "openai",
            "backend_url": "http://localhost:8000",
            "shallow_thinker": "gpt-3.5-turbo",
            "deep_thinker": "gpt-4",
            "status": "pending",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 1, 1, 12, 0, 0),
            "market_report": None,
            "sentiment_report": None,
            "news_report": None,
            "fundamentals_report": None,
            "investment_debate_state": None,
            "trader_investment_plan": None,
            "risk_debate_state": None,
            "final_trade_decision": None,
            "final_report": None,
            "error_message": None,
            "completed_at": None
        }
        
        mock_attrs = Mock()
        mock_attrs.keys.return_value = realistic_data.keys()
        self.mock_inspector.attrs = mock_attrs
        
        for key, value in realistic_data.items():
            setattr(self.mock_row, key, value)
        
        # When
        with pytest.mock.patch('utils.db_utils.inspect', return_value=self.mock_inspector):
            result = row_to_dict(self.mock_row)
        
        # Then
        assert result == realistic_data
        assert len(result) == len(realistic_data)
        
        # Verify specific important fields
        assert result["id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert result["ticker"] == "AAPL"
        assert result["research_depth"] == 3
        assert isinstance(result["created_at"], datetime)
        assert result["market_report"] is None