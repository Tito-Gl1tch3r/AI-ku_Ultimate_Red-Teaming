import React from 'react';

const AnalysisView = ({ result, analysis }) => {
  if (!result || !analysis) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-gray-500">No analysis data available.</p>
      </div>
    );
  }

  const getCredibilityColor = (score) => {
    if (score >= 0.7) return 'bg-green-100 text-green-800';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment.toLowerCase()) {
      case 'positive':
        return 'text-green-500';
      case 'negative':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="bg-indigo-50 p-4 border-b border-indigo-100">
        <h2 className="text-xl font-semibold text-indigo-800">{result.title}</h2>
        <a 
          href={result.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-indigo-600 hover:text-indigo-800 text-sm mt-1 block"
          tabIndex="0"
        >
          {result.url}
        </a>
      </div>
      
      <div className="p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <h3 className="text-lg font-medium mb-3 text-gray-700">Source Details</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Domain:</span>
                <span className="text-sm font-medium">{analysis.domain}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Credibility Score:</span>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCredibilityColor(analysis.credibility_score)}`}>
                  {(analysis.credibility_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Sentiment:</span>
                <span className={`text-sm font-medium ${getSentimentColor(analysis.sentiment)}`}>
                  {analysis.sentiment.charAt(0).toUpperCase() + analysis.sentiment.slice(1)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Published:</span>
                <span className="text-sm">{analysis.timestamps.published}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Last Updated:</span>
                <span className="text-sm">{analysis.timestamps.last_updated}</span>
              </div>
            </div>
          </div>
          
          <div>
            <h3 className="text-lg font-medium mb-3 text-gray-700">Key Entities</h3>
            <div className="flex flex-wrap gap-2">
              {analysis.key_entities.map((entity, index) => (
                <span 
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800"
                >
                  {entity}
                </span>
              ))}
            </div>
          </div>
        </div>
        
        <div className="mt-6">
          <h3 className="text-lg font-medium mb-3 text-gray-700">Content Summary</h3>
          <p className="text-gray-800">{result.snippet}</p>
        </div>
        
        {analysis.connections && analysis.connections.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-medium mb-3 text-gray-700">Entity Connections</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">From</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Relationship</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">To</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {analysis.connections.map((connection, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{connection.from}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-indigo-600">{connection.relationship}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{connection.to}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisView; 