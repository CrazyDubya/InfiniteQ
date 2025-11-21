/**
 * Interview session component managing the Q&A flow
 */
import React, { useState } from 'react';
import { QuestionCard } from './QuestionCard';
import { CoverageDisplay } from './CoverageDisplay';
import type { Question, Answer, CoverageMap } from '../types';

interface InterviewSessionProps {
  sessionId: string;
  questions: Question[];
  coverage: CoverageMap;
  onSubmitAnswers: (answers: Answer[]) => void;
  onFinish: () => void;
  loading: boolean;
}

export const InterviewSession: React.FC<InterviewSessionProps> = ({
  sessionId,
  questions,
  coverage,
  onSubmitAnswers,
  onFinish,
  loading,
}) => {
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [roundComplete, setRoundComplete] = useState(false);

  const handleAnswer = (answer: Answer) => {
    setAnswers((prev) => [...prev, answer]);
  };

  const handleContinue = () => {
    if (answers.length === 0) return;

    onSubmitAnswers(answers);
    setAnswers([]);
    setRoundComplete(false);
  };

  const allQuestionsAnswered = answers.length === questions.length;

  return (
    <div className="interview-session">
      <div className="session-header">
        <h2>Planning Interview</h2>
        <p className="session-id">Session: {sessionId.slice(0, 8)}...</p>
      </div>

      <CoverageDisplay coverage={coverage} />

      <div className="questions-container">
        {questions.map((question) => (
          <QuestionCard
            key={question.id}
            question={question}
            onAnswer={handleAnswer}
            disabled={loading || roundComplete}
          />
        ))}
      </div>

      <div className="session-actions">
        {allQuestionsAnswered && !roundComplete && (
          <button
            className="continue-button"
            onClick={handleContinue}
            disabled={loading}
          >
            {loading ? 'Processing...' : 'Continue Interview'}
          </button>
        )}

        <button
          className="finish-button"
          onClick={onFinish}
          disabled={loading}
        >
          Finish & Generate Plan
        </button>

        {!allQuestionsAnswered && (
          <p className="help-text">
            Answer all questions to continue, or finish early to generate your plan now.
          </p>
        )}
      </div>
    </div>
  );
};
