import React from 'react';

const ResultsList = ({ results, onSelectResult, selectedUrl }) => {
  if (!results || results.length === 0) {
    return null;
  }

  const handleResultClick = (result) => {
    onSelectResult(result);
  };

  const handleKeyDown = (e, result) => {
    if (e.key === 'Enter' || e.key === ' ') {
      onSelectResult(result);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h2 className="text-xl font-semibold mb-4">Search Results</h2>
      <ul className="divide-y divide-gray-200">
        {results.map((result, index) => (
          <li 
            key={index}
            onClick={() => handleResultClick(result)}
            onKeyDown={(e) => handleKeyDown(e, result)}
            className={`py-3 px-2 cursor-pointer hover:bg-gray-50 transition rounded ${
              result.url === selectedUrl ? 'bg-indigo-50 border-l-4 border-indigo-500 pl-2' : ''
            }`}
            tabIndex="0"
            aria-label={`Search result: ${result.title}`}
          >
            <h3 className="text-base font-medium text-indigo-600 mb-1">{result.title}</h3>
            <p className="text-sm text-gray-600 mb-1 truncate">{result.url}</p>
            <p className="text-sm text-gray-800 line-clamp-2">{result.snippet}</p>
            <div className="mt-2 flex justify-between text-xs text-gray-500">
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-800">
                {result.source_type}
              </span>
              <span>{result.timestamp}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ResultsList; 