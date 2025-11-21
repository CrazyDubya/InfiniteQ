/**
 * Final plan display component
 */
import React, { useState } from 'react';

interface FinalPlanProps {
  jsonPlan: any;
  markdownBrief: string;
  onStartNew: () => void;
}

export const FinalPlan: React.FC<FinalPlanProps> = ({
  jsonPlan,
  markdownBrief,
  onStartNew,
}) => {
  const [view, setView] = useState<'markdown' | 'json'>('markdown');
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const content = view === 'markdown' ? markdownBrief : JSON.stringify(jsonPlan, null, 2);
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownload = () => {
    const content = view === 'markdown' ? markdownBrief : JSON.stringify(jsonPlan, null, 2);
    const filename = view === 'markdown' ? 'project-plan.md' : 'project-plan.json';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="final-plan">
      <div className="final-plan-header">
        <h2>Your Project Plan is Ready!</h2>
        <p className="subtitle">
          Copy this plan and paste it into Cursor, ClaudeCode, or any AI coding assistant.
        </p>
      </div>

      <div className="view-controls">
        <button
          className={`view-button ${view === 'markdown' ? 'active' : ''}`}
          onClick={() => setView('markdown')}
        >
          Markdown Brief
        </button>
        <button
          className={`view-button ${view === 'json' ? 'active' : ''}`}
          onClick={() => setView('json')}
        >
          JSON Plan
        </button>
      </div>

      <div className="plan-content">
        <pre className="plan-text">
          {view === 'markdown' ? markdownBrief : JSON.stringify(jsonPlan, null, 2)}
        </pre>
      </div>

      <div className="plan-actions">
        <button className="copy-button" onClick={handleCopy}>
          {copied ? '✓ Copied!' : 'Copy to Clipboard'}
        </button>
        <button className="download-button" onClick={handleDownload}>
          Download {view === 'markdown' ? 'Markdown' : 'JSON'}
        </button>
        <button className="new-session-button" onClick={onStartNew}>
          Start New Planning Session
        </button>
      </div>
    </div>
  );
};
