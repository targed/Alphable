import React from 'react';
import { CandidateMove } from '../types';

interface CandidateTableProps {
  candidates: CandidateMove[];
  onSelectCandidate?: (candidate: CandidateMove) => void;
  onHoverCandidate?: (candidate: CandidateMove | null) => void;
  title?: string;
}

export const CandidateTable: React.FC<CandidateTableProps> = ({
  candidates,
  onSelectCandidate,
  onHoverCandidate,
  title = "AI Move Evaluations"
}) => {
  if (!candidates || candidates.length === 0) {
    return (
      <div className="panel-card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
        No candidate moves evaluated yet. Click "Ask AI for Hint" or make a play.
      </div>
    );
  }

  return (
    <div className="panel-card">
      <div className="panel-title">
        <span>{title}</span>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          {candidates.length} candidates
        </span>
      </div>
      <div style={{ maxHeight: '380px', overflowY: 'auto' }}>
        <table className="candidate-table">
          <thead>
            <tr>
              <th style={{ width: '36px' }}>#</th>
              <th>Word</th>
              <th>Coord</th>
              <th style={{ textAlign: 'right' }}>Pts</th>
              <th>Leave</th>
              <th style={{ textAlign: 'right' }}>Equity</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, idx) => (
              <tr
                key={idx}
                onClick={() => onSelectCandidate && onSelectCandidate(c)}
                onMouseEnter={() => onHoverCandidate && onHoverCandidate(c)}
                onMouseLeave={() => onHoverCandidate && onHoverCandidate(null)}
              >
                <td style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{idx + 1}</td>
                <td style={{ fontWeight: 700, color: '#f8fafc' }}>{c.word || (c.is_pass ? "PASS" : "EXCH")}</td>
                <td style={{ color: '#38bdf8' }}>{c.coord} ({c.direction})</td>
                <td style={{ textAlign: 'right', fontWeight: 700, color: '#10b981' }}>+{c.points}</td>
                <td style={{ color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>{c.leave || "—"}</td>
                <td style={{ textAlign: 'right', fontWeight: 700, color: '#f59e0b' }}>{c.equity.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
