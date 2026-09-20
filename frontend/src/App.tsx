/**
 * Main application component
 *
 * Flow: idea (+ optional profiles) -> interview with threads, reflections and
 * live coverage -> final plan (+ execution bundle).
 */
import { useState, useEffect, useCallback } from 'react';
import { IdeaInput } from './components/IdeaInput';
import type { SessionProfiles } from './components/IdeaInput';
import { InterviewSession } from './components/InterviewSession';
import { FinalPlan } from './components/FinalPlan';
import { CoverageDisplay } from './components/CoverageDisplay';
import { ThreadManager } from './components/v02/ThreadManager';
import { ReflectionInput } from './components/v02/ReflectionInput';
import { ExecutionBundleViewer } from './components/v02/ExecutionBundleViewer';
import { apiService } from './services/api';
import type {
  Answer,
  CoverageMap,
  CreateThreadRequest,
  ExecutionBundle,
  Question,
  ThreadState,
} from './types';
import { Mode, ViewProfile } from './types';
import './App.css';

type AppState = 'input' | 'interview' | 'complete';

// Session storage key
const SESSION_STORAGE_KEY = 'infiniteq_session';

// Session expiry time (24 hours)
const SESSION_EXPIRY_MS = 24 * 60 * 60 * 1000;

/**
 * The server keeps the session state, so only the id needs to be remembered
 * locally to offer "resume".
 */
interface StoredSession {
  sessionId: string;
  timestamp: number;
}

const emptyCoverage = (): CoverageMap => ({
  problem: 0,
  users: 0,
  constraints: 0,
  features: 0,
  architecture: 0,
  data_ml: 0,
  operations: 0,
  risks: 0,
  gtm: 0,
});

