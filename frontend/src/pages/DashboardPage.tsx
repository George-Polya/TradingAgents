import React, { useState } from 'react';
import styled from 'styled-components';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Layout from '../components/common/Layout';
import { useWebSocket } from '../hooks/useWebSocket';
import { AnalysisProgressUpdate } from '../types';
import toast from 'react-hot-toast';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [progressUpdates, setProgressUpdates] = useState<Record<string, AnalysisProgressUpdate>>({});

  const handleProgressUpdate = (update: AnalysisProgressUpdate) => {
    setProgressUpdates(prev => ({
      ...prev,
      [update.analysis_id]: update
    }));
    
    toast.success(`${update.current_agent}: ${update.message || update.status}`);
  };

  useWebSocket({ onProgressUpdate: handleProgressUpdate });

  const getCurrentView = () => {
    const path = location.pathname;
    if (path.includes('/dashboard/new')) return 'form';
    if (path.includes('/dashboard/analysis/')) return 'result';
    return 'list';
  };

  return (
    <Layout>
      <Container>
        <Header>
          <Title>Trading Agents 대시보드</Title>
          <ButtonGroup>
            <NavButton
              active={getCurrentView() === 'list'}
              onClick={() => navigate('/dashboard')}
            >
              분석 목록
            </NavButton>
            <NavButton
              active={getCurrentView() === 'form'}
              onClick={() => navigate('/dashboard/new')}
            >
              새 분석
            </NavButton>
          </ButtonGroup>
        </Header>

        <Content>
          <Outlet />
        </Content>

        {Object.keys(progressUpdates).length > 0 && (
          <ProgressSection>
            <ProgressTitle>실시간 분석 진행 상황</ProgressTitle>
            {Object.values(progressUpdates).map((update) => (
              <ProgressItem key={update.analysis_id}>
                <ProgressInfo>
                  <ProgressAgent>{update.current_agent}</ProgressAgent>
                  <ProgressStatus>{update.status}</ProgressStatus>
                </ProgressInfo>
                <ProgressBar>
                  <ProgressFill percentage={update.progress_percentage} />
                </ProgressBar>
                <ProgressText>
                  {update.progress_percentage.toFixed(1)}% - {update.message || update.current_report_section}
                </ProgressText>
              </ProgressItem>
            ))}
          </ProgressSection>
        )}
      </Container>
    </Layout>
  );
};

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e0e0e0;

  @media (max-width: 768px) {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
`;

const Title = styled.h1`
  color: #333;
  margin: 0;
  font-size: 2rem;

  @media (max-width: 768px) {
    text-align: center;
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 1rem;

  @media (max-width: 768px) {
    justify-content: center;
  }
`;

const NavButton = styled.button<{ active: boolean }>`
  padding: 0.75rem 1.5rem;
  border: 2px solid ${(props) => (props.active ? '#4CAF50' : '#ddd')};
  background-color: ${(props) => (props.active ? '#4CAF50' : 'white')};
  color: ${(props) => (props.active ? 'white' : '#333')};
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;

  &:hover {
    background-color: ${(props) => (props.active ? '#45a049' : '#f5f5f5')};
    border-color: ${(props) => (props.active ? '#45a049' : '#ccc')};
  }
`;

const Content = styled.div`
  min-height: 500px;
`;

const ErrorMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #ff6b6b;
  font-size: 1.1rem;
`;

const ProgressSection = styled.div`
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  max-width: 400px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 1rem;
  z-index: 1000;
`;

const ProgressTitle = styled.h3`
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1rem;
`;

const ProgressItem = styled.div`
  margin-bottom: 1rem;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const ProgressInfo = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
`;

const ProgressAgent = styled.span`
  font-weight: 500;
  color: #333;
  font-size: 0.875rem;
`;

const ProgressStatus = styled.span`
  font-size: 0.875rem;
  color: #666;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 4px;
  background-color: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 0.5rem;
`;

const ProgressFill = styled.div<{ percentage: number }>`
  width: ${(props) => props.percentage}%;
  height: 100%;
  background-color: #4CAF50;
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  font-size: 0.75rem;
  color: #666;
`;

export default DashboardPage;