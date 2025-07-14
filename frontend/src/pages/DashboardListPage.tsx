import React from 'react';
import { useNavigate } from 'react-router-dom';
import AnalysisList from '../components/analysis/AnalysisList';

const DashboardListPage: React.FC = () => {
  const navigate = useNavigate();

  const handleSelectAnalysis = (analysisId: string) => {
    navigate(`/dashboard/analysis/${analysisId}`);
  };

  return <AnalysisList onSelectAnalysis={handleSelectAnalysis} />;
};

export default DashboardListPage;