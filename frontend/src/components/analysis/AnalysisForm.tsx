import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import styled from 'styled-components';
import { AnalystType, TradingAnalysisRequest } from '../../types';
import { AnalysisService } from '../../services/analysisService';
import toast from 'react-hot-toast';

const schema = yup.object().shape({
  ticker: yup
    .string()
    .required('티커는 필수입니다')
    .matches(/^[A-Z]{1,5}$/, '올바른 티커 형식이 아닙니다 (예: NVDA, AAPL)'),
  analysis_date: yup
    .string()
    .required('분석 날짜는 필수입니다'),
  analysts: yup
    .array()
    .of(yup.string().oneOf(Object.values(AnalystType)).required())
    .min(1, '최소 하나의 분석가를 선택해주세요')
    .required('분석가는 필수입니다'),
  research_depth: yup
    .number()
    .min(1, '연구 깊이는 최소 1이어야 합니다')
    .max(5, '연구 깊이는 최대 5까지 가능합니다')
    .required('연구 깊이는 필수입니다'),
  llm_provider: yup
    .string()
    .required('LLM 제공자는 필수입니다'),
  backend_url: yup
    .string()
    .required('백엔드 URL은 필수입니다'),
  shallow_thinker: yup
    .string()
    .required('Shallow Thinker 모델은 필수입니다'),
  deep_thinker: yup
    .string()
    .required('Deep Thinker 모델은 필수입니다'),
});

interface AnalysisFormProps {
  onSuccess?: (analysisId: string) => void;
}

interface LLMOption {
  value: string;
  label: string;
}

interface ProviderConfig {
  url: string;
  shallowModels: LLMOption[];
  deepModels: LLMOption[];
  defaultShallow: string;
  defaultDeep: string;
}

