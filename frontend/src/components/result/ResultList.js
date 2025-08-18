import React from "react";
import timezoneManager from "../../utils/TimezoneManager";

const ResultList = ({ results, selectedVideos, setSelectedVideos, hasQueried }) => {
  const formatEventTime = (event) => {
    try {
      // Check if event has timestamp information
      if (event.start_time) {
        return timezoneManager.displayTime(event.start_time, { 
          format: 'short',
          showTimezone: true 
        });
      }
      
      // Fallback to event time if available
      if (event.event_time) {
        return timezoneManager.displayTime(event.event_time, { 
          format: 'short',
          showTimezone: true 
        });
      }
      
      // Try to extract timestamp from video filename
      if (event.video_file) {
        const timestampMatch = event.video_file.match(/\d{4}-\d{2}-\d{2}[_T]\d{2}-?\d{2}-?\d{2}/);
        if (timestampMatch) {
          const timestamp = timestampMatch[0].replace(/_/g, 'T').replace(/-/g, ':');
          return timezoneManager.displayTime(timestamp, { 
            format: 'short',
            showTimezone: true 
          });
        }
      }
      
      return null;
    } catch (error) {
      console.warn('Error formatting event time:', error);
      return null;
    }
  };
  const handleSelectVideo = (eventId) => {
    if (selectedVideos.includes(eventId)) {
      setSelectedVideos(selectedVideos.filter((id) => id !== eventId));
    } else {
      setSelectedVideos([...selectedVideos, eventId]);
    }
  };

  React.useEffect(() => {
    if (results.length > 0) {
      const newSelectedVideos = results.map(event => event.event_id);
      setSelectedVideos(newSelectedVideos);
    }
  }, [results]);

  return (
    <div className="flex-1 mb-4 bg-gray-700 rounded p-2 overflow-y-auto">
      {hasQueried ? (
        results.length > 0 ? (
          results.map((event, index) => {
            const formattedTime = formatEventTime(event);
            return (
              <label key={event.event_id} className="flex items-start mb-3 p-2 bg-gray-600 rounded hover:bg-gray-500 transition-colors">
                <input
                  type="checkbox"
                  className="mr-3 mt-1"
                  checked={selectedVideos.includes(event.event_id)}
                  onChange={() => handleSelectVideo(event.event_id)}
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white mb-1">
                    {`${index + 1}. ${event.video_file}`}
                  </div>
                  {formattedTime && (
                    <div className="text-xs text-blue-300 mb-1">
                      🕒 {formattedTime}
                    </div>
                  )}
                  {event.confidence && (
                    <div className="text-xs text-green-300">
                      ✓ Độ tin cậy: {Math.round(event.confidence * 100)}%
                    </div>
                  )}
                  {event.detection_type && (
                    <div className="text-xs text-yellow-300">
                      🔍 {event.detection_type === 'hand' ? 'Phát hiện tay' : 'QR Code'}
                    </div>
                  )}
                </div>
              </label>
            );
          }) ) : (
          <p>Không có kết quả</p>
        )
      ) : (
        <p>Vui lòng thực hiện truy vấn</p>
      )}
    </div>
  );
};

export default ResultList;
