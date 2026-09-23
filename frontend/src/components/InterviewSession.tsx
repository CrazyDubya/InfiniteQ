/**
 * Interview session component managing the Q&A flow
 */
import React, { useState } from 'react';
import { QuestionCard } from './QuestionCard';
import { CoverageDisplay } from './CoverageDisplay';
import type { Answer, CoverageMap, Question, ThreadType } from '../types';
import { ViewProfile } from '../types';

interface InterviewSessionProps {
  sessionId: string;
  questions: Question[];
  coverage: CoverageMap;
  coverageTitle?: string;
  threadType?: ThreadType;
  onSubmitAnswers: (answers: Answer[]) => void;
  onFinish: () => void;
  loading: boolean;
  viewProfile: ViewProfile;
  onViewProfileChange: (view: ViewProfile) => void;
  includeExecutionBundle: boolean;
  onIncludeExecutionBundleChange: (include: boolean) => void;
}

const VIEW_PROFILE_LABELS: Record<ViewProfile, string> = {
  [ViewProfile.BUILDER]: 'Builder - full technical detail',
  [ViewProfile.STAKEHOLDER]: 'Stakeholder - business focus',
  [ViewProfile.INVESTOR]: 'Investor - pitch friendly',
  [ViewProfile.AGENT_SPEC]: 'AI agent spec - most detailed',
};

const THREAD_TYPE_LABELS: Record<ThreadType, string> = {
  kickoff: '🚀 Kickoff',
  architecture: '🏗️ Architecture',
  product_ux: '🎨 Product & UX',
  data_ml: '📊 Data & ML',
  ops_infra: '⚙️ Ops & Infra',
  risk: '⚠️ Risk',
  gtm: '📈 Go-to-Market',
  sanity_check: '✅ Sanity Check',
  custom: '✨ Custom',
};

export const InterviewSession: React.FC<InterviewSessionProps> = ({
  sessionId,
  questions,
  coverage,
  coverageTitle,
  threadType,
  onSubmitAnswers,
  onFinish,
  loading,
  viewProfile,
  onViewProfileChange,
  includeExecutionBundle,
  onIncludeExecutionBundleChange,
}) => {
  const [answers, setAnswers] = useState<Answer[]>([]);

  const handleAnswer = (answer: Answer) => {
    setAnswers((prev) => [...prev, answer]);
  };

  const handleContinue = () => {
    if (answers.length === 0) return;
    onSubmitAnswers(answers);
    // Start the next round clean; the parent renders a fresh question set.
    setAnswers([]);
  };

  const allQuestionsAnswered =
    questions.length > 0 && answers.length === questions.length;

  return (
    <div className="interview-session">
      <div className="session-header">
        <h2>{threadType ? THREAD_TYPE_LABELS[threadType] : 'Planning Interview'}</h2>
        <p className="session-id">Session: {sessionId.slice(0, 8)}...</p>
      </div>

      <CoverageDisplay coverage={coverage} title={coverageTitle ?? 'Thread coverage'} />

      <div className="questions-container">
        {questions.length === 0 && (
          <p className="help-text">
            No questions waiting on this thread. Open another thread or generate your
            plan.
          </p>
        )}

        {questions.map((question) => (
          <QuestionCard
            key={question.id}
            question={question}
            onAnswer={handleAnswer}
            disabled={loading}
          />
        ))}
      </div>

      <div className="session-actions">
        {allQuestionsAnswered && (
          <button className="continue-button" onClick={handleContinue} disabled={loading}>
            {loading ? 'Processing...' : 'Continue Interview'}
          </button>
        )}

        <div className="finish-options">
          <label className="finish-option">
            <span>Plan for</span>
            <select
              value={viewProfile}
              onChange={(e) => onViewProfileChange(e.target.value as ViewProfile)}
              disabled={loading}
            >
              {Object.entries(VIEW_PROFILE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="finish-option checkbox">
            <input
              type="checkbox"
              checked={includeExecutionBundle}
              onChange={(e) => onIncludeExecutionBundleChange(e.target.checked)}
              disabled={loading}
            />
            <span>Include an execution bundle</span>
          </label>
        </div>

        <button className="finish-button" onClick={onFinish} disabled={loading}>
          {loading ? 'Working...' : 'Finish & Generate Plan'}
        </button>

        {!allQuestionsAnswered && questions.length > 0 && (
          <p className="help-text">
            Answer all questions to continue, or finish early to generate your plan now.
          </p>
        )}
      </div>
    </div>
  );
};
