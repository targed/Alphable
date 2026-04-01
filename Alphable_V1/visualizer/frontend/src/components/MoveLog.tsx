import React, { useRef, useEffect } from 'react';
import { GameTurn } from '../types';
import './MoveLog.css';

interface MoveLogProps {
  turns: GameTurn[];
  currentTurnIndex: number;
  onSelectTurn: (index: number) => void;
}

const MoveLog: React.FC<MoveLogProps> = ({ turns, currentTurnIndex, onSelectTurn }) => {
  const currentTurnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    currentTurnRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [currentTurnIndex]);

  const formatMove = (turn: GameTurn): string => {
    if (turn.action_type === 'PASS') return 'PASS';
    if (turn.action_type === 'EXCHANGE') return 'EXCHANGE';
    
    if (turn.word && turn.position) {
      const [row, col] = turn.position;
      const colLetter = 'ABCDEFGHIJKLMNO'[col];
      const dir = turn.direction === 'Across' ? '→' : '↓';
      return `${row + 1}${colLetter} ${dir} ${turn.word}`;
    }
    
    return 'MOVE';
  };

  return (
    <div className="move-log">
      <h3>📜 Move Log</h3>
      <div className="move-list">
        {turns.map((turn, index) => (
          <div
            key={index}
            ref={index === currentTurnIndex ? currentTurnRef : null}
            className={`move-item ${index === currentTurnIndex ? 'current' : ''} player-${turn.player}`}
            onClick={() => onSelectTurn(index)}
          >
            <div className="move-number">{index + 1}</div>
            <div className="move-player">P{turn.player}</div>
            <div className="move-details">{formatMove(turn)}</div>
            <div className="move-score">{turn.score > 0 ? `+${turn.score}` : turn.score}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MoveLog;
