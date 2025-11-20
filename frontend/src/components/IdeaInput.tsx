/**
 * Initial idea input component
 */
import React, { useState } from 'react';

interface IdeaInputProps {
  onSubmit: (idea: string, mode: string) => void;
  loading: boolean;
}

export const IdeaInput: React.FC<IdeaInputProps> = ({ onSubmit, loading }) => {
  const [idea, setIdea] = useState('');
  const [mode, setMode] = useState('software');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (idea.trim()) {
      onSubmit(idea, mode);
    }
  };

  return (
    <div className="idea-input-container">
      <div className="header">
        <h1>InfiniteQ Planning Harness</h1>
        <p className="subtitle">
          Turn your idea into a detailed, actionable plan using AI
        </p>
      </div>

      <form onSubmit={handleSubmit} className="idea-form">
        <div className="form-group">
          <label htmlFor="idea">What do you want to build or solve?</label>
          <textarea
            id="idea"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g., I want a web app that helps landlords manage receiverships in NYC..."
            rows={6}
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="mode">Project Type</label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            disabled={loading}
          >
            <option value="software">Software Application</option>
            <option value="story">Story/Narrative</option>
            <option value="process">Process/Workflow</option>
            <option value="other">Other</option>
          </select>
        </div>

        <button type="submit" disabled={loading || !idea.trim()}>
          {loading ? 'Starting...' : 'Start Planning Session'}
        </button>
      </form>
    </div>
  );
};
