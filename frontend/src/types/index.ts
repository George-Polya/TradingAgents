export enum Role {
  USER = "USER",
  ADMIN = "ADMIN"
}

export enum AnalysisStatus {
  PENDING = "PENDING",
  RUNNING = "RUNNING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED"
}

export enum AnalystType {
  NEWS = "news",
  FUNDAMENTALS = "fundamentals"
}

export interface Member {
  id: string;
  name: string | null;
  email: string;
  created_at: string;
  updated_at: string;
  role: Role;
}

export interface CreateUserBody {
  name: string;
  email: string;
  password: string;
  role?: Role;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  member: Member;
}

export interface TradingAnalysisRequest {
  ticker: string;
  analysis_date: string;
  analysts: AnalystType[];
  research_depth: number;
  llm_provider: string;
  backend_url: string;
  shallow_thinker: string;
  deep_thinker: string;
}

export interface AnalysisSessionResponse {
  id: string;
  ticker: string;
  status: AnalysisStatus;
  shallow_thinker: string;
  deep_thinker: string;
  created_at?: string;
}

export interface AnalysisResultResponse {
  id: string;
  ticker: string;
  analysis_date: string;
  status: AnalysisStatus;
  news_report: string | null;
  fundamentals_report: string | null;
  investment_debate_state: any | null;
  trader_investment_plan: string | null;
  risk_debate_state: any | null;
  final_trade_decision: string | null;
  final_report: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface AnalysisProgressUpdate {
  analysis_id: string;
  current_agent: string;
  status: string;
  progress_percentage: number;
  current_report_section: string | null;
  message: string | null;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    path: string;
  };
}