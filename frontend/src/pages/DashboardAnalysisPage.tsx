import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AnalysisResult from '../components/analysis/AnalysisResult';

const DashboardAnalysisPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const handleBackToList = () => {
    navigate('/dashboard');
  };

  if (!id) {
    return <div>분석 ID가 없습니다.</div>;
  }

  return <AnalysisResult analysisId={id} onBack={handleBackToList} />;
};

export default DashboardAnalysisPage;