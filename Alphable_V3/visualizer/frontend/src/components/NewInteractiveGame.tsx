import React, { useState, useEffect } from 'react';
import './NewInteractiveGame.css';
import { API_URL } from '../config';
import { ModelItem } from '../types';

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
  model?: string;
  valueWeight?: number;
}

const NewInteractiveGame: React.FC<Props> = ({ onStart, onCancel }) => {
  const [p1Type, setP1Type] = useState<PlayerType>('human');
  const [p2Type, setP2Type] = useState<PlayerType>('alphable');
  const [autoPlayAI, setAutoPlayAI] = useState(true);
  const [dictionary, setDictionary] = useState('CSW24.txt');
  const [model, setModel] = useState<string>('');
  const [valueWeight, setValueWeight] = useState<number>(60.0);
  const [availableDicts, setAvailableDicts] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<ModelItem[]>([]);

  useEffect(() => {
    // Fetch dictionaries
    fetch(`${API_URL}/dictionaries`)
      .then(res => res.json())
      .then(data => {
        if (data.dictionaries && data.dictionaries.length > 0) {
          setAvailableDicts(data.dictionaries);
          setDictionary(data.dictionaries[0]);
        }
      })
      .catch(err => console.error("Failed to load dictionaries", err));

    // Fetch models
    fetch(`${API_URL}/models`)
      .then(res => res.json())
      .then(data => {
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          setModel(data.default || data.models[0].name);
        }
      })
      .catch(err => console.error("Failed to load models", err));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart({ p1Type, p2Type, autoPlayAI, dictionary, model, valueWeight });
  };

  const isAnyAIAlphable = p1Type === 'alphable' || p2Type === 'alphable';

  return (
    <div className="new-interactive-game">
      <h2>Start Interactive Game</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Player 1 (Goes First):</label>
          <select value={p1Type} onChange={(e) => setP1Type(e.target.value as PlayerType)}>
            <option value="human">Human</option>
            <option value="alphable">Alphable (AI Neural Engine)</option>
            <option value="greedy">Greedy Bot</option>
            <option value="random">Random Bot</option>
          </select>
        </div>
        <div className="form-group">
          <label>Player 2:</label>
          <select value={p2Type} onChange={(e) => setP2Type(e.target.value as PlayerType)}>
            <option value="human">Human</option>
            <option value="alphable">Alphable (AI Neural Engine)</option>
            <option value="greedy">Greedy Bot</option>
            <option value="random">Random Bot</option>
          </select>
        </div>

        {isAnyAIAlphable && (
          <>
            <div className="form-group">
              <label>AI Neural Model Checkpoint:</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {availableModels.length > 0 ? (
                  availableModels.map(m => (
                    <option key={m.name} value={m.name}>
                      {m.name} ({m.size_mb} MB)
                    </option>
                  ))
                ) : (
                  <option value="">Default Checkpoint</option>
                )}
              </select>
            </div>
            <div className="form-group">
              <label>AI Value Weight Multiplier (W = {valueWeight}):</label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={valueWeight}
                onChange={(e) => setValueWeight(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
              <span style={{ fontSize: '0.8rem', color: '#666' }}>
                Recommended: 60.0 (calibrated for balanced leave & blank preservation)
              </span>
            </div>
          </>
        )}

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
