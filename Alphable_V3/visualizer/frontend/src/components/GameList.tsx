import React from 'react';
import { GameListItem } from '../types';
import './GameList.css';

interface GameListProps {
  games: GameListItem[];
  loading: boolean;
  onSelectGame: (game: GameListItem) => void;
}

const GameList: React.FC<GameListProps> = ({ games, loading, onSelectGame }) => {
  if (loading) {
    return <div className="loading">Loading games...</div>;
  }

  if (games.length === 0) {
    return (
      <div className="no-games">
        <h2>No games found</h2>
        <p>Run some evaluation scripts to generate game replays!</p>
        <pre>python evaluate_vs_greedy.py</pre>
        <pre>python evaluate_vs_random.py</pre>
        <pre>python watch_bot.py</pre>
      </div>
    );
  }

  const groupedGames = games.reduce((acc, game) => {
    if (!acc[game.category]) {
      acc[game.category] = [];
    }
    acc[game.category].push(game);
    return acc;
  }, {} as Record<string, GameListItem[]>);

  return (
    <div className="game-list">
      <h2>📋 Available Games ({games.length})</h2>
      
      {Object.entries(groupedGames).map(([category, categoryGames]) => (
        <div key={category} className="game-category">
          <h3>{category.replace(/_/g, ' ').toUpperCase()}</h3>
          
          <div className="games-grid">
            {categoryGames.map((game) => (
              <div
                key={game.id}
                className="game-card"
                onClick={() => onSelectGame(game)}
              >
                <div className="game-card-header">
                  <span className="game-timestamp">
                    {new Date(game.timestamp).toLocaleString()}
                  </span>
                </div>
                
                <div className="game-card-players">
                  <div className="player">
                    <span className="player-name">{game.player_names[0]}</span>
                    <span className="player-score">{game.final_score[0]}</span>
                  </div>
                  <span className="vs">vs</span>
                  <div className="player">
                    <span className="player-name">{game.player_names[1]}</span>
                    <span className="player-score">{game.final_score[1]}</span>
                  </div>
                </div>
                
                <div className="game-card-meta">
                  <span>🎲 {game.total_turns} turns</span>
                  {game.metadata.checkpoint && (
                    <span>🔖 Ckpt {game.metadata.checkpoint}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default GameList;
