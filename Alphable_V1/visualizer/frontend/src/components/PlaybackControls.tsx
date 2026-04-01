import React from 'react';
import './PlaybackControls.css';

interface PlaybackControlsProps {
  currentTurn: number;
  totalTurns: number;
  isPlaying: boolean;
  playbackSpeed: number;
  onJumpToStart: () => void;
  onPrevious: () => void;
  onPlayPause: () => void;
  onNext: () => void;
  onJumpToEnd: () => void;
  onSeek: (turn: number) => void;
  onSpeedChange: (speed: number) => void;
}

const SPEED_OPTIONS = [0.5, 1, 2, 5];

const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  currentTurn,
  totalTurns,
  isPlaying,
  playbackSpeed,
  onJumpToStart,
  onPrevious,
  onPlayPause,
  onNext,
  onJumpToEnd,
  onSeek,
  onSpeedChange
}) => {
  return (
    <div className="playback-controls">
      <div className="timeline">
        <input
          type="range"
          min={0}
          max={totalTurns - 1}
          value={currentTurn}
          onChange={(e) => onSeek(parseInt(e.target.value))}
          className="timeline-slider"
        />
        <div className="timeline-labels">
          <span>Turn {currentTurn + 1}</span>
          <span>{totalTurns} total</span>
        </div>
      </div>

      <div className="transport-controls">
        <button
          onClick={onJumpToStart}
          disabled={currentTurn === 0}
          className="control-button"
          title="Jump to start"
        >
          ⏮
        </button>
        
        <button
          onClick={onPrevious}
          disabled={currentTurn === 0}
          className="control-button"
          title="Previous move"
        >
          ⏪
        </button>
        
        <button
          onClick={onPlayPause}
          className="control-button play-button"
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? '⏸' : '▶️'}
        </button>
        
        <button
          onClick={onNext}
          disabled={currentTurn >= totalTurns - 1}
          className="control-button"
          title="Next move"
        >
          ⏩
        </button>
        
        <button
          onClick={onJumpToEnd}
          disabled={currentTurn >= totalTurns - 1}
          className="control-button"
          title="Jump to end"
        >
          ⏭
        </button>
      </div>

      <div className="speed-control">
        <label>Speed:</label>
        <select
          value={playbackSpeed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
          className="speed-selector"
        >
          {SPEED_OPTIONS.map((speed) => (
            <option key={speed} value={speed}>
              {speed}x
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default PlaybackControls;
