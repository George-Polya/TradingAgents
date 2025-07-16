import React from 'react';
import { useNavigate } from 'react-router-dom';
import AnalysisForm from '../components/analysis/AnalysisForm';

const DashboardNewPage: React.FC = () => {
  const navigate = useNavigate();

  const handleAnalysisSuccess = (analysisId: string) => {
    navigate(`/dashboard/analysis/${analysisId}`);
  };

  return <AnalysisForm onSuccess={handleAnalysisSuccess} />;
};

export default DashboardNewPage;