import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AnalysisResultResponse, AnalysisStatus } from '../../types';
import { AnalysisService } from '../../services/analysisService';
import toast from 'react-hot-toast';

interface AnalysisResultProps {
  analysisId: string;
  onBack?: () => void;
}

const AnalysisResult: React.FC<AnalysisResultProps> = ({ analysisId, onBack }) => {
  const [analysis, setAnalysis] = useState<AnalysisResultResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const fetchAnalysisResult = async (abortSignal?: AbortSignal) => {
    try {
      setIsLoading(true);
      setHasError(false);
      const data = await AnalysisService.getAnalysisResult(analysisId);
      
      // 취소된 요청이 아닌 경우에만 상태 업데이트
      if (!abortSignal?.aborted) {
        setAnalysis(data);
      }
    } catch (error: any) {
      // 취소된 요청이 아닌 경우에만 에러 처리
      if (!abortSignal?.aborted) {
        console.error('분석 결과 로드 에러:', error);
        if (error.response?.status === 404) {
          setHasError(true);
          setAnalysis(null);
        } else if (error.response?.status !== 401) {
          // 401 에러는 api.ts에서 처리하므로 토스트 표시 안 함
          toast.error(error.response?.data?.error?.message || '분석 결과를 불러오는데 실패했습니다');
          setHasError(true);
        }
      }
    } finally {
      if (!abortSignal?.aborted) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    const abortController = new AbortController();
    
    if (analysisId) {
      fetchAnalysisResult(abortController.signal);
    }
    
    // Cleanup function to cancel the request if component unmounts
    return () => {
      abortController.abort();
    };
  }, [analysisId]);
  
  // 분석이 진행 중인 경우 주기적으로 업데이트
  useEffect(() => {
    if (analysis && (analysis.status === AnalysisStatus.RUNNING || analysis.status === AnalysisStatus.PENDING)) {
      const interval = setInterval(() => {
        fetchAnalysisResult();
      }, 5000); // 5초마다 업데이트
      
      return () => clearInterval(interval);
    }
  }, [analysis?.status, analysisId]);

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
        <LoadingMessage>분석 결과를 불러오는 중...</LoadingMessage>
      </Container>
    );
  }

  if (!analysis && hasError) {
    return (
      <Container>
        <ErrorMessage>분석 결과를 찾을 수 없습니다.</ErrorMessage>
      </Container>
    );
  }
  
  if (!analysis) {
    return null;
  }

  return (
    <Container>
      <Header>
        {onBack && <BackButton onClick={onBack}>← 뒤로</BackButton>}
        <Title>분석 결과: {analysis.ticker}</Title>
        <Status color={getStatusColor(analysis.status)}>
          {getStatusText(analysis.status)}
        </Status>
      </Header>

      <InfoSection>
        <InfoItem>
          <InfoLabel>분석 날짜:</InfoLabel>
          <InfoValue>{new Date(analysis.analysis_date).toLocaleDateString('ko-KR')}</InfoValue>
        </InfoItem>
        <InfoItem>
          <InfoLabel>생성 시간:</InfoLabel>
          <InfoValue>{new Date(analysis.created_at).toLocaleString('ko-KR')}</InfoValue>
        </InfoItem>
        {analysis.completed_at && (
          <InfoItem>
            <InfoLabel>완료 시간:</InfoLabel>
            <InfoValue>{new Date(analysis.completed_at).toLocaleString('ko-KR')}</InfoValue>
          </InfoItem>
        )}
      </InfoSection>

      {analysis.error_message && (
        <ErrorSection>
          <ErrorTitle>오류 메시지</ErrorTitle>
          <ErrorText>{analysis.error_message}</ErrorText>
        </ErrorSection>
      )}

      <ResultsSection>
        {/* 시장 분석 보고서 */}
        <ReportSection>
          <ReportTitle>시장 분석 보고서</ReportTitle>
          {analysis.market_report && !analysis.market_report.includes('def get_') ? (
            <ReportContent>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.market_report}
              </ReactMarkdown>
            </ReportContent>
          ) : (
            <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
          )}
        </ReportSection>

        {/* 감정 분석 보고서 */}
        <ReportSection>
          <ReportTitle>감정 분석 보고서</ReportTitle>
          {analysis.sentiment_report ? (
            <ReportContent>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.sentiment_report}
              </ReactMarkdown>
            </ReportContent>
          ) : (
            <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
          )}
        </ReportSection>

        {/* 뉴스 분석 보고서 */}
        <ReportSection>
          <ReportTitle>뉴스 분석 보고서</ReportTitle>
          {analysis.news_report ? (
            <ReportContent>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.news_report}
              </ReactMarkdown>
            </ReportContent>
          ) : (
            <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
          )}
        </ReportSection>

        {/* 펀더멘털 분석 보고서 */}
        <ReportSection>
          <ReportTitle>펀더멘털 분석 보고서</ReportTitle>
          {analysis.fundamentals_report ? (
            <ReportContent>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.fundamentals_report}
              </ReactMarkdown>
            </ReportContent>
          ) : (
            <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
          )}
        </ReportSection>

        {/* 트레이더 투자 계획 */}
        {(analysis.status === AnalysisStatus.COMPLETED || analysis.trader_investment_plan) && (
          <ReportSection>
            <ReportTitle>트레이더 투자 계획</ReportTitle>
            {analysis.trader_investment_plan ? (
              <ReportContent>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysis.trader_investment_plan}
                </ReactMarkdown>
              </ReportContent>
            ) : (
              <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
            )}
          </ReportSection>
        )}

        {/* 최종 거래 결정 */}
        {(analysis.status === AnalysisStatus.COMPLETED || analysis.final_trade_decision) && (
          <ReportSection>
            <ReportTitle>최종 거래 결정</ReportTitle>
            {analysis.final_trade_decision ? (
              <ReportContent>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysis.final_trade_decision}
                </ReactMarkdown>
              </ReportContent>
            ) : (
              <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
            )}
          </ReportSection>
        )}

        {/* 최종 보고서 */}
        {(analysis.status === AnalysisStatus.COMPLETED || analysis.final_report) && (
          <ReportSection>
            <ReportTitle>최종 보고서</ReportTitle>
            {analysis.final_report ? (
              <ReportContent>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysis.final_report}
                </ReactMarkdown>
              </ReportContent>
            ) : (
              <AnalyzingMessage>분석중입니다...</AnalyzingMessage>
            )}
          </ReportSection>
        )}
      </ResultsSection>
    </Container>
  );
};

