import React from 'react';
import { BoardState } from '../types';

export const TILE_POINTS: Record<string, number> = {
  A: 1, B: 3, C: 3, D: 2, E: 1, F: 4, G: 2, H: 4, I: 1, J: 8,
  K: 5, L: 1, M: 3, N: 1, O: 1, P: 3, Q: 10, R: 1, S: 1, T: 1,
  U: 1, V: 4, W: 4, X: 8, Y: 4, Z: 10, '?': 0
};

interface BoardProps {
  board: BoardState;
  highlightCells?: Array<[number, number]>;
  onCellClick?: (row: number, col: number) => void;
}

export const getPremiumType = (row: number, col: number): string => {
  if (row === 7 && col === 7) return 'star';

  const tw = [
    [0, 0], [0, 7], [0, 14],
    [7, 0], [7, 14],
    [14, 0], [14, 7], [14, 14]
  ];
  if (tw.some(([r, c]) => r === row && c === col)) return 'tw';

  const dw = [
    [1, 1], [2, 2], [3, 3], [4, 4],
    [1, 13], [2, 12], [3, 11], [4, 10],
    [13, 1], [12, 2], [11, 3], [10, 4],
    [13, 13], [12, 12], [11, 11], [10, 10]
  ];
  if (dw.some(([r, c]) => r === row && c === col)) return 'dw';

  const tl = [
    [1, 5], [1, 9],
    [5, 1], [5, 5], [5, 9], [5, 13],
    [9, 1], [9, 5], [9, 9], [9, 13],
    [13, 5], [13, 9]
  ];
  if (tl.some(([r, c]) => r === row && c === col)) return 'tl';

  const dl = [
    [0, 3], [0, 11],
    [2, 6], [2, 8],
    [3, 0], [3, 7], [3, 14],
    [6, 2], [6, 6], [6, 8], [6, 12],
    [7, 3], [7, 11],
    [8, 2], [8, 6], [8, 8], [8, 12],
    [11, 0], [11, 7], [11, 14],
    [12, 6], [12, 8],
    [14, 3], [14, 11]
  ];
  if (dl.some(([r, c]) => r === row && c === col)) return 'dl';

  return 'none';
};

export const Board: React.FC<BoardProps> = ({ board, highlightCells = [], onCellClick }) => {
  const isHighlighted = (r: number, c: number) => {
    return highlightCells.some(([hr, hc]) => hr === r && hc === c);
  };

  return (
    <div className="board-wrapper">
      <div className="board-grid">
        {board.map((rowArr, r) =>
          rowArr.map((cell, c) => {
            const premium = getPremiumType(r, c);
            const highlighted = isHighlighted(r, c);

            let premiumClass = '';
            let label = '';
            if (premium === 'tw') { premiumClass = 'premium-tw'; label = '3W'; }
            else if (premium === 'dw') { premiumClass = 'premium-dw'; label = '2W'; }
            else if (premium === 'tl') { premiumClass = 'premium-tl'; label = '3L'; }
            else if (premium === 'dl') { premiumClass = 'premium-dl'; label = '2L'; }
            else if (premium === 'star') { premiumClass = 'premium-star'; label = '2W'; }

            const hasTile = cell && cell !== '.' && cell !== '';
            const letter = hasTile ? cell.toUpperCase() : '';
            const points = hasTile ? (TILE_POINTS[letter] ?? 0) : null;

            return (
              <div
                key={`${r}-${c}`}
                className={`board-cell ${premiumClass}`}
                onClick={() => onCellClick && onCellClick(r, c)}
                title={`Row ${r+1}, Col ${chrCol(c)}`}
              >
                {hasTile ? (
                  <div className={`scrabble-tile ${highlighted ? 'tile-highlight' : ''}`}>
                    <span>{letter}</span>
                    {points !== null && <span className="tile-subscript">{points}</span>}
                  </div>
                ) : (
                  label && <span className="premium-label">{label}</span>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

const chrCol = (c: number): string => String.fromCharCode(65 + c);
