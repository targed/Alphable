import React, { useEffect, useState } from 'react';
import { EngineInfo, ModelInfo } from '../types';

interface EngineSelectorProps {
  selectedEngine: string;
  selectedModel: string;
  onEngineChange: (engine: string) => void;
  onModelChange: (model: string) => void;
}

export const EngineSelector: React.FC<EngineSelectorProps> = ({
  selectedEngine,
  selectedModel,
  onEngineChange,
  onModelChange
}) => {
  const [engines, setEngines] = useState<EngineInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    fetch('/api/engines')
      .then(res => res.json())
      .then(data => setEngines(data.engines || []))
      .catch(err => console.error("Error fetching engines:", err));
  }, []);

  useEffect(() => {
    fetch(`/api/models?engine=${selectedEngine}`)
      .then(res => res.json())
      .then(data => {
        const mList = data.models || [];
        setModels(mList);
        if (mList.length > 0 && !mList.some((m: ModelInfo) => m.id === selectedModel)) {
          onModelChange(mList[0].id);
        }
      })
      .catch(err => console.error("Error fetching models:", err));
  }, [selectedEngine]);

  return (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <div>
        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>
          AI ENGINE
        </label>
        <select
          value={selectedEngine}
          onChange={(e) => onEngineChange(e.target.value)}
          style={{
            backgroundColor: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '0.45rem 0.8rem',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <option value="v4">Alphable V4 (BAMS + MAGPIE)</option>
          <option value="v3">Alphable V3 (Macondo ResNet)</option>
          <option value="magpie">Base MAGPIE (KLV Static)</option>
          <option value="greedy">Score Greedy Bot</option>
        </select>
      </div>

      {models.length > 0 && (
        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>
            PRESET / CHECKPOINT
          </label>
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-elevated)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '0.45rem 0.8rem',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            {models.map(m => (
              <option key={m.id} value={m.id}>
                {m.name} {m.size_mb ? `(${m.size_mb} MB)` : ''}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
