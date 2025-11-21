/**
 * Execution Bundle Viewer - v0.2 Component
 *
 * Displays and exports execution bundles (scaffolds, tasks, prompts).
 */
import React, { useState } from "react";
import { ExecutionBundle, Phase } from "../../types";

interface ExecutionBundleViewerProps {
  bundle: ExecutionBundle;
}

export const ExecutionBundleViewer: React.FC<ExecutionBundleViewerProps> = ({ bundle }) => {
  const [activeTab, setActiveTab] = useState<"scaffold" | "tasks" | "prompts">("scaffold");

  const downloadJSON = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadText = (text: string, filename: string) => {
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const tasksByPhase = bundle.tasks.reduce((acc, task) => {
    if (!acc[task.phase]) acc[task.phase] = [];
    acc[task.phase].push(task);
    return acc;
  }, {} as Record<Phase, typeof bundle.tasks>);

  const phaseLabels: Record<Phase, string> = {
    [Phase.PROTOTYPE]: "🧪 Prototype",
    [Phase.V1]: "🚀 V1",
    [Phase.SCALE_UP]: "📈 Scale Up",
    [Phase.V2_PLUS]: "🌟 V2+",
  };

  return (
    <div className="execution-bundle">
      <div className="bundle-header">
        <h3>⚡ Execution Bundle</h3>
        <button
          className="btn-download-all"
          onClick={() => downloadJSON(bundle, "execution-bundle.json")}
        >
          ⬇️ Download All
        </button>
      </div>

      <div className="bundle-tabs">
        <button
          className={`tab ${activeTab === "scaffold" ? "active" : ""}`}
          onClick={() => setActiveTab("scaffold")}
        >
          📁 Scaffold
        </button>
        <button
          className={`tab ${activeTab === "tasks" ? "active" : ""}`}
          onClick={() => setActiveTab("tasks")}
        >
          📋 Tasks ({bundle.tasks.length})
        </button>
        <button
          className={`tab ${activeTab === "prompts" ? "active" : ""}`}
          onClick={() => setActiveTab("prompts")}
        >
          🤖 AI Prompts ({bundle.prompts.length})
        </button>
      </div>

      <div className="bundle-content">
        {activeTab === "scaffold" && (
          <div className="scaffold-view">
            <div className="scaffold-meta">
              <div className="meta-item">
                <strong>Language:</strong> {bundle.repo_scaffold.language}
              </div>
              <div className="meta-item">
                <strong>Frameworks:</strong> {bundle.repo_scaffold.frameworks.join(", ")}
              </div>
            </div>

            <div className="structure-tree">
              <h4>Repository Structure</h4>
              {Object.entries(bundle.repo_scaffold.structure).map(([path, items]) => (
                <div key={path} className="tree-node">
                  {path && <div className="tree-path">{path}</div>}
                  <div className="tree-items">
                    {items.map((item, i) => (
                      <div key={i} className="tree-item">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <button
              className="btn-secondary"
              onClick={() => downloadJSON(bundle.repo_scaffold, "scaffold.json")}
            >
              Download Scaffold
            </button>
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="tasks-view">
            {Object.entries(phaseLabels).map(([phase, label]) => {
              const tasks = tasksByPhase[phase as Phase] || [];
              if (tasks.length === 0) return null;

              return (
                <div key={phase} className="phase-section">
                  <h4>{label}</h4>
                  <div className="tasks-list">
                    {tasks.map((task) => (
                      <div key={task.id} className="task-card">
                        <div className="task-header">
                          <span className="task-title">{task.title}</span>
                          <span className={`estimate estimate-${task.estimate}`}>
                            {task.estimate}
                          </span>
                        </div>
                        <p className="task-description">{task.description}</p>
                        <div className="task-criteria">
                          <strong>Acceptance Criteria:</strong>
                          <ul>
                            {task.acceptance_criteria.map((criterion, i) => (
                              <li key={i}>{criterion}</li>
                            ))}
                          </ul>
                        </div>
                        {task.dependencies.length > 0 && (
                          <div className="task-deps">
                            <strong>Dependencies:</strong> {task.dependencies.join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            <button
              className="btn-secondary"
              onClick={() => downloadJSON(bundle.tasks, "tasks.json")}
            >
              Download Tasks
            </button>
          </div>
        )}

        {activeTab === "prompts" && (
          <div className="prompts-view">
            {bundle.prompts.map((prompt, i) => (
              <div key={prompt.id} className="prompt-card">
                <div className="prompt-header">
                  <h4>{prompt.title}</h4>
                  <span className="prompt-target">for {prompt.target}</span>
                </div>
                <pre className="prompt-content">{prompt.prompt}</pre>
                <div className="prompt-actions">
                  <button
                    className="btn-copy"
                    onClick={() => copyToClipboard(prompt.prompt)}
                  >
                    📋 Copy
                  </button>
                  <button
                    className="btn-download"
                    onClick={() => downloadText(prompt.prompt, `prompt_${i + 1}_${prompt.target}.txt`)}
                  >
                    ⬇️ Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .execution-bundle {
          background: #ffffff;
          border-radius: 8px;
          padding: 1.5rem;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .bundle-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }

        .bundle-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .btn-download-all {
          background: #28a745;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        .btn-download-all:hover {
          background: #218838;
        }

        .bundle-tabs {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 1.5rem;
          border-bottom: 2px solid #e9ecef;
        }

        .tab {
          background: none;
          border: none;
          padding: 0.75rem 1.5rem;
          cursor: pointer;
          font-size: 1rem;
          font-weight: 600;
          color: #6c757d;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
        }

        .tab:hover {
          color: #007bff;
        }

        .tab.active {
          color: #007bff;
          border-bottom-color: #007bff;
        }

        .bundle-content {
          min-height: 300px;
        }

        /* Scaffold View */
        .scaffold-meta {
          display: flex;
          gap: 2rem;
          margin-bottom: 1.5rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 4px;
        }

        .meta-item {
          color: #495057;
        }

        .meta-item strong {
          margin-right: 0.5rem;
        }

        .structure-tree h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .tree-node {
          margin-bottom: 1rem;
        }

        .tree-path {
          font-weight: 600;
          color: #007bff;
          margin-bottom: 0.5rem;
        }

        .tree-items {
          padding-left: 1.5rem;
        }

        .tree-item {
          color: #495057;
          padding: 0.25rem 0;
          font-family: monospace;
        }

        /* Tasks View */
        .phase-section {
          margin-bottom: 2rem;
        }

        .phase-section h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
          font-size: 1.2rem;
        }

        .tasks-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .task-card {
          background: #f8f9fa;
          border-left: 4px solid #007bff;
          padding: 1rem;
          border-radius: 4px;
        }

        .task-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }

        .task-title {
          font-weight: 600;
          color: #2c3e50;
        }

        .estimate {
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .estimate-S { background: #d4edda; color: #155724; }
        .estimate-M { background: #fff3cd; color: #856404; }
        .estimate-L { background: #f8d7da; color: #721c24; }
        .estimate-XL { background: #f5c6cb; color: #721c24; }

        .task-description {
          color: #495057;
          margin: 0.5rem 0;
        }

        .task-criteria ul {
          margin: 0.5rem 0 0 1.5rem;
          color: #495057;
        }

        .task-deps {
          margin-top: 0.5rem;
          font-size: 0.9rem;
          color: #6c757d;
        }

        /* Prompts View */
        .prompt-card {
          background: #f8f9fa;
          border-radius: 6px;
          padding: 1.5rem;
          margin-bottom: 1.5rem;
        }

        .prompt-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .prompt-header h4 {
          margin: 0;
          color: #2c3e50;
        }

        .prompt-target {
          background: #007bff;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 3px;
          font-size: 0.85rem;
          font-weight: 600;
        }

        .prompt-content {
          background: #ffffff;
          border: 1px solid #dee2e6;
          border-radius: 4px;
          padding: 1rem;
          margin: 1rem 0;
          overflow-x: auto;
          font-size: 0.9rem;
          line-height: 1.6;
          white-space: pre-wrap;
        }

        .prompt-actions {
          display: flex;
          gap: 0.5rem;
        }

        .btn-copy,
        .btn-download,
        .btn-secondary {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        .btn-copy {
          background: #6c757d;
          color: white;
        }

        .btn-copy:hover {
          background: #5a6268;
        }

        .btn-download,
        .btn-secondary {
          background: #007bff;
          color: white;
        }

        .btn-download:hover,
        .btn-secondary:hover {
          background: #0056b3;
        }

        .btn-secondary {
          margin-top: 1.5rem;
        }
      `}</style>
    </div>
  );
};
