import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import LoginForm from '../components/auth/LoginForm';
import RegisterForm from '../components/auth/RegisterForm';

const LoginPage: React.FC = () => {
  const [isLoginMode, setIsLoginMode] = useState(true);
  const navigate = useNavigate();

  const handleSuccess = () => {
    navigate('/dashboard');
  };

  const handleRegisterSuccess = () => {
    setIsLoginMode(true);
  };

  return (
    <Container>
      <Content>
        <WelcomeSection>
          <WelcomeTitle>Trading Agents</WelcomeTitle>
          <WelcomeDescription>
            AI 기반 주식 분석 플랫폼으로 스마트한 투자 결정을 내리세요
          </WelcomeDescription>
        </WelcomeSection>

        <FormSection>
          {isLoginMode ? (
            <>
              <LoginForm onSuccess={handleSuccess} />
              <SwitchText>
                계정이 없으신가요?{' '}
                <SwitchLink onClick={() => setIsLoginMode(false)}>
                  회원가입
                </SwitchLink>
              </SwitchText>
            </>
          ) : (
            <>
              <RegisterForm onSuccess={handleRegisterSuccess} />
              <SwitchText>
                이미 계정이 있으신가요?{' '}
                <SwitchLink onClick={() => setIsLoginMode(true)}>
                  로그인
                </SwitchLink>
              </SwitchText>
            </>
          )}
        </FormSection>
      </Content>
    </Container>
  );
};

const Container = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
`;

const Content = styled.div`
  display: flex;
  max-width: 1000px;
  width: 100%;
  background-color: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;

  @media (max-width: 768px) {
    flex-direction: column;
  }
`;

const WelcomeSection = styled.div`
  flex: 1;
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
  color: white;
  padding: 3rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;

  @media (max-width: 768px) {
    padding: 2rem;
  }
`;

const WelcomeTitle = styled.h1`
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 1rem;

  @media (max-width: 768px) {
    font-size: 2rem;
  }
`;

const WelcomeDescription = styled.p`
  font-size: 1.2rem;
  opacity: 0.9;
  line-height: 1.6;

  @media (max-width: 768px) {
    font-size: 1rem;
  }
`;

const FormSection = styled.div`
  flex: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;

  @media (max-width: 768px) {
    padding: 1rem;
  }
`;

const SwitchText = styled.p`
  text-align: center;
  margin-top: 1rem;
  color: #666;
`;

const SwitchLink = styled.button`
  background: none;
  border: none;
  color: #4CAF50;
  text-decoration: underline;
  cursor: pointer;
  font-size: inherit;

  &:hover {
    color: #45a049;
  }
`;

export default LoginPage;