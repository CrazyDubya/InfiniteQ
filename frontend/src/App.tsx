/**
 * Main application component
 */
import { useState, useEffect, useCallback } from 'react';
import { IdeaInput } from './components/IdeaInput';
import { InterviewSession } from './components/InterviewSession';
import { FinalPlan } from './components/FinalPlan';
import { apiService } from './services/api';
import type { Question, Answer, CoverageMap } from './types';
import './App.css';

type AppState = 'input' | 'interview' | 'complete';

// Session storage key
const SESSION_STORAGE_KEY = 'infiniteq_session';

// Default coverage state matching backend schema
const DEFAULT_COVERAGE: CoverageMap = {
  problem: 0,
  users: 0,
  constraints: 0,
  features: 0,
  architecture: 0,
  data_ml: 0,
  operations: 0,
  risks: 0,
  gtm: 0,
};

// Session state interface for localStorage
interface StoredSession {
  sessionId: string;
  threadId: string;
  questions: Question[];
  coverage: CoverageMap;
  timestamp: number;
}

// Session expiry time (24 hours)
const SESSION_EXPIRY_MS = 24 * 60 * 60 * 1000;

function App() {
  const [state, setState] = useState<AppState>('input');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [coverage, setCoverage] = useState<CoverageMap>(DEFAULT_COVERAGE);
  const [finalPlan, setFinalPlan] = useState<any>(null);
  const [markdownBrief, setMarkdownBrief] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRecoverableSession, setHasRecoverableSession] = useState(false);

  // Check for recoverable session on mount
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      try {
        const session: StoredSession = JSON.parse(stored);
        // Check if session is not expired
        if (Date.now() - session.timestamp < SESSION_EXPIRY_MS) {
          setHasRecoverableSession(true);
        } else {
          // Clear expired session
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
      } catch (e) {
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    }
  }, []);

  // Save session to localStorage whenever it changes
  const saveSession = useCallback(() => {
    if (sessionId && threadId && state === 'interview') {
      const session: StoredSession = {
        sessionId,
        threadId,
        questions,
        coverage,
        timestamp: Date.now(),
      };
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    }
  }, [sessionId, threadId, questions, coverage, state]);

  useEffect(() => {
    saveSession();
  }, [saveSession]);

  // Recover session from localStorage
  const handleRecoverSession = () => {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      try {
        const session: StoredSession = JSON.parse(stored);
        setSessionId(session.sessionId);
        setThreadId(session.threadId);
        setQuestions(session.questions);
        setCoverage(session.coverage);
        setState('interview');
        setHasRecoverableSession(false);
      } catch (e) {
        console.error('Failed to recover session:', e);
        localStorage.removeItem(SESSION_STORAGE_KEY);
        setHasRecoverableSession(false);
      }
    }
  };

  // Clear stored session
  const clearStoredSession = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setHasRecoverableSession(false);
  };

  const handleStartSession = async (idea: string, mode: string) => {
    setLoading(true);
    setError(null);
    // Clear any previous session
    clearStoredSession();

    try {
      const response = await apiService.createSession({
        idea,
        mode: mode as any,
      });

      setSessionId(response.session_id);
      setThreadId(response.thread_id);
      setQuestions(response.first_questions);
      setCoverage(response.coverage);
      setState('interview');
    } catch (err: any) {
      console.error('Failed to create session:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to create session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswers = async (answers: Answer[]) => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.submitAnswers(sessionId, { answers });

      setQuestions(response.next_questions);
      setCoverage(response.coverage);
    } catch (err: any) {
      console.error('Failed to submit answers:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to submit answers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFinish = async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.finishSession(sessionId);

      setFinalPlan(response.json_plan);
      setMarkdownBrief(response.markdown_brief);
      setState('complete');
      // Clear stored session on completion
      clearStoredSession();
    } catch (err: any) {
      console.error('Failed to finish session:', err);
      setError(err.message || err.response?.data?.detail || 'Failed to generate plan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartNew = () => {
    setSessionId(null);
    setThreadId(null);
    setQuestions([]);
    setCoverage(DEFAULT_COVERAGE);
    setFinalPlan(null);
    setMarkdownBrief('');
    setError(null);
    setState('input');
    clearStoredSession();
  };

  return (
    <div className="app">
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">X</button>
        </div>
      )}

      {hasRecoverableSession && state === 'input' && (
        <div className="session-recovery-banner">
          <span>You have an unfinished planning session.</span>
          <button onClick={handleRecoverSession} className="recover-button">
            Resume Session
          </button>
          <button onClick={clearStoredSession} className="dismiss-button">
            Start Fresh
          </button>
        </div>
      )}

      {state === 'input' && (
        <IdeaInput onSubmit={handleStartSession} loading={loading} />
      )}

      {state === 'interview' && sessionId && (
        <InterviewSession
          sessionId={sessionId}
          questions={questions}
          coverage={coverage}
          onSubmitAnswers={handleSubmitAnswers}
          onFinish={handleFinish}
          loading={loading}
        />
      )}

      {state === 'complete' && (
        <FinalPlan
          jsonPlan={finalPlan}
          markdownBrief={markdownBrief}
          onStartNew={handleStartNew}
        />
      )}
    </div>
  );
}

export default App;
