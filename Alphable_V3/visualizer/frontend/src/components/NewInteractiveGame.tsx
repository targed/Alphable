import React, { useState, useEffect } from 'react';
import './NewInteractiveGame.css';

interface Props {
  onStart: (config: InteractiveGameConfig) => void;
  onCancel: () => void;
}

export type PlayerType = 'human' | 'alphable' | 'random' | 'greedy';

export interface InteractiveGameConfig {
  p1Type: PlayerType;
  p2Type: PlayerType;
  autoPlayAI: boolean;
  dictionary: string;
}

const API_URL = 'http://localhost:5000/api';

const NewInteractiveGame: React.FC<Props> = ({ onStart, onCancel }) => {
  const [p1Type, setP1Type] = useState<PlayerType>('human');
  const [p2Type, setP2Type] = useState<PlayerType>('alphable');
  const [autoPlayAI, setAutoPlayAI] = useState(true);
  const [dictionary, setDictionary] = useState('CSW24.txt');
  const [availableDicts, setAvailableDicts] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/dictionaries`)
      .then(res => res.json())
      .then(data => {
        if (data.dictionaries && data.dictionaries.length > 0) {
          setAvailableDicts(data.dictionaries);
          setDictionary(data.dictionaries[0]);
        }
      })
      .catch(err => console.error("Failed to load dictionaries", err));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart({ p1Type, p2Type, autoPlayAI, dictionary });
  };

  return (
    <div className="new-interactive-game">
      <h2>Start Interactive Game</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Player 1 (Goes First):</label>
          <select value={p1Type} onChange={(e) => setP1Type(e.target.value as PlayerType)}>
            <option value="human">Human</option>
            <option value="alphable">Alphable (AI)</option>
            <option value="greedy">Greedy Bot</option>
            <option value="random">Random Bot</option>
          </select>
        </div>
        <div className="form-group">
          <label>Player 2:</label>
          <select value={p2Type} onChange={(e) => setP2Type(e.target.value as PlayerType)}>
            <option value="human">Human</option>
            <option value="alphable">Alphable (AI)</option>
            <option value="greedy">Greedy Bot</option>
            <option value="random">Random Bot</option>
          </select>
        </div>
        <div className="form-group">
          <label>Dictionary:</label>
          <select value={dictionary} onChange={(e) => setDictionary(e.target.value)}>
            {availableDicts.length > 0 ? (
                availableDicts.map(d => <option key={d} value={d}>{d}</option>)
            ) : (
                <option value="CSW24.txt">CSW24.txt</option>
            )}
          </select>
        </div>
        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="checkbox"
            id="autoplay"
            checked={autoPlayAI}
            onChange={(e) => setAutoPlayAI(e.target.checked)}
          />
          <label htmlFor="autoplay" style={{ margin: 0, fontWeight: 'normal' }}>
            Auto-play AI turns (Uncheck to intercept and change racks before AI plays)
          </label>
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
