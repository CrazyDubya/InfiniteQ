/**
 * Initial idea input component.
 *
 * Optionally collects the project and persona profiles, which the backend uses
 * to make the interview questions context-aware.
 */
import React, { useState } from 'react';
import { ProfileForms } from './v02/ProfileForms';
import { Mode } from '../types';
import type { PersonaProfile, ProjectProfile } from '../types';

export interface SessionProfiles {
  project: ProjectProfile;
  persona: PersonaProfile;
}

interface IdeaInputProps {
  onSubmit: (idea: string, mode: Mode, profiles: SessionProfiles) => void;
  loading: boolean;
}

export const IdeaInput: React.FC<IdeaInputProps> = ({ onSubmit, loading }) => {
  const [idea, setIdea] = useState('');
  const [mode, setMode] = useState<Mode>(Mode.KICKOFF);
  const [showProfiles, setShowProfiles] = useState(false);
  const [profiles, setProfiles] = useState<SessionProfiles>({
    project: {},
    persona: {},
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (idea.trim()) {
      onSubmit(idea, mode, profiles);
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
          <label htmlFor="mode">Interview Mode</label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            disabled={loading}
          >
            <option value={Mode.KICKOFF}>Kickoff - broad initial coverage</option>
            <option value={Mode.DEEP_DIVE}>Deep dive - focus on one area</option>
            <option value={Mode.SANITY_CHECK}>Sanity check - review a plan</option>
          </select>
        </div>

        <button
          type="button"
          className="toggle-profiles-button"
          onClick={() => setShowProfiles(!showProfiles)}
          disabled={loading}
        >
          {showProfiles ? 'Hide profiles' : 'Add project & persona profiles (optional)'}
        </button>

        {showProfiles && (
          <ProfileForms
            onProfilesChange={(project, persona) => setProfiles({ project, persona })}
          />
        )}

        <button type="submit" disabled={loading || !idea.trim()}>
          {loading ? 'Starting...' : 'Start Planning Session'}
        </button>
      </form>
    </div>
  );
};
