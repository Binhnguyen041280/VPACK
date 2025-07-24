import React from "react";

const ResultList = ({ results, selectedVideos, setSelectedVideos, hasQueried }) => {
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
          results.map((event, index) => (
            <label key={event.event_id} className="flex items-center mb-2">
              <input
                type="checkbox"
                className="mr-2"
                checked={selectedVideos.includes(event.event_id)}
                onChange={() => handleSelectVideo(event.event_id)}
              />
              {`${index + 1}. ${event.video_file}`}
            </label>
          ))
        ) : (
          <p>Không có kết quả</p>
        )
      ) : (
        <p>Vui lòng thực hiện truy vấn</p>
      )}
    </div>
  );
};

export default ResultList;
