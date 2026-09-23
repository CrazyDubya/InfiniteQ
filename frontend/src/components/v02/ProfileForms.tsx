/**
 * Profile Forms - v0.2 Components
 *
 * Project and Persona profile input forms for session creation. Field names and
 * options mirror backend/app/models/schema.py.
 */
import React, { useState } from "react";
import {
  PersonaProfile,
  PersonaRole,
  ProjectProfile,
  ProjectType,
} from "../../types";

interface ProfileFormsProps {
  onProfilesChange: (project: ProjectProfile, persona: PersonaProfile) => void;
  initialProject?: ProjectProfile;
  initialPersona?: PersonaProfile;
}

export const ProfileForms: React.FC<ProfileFormsProps> = ({
  onProfilesChange,
  initialProject = {},
  initialPersona = {},
}) => {
  const [projectProfile, setProjectProfile] = useState<ProjectProfile>(initialProject);
  const [personaProfile, setPersonaProfile] = useState<PersonaProfile>(initialPersona);
  const [techConstraints, setTechConstraints] = useState<string>(
    initialProject.tech_constraints?.join(", ") || ""
  );
  const [nonGoals, setNonGoals] = useState<string>(
    initialProject.non_goals?.join(", ") || ""
  );

  const handleProjectChange = (field: keyof ProjectProfile, value: unknown) => {
    const updated = { ...projectProfile, [field]: value };
    setProjectProfile(updated);
    onProfilesChange(updated, personaProfile);
  };

  const handlePersonaChange = (field: keyof PersonaProfile, value: unknown) => {
    const updated = { ...personaProfile, [field]: value };
    setPersonaProfile(updated);
    onProfilesChange(projectProfile, updated);
  };

  const toList = (value: string) =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

  return (
    <div className="profile-forms">
      <div className="profile-section">
        <h3>🎯 Project Profile</h3>
        <p className="help-text">
          Tell us about your project to get context-aware questions
        </p>

        <div className="form-grid">
          <div className="form-field">
            <label>Project Type</label>
            <select
              value={projectProfile.type || ProjectType.SAAS}
              onChange={(e) => handleProjectChange("type", e.target.value as ProjectType)}
            >
              <option value={ProjectType.SAAS}>SaaS Platform</option>
              <option value={ProjectType.INTERNAL_TOOL}>Internal Tool</option>
              <option value={ProjectType.GAME}>Game</option>
              <option value={ProjectType.CONTENT_SITE}>Content Site</option>
              <option value={ProjectType.RESEARCH}>Research</option>
              <option value={ProjectType.AUTOMATION}>Automation</option>
              <option value={ProjectType.OTHER}>Other</option>
            </select>
          </div>

          <div className="form-field">
            <label>Sophistication Level</label>
            <select
              value={projectProfile.sophistication || "mvp"}
              onChange={(e) => handleProjectChange("sophistication", e.target.value)}
            >
              <option value="toy">Toy/Learning Project</option>
              <option value="mvp">MVP/Startup</option>
              <option value="production">Production-Ready</option>
            </select>
          </div>

          <div className="form-field">
            <label>Team Size</label>
            <select
              value={projectProfile.team_size || "solo"}
              onChange={(e) => handleProjectChange("team_size", e.target.value)}
            >
              <option value="solo">Solo</option>
              <option value="2-3">2-3 people</option>
              <option value="4-10">4-10 people</option>
              <option value="10+">10+ people</option>
            </select>
          </div>

          <div className="form-field">
            <label>Timeline</label>
            <select
              value={projectProfile.timeline || "1-4_weeks"}
              onChange={(e) => handleProjectChange("timeline", e.target.value)}
            >
              <option value="weekend">Weekend project</option>
              <option value="1-4_weeks">1-4 weeks</option>
              <option value="1-3_months">1-3 months</option>
              <option value="6+_months">6+ months</option>
            </select>
          </div>

          <div className="form-field">
            <label>Budget Band</label>
            <select
              value={projectProfile.budget_band || "<1k"}
              onChange={(e) => handleProjectChange("budget_band", e.target.value)}
            >
              <option value="<1k">&lt; $1,000</option>
              <option value="1k-10k">$1,000 - $10,000</option>
              <option value="10k-100k">$10,000 - $100,000</option>
              <option value="100k+">$100,000+</option>
            </select>
          </div>
        </div>

        <div className="form-field full-width">
          <label>Tech Constraints (comma-separated)</label>
          <input
            type="text"
            placeholder="e.g., python, react, no PHP, no Java"
            value={techConstraints}
            onChange={(e) => {
              setTechConstraints(e.target.value);
              handleProjectChange("tech_constraints", toList(e.target.value));
            }}
          />
          <span className="help-text">
            Required or forbidden technologies. The interview will not propose
            questions about forbidden ones.
          </span>
        </div>

        <div className="form-field full-width">
          <label>Non-Goals (comma-separated)</label>
          <input
            type="text"
            placeholder="e.g., mobile apps, blockchain, realtime chat"
            value={nonGoals}
            onChange={(e) => {
              setNonGoals(e.target.value);
              handleProjectChange("non_goals", toList(e.target.value));
            }}
          />
          <span className="help-text">Explicitly out-of-scope features to avoid</span>
        </div>
      </div>

      <div className="profile-section">
        <h3>👤 Your Profile</h3>
        <p className="help-text">
          Help us tailor questions to your experience and preferences
        </p>

        <div className="form-grid">
          <div className="form-field">
            <label>Your Role</label>
            <select
              value={personaProfile.role || PersonaRole.FOUNDER_TECHNICAL}
              onChange={(e) => handlePersonaChange("role", e.target.value as PersonaRole)}
            >
              <option value={PersonaRole.FOUNDER_NON_TECHNICAL}>
                Non-technical Founder
              </option>
              <option value={PersonaRole.FOUNDER_TECHNICAL}>Technical Founder</option>
              <option value={PersonaRole.TECH_LEAD}>Tech Lead</option>
              <option value={PersonaRole.PM}>Product Manager</option>
              <option value={PersonaRole.DOMAIN_EXPERT}>Domain Expert</option>
              <option value={PersonaRole.HACKER_PLAYING}>Hacker / Side Project</option>
            </select>
          </div>

          <div className="form-field">
            <label>Comfort with Tech</label>
            <select
              value={personaProfile.comfort_with_tech || "medium"}
              onChange={(e) => handlePersonaChange("comfort_with_tech", e.target.value)}
            >
              <option value="low">Low - keep it non-technical</option>
              <option value="medium">Medium - some jargon is fine</option>
              <option value="high">High - technical detail welcome</option>
            </select>
          </div>

          <div className="form-field">
            <label>Comfort with Business</label>
            <select
              value={personaProfile.comfort_with_business || "medium"}
              onChange={(e) =>
                handlePersonaChange("comfort_with_business", e.target.value)
              }
            >
              <option value="low">Low - avoid business jargon</option>
              <option value="medium">Medium</option>
              <option value="high">High - happy to discuss GTM and pricing</option>
            </select>
          </div>

          <div className="form-field">
            <label>Question Depth</label>
            <select
              value={personaProfile.preferred_depth || "balanced"}
              onChange={(e) => handlePersonaChange("preferred_depth", e.target.value)}
            >
              <option value="light">Light (high-level overview)</option>
              <option value="balanced">Balanced (recommended)</option>
              <option value="deep">Deep (comprehensive exploration)</option>
            </select>
          </div>
        </div>
      </div>

      <style>{`
        .profile-forms {
          display: flex;
          flex-direction: column;
          gap: 2rem;
          text-align: left;
        }

        .profile-section {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 1.5rem;
        }

        .profile-section h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .profile-forms .help-text {
          color: #6c757d;
          font-size: 0.9rem;
          margin: 0 0 1rem 0;
        }

        .form-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }

        .form-field {
          display: flex;
          flex-direction: column;
          margin-bottom: 0.5rem;
        }

        .form-field.full-width {
          grid-column: 1 / -1;
        }

        .form-field label {
          font-weight: 600;
          margin-bottom: 0.5rem;
          color: #495057;
        }

        .form-field select,
        .form-field input[type="text"] {
          padding: 0.5rem;
          border: 1px solid #ced4da;
          border-radius: 4px;
          font-size: 1rem;
          background: #ffffff;
        }

        .form-field select:focus,
        .form-field input:focus {
          outline: none;
          border-color: #007bff;
        }

        .profile-forms .help-text {
          margin-top: 0.25rem;
          margin-bottom: 0;
        }
      `}</style>
    </div>
  );
};
