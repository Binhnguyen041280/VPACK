'use client';

import {
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import BrandnameCanvas from './BrandnameCanvas';
import LocationTimeCanvas from './LocationTimeCanvas';
import VideoSourceCanvas from './VideoSourceCanvas';
import PackingAreaCanvas from './PackingAreaCanvas';
import TimingCanvas from './TimingCanvas';
import { useState, useEffect, useRef } from 'react';
import React from 'react';

interface CanvasMessageProps {
  configStep: 'brandname' | 'location_time' | 'video_source' | 'packing_area' | 'timing';
  onStepChange?: (stepName: string, data: any) => void;
  // Chat-controlled state
  brandName?: string;
  isLoading?: boolean;
  // Step 2 state
  locationTimeData?: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  };
  locationTimeLoading?: boolean;
}

// Height breakpoints for adaptive behavior
type HeightMode = 'compact' | 'normal' | 'spacious';

interface AdaptiveConfig {
  mode: HeightMode;
  fontSize: {
    header: string;
    title: string;
    body: string;
    small: string;
  };
  spacing: {
    section: string;
    item: string;
    padding: string;
  };
  showOptional: boolean;
}

export default function CanvasMessage({ configStep, onStepChange, brandName, isLoading, locationTimeData, locationTimeLoading }: CanvasMessageProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  
  // Height detection and adaptive behavior
  const containerRef = useRef<HTMLDivElement>(null);
  const [availableHeight, setAvailableHeight] = useState(0);
  const [adaptiveConfig, setAdaptiveConfig] = useState<AdaptiveConfig>({
    mode: 'normal',
    fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
    spacing: { section: '16px', item: '12px', padding: '20px' },
    showOptional: true
  });

  // Detect container height and adjust config
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const height = rect.height;
        setAvailableHeight(height);
        
        // Determine adaptive config based on height
        let newConfig: AdaptiveConfig;
        
        if (height < 400) {
          // Compact mode - very small height - Match Navigator compact
          newConfig = {
            mode: 'compact',
            fontSize: { header: 'sm', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '8px', item: '6px', padding: '12px' },
            showOptional: false
          };
        } else if (height < 600) {
          // Normal mode - medium height - Match Navigator normal
          newConfig = {
            mode: 'normal',
            fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '12px', item: '8px', padding: '16px' },
            showOptional: true
          };
        } else {
          // Spacious mode - large height - Slightly larger than Navigator
          newConfig = {
            mode: 'spacious',
            fontSize: { header: 'md', title: 'sm', body: 'xs', small: 'xs' },
            spacing: { section: '20px', item: '16px', padding: '24px' },
            showOptional: true
          };
        }
        
        setAdaptiveConfig(newConfig);
      }
    };

    // Initial measurement
    updateHeight();
    
    // Listen for resize events
    const resizeObserver = new ResizeObserver(updateHeight);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    
    return () => resizeObserver.disconnect();
  }, []);
  
  // Render canvas based on current step with adaptive config
  const renderCanvas = () => {
    const commonProps = { 
      onStepChange, 
      adaptiveConfig, 
      availableHeight 
    };
    
    switch (configStep) {
      case 'brandname':
        return <BrandnameCanvas {...commonProps} brandName={brandName} isLoading={isLoading} />;
      case 'location_time':
        return <LocationTimeCanvas {...commonProps} locationTimeData={locationTimeData} locationTimeLoading={locationTimeLoading} />;
      case 'video_source':
        return <VideoSourceCanvas {...commonProps} />;
      case 'packing_area':
        return <PackingAreaCanvas {...commonProps} />;
      case 'timing':
        return <TimingCanvas {...commonProps} />;
      default:
        return <BrandnameCanvas {...commonProps} brandName={brandName} isLoading={isLoading} />;
    }
  };

  // Determine if current step should have scroll (all except step 1)
  const shouldScroll = configStep !== 'brandname';

  return (
    <Box 
      ref={containerRef}
      h="100%" 
      w="100%"
      overflow={shouldScroll ? "auto" : "hidden"}
      pr={configStep === 'packing_area' ? "12px" : "0"}
      css={shouldScroll ? {
        '&::-webkit-scrollbar': {
          width: '6px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'var(--chakra-colors-gray-100)',
        },
        '&::-webkit-scrollbar-thumb': {
          background: 'var(--chakra-colors-gray-300)',
          borderRadius: '3px',
        },
        '&::-webkit-scrollbar-thumb:hover': {
          background: 'var(--chakra-colors-gray-400)',
        },
        // Ensure content can overflow properly
        overflowY: 'auto',
        overflowX: 'hidden',
      } : {
        overflowY: 'hidden',
        overflowX: 'hidden',
      }}
    >
      {/* Dynamic Canvas Content - No Bot Avatar */}
      {renderCanvas()}
    </Box>
  );
}

