// components/config/SourceCard.js
import React from 'react';

const SourceCard = ({ source, onEdit, onDelete, onToggle }) => {
  const getSourceTypeIcon = (type) => {
    const icons = {
      'local': '💻',
      'network': '🌐', 
      'camera': '📹',
      'cloud': '☁️'
    };
    return icons[type] || '📁';
  };

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-4 mb-3">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{getSourceTypeIcon(source.source_type)}</span>
            <h4 className="text-lg font-medium text-white">{source.name}</h4>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              source.active ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
            }`}>
              {source.active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <p className="text-gray-300 text-sm mb-1">
            <strong>Type:</strong> {source.source_type.toUpperCase()}
          </p>
          <p className="text-gray-300 text-sm break-all">
            <strong>Path:</strong> {source.path}
          </p>
        </div>
        
        <div className="flex gap-2 ml-4">
          <button
            onClick={() => onToggle(source.id, !source.active)}
            className={`px-3 py-1 rounded text-sm font-medium ${
              source.active 
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white' 
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {source.active ? 'Disable' : 'Enable'}
          </button>
          <button
            onClick={() => onEdit(source)}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(source.id)}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

export default SourceCard;