import React, { useState, useEffect } from 'react';
import './App.css';
import { GameData, GameListItem } from './types';
import GameList from './components/GameList';
import GameViewer from './components/GameViewer';

const API_URL = 'http://localhost:5000/api';

function App() {
  const [games, setGames] = useState<GameListItem[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/games`);
      const data = await response.json();
      setGames(data.games);
      setError(null);
    } catch (err) {
      setError('Failed to load games. Is the backend running?');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadGame = async (game: GameListItem) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/games/${game.category}/${game.filename}`);
      const data = await response.json();
      setSelectedGame(data);
      setError(null);
    } catch (err) {
      setError('Failed to load game data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Alphable Replay Visualizer</h1>
        <p>Watch AI Scrabble Games in Action</p>
      </header>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <div className="App-content">
        {!selectedGame ? (
          <GameList
            games={games}
            loading={loading}
            onSelectGame={loadGame}
          />
        ) : (
          <GameViewer
            game={selectedGame}
            onBack={() => setSelectedGame(null)}
          />
        )}
      </div>
    </div>
  );
}

export default App;
