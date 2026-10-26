import React, { useState } from 'react';
import { BoardState, ComparisonResult } from '../types';
import { Board } from './Board';

const EMPTY_BOARD = (): BoardState => Array(15).fill(null).map(() => Array(15).fill(null));

export const PositionAnalyzer: React.FC = () => {
  const [board, setBoard] = useState<BoardState>(() => {
    const b = EMPTY_BOARD();
    // Default sample midgame hook
    b[7][6] = 'Q';
    b[7][7] = 'U';
    b[7][8] = 'I';
    b[7][9] = 'Z';
    return b;
  });

  const [rackInput, setRackInput] = useState<string>("TRAINER");
  const [lexicon, setLexicon] = useState<string>("CSW24");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [comparisons, setComparisons] = useState<Record<string, ComparisonResult> | null>(null);

  const setScenario = (name: string) => {
    const b = EMPTY_BOARD();
    if (name === 'opening') {
      setRackInput("AQRTUYZ");
    } else if (name === 'quiz_hook') {
      b[7][6] = 'Q'; b[7][7] = 'U'; b[7][8] = 'I'; b[7][9] = 'Z';
      setRackInput("TRAINER");
    } else if (name === 'bingo_rack') {
      b[7][4] = 'S'; b[7][5] = 'T'; b[7][6] = 'A'; b[7][7] = 'R'; b[7][8] = 'E';
      setRackInput("RETINAS");
    }
    setBoard(b);
    setComparisons(null);
  };

  const handleCellClick = (r: number, c: number) => {
    const cur = board[r][c];
    const letter = prompt(`Enter letter for cell (${r+1}, ${String.fromCharCode(65+c)}) or leave empty to clear:`, cur || "");
    if (letter !== null) {
      const nextB = board.map(row => [...row]);
      nextB[r][c] = letter.trim() ? letter.trim()[0].toUpperCase() : null;
      setBoard(nextB);
      setComparisons(null);
    }
  };

  const runComparison = () => {
    setIsLoading(true);
    const rackArr = rackInput.toUpperCase().replace(/[^A-Z?]/g, '').split('');

    fetch('/api/compare/position', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        board,
        rack: rackArr,
        engines: ['v4', 'v3', 'magpie', 'greedy'],
        lexicon
      })
    })
      .then(res => res.json())
      .then(data => {
        setComparisons(data.comparisons || {});
        setIsLoading(false);
      })
      .catch(err => {
        console.error("Comparison error:", err);
        setIsLoading(false);
      });
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2rem' }}>
      {/* Left: Interactive Board Setup */}
      <div>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button className="btn-secondary" onClick={() => setScenario('opening')}>Scenario: Opening</button>
          <button className="btn-secondary" onClick={() => setScenario('quiz_hook')}>Scenario: QUIZ Hook</button>
          <button className="btn-secondary" onClick={() => setScenario('bingo_rack')}>Scenario: RETINAS Bingo</button>
          <button className="btn-secondary" onClick={() => { setBoard(EMPTY_BOARD()); setComparisons(null); }}>Clear Board</button>
        </div>

        <Board board={board} onCellClick={handleCellClick} />

        <div className="panel-card" style={{ marginTop: '1.25rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>
                PLAYER RACK TILES
              </label>
              <input
                type="text"
                value={rackInput}
                onChange={(e) => setRackInput(e.target.value.toUpperCase())}
                placeholder="e.g. AQRTUYZ"
                style={{
                  width: '100%',
                  padding: '0.6rem 0.9rem',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '1.1rem',
                  letterSpacing: '0.2em'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>
                LEXICON
              </label>
              <select
                value={lexicon}
                onChange={(e) => setLexicon(e.target.value)}
                style={{
                  padding: '0.65rem',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: 'white',
                  fontWeight: 600
                }}
              >
                <option value="CSW24">CSW24</option>
                <option value="NWL23">NWL23</option>
              </select>
            </div>
            <button
              className="btn-primary"
              onClick={runComparison}
              disabled={isLoading}
              style={{ minWidth: '160px', padding: '0.65rem 1.25rem' }}
            >
              {isLoading ? "Analyzing..." : "Compare Engines"}
            </button>
          </div>
        </div>
      </div>

      {/* Right: Side-by-Side Engine Comparison Cards */}
      <div>
        <div className="panel-title" style={{ fontSize: '1.2rem' }}>
          Cross-Engine Evaluation Breakdown
        </div>

        {!comparisons ? (
          <div className="panel-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Configure your board and rack, then click <strong>"Compare Engines"</strong> to see side-by-side choices from Alphable V4, Alphable V3, Base MAGPIE, and Greedy.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.25rem' }}>
            {Object.entries(comparisons).map(([engKey, comp]) => (
              <div
                key={engKey}
                className="panel-card"
                style={{
                  borderTop: engKey === 'v4' ? '4px solid #3b82f6' : (engKey === 'v3' ? '4px solid #8b5cf6' : '4px solid #10b981')
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '1rem', color: engKey === 'v4' ? '#60a5fa' : (engKey === 'v3' ? '#c084fc' : '#34d399') }}>
                    {comp.name || engKey.toUpperCase()}
                  </span>
                  <span style={{ backgroundColor: 'var(--bg-elevated)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                    {comp.action}
                  </span>
                </div>

                {comp.error ? (
                  <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>Error: {comp.error}</div>
                ) : (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                        {comp.move?.word || "PASS"}
                      </span>
                      <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981' }}>
                        +{comp.points} pts
                      </span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.8rem' }}>
                      Coordinates: <span style={{ color: '#38bdf8', fontWeight: 600 }}>{comp.move?.coord || `(${comp.move?.row},${comp.move?.col})`}</span> | Equity: <span style={{ color: '#f59e0b', fontWeight: 700 }}>{comp.equity}</span>
                    </div>

                    {comp.candidates_top3 && comp.candidates_top3.length > 0 && (
                      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.6rem' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
                          Top Alternative Candidates:
                        </div>
                        {comp.candidates_top3.map((alt, i) => (
                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.2rem 0' }}>
                            <span>{i+1}. {alt.word} ({alt.coord})</span>
                            <span style={{ color: 'var(--text-muted)' }}>+{alt.points} pts (Eq: {alt.equity})</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
