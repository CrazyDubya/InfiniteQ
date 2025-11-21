/**
 * API client for backend communication
 */
import axios from 'axios';
import type {
  CreateSessionRequest,
  CreateSessionResponse,
  AnswerRequest,
  AnswerResponse,
  FinishResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * Create a new planning session
   */
  createSession: async (request: CreateSessionRequest): Promise<CreateSessionResponse> => {
    const response = await api.post<CreateSessionResponse>('/session', request);
    return response.data;
  },

  /**
   * Submit answers and get next questions
   */
  submitAnswers: async (sessionId: string, request: AnswerRequest): Promise<AnswerResponse> => {
    const response = await api.post<AnswerResponse>(`/session/${sessionId}/answer`, request);
    return response.data;
  },

  /**
   * Finish session and get final plan
   */
  finishSession: async (sessionId: string): Promise<FinishResponse> => {
    const response = await api.post<FinishResponse>(`/session/${sessionId}/finish`);
    return response.data;
  },

  /**
   * Get session status
   */
  getSessionStatus: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/session/${sessionId}/status`);
    return response.data;
  },
};
