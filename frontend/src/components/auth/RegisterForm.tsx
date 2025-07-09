import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import styled from 'styled-components';
import { AuthService } from '../../services/authService';
import { CreateUserBody, Role } from '../../types';
import toast from 'react-hot-toast';

const schema = yup.object().shape({
  name: yup
    .string()
    .min(1, '이름은 최소 1자 이상이어야 합니다')
    .max(32, '이름은 최대 32자까지 가능합니다')
    .required('이름은 필수입니다'),
  email: yup
    .string()
    .email('올바른 이메일 형식이 아닙니다')
    .max(32, '이메일은 최대 32자까지 가능합니다')
    .required('이메일은 필수입니다'),
  password: yup
    .string()
    .min(6, '비밀번호는 최소 6자 이상이어야 합니다')
    .max(32, '비밀번호는 최대 32자까지 가능합니다')
    .required('비밀번호는 필수입니다'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], '비밀번호가 일치하지 않습니다')
    .required('비밀번호 확인은 필수입니다'),
});

interface RegisterFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

interface RegisterFormProps {
  onSuccess?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: yupResolver(schema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    try {
      const userData: CreateUserBody = {
        name: data.name,
        email: data.email,
        password: data.password,
        role: Role.USER,
      };
      
      await AuthService.register(userData);
      toast.success('회원가입 성공! 로그인해주세요.');
      onSuccess?.();
    } catch (error: any) {
      toast.error(error.response?.data?.error?.message || '회원가입에 실패했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container>
      <Title>회원가입</Title>
      <Form onSubmit={handleSubmit(onSubmit)}>
        <FormGroup>
          <Label htmlFor="name">이름</Label>
          <Input
            id="name"
            type="text"
            {...register('name')}
            hasError={!!errors.name}
          />
          {errors.name && <ErrorMessage>{errors.name.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="email">이메일</Label>
          <Input
            id="email"
            type="email"
            {...register('email')}
            hasError={!!errors.email}
          />
          {errors.email && <ErrorMessage>{errors.email.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="password">비밀번호</Label>
          <Input
            id="password"
            type="password"
            {...register('password')}
            hasError={!!errors.password}
          />
          {errors.password && <ErrorMessage>{errors.password.message}</ErrorMessage>}
        </FormGroup>

        <FormGroup>
          <Label htmlFor="confirmPassword">비밀번호 확인</Label>
          <Input
            id="confirmPassword"
            type="password"
            {...register('confirmPassword')}
            hasError={!!errors.confirmPassword}
          />
          {errors.confirmPassword && (
            <ErrorMessage>{errors.confirmPassword.message}</ErrorMessage>
          )}
        </FormGroup>

        <SubmitButton type="submit" disabled={isLoading}>
          {isLoading ? '회원가입 중...' : '회원가입'}
        </SubmitButton>
      </Form>
    </Container>
  );
};

const Container = styled.div`
  max-width: 400px;
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

export default RegisterForm;