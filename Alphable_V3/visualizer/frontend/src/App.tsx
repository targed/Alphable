import React, { useState, useEffect } from 'react';
import './App.css';
import { GameData, GameListItem } from './types';
import GameList from './components/GameList';
import GameViewer from './components/GameViewer';
import NewInteractiveGame, { InteractiveGameConfig } from './components/NewInteractiveGame';
import InteractiveGame from './components/InteractiveGame';

const API_URL = 'http://localhost:5000/api';

type AppMode = 'replay_list' | 'replay_view' | 'interactive_setup' | 'interactive_play';

function App() {
  const [mode, setMode] = useState<AppMode>('replay_list');

  const [games, setGames] = useState<GameListItem[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameData | null>(null);

  const [interactiveConfig, setInteractiveConfig] = useState<InteractiveGameConfig | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === 'replay_list') {
      fetchGames();
    }
  }, [mode]);

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
      setMode('replay_view');
      setError(null);
    } catch (err) {
      setError('Failed to load game data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartInteractive = (config: InteractiveGameConfig) => {
    setInteractiveConfig(config);
    setMode('interactive_play');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Alphable Visualizer</h1>
        <div className="header-nav">
          <button
            className={mode.startsWith('replay') ? 'active' : ''}
            onClick={() => setMode('replay_list')}
          >
            Replay JSON Games
          </button>
          <button
            className={mode.startsWith('interactive') ? 'active' : ''}
            onClick={() => setMode('interactive_setup')}
          >
            Play Interactive Mode
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <div className="App-content">
        {mode === 'replay_list' && (
          <GameList
            games={games}
            loading={loading}
            onSelectGame={loadGame}
          />
        )}

        {mode === 'replay_view' && selectedGame && (
          <GameViewer
            game={selectedGame}
            onBack={() => {
              setSelectedGame(null);
              setMode('replay_list');
            }}
          />
        )}

        {mode === 'interactive_setup' && (
          <NewInteractiveGame
            onStart={handleStartInteractive}
            onCancel={() => setMode('replay_list')}
          />
        )}

        {mode === 'interactive_play' && interactiveConfig && (
          <InteractiveGame
            config={interactiveConfig}
            onBack={() => setMode('interactive_setup')}
          />
        )}
      </div>
    </div>
  );
}

export default App;
