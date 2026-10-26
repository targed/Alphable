import React from 'react';
import { TILE_POINTS } from './Board';

interface BagModalProps {
  bag: string[];
  onClose: () => void;
}

export const BagModal: React.FC<BagModalProps> = ({ bag, onClose }) => {
  const counts: Record<string, number> = {};
  for (const t of bag) {
    counts[t] = (counts[t] || 0) + 1;
  }

  const vowels = ['A', 'E', 'I', 'O', 'U'];
  const powerTiles = ['Q', 'Z', 'X', 'J', 'K'];
  const blanks = ['?'];

  const totalTiles = bag.length;
  const vowelCount = bag.filter(t => vowels.includes(t)).length;
  const consonantCount = bag.filter(t => !vowels.includes(t) && t !== '?').length;
  const blankCount = bag.filter(t => t === '?').length;

  const renderTileBadge = (letter: string) => {
    const count = counts[letter] || 0;
    const pts = TILE_POINTS[letter] ?? 0;
    return (
      <div
        key={letter}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '0.4rem 0.6rem',
          borderRadius: '4px',
          backgroundColor: count > 0 ? 'var(--bg-elevated)' : '#1a1612',
          border: count > 0 ? '1px solid var(--border-subtle)' : '1px solid #261f18',
          opacity: count > 0 ? 1 : 0.35,
          minWidth: '42px'
        }}
      >
        <span style={{ fontWeight: 800, fontSize: '1rem', color: count > 0 ? '#fef3c7' : 'var(--text-muted)' }}>
          {letter}
          <span style={{ fontSize: '0.6rem', color: '#b45309', marginLeft: '2px' }}>{pts}</span>
        </span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: count > 0 ? '#10b981' : 'var(--text-muted)' }}>
          ×{count}
        </span>
      </div>
    );
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fef3c7' }}>Tile Bag Inventory</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {totalTiles} tiles remaining in bag • V/C Ratio: {consonantCount > 0 ? (vowelCount / consonantCount).toFixed(2) : "N/A"}
            </p>
          </div>
          <button className="btn-secondary" onClick={onClose} style={{ padding: '0.3rem 0.7rem' }}>Close</button>
        </div>

        {/* Overview Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <div className="panel-card" style={{ padding: '0.75rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Vowels</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8' }}>{vowelCount}</div>
          </div>
          <div className="panel-card" style={{ padding: '0.75rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Consonants</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fb923c' }}>{consonantCount}</div>
          </div>
          <div className="panel-card" style={{ padding: '0.75rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Blanks</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#a78bfa' }}>{blankCount}</div>
          </div>
        </div>

        {/* Section: Vowels */}
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>VOWELS</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {vowels.map(renderTileBadge)}
          </div>
        </div>

        {/* Section: High Value & Power Tiles */}
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>POWER TILES & BLANKS</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {[...powerTiles, ...blanks].map(renderTileBadge)}
          </div>
        </div>

        {/* Section: All Consonants */}
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>OTHER CONSONANTS</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {['B', 'C', 'D', 'F', 'G', 'H', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Y'].map(renderTileBadge)}
          </div>
        </div>
      </div>
    </div>
  );
};
