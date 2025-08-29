/**
 * DualAnalysisCanvas Component
 * Real-time dual canvas visualization for ROI analysis
 * Supports both Traditional (hand detection) and QR Code methods
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Box,
  HStack,
  VStack,
  Text,
  Badge,
  Progress,
  IconButton,
  Button,
  Flex,
  useColorModeValue,
  Tooltip
} from '@chakra-ui/react';
import { FaPlay, FaPause, FaStop, FaExpand } from 'react-icons/fa';

// Types for analysis data
interface DetectionResult {
  timestamp: number;
  frame_number: number;
  roi_id: string;
  detection_type: string;
  confidence: number;
  coordinates?: any;
  content?: string;
  landmarks?: any[];
}

interface StreamFrame {
  timestamp: number;
  frame_number: number;
  frame_data?: string;
  detections: DetectionResult[];
  status: string;
}

interface ROIConfig {
  x: number;
  y: number;
  w: number;
  h: number;
  type: string;
  label: string;
}

interface AnalysisSession {
  session_id: string;
  method: string;
  status: string;
  frame_count: number;
  total_frames: number;
  fps: number;
  speed_multiplier: number;
  progress: number;
  elapsed_time: number;
  roi_count: number;
}

interface DualAnalysisCanvasProps {
  sessionId: string | null;
  method: 'traditional' | 'qr_code';
  rois: ROIConfig[];
  videoWidth: number;
  videoHeight: number;
  onAnalysisComplete?: (results: any) => void;
  onError?: (error: string) => void;
}

const DualAnalysisCanvas: React.FC<DualAnalysisCanvasProps> = ({
  sessionId,
  method,
  rois,
  videoWidth,
  videoHeight,
  onAnalysisComplete,
  onError
}) => {
  const canvasRef1 = useRef<HTMLCanvasElement>(null);
  const canvasRef2 = useRef<HTMLCanvasElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamData, setStreamData] = useState<StreamFrame | null>(null);
  const [sessionStatus, setSessionStatus] = useState<AnalysisSession | null>(null);
  const [detectionStats, setDetectionStats] = useState({
    totalDetections: 0,
    averageConfidence: 0,
    recentEvents: [] as DetectionResult[]
  });
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');

  // Canvas dimensions
  const canvasWidth = 400;
  const canvasHeight = 300;

  // Setup Server-Sent Events connection
  const setupEventSource = useCallback(() => {
    if (!sessionId || eventSourceRef.current) return;

    const eventSource = new EventSource(`/api/analysis-streaming/stream/${sessionId}`);
    eventSourceRef.current = eventSource;
    setConnectionStatus('connecting');

    eventSource.onopen = () => {
      console.log('SSE connection opened for session:', sessionId);
      setConnectionStatus('connected');
      setIsStreaming(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'connection':
            console.log('SSE connection confirmed:', data);
            break;
            
          case 'status':
            setSessionStatus(data.data);
            break;
            
          case 'analysis':
            setStreamData(data.data);
            updateDetectionStats(data.data);
            drawAnalysisFrame(data.data);
            break;
            
          case 'complete':
            console.log('Analysis completed:', data);
            setIsStreaming(false);
            onAnalysisComplete?.(data);
            break;
            
          case 'error':
            console.error('SSE error:', data.message);
            onError?.(data.message);
            break;
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      setConnectionStatus('disconnected');
      setIsStreaming(false);
      
      // Try to reconnect after a delay
      setTimeout(() => {
        if (sessionId && !eventSourceRef.current) {
          setupEventSource();
        }
      }, 3000);
    };
  }, [sessionId, onAnalysisComplete, onError]);

  // Cleanup EventSource
  const cleanupEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnectionStatus('disconnected');
      setIsStreaming(false);
    }
  }, []);

  // Update detection statistics
  const updateDetectionStats = useCallback((frameData: StreamFrame) => {
    if (!frameData.detections || frameData.detections.length === 0) return;

    setDetectionStats(prev => {
      const newDetections = frameData.detections;
      const totalDetections = prev.totalDetections + newDetections.length;
      const confidences = newDetections.map(d => d.confidence);
      const avgConfidence = confidences.reduce((sum, c) => sum + c, 0) / confidences.length;
      
      // Keep recent events (last 10)
      const recentEvents = [...prev.recentEvents, ...newDetections].slice(-10);

      return {
        totalDetections,
        averageConfidence: (prev.averageConfidence + avgConfidence) / 2,
        recentEvents
      };
    });
  }, []);

  // Draw analysis frame on canvas
  const drawAnalysisFrame = useCallback((frameData: StreamFrame) => {
    const canvas1 = canvasRef1.current;
    const canvas2 = canvasRef2.current;
    
    if (!canvas1 || !canvas2 || !frameData.detections) return;

    const ctx1 = canvas1.getContext('2d');
    const ctx2 = canvas2.getContext('2d');
    
    if (!ctx1 || !ctx2) return;

    // Clear canvases
    ctx1.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx2.clearRect(0, 0, canvasWidth, canvasHeight);

    // Calculate scale factors
    const scaleX = canvasWidth / videoWidth;
    const scaleY = canvasHeight / videoHeight;

    // Draw ROI boundaries
    rois.forEach((roi, index) => {
      const canvas = index === 0 ? canvas1 : canvas2;
      const ctx = index === 0 ? ctx1 : ctx2;
      
      // Scale ROI coordinates
      const x = roi.x * scaleX;
      const y = roi.y * scaleY;
      const w = roi.w * scaleX;
      const h = roi.h * scaleY;

      // Draw ROI rectangle
      ctx.strokeStyle = roi.type === 'packing_area' ? '#00FF00' : '#FF0000';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      // Draw ROI label
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '12px Arial';
      ctx.fillText(roi.label, x + 5, y - 5);
    });

    // Draw detection results
    frameData.detections.forEach((detection) => {
      const roiIndex = rois.findIndex(roi => 
        detection.roi_id.includes(roi.type)
      );
      
      if (roiIndex === -1) return;

      const canvas = roiIndex === 0 ? canvas1 : canvas2;
      const ctx = roiIndex === 0 ? ctx1 : ctx2;
      const roi = rois[roiIndex];

      if (method === 'traditional' && detection.landmarks) {
        // Draw hand landmarks
        drawHandLandmarks(ctx, detection.landmarks, roi, scaleX, scaleY);
      } else if (method === 'qr_code' && detection.coordinates) {
        // Draw QR detection boxes
        drawQRDetections(ctx, detection.coordinates, roi, scaleX, scaleY);
      }

      // Draw confidence indicator
      const confidenceColor = detection.confidence > 0.7 ? '#00FF00' : 
                             detection.confidence > 0.4 ? '#FFFF00' : '#FF0000';
      ctx.fillStyle = confidenceColor;
      ctx.fillRect(roi.x * scaleX + 5, roi.y * scaleY + 20, 
                   (detection.confidence * 50), 10);
      
      // Draw confidence text
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '10px Arial';
      ctx.fillText(`${(detection.confidence * 100).toFixed(1)}%`, 
                   roi.x * scaleX + 5, roi.y * scaleY + 40);
    });

    // Draw frame info
    [ctx1, ctx2].forEach((ctx, index) => {
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '10px Arial';
      ctx.fillText(`Frame: ${frameData.frame_number}`, 10, canvasHeight - 30);
      ctx.fillText(`Time: ${new Date(frameData.timestamp * 1000).toLocaleTimeString()}`, 
                   10, canvasHeight - 15);
    });
  }, [rois, method, videoWidth, videoHeight]);

  // Draw hand landmarks
  const drawHandLandmarks = (ctx: CanvasRenderingContext2D, landmarks: any[], 
                           roi: ROIConfig, scaleX: number, scaleY: number) => {
    landmarks.forEach((hand) => {
      if (Array.isArray(hand)) {
        hand.forEach((landmark) => {
          const x = (roi.x + landmark.x * roi.w) * scaleX;
          const y = (roi.y + landmark.y * roi.h) * scaleY;
          
          // Draw landmark point
          ctx.fillStyle = '#00FF00';
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, 2 * Math.PI);
          ctx.fill();
        });
      }
    });
  };

  // Draw QR code detections
  const drawQRDetections = (ctx: CanvasRenderingContext2D, coordinates: any[], 
                          roi: ROIConfig, scaleX: number, scaleY: number) => {
    coordinates.forEach((coord) => {
      if (coord.corners) {
        ctx.strokeStyle = '#0088FF';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        coord.corners.forEach((corner: any, index: number) => {
          const x = (roi.x + corner.x * roi.w) * scaleX;
          const y = (roi.y + corner.y * roi.h) * scaleY;
          
          if (index === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        
        ctx.closePath();
        ctx.stroke();

        // Draw QR content if available
        if (coord.content) {
          const centerX = (roi.x + coord.bounding_box.center_x) * scaleX;
          const centerY = (roi.y + coord.bounding_box.center_y) * scaleY;
          
          ctx.fillStyle = '#FFFFFF';
          ctx.font = '10px Arial';
          ctx.fillText(coord.content.substring(0, 10), centerX - 25, centerY + 20);
        }
      }
    });
  };

  // Effect to setup SSE when sessionId changes
  useEffect(() => {
    if (sessionId) {
      setupEventSource();
    }
    
    return cleanupEventSource;
  }, [sessionId, setupEventSource, cleanupEventSource]);

  // Stop analysis
  const stopAnalysis = async () => {
    if (!sessionId) return;
    
    try {
      await fetch(`/api/analysis-streaming/stop-analysis/${sessionId}`, {
        method: 'POST'
      });
      cleanupEventSource();
    } catch (error) {
      console.error('Error stopping analysis:', error);
    }
  };

  return (
    <Box p="20px" bg={bgColor} borderRadius="8px" border="1px solid" borderColor={borderColor}>
      
      {/* Header */}
      <VStack spacing="16px" mb="20px">
        <HStack justify="space-between" width="100%">
          <Text fontSize="lg" fontWeight="bold" color={textColor}>
            Real-time Analysis - {method === 'traditional' ? 'Hand Detection' : 'QR Code Detection'}
          </Text>
          <HStack spacing="8px">
            <Badge colorScheme={connectionStatus === 'connected' ? 'green' : 'red'}>
              {connectionStatus}
            </Badge>
            {isStreaming && (
              <IconButton
                aria-label="Stop analysis"
                icon={<FaStop />}
                size="sm"
                colorScheme="red"
                onClick={stopAnalysis}
              />
            )}
          </HStack>
        </HStack>

        {/* Progress and Stats */}
        {sessionStatus && (
          <Box width="100%">
            <HStack justify="space-between" mb="8px">
              <Text fontSize="sm">Progress: {(sessionStatus.progress * 100).toFixed(1)}%</Text>
              <Text fontSize="sm">
                Frame {sessionStatus.frame_count} / {sessionStatus.total_frames}
              </Text>
            </HStack>
            <Progress value={sessionStatus.progress * 100} colorScheme="blue" size="sm" />
          </Box>
        )}
      </VStack>

      {/* Dual Canvas Display */}
      <HStack spacing="20px" justify="center">
        
        {/* Canvas 1 - ROI 1 */}
        <VStack spacing="8px">
          <Text fontSize="sm" fontWeight="medium">
            {rois[0]?.label || 'ROI 1'}
          </Text>
          <Box border="2px solid" borderColor={borderColor} borderRadius="4px">
            <canvas
              ref={canvasRef1}
              width={canvasWidth}
              height={canvasHeight}
              style={{ display: 'block' }}
            />
          </Box>
        </VStack>

        {/* Canvas 2 - ROI 2 */}
        {rois.length > 1 && (
          <VStack spacing="8px">
            <Text fontSize="sm" fontWeight="medium">
              {rois[1]?.label || 'ROI 2'}
            </Text>
            <Box border="2px solid" borderColor={borderColor} borderRadius="4px">
              <canvas
                ref={canvasRef2}
                width={canvasWidth}
                height={canvasHeight}
                style={{ display: 'block' }}
              />
            </Box>
          </VStack>
        )}

      </HStack>

      {/* Detection Statistics */}
      {detectionStats.totalDetections > 0 && (
        <Box mt="20px" p="16px" bg="gray.50" borderRadius="8px">
          <Text fontSize="sm" fontWeight="bold" mb="8px">Detection Statistics</Text>
          <HStack spacing="24px">
            <VStack align="start" spacing="2px">
              <Text fontSize="xs" color="gray.600">Total Detections</Text>
              <Text fontSize="lg" fontWeight="bold">{detectionStats.totalDetections}</Text>
            </VStack>
            <VStack align="start" spacing="2px">
              <Text fontSize="xs" color="gray.600">Average Confidence</Text>
              <Text fontSize="lg" fontWeight="bold">
                {(detectionStats.averageConfidence * 100).toFixed(1)}%
              </Text>
            </VStack>
            <VStack align="start" spacing="2px">
              <Text fontSize="xs" color="gray.600">Recent Events</Text>
              <Text fontSize="lg" fontWeight="bold">{detectionStats.recentEvents.length}</Text>
            </VStack>
          </HStack>
        </Box>
      )}

      {/* Connection Status */}
      {!sessionId && (
        <Box mt="20px" p="16px" bg="yellow.50" borderRadius="8px" textAlign="center">
          <Text fontSize="sm" color="yellow.800">
            No active analysis session. Start analysis to begin real-time visualization.
          </Text>
        </Box>
      )}

    </Box>
  );
};

export default DualAnalysisCanvas;