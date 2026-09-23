/**
 * Thread Manager - v0.2 Component
 *
 * Manages multiple planning threads for parallel exploration.
 */
import React, { useState } from "react";
import {
  CreateThreadRequest,
  ThreadState,
  ThreadType,
} from "../../types";

interface ThreadManagerProps {
  threads: ThreadState[];
  activeThreadId: string | null;
  busy?: boolean;
  onCreateThread: (request: CreateThreadRequest) => void;
  onActivateThread: (threadId: string) => void;
}

const THREAD_TYPE_LABELS: Record<ThreadType, string> = {
  [ThreadType.KICKOFF]: "🚀 Kickoff",
  [ThreadType.ARCHITECTURE]: "🏗️ Architecture",
  [ThreadType.PRODUCT_UX]: "🎨 Product & UX",
  [ThreadType.DATA_ML]: "📊 Data & ML",
  [ThreadType.OPS_INFRA]: "⚙️ Ops & Infra",
  [ThreadType.RISK]: "⚠️ Risk",
  [ThreadType.GTM]: "📈 Go-to-Market",
  [ThreadType.SANITY_CHECK]: "✅ Sanity Check",
  [ThreadType.CUSTOM]: "✨ Custom",
};

const THREAD_TYPE_DESCRIPTIONS: Record<ThreadType, string> = {
  [ThreadType.KICKOFF]: "Initial brainstorming and direction",
  [ThreadType.ARCHITECTURE]: "Technical architecture and infrastructure",
  [ThreadType.PRODUCT_UX]: "User experience and product design",
  [ThreadType.DATA_ML]: "Data pipelines and ML models",
  [ThreadType.OPS_INFRA]: "Operations, deployment, and scaling",
  [ThreadType.RISK]: "Risk assessment and mitigation",
  [ThreadType.GTM]: "Go-to-market strategy and growth",
  [ThreadType.SANITY_CHECK]: "Quick validation of assumptions",
  [ThreadType.CUSTOM]: "Custom exploration thread",
};

const coverageAverage = (thread: ThreadState): number => {
  const values = Object.values(thread.coverage ?? {});
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
};

export const ThreadManager: React.FC<ThreadManagerProps> = ({
  threads,
  activeThreadId,
  busy = false,
  onCreateThread,
  onActivateThread,
}) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newThread, setNewThread] = useState<CreateThreadRequest>({
    type: ThreadType.ARCHITECTURE,
    title: "",
    root_prompt: "",
  });

  const canCreate = newThread.title.trim().length > 0 && !busy;

  const handleCreateThread = () => {
    if (!canCreate) return;
    onCreateThread(newThread);
    setShowCreateForm(false);
    setNewThread({ type: ThreadType.ARCHITECTURE, title: "", root_prompt: "" });
  };

  return (
    <div className="thread-manager">
      <div className="thread-header">
        <h3>Planning Threads</h3>
        <button
          className="btn-create"
          onClick={() => setShowCreateForm(!showCreateForm)}
          disabled={busy}
        >
          {showCreateForm ? "Cancel" : "+ New Thread"}
        </button>
      </div>

      {showCreateForm && (
        <div className="create-thread-form">
          <h4>Create New Thread</h4>

          <div className="form-field">
            <label>Thread Type</label>
            <select
              value={newThread.type}
              onChange={(e) =>
                setNewThread({ ...newThread, type: e.target.value as ThreadType })
              }
            >
              {Object.entries(THREAD_TYPE_LABELS).map(([type, label]) => (
                <option key={type} value={type}>
                  {label}
                </option>
              ))}
            </select>
            <span className="help-text">{THREAD_TYPE_DESCRIPTIONS[newThread.type]}</span>
          </div>

          <div className="form-field">
            <label>Thread Title</label>
            <input
              type="text"
              placeholder="e.g., Backend scalability planning"
              value={newThread.title}
              onChange={(e) => setNewThread({ ...newThread, title: e.target.value })}
            />
          </div>

          <div className="form-field">
            <label>Starting Prompt (optional)</label>
            <textarea
              placeholder="e.g., Let's focus on handling 10k concurrent users..."
              value={newThread.root_prompt || ""}
              onChange={(e) =>
                setNewThread({ ...newThread, root_prompt: e.target.value })
              }
              rows={3}
            />
          </div>

          <button className="btn-primary" onClick={handleCreateThread} disabled={!canCreate}>
            Create Thread
          </button>
        </div>
      )}

      <div className="thread-list">
        {threads.map((thread) => (
          <div
            key={thread.id}
            className={`thread-card ${thread.id === activeThreadId ? "active" : ""} ${
              thread.active ? "" : "parked"
            }`}
            onClick={() => onActivateThread(thread.id)}
          >
            <div className="thread-icon">{THREAD_TYPE_LABELS[thread.type]}</div>
            <div className="thread-content">
              <h4>{thread.title}</h4>
              <div className="thread-meta">
                <span>{thread.questions_asked} questions</span>
                <span>{coverageAverage(thread).toFixed(0)}% covered</span>
                {thread.notes.length > 0 && (
                  <span>💭 {thread.notes.length} reflections</span>
                )}
              </div>
            </div>
            {thread.id === activeThreadId && <div className="active-badge">Active</div>}
          </div>
        ))}
      </div>

      <style>{`
        .thread-manager {
          background: #ffffff;
          border-radius: 8px;
          padding: 1.5rem;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .thread-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .thread-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .btn-create {
          background: #007bff;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        .btn-create:hover:not(:disabled) {
          background: #0056b3;
        }

        .btn-create:disabled,
        .btn-primary:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .create-thread-form {
          background: #f8f9fa;
          border-radius: 6px;
          padding: 1.5rem;
          margin-bottom: 1.5rem;
        }

        .create-thread-form h4 {
          margin: 0 0 1rem 0;
          color: #495057;
        }

        .form-field {
          margin-bottom: 1rem;
        }

        .form-field label {
          display: block;
          font-weight: 600;
          margin-bottom: 0.5rem;
          color: #495057;
        }

        .form-field input,
        .form-field select,
        .form-field textarea {
          width: 100%;
          padding: 0.5rem;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-size: 1rem;
        }

        .form-field textarea {
          font-family: inherit;
          resize: vertical;
        }

        .help-text {
          display: block;
          font-size: 0.85rem;
          color: #6c757d;
          margin-top: 0.25rem;
        }

        .btn-primary {
          background: #28a745;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
        }

        .btn-primary:hover:not(:disabled) {
          background: #218838;
        }

        .thread-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .thread-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          border: 2px solid #e9ecef;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .thread-card:hover {
          border-color: #007bff;
          background: #f8f9fa;
        }

        .thread-card.active {
          border-color: #007bff;
          background: #e7f3ff;
        }

        .thread-card.parked {
          opacity: 0.7;
        }

        .thread-icon {
          font-size: 1.5rem;
        }

        .thread-content {
          flex: 1;
        }

        .thread-content h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .thread-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          font-size: 0.85rem;
          color: #6c757d;
        }

        .active-badge {
          background: #007bff;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
};
