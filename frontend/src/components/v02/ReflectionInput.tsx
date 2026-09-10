/**
 * Reflection Input - v0.2 Component
 *
 * Captures freeform reflections during the planning process.
 */
import React, { useState } from "react";
import { PlanNote, Question } from "../../types";

interface ReflectionInputProps {
  reflectionPrompt?: Question;
  onSubmitReflection: (reflection: string) => void;
  recentNotes?: PlanNote[];
}

export const ReflectionInput: React.FC<ReflectionInputProps> = ({
  reflectionPrompt,
  onSubmitReflection,
  recentNotes = [],
}) => {
  const [reflection, setReflection] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = () => {
    if (!reflection.trim()) {
      alert("Please enter your reflection");
      return;
    }
    onSubmitReflection(reflection);
    setReflection("");
    setIsExpanded(false);
  };

  const getTagColor = (tag: string): string => {
    if (tag.startsWith("constraint:")) return "#dc3545";
    if (tag.startsWith("risk:")) return "#fd7e14";
    if (tag.startsWith("preference:")) return "#6f42c1";
    if (tag.startsWith("decision:")) return "#28a745";
    if (tag.startsWith("insight:")) return "#17a2b8";
    return "#6c757d";
  };

  return (
    <div className="reflection-input">
      {reflectionPrompt && (
        <div className="reflection-prompt">
          <div className="prompt-icon">💭</div>
          <div className="prompt-content">
            <h4>Reflection Pulse</h4>
            <p>{reflectionPrompt.text}</p>
            <button
              className="btn-reflect"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? "Collapse" : "Share Your Thoughts"}
            </button>
          </div>
        </div>
      )}

      {!reflectionPrompt && (
        <div className="manual-reflection">
          <button
            className="btn-add-reflection"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            💭 Add Reflection
          </button>
        </div>
      )}

      {isExpanded && (
        <div className="reflection-form">
          <h4>Your Reflection</h4>
          <p className="help-text">
            Share any insights, concerns, constraints, or preferences that came to mind.
            This will be distilled into tagged notes to improve your plan.
          </p>

          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="e.g., I'm worried about scalability. We need to handle 10k concurrent users from day 1..."
            rows={6}
          />

          <div className="form-actions">
            <button className="btn-cancel" onClick={() => setIsExpanded(false)}>
              Cancel
            </button>
            <button className="btn-submit" onClick={handleSubmit}>
              Submit Reflection
            </button>
          </div>

          <div className="reflection-tips">
            <strong>Tips for better reflections:</strong>
            <ul>
              <li>🚫 Constraints: "We can't use AWS" or "Budget limited to $5k"</li>
              <li>⚠️ Risks: "Competition is fierce" or "Scaling could be expensive"</li>
              <li>💡 Insights: "Users need mobile-first" or "Real-time is critical"</li>
              <li>✅ Decisions: "Going with microservices" or "MVP first, scale later"</li>
            </ul>
          </div>
        </div>
      )}

      {recentNotes.length > 0 && (
        <div className="recent-notes">
          <h4>Recent Reflections</h4>
          <div className="notes-list">
            {recentNotes.map((note) => (
              <div key={note.id} className="note-card">
                <div className="note-distilled">{note.distilled}</div>
                <div className="note-tags">
                  {note.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="tag"
                      style={{ backgroundColor: getTagColor(tag) }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .reflection-input {
          background: #ffffff;
          border-radius: 8px;
          padding: 1.5rem;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .reflection-prompt {
          display: flex;
          gap: 1rem;
          background: #fff3cd;
          border: 2px solid #ffc107;
          border-radius: 6px;
          padding: 1rem;
          margin-bottom: 1rem;
        }

        .prompt-icon {
          font-size: 2rem;
        }

        .prompt-content {
          flex: 1;
        }

        .prompt-content h4 {
          margin: 0 0 0.5rem 0;
          color: #856404;
        }

        .prompt-content p {
          margin: 0 0 1rem 0;
          color: #856404;
        }

        .btn-reflect {
          background: #ffc107;
          color: #212529;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        .btn-reflect:hover {
          background: #e0a800;
        }

        .manual-reflection {
          text-align: center;
          margin: 1rem 0;
        }

        .btn-add-reflection {
          background: #f8f9fa;
          border: 2px dashed #dee2e6;
          padding: 1rem 2rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 1rem;
          color: #495057;
        }

        .btn-add-reflection:hover {
          background: #e9ecef;
          border-color: #adb5bd;
        }

        .reflection-form {
          background: #f8f9fa;
          border-radius: 6px;
          padding: 1.5rem;
          margin-top: 1rem;
        }

        .reflection-form h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .help-text {
          color: #6c757d;
          font-size: 0.9rem;
          margin: 0 0 1rem 0;
        }

        textarea {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-family: inherit;
          font-size: 1rem;
          resize: vertical;
        }

        .form-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .btn-cancel,
        .btn-submit {
          flex: 1;
          padding: 0.75rem;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
        }

        .btn-cancel {
          background: #6c757d;
          color: white;
        }

        .btn-cancel:hover {
          background: #5a6268;
        }

        .btn-submit {
          background: #28a745;
          color: white;
        }

        .btn-submit:hover {
          background: #218838;
        }

        .reflection-tips {
          margin-top: 1rem;
          padding: 1rem;
          background: #e7f3ff;
          border-radius: 4px;
          font-size: 0.9rem;
        }

        .reflection-tips strong {
          display: block;
          margin-bottom: 0.5rem;
          color: #004085;
        }

        .reflection-tips ul {
          margin: 0;
          padding-left: 1.5rem;
        }

        .reflection-tips li {
          margin-bottom: 0.25rem;
          color: #004085;
        }

        .recent-notes {
          margin-top: 2rem;
        }

        .recent-notes h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .notes-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .note-card {
          background: #f8f9fa;
          border-left: 4px solid #007bff;
          padding: 0.75rem;
          border-radius: 4px;
        }

        .note-distilled {
          margin-bottom: 0.5rem;
          color: #2c3e50;
        }

        .note-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .tag {
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          font-size: 0.75rem;
          color: white;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
};
