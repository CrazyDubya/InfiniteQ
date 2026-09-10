/**
 * Profile Forms - v0.2 Components
 *
 * Project and Persona profile input forms for session creation.
 */
import React, { useState } from "react";
import {
  ProjectProfile,
  PersonaProfile,
  ProjectType,
  PersonaRole,
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

  const handleProjectChange = (field: keyof ProjectProfile, value: any) => {
    const updated = { ...projectProfile, [field]: value };
    setProjectProfile(updated);
    onProfilesChange(updated, personaProfile);
  };

  const handlePersonaChange = (field: keyof PersonaProfile, value: any) => {
    const updated = { ...personaProfile, [field]: value };
    setPersonaProfile(updated);
    onProfilesChange(projectProfile, updated);
  };

  const handleTechConstraintsChange = (value: string) => {
    setTechConstraints(value);
    const constraints = value.split(",").map((s) => s.trim()).filter(Boolean);
    handleProjectChange("tech_constraints", constraints);
  };

  const handleNonGoalsChange = (value: string) => {
    setNonGoals(value);
    const goals = value.split(",").map((s) => s.trim()).filter(Boolean);
    handleProjectChange("non_goals", goals);
  };

  return (
    <div className="profile-forms">
      <div className="profile-section">
        <h3>🎯 Project Profile</h3>
        <p className="help-text">
          Tell us about your project to get context-aware questions
        </p>

        <div className="form-grid">
          {/* Project Type */}
          <div className="form-field">
            <label>Project Type</label>
            <select
              value={projectProfile.type || ProjectType.SAAS}
              onChange={(e) => handleProjectChange("type", e.target.value as ProjectType)}
            >
              <option value={ProjectType.SAAS}>SaaS Platform</option>
              <option value={ProjectType.MOBILE_APP}>Mobile App</option>
              <option value={ProjectType.WEB_APP}>Web Application</option>
              <option value={ProjectType.ENTERPRISE}>Enterprise Software</option>
              <option value={ProjectType.ECOMMERCE}>E-Commerce</option>
              <option value={ProjectType.ANALYTICS}>Analytics/Data</option>
              <option value={ProjectType.DEV_TOOLS}>Developer Tools</option>
              <option value={ProjectType.CONTENT}>Content Platform</option>
              <option value={ProjectType.OTHER}>Other</option>
            </select>
          </div>

          {/* Sophistication */}
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

          {/* Team Size */}
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

          {/* Timeline */}
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

          {/* Budget */}
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

        {/* Tech Constraints */}
        <div className="form-field full-width">
          <label>Tech Constraints (comma-separated)</label>
          <input
            type="text"
            placeholder="e.g., python, react, no PHP, no Java"
            value={techConstraints}
            onChange={(e) => handleTechConstraintsChange(e.target.value)}
          />
          <span className="help-text">
            List required tech OR forbidden tech (prefix with "no")
          </span>
        </div>

        {/* Non-Goals */}
        <div className="form-field full-width">
          <label>Non-Goals (comma-separated)</label>
          <input
            type="text"
            placeholder="e.g., mobile apps, blockchain, realtime chat"
            value={nonGoals}
            onChange={(e) => handleNonGoalsChange(e.target.value)}
          />
          <span className="help-text">
            Explicitly out-of-scope features to avoid
          </span>
        </div>
      </div>

      <div className="profile-section">
        <h3>👤 Your Profile</h3>
        <p className="help-text">
          Help us tailor questions to your experience and preferences
        </p>

        <div className="form-grid">
          {/* Role */}
          <div className="form-field">
            <label>Your Role</label>
            <select
              value={personaProfile.role || PersonaRole.FOUNDER_SOLO}
              onChange={(e) => handlePersonaChange("role", e.target.value as PersonaRole)}
            >
              <option value={PersonaRole.FOUNDER_SOLO}>Solo Founder</option>
              <option value={PersonaRole.FOUNDER_TEAM}>Founding Team</option>
              <option value={PersonaRole.TECH_LEAD}>Tech Lead</option>
              <option value={PersonaRole.PRODUCT_MANAGER}>Product Manager</option>
              <option value={PersonaRole.BUSINESS_LEADER}>Business Leader</option>
              <option value={PersonaRole.ENGINEER}>Engineer</option>
              <option value={PersonaRole.DESIGNER}>Designer</option>
              <option value={PersonaRole.OTHER}>Other</option>
            </select>
          </div>

          {/* Tech Comfort */}
          <div className="form-field">
            <label>
              Technical Comfort: {personaProfile.tech_comfort || 5}/10
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={personaProfile.tech_comfort || 5}
              onChange={(e) => handlePersonaChange("tech_comfort", parseInt(e.target.value))}
              className="slider"
            />
            <span className="slider-labels">
              <span>Non-technical</span>
              <span>Expert</span>
            </span>
          </div>

          {/* Business Comfort */}
          <div className="form-field">
            <label>
              Business Comfort: {personaProfile.business_comfort || 5}/10
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={personaProfile.business_comfort || 5}
              onChange={(e) => handlePersonaChange("business_comfort", parseInt(e.target.value))}
              className="slider"
            />
            <span className="slider-labels">
              <span>New to business</span>
              <span>Experienced</span>
            </span>
          </div>

          {/* Preferred Depth */}
          <div className="form-field">
            <label>Question Depth</label>
            <select
              value={personaProfile.preferred_depth || "medium"}
              onChange={(e) => handlePersonaChange("preferred_depth", e.target.value)}
            >
              <option value="light">Light (high-level overview)</option>
              <option value="medium">Medium (balanced detail)</option>
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

        .help-text {
          color: #6c757d;
          font-size: 0.9rem;
          margin: 0 0 1rem 0;
        }

        .form-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }

        .form-field {
          display: flex;
          flex-direction: column;
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
        }

        .form-field select:focus,
        .form-field input:focus {
          outline: none;
          border-color: #007bff;
        }

        .slider {
          width: 100%;
        }

        .slider-labels {
          display: flex;
          justify-content: space-between;
          font-size: 0.8rem;
          color: #6c757d;
          margin-top: 0.25rem;
        }
      `}</style>
    </div>
  );
};
