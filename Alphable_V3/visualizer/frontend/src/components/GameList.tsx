import React, { useState, useMemo } from 'react';
import { GameListItem } from '../types';
import './GameList.css';

interface GameListProps {
  games: GameListItem[];
  loading: boolean;
  onSelectGame: (game: GameListItem) => void;
}

const formatTimestamp = (raw: string): string => {
  if (!raw) return 'Unknown Date';
  // Match YYYYMMDD_HHMMSS
  const match = String(raw).match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
  if (match) {
    const [, y, m, d, h, min, s] = match;
    const date = new Date(Number(y), Number(m) - 1, Number(d), Number(h), Number(min), Number(s));
    return date.toLocaleString();
  }
  const parsed = new Date(raw);
  if (!isNaN(parsed.getTime())) {
    return parsed.toLocaleString();
  }
  return raw;
};

const GameList: React.FC<GameListProps> = ({ games, loading, onSelectGame }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Discover all unique categories
  const categories = useMemo(() => {
    const set = new Set<string>();
    games.forEach((g) => set.add(g.category));
    return Array.from(set).sort();
  }, [games]);

  // Filter games based on search and category
  const filteredGames = useMemo(() => {
    return games.filter((game) => {
      if (selectedCategory !== 'all' && game.category !== selectedCategory) {
        return false;
      }
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const p0 = (game.player_names[0] || '').toLowerCase();
      const p1 = (game.player_names[1] || '').toLowerCase();
      const filename = (game.filename || '').toLowerCase();
      const winner = (game.winner || '').toLowerCase();
      return p0.includes(q) || p1.includes(q) || filename.includes(q) || winner.includes(q);
    });
  }, [games, searchQuery, selectedCategory]);

  const groupedGames = useMemo(() => {
    return filteredGames.reduce((acc, game) => {
      if (!acc[game.category]) {
        acc[game.category] = [];
      }
      acc[game.category].push(game);
      return acc;
    }, {} as Record<string, GameListItem[]>);
  }, [filteredGames]);

  if (loading) {
    return <div className="loading">Loading games...</div>;
  }

  if (games.length === 0) {
    return (
      <div className="no-games">
        <h2>No games found</h2>
        <p>Run evaluation matches using the Alphable CLI to generate game replays:</p>
        <pre>alphable eval baseline --opponent greedy --games 10</pre>
        <pre>alphable eval baseline --opponent random --games 5</pre>
        <pre>alphable eval matches --model-a models/alphable_v3_expert.pth --model-b models/alphable_v3_rl_gen2.pth</pre>
      </div>
    );
  }

  return (
    <div className="game-list">
      <div className="game-list-controls">
        <h2>📋 Available Games ({filteredGames.length}/{games.length})</h2>
        <input
          type="text"
          className="search-input"
          placeholder="Search by player, opponent, winner, or filename..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <div className="filter-pills">
          <button
            type="button"
            className={`filter-pill ${selectedCategory === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('all')}
          >
            All Categories ({games.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`filter-pill ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat.replace(/_/g, ' ').toUpperCase()} ({games.filter((g) => g.category === cat).length})
            </button>
          ))}
        </div>
      </div>

      {Object.keys(groupedGames).length === 0 ? (
        <div className="no-games" style={{ padding: '2rem' }}>
          <h3>No games matching your filter</h3>
          <p>Try clearing your search query or switching category filter.</p>
        </div>
      ) : (
        Object.entries(groupedGames).map(([category, categoryGames]) => (
          <div key={category} className="game-category">
            <h3>{category.replace(/_/g, ' ').toUpperCase()} ({categoryGames.length})</h3>

            <div className="games-grid">
              {categoryGames.map((game) => {
                const isAlphableWin =
                  game.winner && game.winner.toLowerCase().includes('alphable');
                return (
                  <div
                    key={game.id}
                    className="game-card"
                    onClick={() => onSelectGame(game)}
                  >
                    <div className="game-card-header">
                      <span className="game-timestamp">
                        {formatTimestamp(game.timestamp)}
                      </span>
                      {game.winner && (
                        <span
                          className={`winner-badge ${
                            isAlphableWin ? 'winner-alphable' : 'winner-other'
                          }`}
                        >
                          🏆 {game.winner}{' '}
                          {game.score_margin !== undefined
                            ? `(+${game.score_margin})`
                            : ''}
                        </span>
                      )}
                    </div>

                    <div className="game-card-players">
                      <div className="player">
                        <span className="player-name">
                          {game.player_names[0]}
                        </span>
                        <span className="player-score">
                          {game.final_score[0]}
                        </span>
                      </div>
                      <span className="vs">vs</span>
                      <div className="player">
                        <span className="player-name">
                          {game.player_names[1]}
                        </span>
                        <span className="player-score">
                          {game.final_score[1]}
                        </span>
                      </div>
                    </div>

                    <div className="game-card-meta">
                      <span>🎲 {game.total_turns} turns</span>
                      {game.bingos !== undefined && game.bingos > 0 && (
                        <span>✨ {game.bingos} bingos</span>
                      )}
                      {game.metadata && game.metadata.checkpoint && (
                        <span>🔖 Ckpt {game.metadata.checkpoint}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default GameList;
