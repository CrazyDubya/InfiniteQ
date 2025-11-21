/**
 * Question card component for displaying multiple-choice questions
 */
import React, { useState } from 'react';
import type { Question, Answer } from '../types';

interface QuestionCardProps {
  question: Question;
  onAnswer: (answer: Answer) => void;
  disabled: boolean;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  onAnswer,
  disabled,
}) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [otherText, setOtherText] = useState('');
  const [isAnswered, setIsAnswered] = useState(false);

  const handleOptionSelect = (optionId: string) => {
    if (disabled || isAnswered) return;
    setSelectedOption(optionId);
  };

  const handleSubmit = () => {
    if (!selectedOption || disabled || isAnswered) return;

    const answer: Answer = {
      question_id: question.id,
      choice_id: selectedOption,
    };

    // Add free text if "OTHER" option selected
    if (selectedOption === 'OTHER' && otherText.trim()) {
      answer.free_text = otherText.trim();
    }

    setIsAnswered(true);
    onAnswer(answer);
  };

  const isOtherSelected = selectedOption === 'OTHER';
  const canSubmit = selectedOption && (!isOtherSelected || otherText.trim());

  return (
    <div className={`question-card ${isAnswered ? 'answered' : ''}`}>
      <div className="question-header">
        <span className="coverage-badge">{question.coverage_key}</span>
        <span className="priority-badge">Priority: {(question.priority * 100).toFixed(0)}%</span>
      </div>

      <h3 className="question-text">{question.text}</h3>

      <div className="options-container">
        {question.options.map((option) => (
          <div key={option.id} className="option-wrapper">
            <button
              className={`option-button ${selectedOption === option.id ? 'selected' : ''}`}
              onClick={() => handleOptionSelect(option.id)}
              disabled={disabled || isAnswered}
            >
              <span className="option-id">{option.id}</span>
              <span className="option-text">{option.text}</span>
            </button>

            {option.id === 'OTHER' && isOtherSelected && !isAnswered && (
              <textarea
                className="other-text-input"
                value={otherText}
                onChange={(e) => setOtherText(e.target.value)}
                placeholder="Please specify..."
                rows={2}
                disabled={disabled}
              />
            )}
          </div>
        ))}
      </div>

      {!isAnswered && (
        <button
          className="submit-answer-button"
          onClick={handleSubmit}
          disabled={!canSubmit || disabled}
        >
          Submit Answer
        </button>
      )}

      {isAnswered && (
        <div className="answered-indicator">
          ✓ Answered
        </div>
      )}
    </div>
  );
};
