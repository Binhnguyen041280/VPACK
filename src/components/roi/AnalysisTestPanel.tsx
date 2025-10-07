/**
 * Analysis Test Panel Component
 * Test panel để kiểm tra real-time analysis streaming
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  VStack,
  HStack,
  Button,
  Text,
  Badge,
  Alert,
  AlertIcon,
  Code,
  Textarea,
  useToast,
  Divider
} from '@chakra-ui/react';
// import DualAnalysisCanvas from './DualAnalysisCanvas'; // TODO: File missing

interface AnalysisTestPanelProps {
  onClose?: () => void;
}

const AnalysisTestPanel: React.FC<AnalysisTestPanelProps> = ({ onClose }) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [method, setMethod] = useState<'traditional' | 'qr_code'>('traditional');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<any>(null);
  const [streamLogs, setStreamLogs] = useState<string[]>([]);
  const toast = useToast();

  // Test data
  const testROIs = {
    traditional: [
      {
        x: 480,
        y: 270,
        w: 960,
        h: 540,
        type: 'packing_area',
        label: 'Test Packing Area'
      }
    ],
    qr_code: [
      {
        x: 480,
        y: 270,
        w: 640,
        h: 360,
        type: 'qr_mvd',
        label: 'Test QR MVD Area'
      },
      {
        x: 1170,
        y: 270,
        w: 320,
        h: 180,
        type: 'qr_trigger',
        label: 'Test QR Trigger Area'
      }
    ]
  };

  // Start analysis test
  const startAnalysisTest = async (testMethod: 'traditional' | 'qr_code') => {
    setIsLoading(true);
    setError(null);
    setStreamLogs([]);

    try {
      const endpoint = testMethod === 'traditional' 
        ? '/api/analysis-streaming/test-traditional'
        : '/api/analysis-streaming/test-qr';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (data.success) {
        setSessionId(data.session_id);
        setMethod(testMethod);
        setSessionData(data);
        setStreamLogs(prev => [...prev, `✅ ${testMethod} test started: ${data.session_id}`]);
        
        toast({
          title: 'Analysis Started',
          description: `${testMethod} analysis test started successfully`,
          status: 'success',
          duration: 3000
        });
      } else {
        throw new Error(data.error || 'Failed to start analysis');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(errorMessage);
      setStreamLogs(prev => [...prev, `❌ Error: ${errorMessage}`]);
      
      toast({
        title: 'Analysis Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Stop analysis
  const stopAnalysis = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`/api/analysis-streaming/stop-analysis/${sessionId}`, {
        method: 'POST'
      });

      const data = await response.json();
      
      if (data.success) {
        setStreamLogs(prev => [...prev, `🛑 Analysis stopped: ${sessionId}`]);
        setSessionId(null);
        setSessionData(null);
        
        toast({
          title: 'Analysis Stopped',
          description: 'Analysis session stopped successfully',
          status: 'info',
          duration: 3000
        });
      }
    } catch (error) {
      console.error('Error stopping analysis:', error);
    }
  };

  // Cleanup session
  const cleanupSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`/api/analysis-streaming/cleanup-session/${sessionId}`, {
        method: 'POST'
      });
      setStreamLogs(prev => [...prev, `🧹 Session cleaned up: ${sessionId}`]);
    } catch (error) {
      console.error('Error cleaning up session:', error);
    }
  };

  // Handle analysis completion
  const handleAnalysisComplete = (results: any) => {
    setStreamLogs(prev => [...prev, `🏁 Analysis completed: ${JSON.stringify(results)}`]);
    toast({
      title: 'Analysis Complete',
      description: 'Video analysis has been completed',
      status: 'success',
      duration: 5000
    });
  };

  // Handle analysis error
  const handleAnalysisError = (errorMessage: string) => {
    setStreamLogs(prev => [...prev, `⚠️ Stream error: ${errorMessage}`]);
    setError(errorMessage);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sessionId) {
        cleanupSession();
      }
    };
  }, [sessionId]);

  return (
    <Box p="24px" maxW="1200px" mx="auto">
      <VStack spacing="24px">
        
        {/* Header */}
        <HStack justify="space-between" width="100%">
          <Text fontSize="xl" fontWeight="bold">
            Real-time Analysis Test Panel
          </Text>
          {onClose && (
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </HStack>

        {/* Control Panel */}
        <Box width="100%" p="16px" borderWidth="1px" borderRadius="8px">
          <VStack spacing="16px">
            <Text fontSize="lg" fontWeight="medium">Test Controls</Text>
            
            <HStack spacing="16px" wrap="wrap">
              <Button
                colorScheme="blue"
                onClick={() => startAnalysisTest('traditional')}
                isLoading={isLoading && method === 'traditional'}
                isDisabled={!!sessionId}
              >
                Test Traditional Detection
              </Button>
              
              <Button
                colorScheme="green"
                onClick={() => startAnalysisTest('qr_code')}
                isLoading={isLoading && method === 'qr_code'}
                isDisabled={!!sessionId}
              >
                Test QR Code Detection
              </Button>
              
              {sessionId && (
                <Button
                  colorScheme="red"
                  onClick={stopAnalysis}
                >
                  Stop Analysis
                </Button>
              )}
            </HStack>

            {/* Session Status */}
            {sessionId && (
              <HStack spacing="12px">
                <Badge colorScheme="green">Active Session</Badge>
                <Text fontSize="sm" fontFamily="mono">{sessionId}</Text>
                <Badge colorScheme="blue">{method}</Badge>
              </HStack>
            )}
          </VStack>
        </Box>

        {/* Error Display */}
        {error && (
          <Alert status="error">
            <AlertIcon />
            <Text>{error}</Text>
          </Alert>
        )}

        {/* Session Info */}
        {sessionData && (
          <Box width="100%" p="16px" bg="gray.50" borderRadius="8px">
            <Text fontSize="md" fontWeight="medium" mb="8px">Session Information</Text>
            <Code p="12px" borderRadius="4px" fontSize="sm" width="100%">
              <pre>{JSON.stringify(sessionData, null, 2)}</pre>
            </Code>
          </Box>
        )}

        {/* Dual Canvas Analysis */}
        {sessionId && (
          <Box p={4} bg="gray.50" borderRadius="md">
            <Text>DualAnalysisCanvas component temporarily disabled (file missing)</Text>
          </Box>
          // <DualAnalysisCanvas
          //   sessionId={sessionId}
          //   method={method}
          //   rois={testROIs[method]}
          //   videoWidth={1920}
          //   videoHeight={1080}
          //   onAnalysisComplete={handleAnalysisComplete}
          //   onError={handleAnalysisError}
          // />
        )}

        <Divider />

        {/* Stream Logs */}
        <Box width="100%">
          <Text fontSize="lg" fontWeight="medium" mb="8px">Stream Logs</Text>
          <Textarea
            value={streamLogs.join('\n')}
            readOnly
            height="200px"
            fontFamily="mono"
            fontSize="sm"
            placeholder="Stream logs will appear here..."
          />
        </Box>

        {/* Instructions */}
        <Box width="100%" p="16px" bg="blue.50" borderRadius="8px">
          <Text fontSize="md" fontWeight="medium" mb="8px">Test Instructions</Text>
          <VStack align="start" spacing="4px" fontSize="sm">
            <Text>1. Click "Test Traditional Detection" to start hand detection analysis</Text>
            <Text>2. Click "Test QR Code Detection" to start QR code analysis</Text>
            <Text>3. Watch the dual canvas for real-time visualization</Text>
            <Text>4. Check stream logs for detailed information</Text>
            <Text>5. Use "Stop Analysis" to terminate the session</Text>
          </VStack>
        </Box>

      </VStack>
    </Box>
  );
};

export default AnalysisTestPanel;