function App() {
  const [state, setState] = useState<AppState>('input');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ThreadState[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [globalCoverage, setGlobalCoverage] = useState<CoverageMap>(emptyCoverage);
  const [reflectionPrompt, setReflectionPrompt] = useState<Question | null>(null);
  const [viewProfile, setViewProfile] = useState<ViewProfile>(ViewProfile.BUILDER);
  const [includeExecutionBundle, setIncludeExecutionBundle] = useState(true);
  const [finalPlan, setFinalPlan] = useState<unknown>(null);
  const [markdownBrief, setMarkdownBrief] = useState<string>('');
  const [executionBundle, setExecutionBundle] = useState<ExecutionBundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRecoverableSession, setHasRecoverableSession] = useState(false);

  const activeThread = threads.find((thread) => thread.id === activeThreadId) ?? null;
  const questions = activeThread?.pending_questions ?? [];
  const threadCoverage = activeThread?.coverage ?? emptyCoverage();

  // Check for a resumable session on mount
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!stored) return;

    try {
      const session: StoredSession = JSON.parse(stored);
      if (Date.now() - session.timestamp < SESSION_EXPIRY_MS) {
        setHasRecoverableSession(true);
      } else {
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    } catch {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, []);

  // Remember the session id while an interview is in progress
  useEffect(() => {
    if (state === 'interview' && sessionId) {
      const session: StoredSession = { sessionId, timestamp: Date.now() };
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    }
  }, [state, sessionId]);

  const clearStoredSession = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setHasRecoverableSession(false);
  };

  const describeError = (err: any, fallback: string): string =>
    err?.message || err?.response?.data?.detail || fallback;

  /** Pull the threads (with their pending questions and notes) from the server. */
  const loadThreads = useCallback(async (id: string) => {
    const listing = await apiService.listThreads(id);
    setThreads(listing.threads);
    setActiveThreadId(listing.active_thread_id);
    return listing;
  }, []);

  const handleStartSession = async (
    idea: string,
    mode: Mode,
    profiles: SessionProfiles
  ) => {
    setLoading(true);
    setError(null);
    clearStoredSession();

    try {
      const response = await apiService.createSession({
        idea,
        mode,
        project_profile: profiles.project,
        persona_profile: profiles.persona,
      });

      setSessionId(response.session_id);
      setGlobalCoverage(response.coverage);
      setReflectionPrompt(null);
      await loadThreads(response.session_id);
      setState('interview');
    } catch (err: any) {
      console.error('Failed to create session:', err);
      setError(describeError(err, 'Failed to create session. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswers = async (answers: Answer[]) => {
    if (!sessionId || !activeThreadId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.submitThreadAnswers(sessionId, activeThreadId, {
        answers,
      });

      setGlobalCoverage(response.global_coverage);
      setReflectionPrompt(response.reflection_prompt ?? null);
      await loadThreads(sessionId);
    } catch (err: any) {
      console.error('Failed to submit answers:', err);
      setError(describeError(err, 'Failed to submit answers. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateThread = async (request: CreateThreadRequest) => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const created = await apiService.createThread(sessionId, request);
      // Switch to the new thread so the questions we just generated are shown.
      await apiService.activateThread(sessionId, created.thread.id);
      setReflectionPrompt(null);
      await loadThreads(sessionId);
    } catch (err: any) {
      console.error('Failed to create thread:', err);
      setError(describeError(err, 'Failed to create thread. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleActivateThread = async (threadId: string) => {
    if (!sessionId || threadId === activeThreadId) return;

    setLoading(true);
    setError(null);

    try {
      await apiService.activateThread(sessionId, threadId);
      setReflectionPrompt(null);
      await loadThreads(sessionId);
    } catch (err: any) {
      console.error('Failed to switch thread:', err);
      setError(describeError(err, 'Failed to switch thread. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitReflection = async (reflection: string) => {
    if (!sessionId || !activeThreadId) return;

    setLoading(true);
    setError(null);

    try {
      await apiService.submitReflection(sessionId, activeThreadId, { text: reflection });
      setReflectionPrompt(null);
      await loadThreads(sessionId);
    } catch (err: any) {
      console.error('Failed to submit reflection:', err);
      setError(describeError(err, 'Failed to submit reflection. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleFinish = async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.finishSession(sessionId, {
        viewProfile,
        includeExecutionBundle,
      });

      setFinalPlan(response.json_plan);
      setMarkdownBrief(response.markdown_brief);
      setExecutionBundle(response.execution_bundle ?? null);
      setState('complete');
      clearStoredSession();
    } catch (err: any) {
      console.error('Failed to finish session:', err);
      setError(describeError(err, 'Failed to generate plan. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleRecoverSession = async () => {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!stored) return;

    setLoading(true);
    setError(null);

    try {
      const session: StoredSession = JSON.parse(stored);
      const [listing, status] = await Promise.all([
        apiService.listThreads(session.sessionId),
        apiService.getSessionStatus(session.sessionId),
      ]);

      setSessionId(session.sessionId);
      setThreads(listing.threads);
      setActiveThreadId(listing.active_thread_id);
      setGlobalCoverage(status.coverage);
      setHasRecoverableSession(false);
      setState('interview');
    } catch (err: any) {
      console.error('Failed to recover session:', err);
      localStorage.removeItem(SESSION_STORAGE_KEY);
      setHasRecoverableSession(false);
      setError('That session is no longer available. Please start a new one.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartNew = () => {
    setSessionId(null);
    setThreads([]);
    setActiveThreadId(null);
    setGlobalCoverage(emptyCoverage());
    setReflectionPrompt(null);
    setFinalPlan(null);
    setMarkdownBrief('');
    setExecutionBundle(null);
    setError(null);
    setState('input');
    clearStoredSession();
  };

  return (
    <div className="app">
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">
            X
          </button>
        </div>
      )}

      {hasRecoverableSession && state === 'input' && (
        <div className="session-recovery-banner">
          <span>You have an unfinished planning session.</span>
          <button
            onClick={handleRecoverSession}
            className="recover-button"
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Resume Session'}
          </button>
          <button onClick={clearStoredSession} className="dismiss-button">
            Start Fresh
          </button>
        </div>
      )}

      {state === 'input' && <IdeaInput onSubmit={handleStartSession} loading={loading} />}

      {state === 'interview' && sessionId && (
        <div className="interview-layout">
          <aside className="interview-sidebar">
            <ThreadManager
              threads={threads}
              activeThreadId={activeThreadId}
              busy={loading}
              onCreateThread={handleCreateThread}
              onActivateThread={handleActivateThread}
            />

            <ReflectionInput
              reflectionPrompt={reflectionPrompt ?? undefined}
              onSubmitReflection={handleSubmitReflection}
              recentNotes={activeThread?.notes ?? []}
            />
          </aside>

          <main className="interview-main">
            <CoverageDisplay coverage={globalCoverage} title="Overall coverage" />
            <InterviewSession
              // Remount per thread so per-round answer state never leaks across
              // threads (each thread has its own question set).
              key={activeThreadId ?? 'no-thread'}
              sessionId={sessionId}
              questions={questions}
              coverage={threadCoverage}
              coverageTitle={
                activeThread ? `Thread coverage: ${activeThread.title}` : 'Thread coverage'
              }
              threadType={activeThread?.type}
              onSubmitAnswers={handleSubmitAnswers}
              onFinish={handleFinish}
              loading={loading}
              viewProfile={viewProfile}
              onViewProfileChange={setViewProfile}
              includeExecutionBundle={includeExecutionBundle}
              onIncludeExecutionBundleChange={setIncludeExecutionBundle}
            />
          </main>
        </div>
      )}

      {state === 'complete' && (
        <div className="final-layout">
          <FinalPlan
            jsonPlan={finalPlan}
            markdownBrief={markdownBrief}
            onStartNew={handleStartNew}
          />
          {executionBundle && <ExecutionBundleViewer bundle={executionBundle} />}
        </div>
      )}
    </div>
  );
}

export default App;
