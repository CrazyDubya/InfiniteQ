/**
 * Coverage display component showing progress across dimensions
 */
import React from 'react';
import type { CoverageMap } from '../types';

interface CoverageDisplayProps {
  coverage: CoverageMap;
}

export const CoverageDisplay: React.FC<CoverageDisplayProps> = ({ coverage }) => {
  const dimensions = [
    { key: 'problem', label: 'Problem', color: '#3b82f6' },
    { key: 'users', label: 'Users', color: '#8b5cf6' },
    { key: 'constraints', label: 'Constraints', color: '#ec4899' },
    { key: 'features', label: 'Features', color: '#f59e0b' },
    { key: 'architecture', label: 'Architecture', color: '#10b981' },
    { key: 'operations', label: 'Operations', color: '#06b6d4' },
    { key: 'risks', label: 'Risks', color: '#ef4444' },
    { key: 'deliverables', label: 'Deliverables', color: '#6366f1' },
  ];

  const overallCoverage = Object.values(coverage).reduce((a, b) => a + b, 0) / 8;

  return (
    <div className="coverage-display">
      <h3 className="coverage-title">
        Planning Coverage: {overallCoverage.toFixed(0)}%
      </h3>

      <div className="coverage-bars">
        {dimensions.map(({ key, label, color }) => {
          const value = coverage[key as keyof CoverageMap];
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
