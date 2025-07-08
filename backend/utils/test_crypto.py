import pytest
from unittest.mock import Mock, patch

from utils.crypto import Crypto


class TestCrypto:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.crypto = Crypto()
        self.test_password = "password123"
        self.test_hash = "$2b$12$abcdefghijklmnopqrstuvwxyz"

    def test_crypto_initialization(self):
        """Crypto 클래스 초기화 테스트"""
        # Given & When
        crypto = Crypto()
        
        # Then
        assert crypto.pwd_context is not None
        assert "bcrypt" in crypto.pwd_context.schemes()

    def test_encrypt_password(self):
        """패스워드 암호화 테스트"""
        # Given
        password = "test_password"
        
        # When
        encrypted = self.crypto.encrypt(password)
        
        # Then
        assert encrypted is not None
        assert encrypted != password  # 원본과 다름
        assert isinstance(encrypted, str)
        assert encrypted.startswith("$2b$")  # bcrypt 해시 형태

    def test_encrypt_different_passwords_produce_different_hashes(self):
        """다른 패스워드는 다른 해시를 생성하는지 테스트"""
        # Given
        password1 = "password123"
        password2 = "password456"
        
        # When
        hash1 = self.crypto.encrypt(password1)
        hash2 = self.crypto.encrypt(password2)
        
        # Then
        assert hash1 != hash2

    def test_encrypt_same_password_produces_different_salts(self):
        """같은 패스워드도 다른 솔트로 인해 다른 해시 생성 테스트"""
        # Given
        password = "same_password"
        
        # When
        hash1 = self.crypto.encrypt(password)
        hash2 = self.crypto.encrypt(password)
        
        # Then
        assert hash1 != hash2  # 솔트가 다르므로 해시도 다름

    def test_verify_correct_password(self):
        """올바른 패스워드 검증 테스트"""
        # Given
        password = "test_password"
        encrypted = self.crypto.encrypt(password)
        
        # When
        result = self.crypto.verify(password, encrypted)
        
        # Then
        assert result is True

    def test_verify_incorrect_password(self):
        """잘못된 패스워드 검증 테스트"""
        # Given
        password = "test_password"
        wrong_password = "wrong_password"
        encrypted = self.crypto.encrypt(password)
        
        # When
        result = self.crypto.verify(wrong_password, encrypted)
        
        # Then
        assert result is False

    def test_verify_empty_password(self):
        """빈 패스워드 검증 테스트"""
        # Given
        password = ""
        encrypted = self.crypto.encrypt(password)
        
        # When
        result = self.crypto.verify(password, encrypted)
        
        # Then
        assert result is True

    def test_verify_with_invalid_hash(self):
        """잘못된 해시 형태로 검증 테스트"""
        # Given
        password = "test_password"
        invalid_hash = "invalid_hash"
        
        # When & Then
        with pytest.raises(ValueError):
            self.crypto.verify(password, invalid_hash)

    def test_verify_with_none_values(self):
        """None 값으로 검증 테스트"""
        # Given
        password = "test_password"
        encrypted = self.crypto.encrypt(password)
        
        # When & Then
        with pytest.raises((TypeError, ValueError)):
            self.crypto.verify(None, encrypted)
            
        with pytest.raises((TypeError, ValueError)):
            self.crypto.verify(password, None)

    def test_encrypt_with_special_characters(self):
        """특수 문자가 포함된 패스워드 암호화 테스트"""
        # Given
        password = "P@ssw0rd!@#$%^&*()"
        
        # When
        encrypted = self.crypto.encrypt(password)
        
        # Then
        assert encrypted is not None
        assert self.crypto.verify(password, encrypted) is True

    def test_encrypt_with_unicode_characters(self):
        """유니코드 문자가 포함된 패스워드 암호화 테스트"""
        # Given
        password = "패스워드123"
        
        # When
        encrypted = self.crypto.encrypt(password)
        
        # Then
        assert encrypted is not None
        assert self.crypto.verify(password, encrypted) is True

    def test_encrypt_long_password(self):
        """긴 패스워드 암호화 테스트"""
        # Given
        password = "a" * 100  # 100자 길이
        
        # When
        encrypted = self.crypto.encrypt(password)
        
        # Then
        assert encrypted is not None
        assert self.crypto.verify(password, encrypted) is True

    @patch('utils.crypto.CryptContext')
    def test_crypto_context_configuration(self, mock_crypt_context):
        """CryptContext 설정 테스트"""
        # Given
        mock_context = Mock()
        mock_crypt_context.return_value = mock_context
        
        # When
        crypto = Crypto()
        
        # Then
        mock_crypt_context.assert_called_once_with(schemes=["bcrypt"], deprecated="auto")
        assert crypto.pwd_context == mock_context

    def test_encrypt_method_delegation(self):
        """encrypt 메서드가 CryptContext.hash를 호출하는지 테스트"""
        # Given
        password = "test_password"
        expected_hash = "$2b$12$test_hash"
        
        with patch.object(self.crypto.pwd_context, 'hash', return_value=expected_hash) as mock_hash:
            # When
            result = self.crypto.encrypt(password)
            
            # Then
            mock_hash.assert_called_once_with(password)
            assert result == expected_hash

    def test_verify_method_delegation(self):
        """verify 메서드가 CryptContext.verify를 호출하는지 테스트"""
        # Given
        password = "test_password"
        hash_value = "$2b$12$test_hash"
        expected_result = True
        
        with patch.object(self.crypto.pwd_context, 'verify', return_value=expected_result) as mock_verify:
            # When
            result = self.crypto.verify(password, hash_value)
            
            # Then
            mock_verify.assert_called_once_with(password, hash_value)
            assert result == expected_result

    def test_multiple_crypto_instances_independence(self):
        """여러 Crypto 인스턴스가 독립적으로 동작하는지 테스트"""
        # Given
        crypto1 = Crypto()
        crypto2 = Crypto()
        password = "test_password"
        
        # When
        hash1 = crypto1.encrypt(password)
        hash2 = crypto2.encrypt(password)
        
        # Then
        # 각 인스턴스는 독립적이므로 다른 해시 생성
        assert hash1 != hash2
        
        # 하지만 서로 검증 가능
        assert crypto1.verify(password, hash2) is True
        assert crypto2.verify(password, hash1) is True