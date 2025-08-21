'use client';
import { Box, useColorModeValue } from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';

interface VPackIconProps {
  size?: string;
  collapsed?: boolean;
}

export const VPackIcon = ({ size = '40px', collapsed = false }: VPackIconProps) => {
  const borderColor = useColorModeValue('gray.300', 'whiteAlpha.400');
  const { currentColors } = useColorTheme();
  const circleColor = useColorModeValue(currentColors.brand500, 'white');
  
  return (
    <Box
      width={size}
      height={size}
      position="relative"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      {/* Outer Square with rounded corners */}
      <Box
        width="100%"
        height="100%"
        border={(size === '30px' || size === '27px') ? '1.5px solid' : '2px solid'}
        borderColor={borderColor}
        borderRadius={(size === '30px' || size === '27px') ? '6px' : '8px'}
        position="absolute"
        top="0"
        left="0"
      />
      
      {/* Inner Circle with dashed border */}
      <Box
        width={(size === '30px' || size === '27px') ? (size === '27px' ? '16px' : '18px') : '24px'}
        height={(size === '30px' || size === '27px') ? (size === '27px' ? '16px' : '18px') : '24px'}
        border={(size === '30px' || size === '27px') ? '1.5px dashed' : '2px dashed'}
        borderColor={circleColor}
        borderRadius="50%"
        background={`linear-gradient(135deg, ${useColorModeValue(currentColors.primary, currentColors.secondary)} 0%, ${useColorModeValue(currentColors.primary + '1A', currentColors.secondary + '1A')} 100%)`}
        position="relative"
        opacity={0.9}
      >
        {/* Optional: Small center dot for "globe" effect */}
        <Box
          width={(size === '30px' || size === '27px') ? (size === '27px' ? '2.5px' : '3px') : '4px'}
          height={(size === '30px' || size === '27px') ? (size === '27px' ? '2.5px' : '3px') : '4px'}
          bg={circleColor}
          borderRadius="50%"
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          opacity={0.6}
        />
      </Box>
    </Box>
  );
};

export default VPackIcon;