import React from 'react';

interface PlayerHUDProps {
  p1Name: string;
  p2Name: string;
  p1Score: number;
  p2Score: number;
  p1Bingos?: number;
  p2Bingos?: number;
  bagCount: number;
  activePlayer: number; // 0 or 1
  scoreDelta?: { player: number; delta: number } | null;
  onOpenBag?: () => void;
}

export const PlayerHUD: React.FC<PlayerHUDProps> = ({
  p1Name,
  p2Name,
  p1Score,
  p2Score,
  p1Bingos = 0,
  p2Bingos = 0,
  bagCount,
  activePlayer,
  scoreDelta,
  onOpenBag,
}) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1.25rem', alignItems: 'center', marginBottom: '1.25rem' }}>
      {/* Player 1 Card */}
      <div
        className="panel-card"
        style={{
          borderLeft: activePlayer === 0 ? '4px solid #3b82f6' : '1px solid var(--border-subtle)',
          backgroundColor: activePlayer === 0 ? 'var(--bg-elevated)' : 'var(--bg-surface)',
          transition: 'all 0.2s ease'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Player 1 {activePlayer === 0 && <span style={{ color: '#60a5fa', fontWeight: 800 }}>• ACTIVE</span>}
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fef3c7' }}>{p1Name}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '2.1rem', fontWeight: 800, color: '#38bdf8' }}>{p1Score}</div>
            {scoreDelta && scoreDelta.player === 0 && (
              <div style={{ color: '#10b981', fontWeight: 700, fontSize: '0.85rem' }}>+{scoreDelta.delta}</div>
            )}
          </div>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
          Bingos: {p1Bingos}
        </div>
      </div>

      {/* Center Bag & Differential Pill */}
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '0.3rem', alignItems: 'center' }}>
        <button
          onClick={onOpenBag}
          style={{
            backgroundColor: 'var(--bg-deep)',
            padding: '0.4rem 1rem',
            borderRadius: '9999px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            cursor: onOpenBag ? 'pointer' : 'default',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            transition: 'border-color 0.15s ease'
          }}
          title="Click to view remaining bag tiles"
        >
          <span>Bag:</span>
          <span style={{ color: '#f59e0b', fontWeight: 800 }}>{bagCount}</span>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>[inspect]</span>
        </button>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Spread: {Math.abs(p1Score - p2Score)} pts {p1Score > p2Score ? '(P1 leads)' : (p2Score > p1Score ? '(P2 leads)' : '(Tied)')}
        </div>
      </div>

      {/* Player 2 Card */}
      <div
        className="panel-card"
        style={{
          borderRight: activePlayer === 1 ? '4px solid #8b5cf6' : '1px solid var(--border-subtle)',
          backgroundColor: activePlayer === 1 ? 'var(--bg-elevated)' : 'var(--bg-surface)',
          transition: 'all 0.2s ease'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Player 2 {activePlayer === 1 && <span style={{ color: '#c084fc', fontWeight: 800 }}>• ACTIVE</span>}
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fef3c7' }}>{p2Name}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '2.1rem', fontWeight: 800, color: '#c084fc' }}>{p2Score}</div>
            {scoreDelta && scoreDelta.player === 1 && (
              <div style={{ color: '#10b981', fontWeight: 700, fontSize: '0.85rem' }}>+{scoreDelta.delta}</div>
            )}
          </div>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
          Bingos: {p2Bingos}
        </div>
      </div>
    </div>
  );
};
