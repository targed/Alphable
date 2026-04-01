import React, { useEffect, useState } from 'react';
import './PlayerHUD.css';

interface PlayerHUDProps {
  playerName: string;
  playerId: number;
  currentPlayer: number;
  score: number;
  rack: string[];
  lastScore?: number;
}

const PlayerHUD: React.FC<PlayerHUDProps> = ({
  playerName,
  playerId,
  currentPlayer,
  score,
  rack,
  lastScore
}) => {
  const [showScoreDelta, setShowScoreDelta] = useState(false);
  const isActive = currentPlayer === playerId;

  useEffect(() => {
    if (lastScore && lastScore > 0) {
      setShowScoreDelta(true);
      const timer = setTimeout(() => setShowScoreDelta(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [lastScore]);

  return (
    <div className={`player-hud ${isActive ? 'active' : ''}`}>
      <div className="player-header">
        <div className="player-avatar">
          {playerName[0].toUpperCase()}
        </div>
        <div className="player-info">
          <h3 className="player-name">{playerName}</h3>
          <div className="player-id">Player {playerId}</div>
        </div>
      </div>

      <div className="score-display">
        <div className="score-label">Score</div>
        <div className="score-value">{score}</div>
        {showScoreDelta && lastScore && lastScore > 0 && (
          <div className="score-delta">+{lastScore}</div>
        )}
      </div>

      <div className="rack-display">
        <div className="rack-label">Rack</div>
        <div className="rack-tiles">
          {rack.length > 0 ? (
            rack.map((tile, index) => (
              <div key={index} className="rack-tile">
                {tile}
              </div>
            ))
          ) : (
            <div className="rack-empty">Empty</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlayerHUD;
