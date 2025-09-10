/**
 * SyncedVideoPlayerDemo Component
 * Demo component to test SyncedVideoPlayer với hand detection
 * Tận dụng test video có sẵn trong system
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Button,
  Text,
  Alert,
  AlertIcon,
  Badge,
  useColorModeValue,
  Card,
  CardHeader,
  CardBody,
  Heading,
  SimpleGrid
} from '@chakra-ui/react';

import SyncedVideoPlayer from './SyncedVideoPlayer';
import type { VideoMetadata, ROIConfig } from './SyncedVideoPlayer';

interface SyncedVideoPlayerDemoProps {
  className?: string;
}

const SyncedVideoPlayerDemo: React.FC<SyncedVideoPlayerDemoProps> = ({
  className
}) => {
  // Demo states
  const [demoStatus, setDemoStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [videoMetadata, setVideoMetadata] = useState<VideoMetadata | null>(null);
  const [analysisResults, setAnalysisResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Test video path (từ analysis_streaming_bp.py)
  const TEST_VIDEO = "/Users/annhu/vtrack_app/V_Track/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4";

  // Demo ROI configurations
  const demoROIs: ROIConfig[] = [
    {
      x: 200,
      y: 150,
      w: 400,
      h: 300,
      type: 'packing_area',
      label: 'Demo Packing Area'
    }
  ];

  // Handlers
  const handleMetadataLoaded = useCallback((metadata: VideoMetadata) => {
    console.log('Demo: Video metadata loaded:', metadata);
    setVideoMetadata(metadata);
    setDemoStatus('ready');
    setError(null);
  }, []);

  const handleAnalysisComplete = useCallback((results: any) => {
    console.log('Demo: Analysis completed:', results);
    setAnalysisResults(results);
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    console.error('Demo: Error occurred:', errorMessage);
    setError(errorMessage);
    setDemoStatus('error');
  }, []);

  const startDemo = useCallback(() => {
    setDemoStatus('loading');
    setError(null);
    setAnalysisResults(null);
  }, []);

  const resetDemo = useCallback(() => {
    setDemoStatus('idle');
    setError(null);
    setAnalysisResults(null);
    setVideoMetadata(null);
  }, []);

  return (
    <Box className={className} p="20px">
      <VStack spacing="24px" align="stretch">
        
        {/* Header */}
        <Card>
          <CardHeader>
            <HStack justify="space-between" align="center">
              <VStack align="start" spacing="4px">
                <Heading size="md">SyncedVideoPlayer Demo</Heading>
                <Text fontSize="sm" color="gray.600">
                  Test synchronized hand detection overlay với video playback
                </Text>
              </VStack>
              
              <HStack spacing="8px">
                <Badge colorScheme={
                  demoStatus === 'ready' ? 'green' :
                  demoStatus === 'loading' ? 'yellow' :
                  demoStatus === 'error' ? 'red' : 'gray'
                }>
                  {demoStatus}
                </Badge>
                
                {demoStatus === 'idle' && (
                  <Button colorScheme="blue" onClick={startDemo}>
                    Start Demo
                  </Button>
                )}
                
                {demoStatus !== 'idle' && (
                  <Button variant="outline" onClick={resetDemo}>
                    Reset Demo
                  </Button>
                )}
              </HStack>
            </HStack>
          </CardHeader>
        </Card>

        {/* Error Display */}
        {error && (
          <Alert status="error">
            <AlertIcon />
            <VStack align="start" flex="1">
              <Text fontWeight="bold">Demo Error</Text>
              <Text fontSize="sm">{error}</Text>
            </VStack>
          </Alert>
        )}

        {/* Demo Info */}
        {demoStatus === 'ready' && videoMetadata && (
          <Card>
            <CardHeader>
              <Heading size="sm">Video Information</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={2} spacing="16px">
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">File</Text>
                  <Text fontSize="sm" fontFamily="mono">{videoMetadata.filename}</Text>
                </VStack>
                
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">Duration</Text>
                  <Text fontSize="sm">{videoMetadata.duration_formatted}</Text>
                </VStack>
                
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">Resolution</Text>
                  <Text fontSize="sm">{videoMetadata.resolution.width} x {videoMetadata.resolution.height}</Text>
                </VStack>
                
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">FPS</Text>
                  <Text fontSize="sm">{videoMetadata.fps}</Text>
                </VStack>
                
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">Frame Count</Text>
                  <Text fontSize="sm">{videoMetadata.frame_count}</Text>
                </VStack>
                
                <VStack align="start" spacing="4px">
                  <Text fontSize="xs" color="gray.600">ROI Count</Text>
                  <Text fontSize="sm">{demoROIs.length}</Text>
                </VStack>
              </SimpleGrid>
            </CardBody>
          </Card>
        )}

        {/* Main Demo Player */}
        {demoStatus === 'loading' && (
          <Box textAlign="center" p="40px">
            <Text>Loading SyncedVideoPlayer demo...</Text>
          </Box>
        )}

        {demoStatus === 'ready' && (
          <Card>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="sm">Synchronized Hand Detection</Heading>
                <Badge colorScheme="green">Real-time Overlay Active</Badge>
              </HStack>
            </CardHeader>
            <CardBody p="0">
              <SyncedVideoPlayer
                videoPath={TEST_VIDEO}
                method="traditional"
                rois={demoROIs}
                onMetadataLoaded={handleMetadataLoaded}
                onAnalysisComplete={handleAnalysisComplete}
                onError={handleError}
                width="100%"
                height="600px"
                autoPlay={false}
                autoStartAnalysis={true}
              />
            </CardBody>
          </Card>
        )}

        {/* Analysis Results */}
        {analysisResults && (
          <Card>
            <CardHeader>
              <Heading size="sm">Analysis Results</Heading>
            </CardHeader>
            <CardBody>
              <Text fontSize="sm" color="gray.600" mb="8px">
                Analysis completed successfully
              </Text>
              <Box
                p="12px"
                bg="gray.50"
                borderRadius="4px"
                fontFamily="mono"
                fontSize="xs"
                overflow="auto"
                maxHeight="200px"
              >
                <pre>{JSON.stringify(analysisResults, null, 2)}</pre>
              </Box>
            </CardBody>
          </Card>
        )}

        {/* Demo Instructions */}
        <Card>
          <CardHeader>
            <Heading size="sm">Demo Instructions</Heading>
          </CardHeader>
          <CardBody>
            <VStack align="start" spacing="8px" fontSize="sm">
              <Text>
                <strong>1.</strong> Click "Start Demo" để tải SyncedVideoPlayer với test video
              </Text>
              <Text>
                <strong>2.</strong> Video player sẽ automatically start hand detection analysis
              </Text>
              <Text>
                <strong>3.</strong> Hand landmarks sẽ hiển thị as green dots và lines trên video
              </Text>
              <Text>
                <strong>4.</strong> Overlay được synchronized chính xác với video playback time
              </Text>
              <Text>
                <strong>5.</strong> Use confidence slider để filter detections by confidence level
              </Text>
              <Text>
                <strong>6.</strong> Toggle overlay on/off với overlay switch
              </Text>
              <Text>
                <strong>7.</strong> Seek video để thấy landmarks appear tại đúng frame positions
              </Text>
            </VStack>
          </CardBody>
        </Card>

        {/* Technical Details */}
        <Card>
          <CardHeader>
            <Heading size="sm">Technical Implementation</Heading>
          </CardHeader>
          <CardBody>
            <VStack align="start" spacing="8px" fontSize="sm">
              <Text>
                <strong>Backend:</strong> HandDetectionStreaming với MediaPipe Hands
              </Text>
              <Text>
                <strong>Streaming:</strong> Server-Sent Events (SSE) cho real-time data
              </Text>
              <Text>
                <strong>Synchronization:</strong> Frame-accurate timing với video timestamp
              </Text>
              <Text>
                <strong>Coordinate Transform:</strong> ROI coordinates → Full video coordinates → Canvas pixels
              </Text>
              <Text>
                <strong>Performance:</strong> Detection buffering với frame-based filtering
              </Text>
              <Text>
                <strong>Canvas Overlay:</strong> HTML5 Canvas positioned absolute over video element
              </Text>
            </VStack>
          </CardBody>
        </Card>

      </VStack>
    </Box>
  );
};

export default SyncedVideoPlayerDemo;