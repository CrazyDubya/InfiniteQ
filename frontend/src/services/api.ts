/**
 * API client for backend communication
 */
import axios, { AxiosError } from 'axios';
import type {
  CreateSessionRequest,
  CreateSessionResponse,
  AnswerRequest,
  AnswerResponse,
  FinishResponse,
  FinishRequestV2,
} from '../types';
// An enum, so it must be a value import - it is used as ViewProfile.BUILDER.
import { ViewProfile } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Timeout configuration (in milliseconds)
const DEFAULT_TIMEOUT = 30000; // 30 seconds for normal requests
const LLM_TIMEOUT = 120000; // 2 minutes for LLM operations (question generation, plan synthesis)

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding request ID
api.interceptors.request.use(
  (config) => {
    // Add unique request ID for tracking
    config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.code === 'ECONNABORTED') {
      // Timeout error
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }
    if (error.response?.status === 429) {
      // Rate limited
      return Promise.reject(new Error('Too many requests. Please wait a moment and try again.'));
    }
    if (error.response?.status === 503) {
      // Service unavailable
      return Promise.reject(new Error('Service is temporarily unavailable. Please try again later.'));
    }
    if (!error.response) {
      // Network error
      return Promise.reject(new Error('Network error. Please check your connection.'));
    }
    return Promise.reject(error);
  }
);

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiService = {
  /**
   * Create a new planning session
   */
  createSession: async (request: CreateSessionRequest): Promise<CreateSessionResponse> => {
    const response = await api.post<CreateSessionResponse>('/session', request, {
      timeout: LLM_TIMEOUT, // LLM operations may take longer
    });
    return response.data;
  },

  /**
   * Submit answers and get next questions
   */
  submitAnswers: async (sessionId: string, request: AnswerRequest): Promise<AnswerResponse> => {
    const response = await api.post<AnswerResponse>(`/session/${sessionId}/answer`, request, {
      timeout: LLM_TIMEOUT, // LLM operations may take longer
    });
    return response.data;
  },

  /**
   * Finish session and get final plan
   */
  finishSession: async (
    sessionId: string,
    options: { viewProfile?: ViewProfile; includeExecutionBundle?: boolean } = {}
  ): Promise<FinishResponse> => {
    const request: FinishRequestV2 = {
      view_profile: options.viewProfile || ViewProfile.BUILDER,
      include_execution_bundle: options.includeExecutionBundle ?? true,
    };
    const response = await api.post<FinishResponse>(`/session/${sessionId}/finish`, request, {
      timeout: LLM_TIMEOUT * 2, // Plan synthesis may take longer
    });
    return response.data;
  },

  /**
   * Get session status
   */
  getSessionStatus: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/session/${sessionId}/status`);
    return response.data;
  },

  /**
   * Health check
   */
  healthCheck: async (): Promise<{ status: string; models_available: number }> => {
    const response = await api.get('/health', {
      baseURL: API_BASE_URL.replace('/api/v1', ''),
      timeout: 5000, // Quick timeout for health check
    });
    return response.data;
  },
};