const Container = styled.div`
  padding: 2rem;
  max-width: 1000px;
  margin: 0 auto;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
`;

const BackButton = styled.button`
  background-color: #f5f5f5;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  
  &:hover {
    background-color: #e0e0e0;
  }
`;

const Title = styled.h1`
  color: #333;
  margin: 0;
  flex: 1;
`;

const Status = styled.span<{ color: string }>`
  background-color: ${(props) => props.color};
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
`;

const InfoSection = styled.div`
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const InfoItem = styled.div`
  display: flex;
  margin-bottom: 0.5rem;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const InfoLabel = styled.span`
  font-weight: 500;
  color: #666;
  width: 120px;
`;

const InfoValue = styled.span`
  color: #333;
`;

const ErrorSection = styled.div`
  background-color: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
`;

const ErrorTitle = styled.h3`
  color: #d32f2f;
  margin: 0 0 1rem 0;
`;

const ErrorText = styled.p`
  color: #d32f2f;
  margin: 0;
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
  font-size: 1.1rem;
`;

const ErrorMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #ff6b6b;
  font-size: 1.1rem;
`;

const ResultsSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2rem;
`;

const ReportSection = styled.div`
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const ReportTitle = styled.h3`
  color: #333;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #4caf50;
`;

const ReportContent = styled.div`
  color: #555;
  line-height: 1.6;

  /* 마크다운 스타일링 */
  h1, h2, h3, h4, h5, h6 {
    color: #333;
    margin: 1.5rem 0 1rem 0;
    font-weight: 600;
  }

  h1 { font-size: 1.8rem; border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; }
  h2 { font-size: 1.5rem; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; }
  h3 { font-size: 1.3rem; }
  h4 { font-size: 1.1rem; }

  p {
    margin: 1rem 0;
    line-height: 1.7;
  }

  ul, ol {
    margin: 1rem 0;
    padding-left: 2rem;
  }

  li {
    margin: 0.5rem 0;
    line-height: 1.6;
  }

  blockquote {
    border-left: 4px solid #4CAF50;
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    background-color: #f9f9f9;
    font-style: italic;
  }

  code {
    background-color: #f5f5f5;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9rem;
  }

  pre {
    background-color: #f8f8f8;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;

    code {
      background: none;
      padding: 0;
    }
  }

  table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
  }

  th, td {
    border: 1px solid #ddd;
    padding: 0.8rem;
    text-align: left;
  }

  th {
    background-color: #f5f5f5;
    font-weight: 600;
  }

  tr:nth-child(even) {
    background-color: #f9f9f9;
  }

  strong {
    font-weight: 600;
    color: #333;
  }

  em {
    font-style: italic;
    color: #666;
  }

  a {
    color: #4CAF50;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }

  hr {
    border: none;
    border-top: 2px solid #e0e0e0;
    margin: 2rem 0;
  }

  /* GitHub 마크다운 확장 지원 */
  .task-list-item {
    list-style: none;
    margin-left: -1.5rem;
  }

  .task-list-item input {
    margin-right: 0.5rem;
  }
`;

const AnalyzingMessage = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
  font-style: italic;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 1px dashed #ddd;
`;

export default AnalysisResult;