import React from 'react';
import { EngineStats, CandidateMove } from '../types';

interface EngineStatsViewProps {
  stats: EngineStats | null;
  currentCandidates?: CandidateMove[];
  onSelectWord?: (word: string) => void;
}

export const EngineStatsView: React.FC<EngineStatsViewProps> = ({
  stats,
  currentCandidates = [],
  onSelectWord,
}) => {
  if (!stats) {
    return (
      <div className="panel-card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
          No Active Engine Thoughts
        </div>
        <div style={{ fontSize: '0.8rem' }}>
          Step an AI turn or enable auto-play to view real-time search thoughts, Bayesian belief samples, and rollout evaluations.
        </div>
      </div>
    );
  }

  const formatMethod = (method: string) => {
    switch (method) {
      case 'bams_mc_rollout_2ply':
        return 'BAMS Monte Carlo Rollout (2-Ply Nested)';
      case 'bams_mc_rollout':
        return 'BAMS Monte Carlo Rollout (1-Ply)';
      case 'deterministic_endgame':
        return 'Exact Deterministic Endgame Solver';
      case 'classical_klv':
        return 'Classical KLV Static Leave Equity';
      case 'greedy_score':
        return 'Greedy Immediate Score Maximizer';
      default:
        return method.replace(/_/g, ' ').toUpperCase();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Top Architecture & Execution Metrics */}
      <div
        className="panel-card"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '0.75rem',
          padding: '1rem'
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Method</span>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#38bdf8' }}>
            {formatMethod(stats.method)}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Latency</span>
          <span style={{
            fontSize: '0.85rem',
            fontWeight: 800,
            color: stats.latency_ms < 100 ? '#10b981' : (stats.latency_ms < 500 ? '#f59e0b' : '#ef4444')
          }}>
            {stats.latency_ms} ms
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Game Stage</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c084fc' }}>
            {stats.stage || 'Midgame'}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Evaluated</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {stats.num_candidates_evaluated} candidates
          </span>
        </div>

        {stats.num_samples !== undefined && stats.num_samples > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Belief Samples</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f59e0b' }}>
              N = {stats.num_samples} racks
            </span>
          </div>
        )}

        {stats.volatility_used !== undefined && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Volatility Control</span>
            <span style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              color: stats.volatility_used ? '#10b981' : 'var(--text-muted)'
            }}>
              {stats.volatility_used ? 'Active' : 'Off'}
            </span>
          </div>
        )}
      </div>

      {/* Equity Differential Summary (BAMS vs Static KLV) */}
      {(stats.best_bams_score !== undefined || stats.static_equity !== undefined) && (
        <div
          className="panel-card"
          style={{
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-around',
            backgroundColor: 'var(--bg-deep)'
          }}
        >
          {stats.best_bams_score !== undefined && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>BAMS Search Score</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#10b981' }}>
                {stats.best_bams_score.toFixed(2)}
              </div>
            </div>
          )}

          {stats.static_equity !== undefined && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Static KLV Equity</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#38bdf8' }}>
                {stats.static_equity.toFixed(2)}
              </div>
            </div>
          )}

          {stats.best_bams_score !== undefined && stats.static_equity !== undefined && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Search Delta</div>
              <div style={{
                fontSize: '1.25rem',
                fontWeight: 900,
                color: (stats.best_bams_score - stats.static_equity) >= 0 ? '#34d399' : '#f87171'
              }}>
                {(stats.best_bams_score - stats.static_equity) >= 0 ? '+' : ''}
                {(stats.best_bams_score - stats.static_equity).toFixed(2)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bayesian Opponent Belief Samples */}
      {stats.sampled_racks && stats.sampled_racks.length > 0 && (
        <div className="panel-card" style={{ padding: '1rem' }}>
          <div className="panel-title" style={{ marginBottom: '0.6rem' }}>
            <span>Bayesian Opponent Rack Samples (Belief Net)</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{stats.sampled_racks.length} simulated pools</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.5rem' }}>
            {stats.sampled_racks.map((rackStr, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem',
                  padding: '0.4rem 0.6rem',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)'
                }}
              >
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '0.2rem' }}>#{idx + 1}</span>
                {rackStr.split('').map((char, cIdx) => (
                  <span
                    key={cIdx}
                    style={{
                      display: 'inline-block',
                      width: '18px',
                      height: '20px',
                      lineHeight: '20px',
                      textAlign: 'center',
                      borderRadius: '2px',
                      backgroundColor: 'var(--bg-deep)',
                      color: char === '?' ? '#94a3b8' : '#fef08a',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.75rem'
                    }}
                  >
                    {char}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Rollout Evaluations Breakdown */}
      {stats.evaluations && stats.evaluations.length > 0 && (
        <div className="panel-card" style={{ padding: '1rem', overflowX: 'auto' }}>
          <div className="panel-title" style={{ marginBottom: '0.6rem' }}>
            <span>Deep Search Evaluation Breakdown</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Top candidate rollouts</span>
          </div>

          <table className="candidate-table" style={{ fontSize: '0.78rem' }}>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Move</th>
                <th>Coord</th>
                <th style={{ textAlign: 'right' }}>Immediate</th>
                <th style={{ textAlign: 'right' }}>Opp Threat</th>
                <th style={{ textAlign: 'right' }}>2-Ply Net</th>
                <th style={{ textAlign: 'right' }}>Value Net</th>
                <th style={{ textAlign: 'right' }}>BAMS Score</th>
              </tr>
            </thead>
            <tbody>
              {stats.evaluations.map((ev, idx) => (
                <tr
                  key={idx}
                  style={{
                    backgroundColor: idx === 0 ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                    fontWeight: idx === 0 ? 700 : 400
                  }}
                >
                  <td style={{ color: idx === 0 ? '#38bdf8' : 'var(--text-muted)' }}>
                    #{idx + 1} {idx === 0 && <span style={{ fontSize: '0.65rem', color: '#10b981' }}>BEST</span>}
                  </td>
                  <td
                    onClick={() => onSelectWord && onSelectWord(ev.word)}
                    style={{
                      cursor: 'pointer',
                      color: '#60a5fa',
                      fontWeight: 700
                    }}
                    title="Click to inspect word definition"
                  >
                    {ev.word || 'PASS'}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {ev.row !== undefined && ev.col !== undefined ? `${ev.direction?.charAt(0) || 'A'} ${ev.row},${ev.col}` : '-'}
                  </td>
                  <td style={{ textAlign: 'right', color: '#f59e0b', fontWeight: 600 }}>
                    +{ev.score}
                  </td>
                  <td style={{ textAlign: 'right', color: '#f87171' }}>
                    {ev.opp_reply_mean !== undefined ? `-${ev.opp_reply_mean}` : '-'}
                  </td>
                  <td style={{ textAlign: 'right', color: (ev.mean_2ply_net ?? 0) >= 0 ? '#34d399' : '#f87171' }}>
                    {ev.mean_2ply_net !== undefined ? `${(ev.mean_2ply_net ?? 0) >= 0 ? '+' : ''}${ev.mean_2ply_net}` : '-'}
                  </td>
                  <td style={{ textAlign: 'right', color: '#c084fc' }}>
                    {ev.value_net_mean !== undefined ? ev.value_net_mean : '-'}
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 800, color: idx === 0 ? '#10b981' : 'var(--text-primary)' }}>
                    {ev.bams_score !== undefined ? ev.bams_score : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
