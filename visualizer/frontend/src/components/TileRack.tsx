import React from 'react';
import { TILE_POINTS } from './Board';

interface TileRackProps {
  rack: string[];
  selectedIndices?: number[];
  onTileClick?: (index: number) => void;
  onShuffle?: () => void;
}

export const TileRack: React.FC<TileRackProps> = ({
  rack,
  selectedIndices = [],
  onTileClick,
  onShuffle
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem' }}>
      <div className="rack-container">
        {rack.map((tile, i) => {
          const letter = tile ? tile.toUpperCase() : '';
          const pts = TILE_POINTS[letter] ?? 0;
          const isSelected = selectedIndices.includes(i);

          return (
            <div
              key={i}
              className={`scrabble-tile rack-tile ${isSelected ? 'tile-highlight' : ''}`}
              onClick={() => onTileClick && onTileClick(i)}
              style={{
                outline: isSelected ? '2px solid #38bdf8' : 'none',
                transform: isSelected ? 'translateY(-6px)' : 'none'
              }}
            >
              <span>{letter}</span>
              <span className="tile-subscript">{pts}</span>
            </div>
          );
        })}
      </div>
      {onShuffle && (
        <button
          className="btn-secondary"
          onClick={onShuffle}
          style={{ padding: '0.3rem 0.8rem', fontSize: '0.8rem' }}
        >
          Shuffle Rack
        </button>
      )}
    </div>
  );
};
