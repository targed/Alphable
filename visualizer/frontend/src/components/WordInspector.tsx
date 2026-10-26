import React, { useState, useEffect } from 'react';
import { WordDefinitionResult } from '../types';

interface WordInspectorProps {
  initialWord?: string;
  lexicon?: string;
  onClose?: () => void;
  isInline?: boolean;
  autoDefine?: boolean;
  onToggleAutoDefine?: (enabled: boolean) => void;
}

export const WordInspector: React.FC<WordInspectorProps> = ({
  initialWord = '',
  lexicon = 'CSW24',
  onClose,
  isInline = false,
  autoDefine = true,
  onToggleAutoDefine,
}) => {
  const [query, setQuery] = useState(initialWord);
  const [activeLexicon, setActiveLexicon] = useState(lexicon);
  const [result, setResult] = useState<WordDefinitionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recentWords, setRecentWords] = useState<string[]>([]);

  const handleLookup = (wordToLookup: string, lex = activeLexicon) => {
    const clean = wordToLookup.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
    if (!clean) return;

    setIsLoading(true);
    fetch(`/api/dictionary/lookup?word=${encodeURIComponent(clean)}&lexicon=${encodeURIComponent(lex)}`)
      .then(res => res.json())
      .then(data => {
        setIsLoading(false);
        setResult(data);
        setRecentWords(prev => {
          const next = [clean, ...prev.filter(w => w !== clean)];
          return next.slice(0, 8);
        });
      })
      .catch(err => {
        setIsLoading(false);
        console.error("Lookup error:", err);
      });
  };

  useEffect(() => {
    setActiveLexicon(lexicon);
  }, [lexicon]);

  useEffect(() => {
    if (initialWord && initialWord.trim()) {
      const clean = initialWord.replace(/[^A-Za-z]/g, '').trim().toUpperCase();
      if (clean) {
        setQuery(clean);
        handleLookup(clean, activeLexicon);
      }
    }
  }, [initialWord, activeLexicon]);

  return (
    <div
      className="panel-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        padding: '1.25rem',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.95rem', fontWeight: 800, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
            LEXICON &amp; DEFINITIONS
          </span>
          <span style={{
            fontSize: '0.7rem',
            padding: '0.15rem 0.45rem',
            borderRadius: '4px',
            backgroundColor: 'var(--bg-elevated)',
            color: '#38bdf8',
            border: '1px solid var(--border-subtle)',
            fontWeight: 700
          }}>
            {activeLexicon}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Auto Define Checkbox Toggle */}
          {onToggleAutoDefine && (
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.75rem',
                color: autoDefine ? '#10b981' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: 'var(--bg-elevated)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--border-subtle)'
              }}
              title="Automatically look up and define any word played on the board"
            >
              <input
                type="checkbox"
                checked={autoDefine}
                onChange={(e) => onToggleAutoDefine(e.target.checked)}
                style={{ accentColor: '#10b981', cursor: 'pointer' }}
              />
              <span>Auto-define</span>
            </label>
          )}

          {/* Lexicon Toggle */}
          <div style={{ display: 'flex', gap: '0.2rem' }}>
            {['CSW24', 'NWL23'].map(l => (
              <button
                key={l}
                className={`studio-tab-btn ${activeLexicon === l ? 'active' : ''}`}
                onClick={() => {
                  setActiveLexicon(l);
                  if (query) handleLookup(query, l);
                }}
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
              >
                {l}
              </button>
            ))}
          </div>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: 700,
                padding: '0 0.4rem'
              }}
              title="Close Inspector"
            >
              x
            </button>
          )}
        </div>
      </div>

      {/* Search Input Box */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleLookup(query);
          }}
          placeholder="ENTER WORD (E.G. QUIZ, AA, AGILITY)"
          style={{
            flex: 1,
            padding: '0.55rem 0.8rem',
            backgroundColor: 'var(--bg-deep)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            color: 'var(--text-primary)',
            fontWeight: 700,
            fontSize: '0.85rem',
            letterSpacing: '0.08em'
          }}
        />
        <button
          className="btn-primary"
          onClick={() => handleLookup(query)}
          disabled={isLoading || !query.trim()}
          style={{ padding: '0.55rem 1rem', fontSize: '0.8rem', minWidth: '80px' }}
        >
          {isLoading ? 'Checking...' : 'Lookup'}
        </button>
      </div>

      {/* Recent Lookups */}
      {recentWords.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Recent:</span>
          {recentWords.map(w => (
            <button
              key={w}
              onClick={() => {
                setQuery(w);
                handleLookup(w);
              }}
              style={{
                fontSize: '0.72rem',
                padding: '0.15rem 0.45rem',
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '3px',
                color: query === w ? '#60a5fa' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {w}
            </button>
          ))}
        </div>
      )}

      {/* Result Display Box */}
      {result && (
        <div
          style={{
            marginTop: '0.25rem',
            padding: '1rem',
            borderRadius: '6px',
            backgroundColor: 'var(--bg-deep)',
            border: `1px solid ${result.valid ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.65rem'
          }}
        >
          {/* Word & Validity Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <span style={{ fontSize: '1.4rem', fontWeight: 900, letterSpacing: '0.1em', color: 'var(--text-primary)' }}>
                {result.word}
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  padding: '0.2rem 0.6rem',
                  borderRadius: '4px',
                  backgroundColor: result.valid ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: result.valid ? '#10b981' : '#f87171',
                  border: `1px solid ${result.valid ? '#10b981' : '#ef4444'}`
                }}
              >
                {result.valid ? 'VALID PLAY' : 'INVALID / PHONEY'}
              </span>
            </div>

            {/* Badges: Score & Length */}
            <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-elevated)',
                color: '#f59e0b',
                border: '1px solid var(--border-subtle)'
              }}>
                {result.score} Pts
              </span>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-subtle)'
              }}>
                {result.length} Letters
              </span>
            </div>
          </div>

          {/* Lexicon Coverage Badges */}
          <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem' }}>
            <span style={{
              color: result.valid_csw24 ? '#34d399' : '#9ca3af',
              fontWeight: result.valid_csw24 ? 700 : 500
            }}>
              CSW24: {result.valid_csw24 ? 'Acceptable' : 'Not listed'}
            </span>
            <span style={{ color: 'var(--border-subtle)' }}>|</span>
            <span style={{
              color: result.valid_nwl23 ? '#34d399' : '#9ca3af',
              fontWeight: result.valid_nwl23 ? 700 : 500
            }}>
              NWL23: {result.valid_nwl23 ? 'Acceptable' : 'Not listed'}
            </span>
            {result.part_of_speech && (
              <>
                <span style={{ color: 'var(--border-subtle)' }}>|</span>
                <span style={{ color: '#c084fc', fontStyle: 'italic', textTransform: 'capitalize' }}>
                  {result.part_of_speech}
                </span>
              </>
            )}
          </div>

          {/* Definition Text Box */}
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-elevated)',
              fontSize: '0.85rem',
              lineHeight: '1.45',
              color: 'var(--text-secondary)',
              borderLeft: `3px solid ${result.valid ? '#10b981' : '#ef4444'}`
            }}
          >
            {result.definition}
          </div>

          {/* Source Attribution */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            Source: {result.source}
          </div>
        </div>
      )}

      {!result && !isLoading && (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
          Enter any word or click a move from the candidate list to view tournament validity and full definitions.
        </div>
      )}
    </div>
  );
};
