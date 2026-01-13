import React from 'react';
import './MoveValidity.css';

interface MoveValidityProps {
  isValid: boolean;
  moveDescription?: string;
}

const MoveValidity: React.FC<MoveValidityProps> = ({ isValid, moveDescription }) => {
  return (
    <div className={`move-validity ${isValid ? 'valid' : 'invalid'}`}>
      <h3>📋 Last Move</h3>
      <div className="validity-status">
        <span className="validity-icon">{isValid ? '✅' : '❌'}</span>
        <span className="validity-text">{isValid ? 'VALID' : 'INVALID'}</span>
      </div>
      {moveDescription && (
        <div className="move-description">{moveDescription}</div>
      )}
    </div>
  );
};

export default MoveValidity;
