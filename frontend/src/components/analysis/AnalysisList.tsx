import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { AnalysisSessionResponse, AnalysisStatus } from '../../types';
import { AnalysisService } from '../../services/analysisService';
import toast from 'react-hot-toast';

interface AnalysisListProps {
  onSelectAnalysis?: (analysisId: string) => void;
}

const AnalysisList: React.FC<AnalysisListProps> = ({ onSelectAnalysis }) => {
  const [analyses, setAnalyses] = useState<AnalysisSessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAnalyses = async () => {
    try {
      const data = await AnalysisService.getAnalysisList();
      setAnalyses(data);
    } catch (error: any) {
      toast.error(error.response?.data?.error?.message || '분석 목록을 불러오는데 실패했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, []);

  const getStatusColor = (status: AnalysisStatus) => {
    switch (status) {
      case AnalysisStatus.PENDING:
        return '#ffa500';
      case AnalysisStatus.RUNNING:
        return '#2196f3';
      case AnalysisStatus.COMPLETED:
        return '#4caf50';
      case AnalysisStatus.FAILED:
        return '#ff6b6b';
      default:
        return '#999';
    }
  };

  const getStatusText = (status: AnalysisStatus) => {
    switch (status) {
      case AnalysisStatus.PENDING:
        return '대기 중';
      case AnalysisStatus.RUNNING:
        return '진행 중';
      case AnalysisStatus.COMPLETED:
        return '완료';
      case AnalysisStatus.FAILED:
        return '실패';
      default:
        return '알 수 없음';
    }
  };

  if (isLoading) {
    return (
      <Container>
        <Title>분석 목록</Title>
        <LoadingMessage>분석 목록을 불러오는 중...</LoadingMessage>
      </Container>
    );
  }

  return (
    <Container>
      <Title>분석 목록</Title>
      {analyses.length === 0 ? (
        <EmptyMessage>아직 분석이 없습니다. 새로운 분석을 시작해보세요!</EmptyMessage>
      ) : (
        <AnalysisGrid>
          {analyses.map((analysis) => (
            <AnalysisCard
              key={analysis.id}
              onClick={() => onSelectAnalysis?.(analysis.id)}
            >
              <AnalysisHeader>
                <Ticker>{analysis.ticker}</Ticker>
                <Status color={getStatusColor(analysis.status)}>
                  {getStatusText(analysis.status)}
                </Status>
              </AnalysisHeader>
              <AnalysisDetails>
                <Detail>
                  <DetailLabel>Shallow Thinker:</DetailLabel>
                  <DetailValue>{analysis.shallow_thinker}</DetailValue>
                </Detail>
                <Detail>
                  <DetailLabel>Deep Thinker:</DetailLabel>
                  <DetailValue>{analysis.deep_thinker}</DetailValue>
                </Detail>
              </AnalysisDetails>
            </AnalysisCard>
          ))}
        </AnalysisGrid>
      )}
    </Container>
  );
};

const Container = styled.div`
  padding: 2rem;
`;

const Title = styled.h2`
  color: #333;
  margin-bottom: 2rem;
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
`;

const EmptyMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
  font-size: 1.1rem;
`;

const AnalysisGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
`;

const AnalysisCard = styled.div`
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  }
`;

const AnalysisHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
`;

const Ticker = styled.h3`
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
  margin: 0;
`;

const Status = styled.span<{ color: string }>`
  background-color: ${(props) => props.color};
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
`;

const AnalysisDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Detail = styled.div`
  display: flex;
  flex-direction: column;
`;

const DetailLabel = styled.span`
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
`;

const DetailValue = styled.span`
  font-size: 0.875rem;
  color: #333;
  word-break: break-word;
`;

export default AnalysisList;