const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  openai: {
    url: 'https://api.openai.com/v1',
    shallowModels: [
      { value: 'gpt-4o-mini', label: 'GPT-4o-mini [빠르고 효율적인 경량 모델]' },
      { value: 'gpt-4.1-nano', label: 'GPT-4.1-nano [초경량 기본 작업용 모델]' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1-mini [성능이 좋은 컴팩트 모델]' },
      { value: 'gpt-4o', label: 'GPT-4o [탄탄한 성능의 표준 모델]' },
      { value: 'o4-mini', label: 'o4-mini [컴팩트한 특화 추론 모델]' },
      { value: 'o3', label: 'o3 [고급 추론 완전체 모델]' },
    ],
    deepModels: [
      { value: 'gpt-4.1-nano', label: 'GPT-4.1-nano [초경량 기본 작업용 모델]' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1-mini [성능이 좋은 컴팩트 모델]' },
      { value: 'gpt-4o', label: 'GPT-4o [탄탄한 성능의 표준 모델]' },
      { value: 'o4-mini', label: 'o4-mini [컴팩트한 특화 추론 모델]' },
      { value: 'o3-mini', label: 'o3-mini [경량 고급 추론 모델]' },
      { value: 'o3', label: 'o3 [고급 추론 완전체 모델]' },
      { value: 'o1', label: 'o1 [최고급 추론 및 문제 해결 모델]' },
    ],
    defaultShallow: 'gpt-4o-mini',
    defaultDeep: 'gpt-4o',
  },
  google: {
    url: 'https://generativelanguage.googleapis.com/v1',
    shallowModels: [
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash [차세대 기능과 속도, 사고력]' },
      { value: 'gemini-2.5-flash-lite-preview-06-17', label: 'Gemini 2.5 Flash-Lite [비용 효율성과 낮은 지연시간]' },
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash [적응형 사고력, 비용 효율성]' },
    ],
    deepModels: [
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash [차세대 기능과 속도, 사고력]' },
      { value: 'gemini-2.5-flash-lite-preview-06-17', label: 'Gemini 2.5 Flash-Lite [비용 효율성과 낮은 지연시간]' },
      { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash [적응형 사고력, 비용 효율성]' },
      { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro [가장 강력한 Gemini 모델]' },
    ],
    defaultShallow: 'gemini-2.5-flash-lite-preview-06-17',
    defaultDeep: 'gemini-2.5-flash',
  },
};

const RESEARCH_DEPTH_OPTIONS = [
  { value: 1, label: '얕은 분석 - 빠른 분석, 간단한 토론' },
  { value: 3, label: '중간 분석 - 적절한 깊이의 분석과 토론' },
  { value: 5, label: '깊은 분석 - 포괄적인 연구와 심층 토론' },
];

const AnalysisForm: React.FC<AnalysisFormProps> = ({ onSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<TradingAnalysisRequest>({
    resolver: yupResolver(schema),
    defaultValues: {
      ticker: 'NVDA',
      analysis_date: new Date().toISOString().split('T')[0],
      analysts: [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
      research_depth: 1,
      llm_provider: 'google',
      backend_url: 'https://generativelanguage.googleapis.com/v1',
      shallow_thinker: 'gemini-2.5-flash-lite-preview-06-17',
      deep_thinker: 'gemini-2.5-flash-lite-preview-06-17',
    },
  });

  const watchedAnalysts = watch('analysts');
  const watchedProvider = watch('llm_provider');
  
  useEffect(() => {
    if (watchedProvider && PROVIDER_CONFIGS[watchedProvider]) {
      const config = PROVIDER_CONFIGS[watchedProvider];
      setValue('backend_url', config.url);
      setValue('shallow_thinker', config.defaultShallow);
      setValue('deep_thinker', config.defaultDeep);
    }
  }, [watchedProvider, setValue]);

  const onSubmit = async (data: TradingAnalysisRequest) => {
    setIsLoading(true);
    try {
      const response = await AnalysisService.startAnalysis(data);
      toast.success('분석이 시작되었습니다!');
      onSuccess?.(response.id);
    } catch (error: any) {
      toast.error(error.response?.data?.error?.message || '분석 시작에 실패했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalystChange = (analyst: AnalystType, checked: boolean) => {
    const currentAnalysts = watchedAnalysts || [];
    if (checked) {
      setValue('analysts', [...currentAnalysts, analyst]);
    } else {
      setValue('analysts', currentAnalysts.filter((a: AnalystType) => a !== analyst));
    }
  };

  return (
    <Container>
      <Title>새로운 분석 시작</Title>
      <Form onSubmit={handleSubmit(onSubmit)}>
        <FormGroup>
          <Label htmlFor="ticker">티커</Label>
          <Input
            id="ticker"
            type="text"
            {...register('ticker')}
            hasError={!!errors.ticker}
            placeholder="예: NVDA, AAPL"
          />
          {errors.ticker && <ErrorMessage>{errors.ticker.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="analysis_date">분석 날짜</Label>
          <Input
            id="analysis_date"
            type="date"
            {...register('analysis_date')}
            hasError={!!errors.analysis_date}
          />
          {errors.analysis_date && <ErrorMessage>{errors.analysis_date.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label>분석가 선택</Label>
          <CheckboxGroup>
            {Object.values(AnalystType).map((analyst) => (
              <CheckboxItem key={analyst}>
                <Checkbox
                  type="checkbox"
                  id={analyst}
                  checked={watchedAnalysts?.includes(analyst) || false}
                  onChange={(e) => handleAnalystChange(analyst, e.target.checked)}
                />
                <CheckboxLabel htmlFor={analyst}>
                  {analyst === AnalystType.MARKET && '시장 분석가'}
                  {analyst === AnalystType.NEWS && '뉴스 분석가'}
                  {analyst === AnalystType.FUNDAMENTALS && '펀더멘털 분석가'}
                </CheckboxLabel>
              </CheckboxItem>
            ))}
          </CheckboxGroup>
          {errors.analysts && <ErrorMessage>{errors.analysts.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="research_depth">연구 깊이</Label>
          <Select
            id="research_depth"
            {...register('research_depth')}
            hasError={!!errors.research_depth}
          >
            {RESEARCH_DEPTH_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          {errors.research_depth && <ErrorMessage>{errors.research_depth.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="llm_provider">LLM 제공자</Label>
          <Select
            id="llm_provider"
            {...register('llm_provider')}
            hasError={!!errors.llm_provider}
          >
            <option value="google">Google</option>
            <option value="openai">OpenAI</option>
          </Select>
          {errors.llm_provider && <ErrorMessage>{errors.llm_provider.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="shallow_thinker">빠른 분석 LLM 엔진</Label>
          <Select
            id="shallow_thinker"
            {...register('shallow_thinker')}
            hasError={!!errors.shallow_thinker}
          >
            {watchedProvider && PROVIDER_CONFIGS[watchedProvider]?.shallowModels.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </Select>
          {errors.shallow_thinker && <ErrorMessage>{errors.shallow_thinker.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="deep_thinker">심층 분석 LLM 엔진</Label>
          <Select
            id="deep_thinker"
            {...register('deep_thinker')}
            hasError={!!errors.deep_thinker}
          >
            {watchedProvider && PROVIDER_CONFIGS[watchedProvider]?.deepModels.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </Select>
          {errors.deep_thinker && <ErrorMessage>{errors.deep_thinker.message}</ErrorMessage>}
        </FormGroup>

        <SubmitButton type="submit" disabled={isLoading}>
          {isLoading ? '분석 시작 중...' : '분석 시작'}
        </SubmitButton>
      </Form>
    </Container>
  );
};

const Container = styled.div`
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h2`
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
`;

const Input = styled.input<{ hasError?: boolean }>`
  padding: 0.75rem;
  border: 2px solid ${(props) => (props.hasError ? '#ff6b6b' : '#ddd')};
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;

  &:focus {
    outline: none;
    border-color: ${(props) => (props.hasError ? '#ff6b6b' : '#4CAF50')};
  }
`;

const Select = styled.select<{ hasError?: boolean }>`
  padding: 0.75rem;
  border: 2px solid ${(props) => (props.hasError ? '#ff6b6b' : '#ddd')};
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;

  &:focus {
    outline: none;
    border-color: ${(props) => (props.hasError ? '#ff6b6b' : '#4CAF50')};
  }
`;

const CheckboxGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
`;

const CheckboxItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const Checkbox = styled.input`
  width: 18px;
  height: 18px;
`;

const CheckboxLabel = styled.label`
  font-size: 0.9rem;
  color: #666;
  cursor: pointer;
`;

const ErrorMessage = styled.span`
  color: #ff6b6b;
  font-size: 0.875rem;
  margin-top: 0.25rem;
`;

const SubmitButton = styled.button`
  padding: 0.75rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover:not(:disabled) {
    background-color: #45a049;
  }

  &:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
`;

export default AnalysisForm;