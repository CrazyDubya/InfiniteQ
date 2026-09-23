/**
 * Coverage display component showing progress across dimensions
 */
import React from 'react';
import type { CoverageMap } from '../types';

interface CoverageDisplayProps {
  coverage: CoverageMap;
  /** Heading, e.g. "Overall coverage" vs "Thread coverage". */
  title?: string;
}

// Must match the backend CoverageMap: 9 dimensions.
const DIMENSIONS: { key: keyof CoverageMap; label: string; color: string }[] = [
  { key: 'problem', label: 'Problem', color: '#3b82f6' },
  { key: 'users', label: 'Users', color: '#8b5cf6' },
  { key: 'constraints', label: 'Constraints', color: '#ec4899' },
  { key: 'features', label: 'Features', color: '#f59e0b' },
  { key: 'architecture', label: 'Architecture', color: '#10b981' },
  { key: 'data_ml', label: 'Data / ML', color: '#14b8a6' },
  { key: 'operations', label: 'Operations', color: '#06b6d4' },
  { key: 'risks', label: 'Risks', color: '#ef4444' },
  { key: 'gtm', label: 'Go-to-market', color: '#6366f1' },
];

export const CoverageDisplay: React.FC<CoverageDisplayProps> = ({
  coverage,
  title = 'Planning Coverage',
}) => {
  const overallCoverage =
    DIMENSIONS.reduce((total, { key }) => total + (coverage[key] ?? 0), 0) /
    DIMENSIONS.length;

  return (
    <div className="coverage-display">
      <h3 className="coverage-title">
        {title}: {overallCoverage.toFixed(0)}%
      </h3>

      <div className="coverage-bars">
        {DIMENSIONS.map(({ key, label, color }) => {
          const value = coverage[key] ?? 0;
          return (
            <div key={key} className="coverage-bar-item">
              <div className="coverage-bar-header">
                <span className="coverage-label">{label}</span>
                <span className="coverage-value">{value.toFixed(0)}%</span>
              </div>
              <div className="coverage-bar-track">
                <div
                  className="coverage-bar-fill"
                  style={{
                    width: `${value}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
