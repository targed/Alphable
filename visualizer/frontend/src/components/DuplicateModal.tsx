import React from 'react';
import { CandidateMove } from '../types';

interface EngineDecision {
  name: string;
  action: string;
  move: { word: string; row: number; col: number; direction: string; coord: string };
  points: number;
  equity: number;
  candidates: CandidateMove[];
  error?: string;
}

interface DuplicateModalProps {
  rack: string[];
  p1Name: string;
  p2Name: string;
  p1Decision: EngineDecision | null;
  p2Decision: EngineDecision | null;
  isLoading: boolean;
  onApplyDecision: (decision: EngineDecision) => void;
  onClose: () => void;
}

export const DuplicateModal: React.FC<DuplicateModalProps> = ({
  rack,
  p1Name,
  p2Name,
  p1Decision,
  p2Decision,
  isLoading,
  onApplyDecision,
  onClose
}) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '850px' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fef3c7' }}>
              Duplicate Position Decision Comparison
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Evaluating identical rack <strong style={{ color: '#f59e0b', letterSpacing: '0.1em' }}>{' '}{rack.join(' ')}{' '}</strong> on current board state.
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose} style={{ padding: '0.3rem 0.7rem' }}>Close</button>
        </div>

        {isLoading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Evaluating both engines on identical position...
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
            {/* Player 1 Decision Card */}
            <div className="panel-card" style={{ borderTop: '4px solid #3b82f6' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
                Player 1 Choice
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#60a5fa', marginBottom: '0.75rem' }}>
                {p1Name}
              </div>

              {p1Decision && !p1Decision.error ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc' }}>
                      {p1Decision.move.word || p1Decision.action}
                    </span>
                    <span style={{ fontSize: '1.3rem', fontWeight: 800, color: '#10b981' }}>
                      +{p1Decision.points} pts
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    Coordinate: <strong style={{ color: '#38bdf8' }}>{p1Decision.move.coord}</strong> ({p1Decision.move.direction}) • Equity: <strong style={{ color: '#f59e0b' }}>{p1Decision.equity}</strong>
                  </div>

                  {p1Decision.candidates && p1Decision.candidates.length > 1 && (
                    <div style={{ marginBottom: '1.25rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.5rem' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Alternative Options:</div>
                      {p1Decision.candidates.slice(1, 4).map((alt, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.15rem 0' }}>
                          <span>{alt.word} ({alt.coord})</span>
                          <span>+{alt.points} pts (Eq: {alt.equity})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    className="btn-primary"
                    onClick={() => onApplyDecision(p1Decision)}
                    style={{ width: '100%' }}
                  >
                    Apply {p1Name}'s Move
                  </button>
                </>
              ) : (
                <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>{p1Decision?.error || "No decision available."}</div>
              )}
            </div>

            {/* Player 2 Decision Card */}
            <div className="panel-card" style={{ borderTop: '4px solid #8b5cf6' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
                Player 2 Choice
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#c084fc', marginBottom: '0.75rem' }}>
                {p2Name}
              </div>

              {p2Decision && !p2Decision.error ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc' }}>
                      {p2Decision.move.word || p2Decision.action}
                    </span>
                    <span style={{ fontSize: '1.3rem', fontWeight: 800, color: '#10b981' }}>
                      +{p2Decision.points} pts
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    Coordinate: <strong style={{ color: '#38bdf8' }}>{p2Decision.move.coord}</strong> ({p2Decision.move.direction}) • Equity: <strong style={{ color: '#f59e0b' }}>{p2Decision.equity}</strong>
                  </div>

                  {p2Decision.candidates && p2Decision.candidates.length > 1 && (
                    <div style={{ marginBottom: '1.25rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.5rem' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Alternative Options:</div>
                      {p2Decision.candidates.slice(1, 4).map((alt, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.15rem 0' }}>
                          <span>{alt.word} ({alt.coord})</span>
                          <span>+{alt.points} pts (Eq: {alt.equity})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    className="btn-primary"
                    onClick={() => onApplyDecision(p2Decision)}
                    style={{ width: '100%', background: 'linear-gradient(180deg, #7c3aed 0%, #6d28d9 100%)', borderColor: '#5b21b6' }}
                  >
                    Apply {p2Name}'s Move
                  </button>
                </>
              ) : (
                <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>{p2Decision?.error || "No decision available."}</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
