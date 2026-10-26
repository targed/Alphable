import React, { useState } from 'react';
import { TournamentSummary } from '../types';

interface TournamentModalProps {
  tournament: TournamentSummary | null;
  onClose: () => void;
}

export const TournamentModal: React.FC<TournamentModalProps> = ({ tournament, onClose }) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  if (!tournament) return null;

  const {
    run_id,
    mode,
    tag,
    lexicon,
    total_games,
    duplicate_pairs,
    duration_seconds,
    seconds_per_game,
    player1,
    player2,
    draws,
    win_rate,
    net_spread,
    significance,
    notes,
    details = []
  } = tournament;

  const p1Wins = player1.wins;
  const p2Wins = player2.wins;
  const p1WinPct = ((p1Wins / total_games) * 100).toFixed(1);
  const p2WinPct = ((p2Wins / total_games) * 100).toFixed(1);

  // Compute distribution buckets for net score spread if details are present
  const buckets = [
    { label: '< -60', count: 0, min: -Infinity, max: -60 },
    { label: '-60 to -30', count: 0, min: -60, max: -30 },
    { label: '-30 to -10', count: 0, min: -30, max: -10 },
    { label: '-10 to 0', count: 0, min: -10, max: 0 },
    { label: '0 to +10', count: 0, min: 0, max: 10 },
    { label: '+10 to +30', count: 0, min: 10, max: 30 },
    { label: '+30 to +60', count: 0, min: 30, max: 60 },
    { label: '> +60', count: 0, min: 60, max: Infinity },
  ];

  if (details && details.length > 0) {
    details.forEach(d => {
      const spread = d.net_spread;
      for (const b of buckets) {
        if (spread >= b.min && spread < b.max) {
          b.count++;
          break;
        }
      }
    });
  }

  const maxBucketCount = Math.max(1, ...buckets.map(b => b.count));

  // Filter pairs if details are present
  const filteredDetails = (details || []).filter(d => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      d.pair.toString().includes(q) ||
      d.verdict.toLowerCase().includes(q) ||
      d.net_spread.toString().includes(q)
    );
  });

  const totalPages = Math.ceil(filteredDetails.length / pageSize);
  const currentPairSlice = filteredDetails.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(6px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem'
      }}
      onClick={onClose}
    >
      <div
        className="panel-card"
        style={{
          width: '100%',
          maxWidth: '920px',
          maxHeight: '90vh',
          overflowY: 'auto',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          padding: '1.75rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 900, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
                TOURNAMENT ANALYTICS
              </span>
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'rgba(245, 158, 11, 0.15)',
                color: '#f59e0b',
                border: '1px solid rgba(245, 158, 11, 0.3)'
              }}>
                {mode.toUpperCase()}
              </span>
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-elevated)',
                color: '#38bdf8',
                border: '1px solid var(--border-subtle)'
              }}>
                {lexicon}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
              Run ID: <strong style={{ color: 'var(--text-secondary)' }}>{run_id}</strong> &bull; {tag || 'Tournament Series'} &bull; {total_games.toLocaleString()} Games ({duplicate_pairs ? `${duplicate_pairs.toLocaleString()} Pairs` : 'Standard'})
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '1.25rem',
              fontWeight: 700,
              padding: '0.2rem 0.6rem'
            }}
            title="Close"
          >
            x
          </button>
        </div>

        {/* Head-to-Head Hero Matchup Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', alignItems: 'center' }}>
          {/* Player 1 Card */}
          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-deep)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem'
            }}
          >
            <div style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase' }}>
              Champion (Player 1)
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {player1.name}
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#60a5fa', marginTop: '0.2rem' }}>
              {p1Wins.toLocaleString()} <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Wins ({p1WinPct}%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
              <span>Mean Score: <strong style={{ color: 'white' }}>{player1.mean_score}</strong></span>
              <span>Bingos/G: <strong style={{ color: '#10b981' }}>{player1.bingos_per_game}</strong></span>
            </div>
          </div>

          {/* VS Divider */}
          <div style={{ textAlign: 'center', padding: '0 0.5rem' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--text-muted)' }}>VS</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {draws} Draws
            </div>
          </div>

          {/* Player 2 Card */}
          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-deep)',
              border: '1px solid rgba(192, 132, 252, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem'
            }}
          >
            <div style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: 700, textTransform: 'uppercase' }}>
              Opponent (Player 2)
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {player2.name}
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#c084fc', marginTop: '0.2rem' }}>
              {p2Wins.toLocaleString()} <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Wins ({p2WinPct}%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
              <span>Mean Score: <strong style={{ color: 'white' }}>{player2.mean_score}</strong></span>
              <span>Bingos/G: <strong style={{ color: '#10b981' }}>{player2.bingos_per_game}</strong></span>
            </div>
          </div>
        </div>

        {/* Win Rate & Confidence Interval Bar */}
        <div className="panel-card" style={{ padding: '1.25rem', backgroundColor: 'var(--bg-deep)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <span style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-primary)' }}>
                WIN RATE WITH 95% CONFIDENCE INTERVAL
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                (Null hypothesis parity at 50.0%)
              </span>
            </div>
            <span style={{ fontSize: '1.15rem', fontWeight: 900, color: win_rate.percentage >= 50 ? '#10b981' : '#f87171' }}>
              {win_rate.percentage}% {win_rate.ci95 ? `± ${win_rate.ci95}%` : ''}
            </span>
          </div>

          {/* Visual Gauge Track */}
          <div style={{ position: 'relative', height: '24px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px', overflow: 'hidden' }}>
            {/* 50% Marker Line */}
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: 0,
                bottom: 0,
                width: '2px',
                backgroundColor: 'rgba(255, 255, 255, 0.4)',
                zIndex: 3
              }}
              title="50% Parity Baseline"
            />

            {/* Win Rate Bar */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: `${Math.min(100, Math.max(0, win_rate.percentage))}%`,
                backgroundColor: '#3b82f6',
                zIndex: 1
              }}
            />

            {/* 95% Confidence Interval Band */}
            {win_rate.ci_lower !== undefined && win_rate.ci_upper !== undefined && (
              <div
                style={{
                  position: 'absolute',
                  left: `${Math.max(0, win_rate.ci_lower)}%`,
                  width: `${Math.min(100, win_rate.ci_upper) - Math.max(0, win_rate.ci_lower)}%`,
                  top: 0,
                  bottom: 0,
                  backgroundColor: 'rgba(16, 185, 129, 0.45)',
                  borderLeft: '2px solid #10b981',
                  borderRight: '2px solid #10b981',
                  zIndex: 2
                }}
                title={`95% CI Band: [${win_rate.ci_lower}% - ${win_rate.ci_upper}%]`}
              />
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
            <span>40%</span>
            <span>45%</span>
            <span style={{ color: 'white', fontWeight: 700 }}>50% Parity</span>
            <span>55%</span>
            <span>60%</span>
          </div>
        </div>

        {/* Statistical Hypothesis & Significance Card */}
        {significance && (
          <div
            className="panel-card"
            style={{
              padding: '1.25rem',
              backgroundColor: 'var(--bg-deep)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-primary)' }}>
                STATISTICAL SIGNIFICANCE (HYPOTHESIS TEST)
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  padding: '0.25rem 0.65rem',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                  color: '#10b981',
                  border: '1px solid #10b981'
                }}
              >
                {significance.verdict}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Student t-statistic</span>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#38bdf8' }}>
                  t = {significance.t_statistic.toFixed(2)}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Two-Tailed p-value</span>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: significance.p_value < 0.01 ? '#10b981' : '#f59e0b' }}>
                  {significance.p_value === 0 ? 'p < 0.0001 (Zero)' : `p = ${significance.p_value.toFixed(4)}`}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Tested Hypothesis</span>
                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  {significance.hypothesis}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Net Point Spread</span>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: net_spread.mean >= 0 ? '#10b981' : '#f87171' }}>
                  +{net_spread.mean.toFixed(1)} pts {net_spread.ci95 ? `± ${net_spread.ci95.toFixed(1)}` : ''}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Spread Histogram Visualizer (When details exist) */}
        {details && details.length > 0 && (
          <div className="panel-card" style={{ padding: '1.25rem', backgroundColor: 'var(--bg-deep)' }}>
            <div className="panel-title" style={{ marginBottom: '0.75rem' }}>
              <span>Duplicate Match Score Margin Distribution</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{details.length} duplicate pairs</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end', height: '140px', gap: '0.5rem', padding: '0.5rem 0' }}>
              {buckets.map((b, idx) => {
                const heightPct = Math.max(4, (b.count / maxBucketCount) * 100);
                const isPositive = idx >= 4;
                return (
                  <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                      {b.count}
                    </span>
                    <div
                      style={{
                        width: '100%',
                        height: `${heightPct}%`,
                        backgroundColor: isPositive ? '#10b981' : '#ef4444',
                        borderRadius: '3px 3px 0 0',
                        opacity: 0.85
                      }}
                      title={`${b.label}: ${b.count} matches`}
                    />
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '0.3rem', whiteSpace: 'nowrap' }}>
                      {b.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Duplicate Match Breakdown Table (if details exist) */}
        {details && details.length > 0 && (
          <div className="panel-card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div className="panel-title" style={{ margin: 0 }}>
                <span>Duplicate Pair Matches ({filteredDetails.length})</span>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Filter pairs (e.g. WON, seed)"
                  value={filterQuery}
                  onChange={(e) => { setFilterQuery(e.target.value); setPage(0); }}
                  style={{
                    padding: '0.35rem 0.6rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'var(--bg-deep)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '4px',
                    color: 'white'
                  }}
                />

                <div style={{ display: 'flex', gap: '0.2rem' }}>
                  <button
                    className="btn-secondary"
                    disabled={page === 0}
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                  >
                    &lt;
                  </button>
                  <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.4rem', color: 'var(--text-muted)' }}>
                    {page + 1}/{totalPages || 1}
                  </span>
                  <button
                    className="btn-secondary"
                    disabled={page >= totalPages - 1}
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                  >
                    &gt;
                  </button>
                </div>
              </div>
            </div>

            <table className="candidate-table" style={{ fontSize: '0.75rem' }}>
              <thead>
                <tr>
                  <th>Pair #</th>
                  <th>Seed</th>
                  <th>{player1.short_name} (A + B = Total)</th>
                  <th>{player2.short_name} (A + B = Total)</th>
                  <th style={{ textAlign: 'right' }}>Net Spread</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {currentPairSlice.map(d => (
                  <tr key={d.pair}>
                    <td style={{ color: 'var(--text-muted)' }}>#{d.pair}</td>
                    <td style={{ fontFamily: 'monospace' }}>{d.seed}</td>
                    <td style={{ color: '#60a5fa', fontWeight: 600 }}>
                      {d.p1_gameA_score} + {d.p1_gameB_score} = <strong>{d.p1_pair_total}</strong>
                    </td>
                    <td style={{ color: '#c084fc', fontWeight: 600 }}>
                      {d.p2_gameA_score} + {d.p2_gameB_score} = <strong>{d.p2_pair_total}</strong>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: d.net_spread >= 0 ? '#10b981' : '#f87171' }}>
                      {d.net_spread >= 0 ? '+' : ''}{d.net_spread}
                    </td>
                    <td style={{ fontWeight: 600, color: d.verdict.includes('WON') ? '#34d399' : '#94a3b8' }}>
                      {d.verdict}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Notes */}
        {notes && (
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.4', backgroundColor: 'var(--bg-deep)', padding: '0.75rem', borderRadius: '6px' }}>
            <strong>Tournament Summary:</strong> {notes}
          </div>
        )}
      </div>
    </div>
  );
};
