import React, { useState, useEffect, useRef } from 'react';
import { GameSummary, TournamentSummary, BoardState } from '../types';
import { Board } from './Board';
import { PlayerHUD } from './PlayerHUD';

const EMPTY_BOARD = (): BoardState => Array(15).fill(null).map(() => Array(15).fill(null));

export const GameReplayView: React.FC = () => {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [tournaments, setTournaments] = useState<TournamentSummary[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameSummary | null>(null);
  const [activeGameData, setActiveGameData] = useState<any>(null);
  const [currentTurnIdx, setCurrentTurnIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playSpeed, setPlaySpeed] = useState<number>(1.0);
  const [activeSubTab, setActiveSubTab] = useState<'games' | 'tournaments'>('games');

  const playTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetch('/api/games')
      .then(res => res.json())
      .then(data => {
        const gList = data.games || [];
        setGames(gList);
        if (gList.length > 0) {
          loadGame(gList[0]);
        }
      })
      .catch(err => console.error("Error fetching games:", err));

    fetch('/api/tournaments')
      .then(res => res.json())
      .then(data => setTournaments(data.tournaments || []))
      .catch(err => console.error("Error fetching tournaments:", err));
  }, []);

  const loadGame = (game: GameSummary) => {
    setSelectedGame(game);
    setCurrentTurnIdx(0);
    setIsPlaying(false);
    fetch(`/api/games/${game.category}/${game.filename}`)
      .then(res => res.json())
      .then(data => setActiveGameData(data))
      .catch(err => console.error("Error loading game details:", err));
  };

  const turns = activeGameData?.turns || [];
  const totalTurns = turns.length;

  // Autoplay management
  useEffect(() => {
    if (isPlaying && totalTurns > 0) {
      playTimerRef.current = setTimeout(() => {
        if (currentTurnIdx < totalTurns - 1) {
          setCurrentTurnIdx(prev => prev + 1);
        } else {
          setIsPlaying(false);
        }
      }, 1000 / playSpeed);
    }
    return () => {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
    };
  }, [isPlaying, currentTurnIdx, playSpeed, totalTurns]);

  // Derive board state up to currentTurnIdx
  const currentBoard = EMPTY_BOARD();
  let p1Score = 0;
  let p2Score = 0;

  for (let i = 0; i <= currentTurnIdx && i < turns.length; i++) {
    const t = turns[i];
    if (t.player === 0) p1Score += (t.score || 0);
    else p2Score += (t.score || 0);

    // Apply placements
    if (t.action_type === 'PLAY' && t.word && t.position) {
      const [row, col] = t.position;
      const isAcross = (t.direction || 'Across').toLowerCase().startsWith('a');
      const word = t.word.toUpperCase();
      for (let w = 0; w < word.length; w++) {
        const r = isAcross ? row : row + w;
        const c = isAcross ? col + w : col;
        if (r >= 0 && r < 15 && c >= 0 && c < 15) {
          currentBoard[r][c] = word[w];
        }
      }
    }
  }

  const currentTurn = turns[currentTurnIdx] || null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr 340px', gap: '1.5rem' }}>
      {/* Sidebar: Game & Tournament List */}
      <div className="panel-card" style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem' }}>
          <button
            className={`studio-tab-btn ${activeSubTab === 'games' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('games')}
            style={{ flex: 1, padding: '0.35rem' }}
          >
            Replays ({games.length})
          </button>
          <button
            className={`studio-tab-btn ${activeSubTab === 'tournaments' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('tournaments')}
            style={{ flex: 1, padding: '0.35rem' }}
          >
            Tournaments ({tournaments.length})
          </button>
        </div>

        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {activeSubTab === 'games' ? (
            games.map(g => (
              <div
                key={g.id}
                onClick={() => loadGame(g)}
                style={{
                  padding: '0.75rem',
                  borderRadius: '8px',
                  backgroundColor: selectedGame?.id === g.id ? 'var(--bg-elevated)' : 'var(--bg-deep)',
                  border: selectedGame?.id === g.id ? '1px solid #3b82f6' : '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'background 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>{g.category}</span>
                  <span>{g.total_turns} turns</span>
                </div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', marginTop: '0.2rem' }}>
                  {g.player_names[0]} vs {g.player_names[1]}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginTop: '0.3rem' }}>
                  <span style={{ color: '#38bdf8', fontWeight: 700 }}>{g.final_score[0]} - {g.final_score[1]}</span>
                  <span style={{ color: '#10b981' }}>Winner: {g.winner}</span>
                </div>
              </div>
            ))
          ) : (
            tournaments.map(t => (
              <div
                key={t.run_id}
                style={{
                  padding: '0.75rem',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-deep)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.85rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#f59e0b', fontWeight: 700 }}>
                  <span>{t.run_id}</span>
                  <span>{t.total_games} games</span>
                </div>
                <div style={{ fontWeight: 600, marginTop: '0.25rem' }}>
                  {t.player1.short_name} vs {t.player2.short_name}
                </div>
                <div style={{ marginTop: '0.4rem', color: '#10b981', fontWeight: 700 }}>
                  Win Rate: {t.win_rate.percentage}% ± {t.win_rate.ci95 || 0}%
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Net Spread: +{t.net_spread.mean} pts | Tag: {t.tag || 'N/A'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Board & Playback View */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <PlayerHUD
          p1Name={selectedGame?.player_names[0] || "Player 1"}
          p2Name={selectedGame?.player_names[1] || "Player 2"}
          p1Score={p1Score}
          p2Score={p2Score}
          bagCount={currentTurn?.tiles_in_bag ?? 80}
          activePlayer={currentTurn?.player ?? 0}
        />

        <Board board={currentBoard} />

        {/* Playback Transport Controls */}
        <div className="panel-card" style={{ width: '100%', marginTop: '1.25rem', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
            <button className="btn-secondary" onClick={() => setCurrentTurnIdx(0)} title="First Turn" style={{ padding: '0.35rem 0.6rem' }}>|&lt;</button>
            <button className="btn-secondary" onClick={() => setCurrentTurnIdx(p => Math.max(0, p - 1))} title="Prev Turn" style={{ padding: '0.35rem 0.6rem' }}>&lt;</button>
            <button
              className="btn-primary"
              onClick={() => setIsPlaying(!isPlaying)}
              style={{ minWidth: '70px', padding: '0.35rem 0.8rem' }}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <button className="btn-secondary" onClick={() => setCurrentTurnIdx(p => Math.min(totalTurns - 1, p + 1))} title="Next Turn" style={{ padding: '0.35rem 0.6rem' }}>&gt;</button>
            <button className="btn-secondary" onClick={() => setCurrentTurnIdx(totalTurns - 1)} title="Last Turn" style={{ padding: '0.35rem 0.6rem' }}>&gt;|</button>


            {/* Speed Selector */}
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Speed:</span>
              {[0.5, 1.0, 2.0, 4.0].map(s => (
                <button
                  key={s}
                  className={`studio-tab-btn ${playSpeed === s ? 'active' : ''}`}
                  onClick={() => setPlaySpeed(s)}
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          {/* Scrubber slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Turn {currentTurnIdx + 1}/{totalTurns || 1}</span>
            <input
              type="range"
              min={0}
              max={Math.max(0, totalTurns - 1)}
              value={currentTurnIdx}
              onChange={(e) => setCurrentTurnIdx(Number(e.target.value))}
              style={{ flex: 1, accentColor: '#3b82f6', cursor: 'pointer' }}
            />
          </div>
        </div>
      </div>

      {/* Right Column: Turn Log */}
      <div className="panel-card" style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
        <div className="panel-title">
          <span>Turn-by-Turn Move Log</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{turns.length} plays</span>
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <table className="candidate-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Player</th>
                <th>Play</th>
                <th style={{ textAlign: 'right' }}>Pts</th>
              </tr>
            </thead>
            <tbody>
              {turns.map((t: any, idx: number) => (
                <tr
                  key={idx}
                  onClick={() => setCurrentTurnIdx(idx)}
                  style={{
                    backgroundColor: idx === currentTurnIdx ? 'var(--bg-elevated)' : 'transparent',
                    borderLeft: idx === currentTurnIdx ? '3px solid #3b82f6' : 'none'
                  }}
                >
                  <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                  <td style={{ color: t.player === 0 ? '#38bdf8' : '#c084fc', fontWeight: 600 }}>
                    P{t.player + 1}
                  </td>
                  <td style={{ fontWeight: 700 }}>
                    {t.action_type === 'PLAY' ? (t.word || "PLAY") : t.action_type}
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700, color: '#10b981' }}>
                    +{t.score || 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
