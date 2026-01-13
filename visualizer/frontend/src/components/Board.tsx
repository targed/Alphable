import React from 'react';
import { BoardSquare } from '../types';
import './Board.css';

interface BoardProps {
  board: BoardSquare[][];
}

const COLUMNS = 'ABCDEFGHIJKLMNO'.split('');

const Board: React.FC<BoardProps> = ({ board }) => {
  return (
    <div className="board-container">
      <div className="board-grid">
        {/* Column headers */}
        <div className="board-header corner"></div>
        {COLUMNS.map((col) => (
          <div key={col} className="board-header col-header">
            {col}
          </div>
        ))}

        {/* Board rows */}
        {board.map((row, rowIndex) => (
          <React.Fragment key={rowIndex}>
            {/* Row number */}
            <div className="board-header row-header">{rowIndex + 1}</div>
            
            {/* Row cells */}
            {row.map((square, colIndex) => {
              const premiumClass = square.premium ? `premium-${square.premium.toLowerCase()}` : '';
              const newTileClass = square.isNew ? 'new-tile' : '';
              const hasLetterClass = square.letter ? 'has-letter' : '';
              
              return (
                <div
                  key={`${rowIndex}-${colIndex}`}
                  className={`board-square ${premiumClass} ${newTileClass} ${hasLetterClass}`}
                >
                  {square.letter ? (
                    <div className="tile">
                      <span className="tile-letter">{square.letter}</span>
                    </div>
                  ) : square.premium ? (
                    <span className="premium-label">{square.premium}</span>
                  ) : null}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default Board;
