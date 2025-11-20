/**
 * Main application component
 */
import React, { useState } from 'react';
import { IdeaInput } from './components/IdeaInput';
import { InterviewSession } from './components/InterviewSession';
import { FinalPlan } from './components/FinalPlan';
import { apiService } from './services/api';
import type { Question, Answer, CoverageMap } from './types';
import './App.css';

type AppState = 'input' | 'interview' | 'complete';

function App() {
  const [state, setState] = useState<AppState>('input');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [coverage, setCoverage] = useState<CoverageMap>({
    problem: 0,
    users: 0,
    constraints: 0,
    features: 0,
    architecture: 0,
    operations: 0,
    risks: 0,
    deliverables: 0,
  });
  const [finalPlan, setFinalPlan] = useState<any>(null);
  const [markdownBrief, setMarkdownBrief] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartSession = async (idea: string, mode: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.createSession({
        idea,
        mode: mode as any,
      });

      setSessionId(response.session_id);
      setQuestions(response.first_questions);
      setCoverage(response.coverage);
      setState('interview');
    } catch (err: any) {
      console.error('Failed to create session:', err);
      setError(err.response?.data?.detail || 'Failed to create session. Please try again.');
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
      setError(err.response?.data?.detail || 'Failed to submit answers. Please try again.');
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
    } catch (err: any) {
      console.error('Failed to finish session:', err);
      setError(err.response?.data?.detail || 'Failed to generate plan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartNew = () => {
    setSessionId(null);
    setQuestions([]);
    setCoverage({
      problem: 0,
      users: 0,
      constraints: 0,
      features: 0,
      architecture: 0,
      operations: 0,
      risks: 0,
      deliverables: 0,
    });
    setFinalPlan(null);
    setMarkdownBrief('');
    setError(null);
    setState('input');
  };

  return (
    <div className="app">
      {error && (
        <div className="error-banner">
          <span>⚠ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
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
