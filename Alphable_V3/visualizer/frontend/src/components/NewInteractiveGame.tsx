import React, { useState } from 'react';
import './NewInteractiveGame.css';

interface Props {
  onStart: (config: InteractiveGameConfig) => void;
  onCancel: () => void;
}

export interface InteractiveGameConfig {
  aiType: 'alphable' | 'random' | 'greedy';
  playerGoesFirst: boolean;
}

const NewInteractiveGame: React.FC<Props> = ({ onStart, onCancel }) => {
  const [aiType, setAiType] = useState<'alphable' | 'random' | 'greedy'>('alphable');
  const [playerGoesFirst, setPlayerGoesFirst] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart({ aiType, playerGoesFirst });
  };

  return (
    <div className="new-interactive-game">
      <h2>Start Interactive Game</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Opponent Type:</label>
          <select value={aiType} onChange={(e) => setAiType(e.target.value as any)}>
            <option value="alphable">Alphable (AI)</option>
            <option value="greedy">Greedy (Max Points)</option>
            <option value="random">Random</option>
          </select>
        </div>
        <div className="form-group">
          <label>Who goes first?</label>
          <select value={playerGoesFirst ? 'true' : 'false'} onChange={(e) => setPlayerGoesFirst(e.target.value === 'true')}>
            <option value="true">You</option>
            <option value="false">Opponent</option>
          </select>
        </div>
        <div className="form-actions">
          <button type="button" onClick={onCancel} className="btn-cancel">Cancel</button>
          <button type="submit" className="btn-start">Start Game</button>
        </div>
      </form>
    </div>
  );
};

export default NewInteractiveGame;
