/**
 * SyncedVideoPlayerTest Component
 * Quick integration test cho SyncedVideoPlayer
 * Minimal component để verify functionality
 */

import React from 'react';
import { Box, VStack, Text, Card, CardBody } from '@chakra-ui/react';
import SyncedVideoPlayer from './SyncedVideoPlayer';

const SyncedVideoPlayerTest: React.FC = () => {
  // Test configuration
  const TEST_VIDEO = "/Users/annhu/vtrack_app/V_Track/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4";
  
  const TEST_ROIS = [
    {
      x: 200,
      y: 150, 
      w: 400,
      h: 300,
      type: 'packing_area',
      label: 'Test Hand Detection Area'
    }
  ];

  return (
    <Box p="20px" maxWidth="1200px" mx="auto">
      <VStack spacing="20px" align="stretch">
        
        <Card>
          <CardBody>
            <VStack spacing="12px" align="center">
              <Text fontSize="xl" fontWeight="bold">
                SyncedVideoPlayer Integration Test
              </Text>
              <Text fontSize="sm" color="gray.600" textAlign="center">
                Testing synchronized hand detection overlay với real video playback
              </Text>
            </VStack>
          </CardBody>
        </Card>

        <Card>
          <CardBody p="0">
            <SyncedVideoPlayer
              videoPath={TEST_VIDEO}
              method="traditional"
              rois={TEST_ROIS}
              width="100%"
              height="600px"
              autoPlay={false}
              autoStartAnalysis={true}
              onMetadataLoaded={(metadata) => {
                console.log('Test: Video metadata loaded:', metadata);
              }}
              onAnalysisComplete={(results) => {
                console.log('Test: Analysis completed:', results);
              }}
              onError={(error) => {
                console.error('Test: Error:', error);
              }}
            />
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <VStack align="start" spacing="8px" fontSize="sm">
              <Text fontWeight="bold">Expected Behavior:</Text>
              <Text>• Video loads and displays in player</Text>
              <Text>• Analysis session starts automatically</Text>
              <Text>• Hand detection overlay appears as green dots/lines</Text>
              <Text>• Overlay synchronizes with video playback time</Text>
              <Text>• Confidence filter controls detection visibility</Text>
              <Text>• Overlay toggle shows/hides detection results</Text>
              <Text>• Seeking video updates overlay positions correctly</Text>
            </VStack>
          </CardBody>
        </Card>

      </VStack>
    </Box>
  );
};

export default SyncedVideoPlayerTest;