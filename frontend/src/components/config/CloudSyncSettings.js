// components/config/CloudSyncSettings.js - Focused Sync Configuration
import React, { useState, useEffect } from 'react';

const CloudSyncSettings = ({ config, onChange }) => {
  // Default settings
  const defaultSettings = {
    interval_minutes: 15,
    auto_sync_enabled: true,
    // Hidden/Fixed settings (not shown in UI) - BEST defaults for amature users
    organize_by_date: true,       // Always organize by date - optimal structure
    backup_metadata: true,        // Always preserve metadata - safe approach
    sync_only_new: true,          // Always incremental sync - efficient
    skip_duplicates: true,        // Always skip duplicates - smart behavior
    duplicate_handling: 'compare_size', // Compare by size - best balance
    max_file_size_mb: 1000,       // 30-min video ~1GB at standard quality
    bandwidth_limit_mbps: 10,     // 10 Mbps reasonable for background sync
    file_types: ['.mp4', '.avi', '.mov', '.mkv', '.m4v']
  };

  // Local state
  const [settings, setSettings] = useState({ ...defaultSettings, ...config });
  const [localStorageWarning, setLocalStorageWarning] = useState(false);

  // Sync interval options - focused on practical camera recording frequencies
  const syncIntervals = [
    { value: 5, label: "5 minutes", description: "High-frequency cameras (security)" },
    { value: 15, label: "15 minutes", description: "Standard recording (recommended)" },
    { value: 30, label: "30 minutes", description: "Low-frequency cameras" },
    { value: 60, label: "1 hour", description: "Periodic recording" },
    { value: 180, label: "3 hours", description: "Daily batch cameras" },
    { value: 360, label: "6 hours", description: "Archive/backup mode" }
  ];

  // Check local storage periodically
  useEffect(() => {
    const checkLocalStorage = () => {
      try {
        // Check available disk space (simplified estimation)
        if (navigator.storage && navigator.storage.estimate) {
          navigator.storage.estimate().then(estimate => {
            const usedGB = (estimate.usage || 0) / (1024 ** 3);
            const quotaGB = (estimate.quota || 0) / (1024 ** 3);
            const freeSpaceGB = quotaGB - usedGB;
            
            // Warn if less than 5GB free space
            if (freeSpaceGB < 5) {
              setLocalStorageWarning(true);
            } else {
              setLocalStorageWarning(false);
            }
          });
        }
      } catch (error) {
        console.warn('Could not check storage:', error);
      }
    };

    checkLocalStorage();
    // Check every 5 minutes
    const interval = setInterval(checkLocalStorage, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  // Update settings and notify parent
  const updateSetting = (key, value) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    
    if (onChange) {
      onChange(newSettings);
    }
  };

  // Get interval description
  const getIntervalDescription = (minutes) => {
    const interval = syncIntervals.find(i => i.value === minutes);
    return interval ? interval.description : '';
  };

  return (
    <div className="space-y-4">
      
      {/* Local Storage Warning */}
      {localStorageWarning && (
        <div className="bg-yellow-800 border border-yellow-600 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="text-yellow-200">⚠️</span>
            <div className="text-yellow-200 text-sm">
              <div className="font-medium">Low disk space detected</div>
              <div className="text-xs">Consider freeing up space to continue video sync</div>
            </div>
          </div>
        </div>
      )}

      {/* Sync Frequency */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="font-medium text-white mb-3">⏱️ Sync Frequency</h4>
        
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              How often should VTrack check for new videos?
            </label>
            <select
              value={settings.interval_minutes}
              onChange={(e) => updateSetting('interval_minutes', parseInt(e.target.value))}
              className="w-full p-3 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-blue-500"
            >
              {syncIntervals.map(interval => (
                <option key={interval.value} value={interval.value}>
                  {interval.label} - {interval.description}
                </option>
              ))}
            </select>
          </div>
          
          <div className="text-xs text-gray-400 bg-gray-600 p-3 rounded">
            <div className="font-medium mb-1">💡 Sync Frequency Guide:</div>
            <div>• <strong>5-15 minutes:</strong> Security cameras with frequent recording</div>
            <div>• <strong>30-60 minutes:</strong> Dashcams, action cameras with periodic recording</div>
            <div>• <strong>3-6 hours:</strong> Archive cameras or manual uploads</div>
          </div>
        </div>
      </div>

      {/* File Size Limits (Info Only) */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="font-medium text-white mb-3">📏 File Size Limits</h4>
        
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-300">Maximum file size:</span>
            <span className="text-white font-medium">{settings.max_file_size_mb} MB</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-300">Supported formats:</span>
            <span className="text-white font-medium">MP4, AVI, MOV, MKV, M4V</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-300">Background bandwidth:</span>
            <span className="text-white font-medium">{settings.bandwidth_limit_mbps} Mbps max</span>
          </div>
        </div>
        
        <div className="text-xs text-gray-400 bg-gray-600 p-3 rounded mt-3">
          <div className="font-medium mb-1">ℹ️ Automatic optimizations:</div>
          <div>• Videos organized by date folders for easy browsing</div>
          <div>• Original timestamps and camera info preserved</div>
          <div>• Duplicate files automatically skipped (smart detection)</div>
          <div>• Only new files downloaded (incremental sync)</div>
          <div>• Bandwidth limited to {settings.bandwidth_limit_mbps} Mbps (background mode)</div>
        </div>
      </div>



      {/* Advanced Settings Summary */}
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-4">
        <h4 className="font-medium text-gray-200 mb-3">⚙️ Advanced Settings (Auto-Configured)</h4>
        
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-400">
          <div>
            <div className="font-medium text-gray-300 mb-1">File Handling:</div>
            <div>• Organize by date: {settings.organize_by_date ? 'Yes' : 'No'}</div>
            <div>• Backup metadata: {settings.backup_metadata ? 'Yes' : 'No'}</div>
            <div>• Sync only new: {settings.sync_only_new ? 'Yes' : 'No'}</div>
          </div>
          <div>
            <div className="font-medium text-gray-300 mb-1">Performance:</div>
            <div>• Skip duplicates: {settings.skip_duplicates ? 'Yes' : 'No'}</div>
            <div>• Duplicate method: {settings.duplicate_handling}</div>
            <div>• Max file size: {settings.max_file_size_mb}MB</div>
          </div>
        </div>
        
        <div className="mt-3 text-xs text-gray-500">
          💡 These advanced settings are automatically optimized for Google Drive Picker workflow
        </div>
      </div>

      {/* Debug Info (Development) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="bg-gray-800 rounded p-3">
          <summary className="text-xs text-gray-400 cursor-pointer">🔧 Debug - Sync Settings</summary>
          <pre className="text-xs text-gray-400 mt-2 overflow-auto">
            {JSON.stringify(settings, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default CloudSyncSettings;