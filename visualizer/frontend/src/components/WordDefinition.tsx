import React, { useEffect, useState } from 'react';
import './WordDefinition.css';

interface WordDefinitionProps {
  word: string | null;
}

interface Definition {
  partOfSpeech: string;
  definition: string;
}

const WordDefinition: React.FC<WordDefinitionProps> = ({ word }) => {
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!word || word.length === 0) {
      setDefinitions([]);
      return;
    }

    const fetchDefinition = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Use Free Dictionary API
        const response = await fetch(
          `https://api.dictionaryapi.dev/api/v2/entries/en/${word.toLowerCase()}`
        );
        
        if (!response.ok) {
          throw new Error('Definition not found');
        }
        
        const data = await response.json();
        
        if (data && data.length > 0) {
          const defs: Definition[] = [];
          
          // Extract up to 2 definitions
          data[0].meanings.slice(0, 2).forEach((meaning: any) => {
            if (meaning.definitions && meaning.definitions.length > 0) {
              defs.push({
                partOfSpeech: meaning.partOfSpeech,
                definition: meaning.definitions[0].definition
              });
            }
          });
          
          setDefinitions(defs);
        }
      } catch (err) {
        setError('No definition available');
        setDefinitions([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDefinition();
  }, [word]);

  if (!word) {
    return (
      <div className="word-definition">
        <h3>📖 Word Definition</h3>
        <div className="definition-placeholder">
          No word played yet
        </div>
      </div>
    );
  }

  return (
    <div className="word-definition">
      <h3>📖 Word Definition</h3>
      <div className="word-title">{word}</div>
      
      {loading && <div className="definition-loading">Loading...</div>}
      
      {error && <div className="definition-error">{error}</div>}
      
      {!loading && !error && definitions.length > 0 && (
        <div className="definitions-list">
          {definitions.map((def, index) => (
            <div key={index} className="definition-item">
              <div className="part-of-speech">{def.partOfSpeech}</div>
              <div className="definition-text">{def.definition}</div>
            </div>
          ))}
        </div>
      )}
      
      {!loading && !error && definitions.length === 0 && word && (
        <div className="definition-placeholder">
          Valid Scrabble word
        </div>
      )}
    </div>
  );
};

export default WordDefinition;
