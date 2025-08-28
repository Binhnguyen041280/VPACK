'use client';
import { Box, useColorModeValue } from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import Image from 'next/image';

interface VPackIconProps {
  size?: string;
  collapsed?: boolean;
}

export const VPackIcon = ({ size = '40px', collapsed = false }: VPackIconProps) => {
  const { currentColors } = useColorTheme();
  
  // Convert size string to number for calculations
  const sizeNum = parseInt(size.replace('px', ''));
  
  return (
    <Box
      width={size}
      height={size}
      position="relative"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      {/* SVG Logo using Next.js Image component for optimized loading */}
      <Image
        src="/LOGO ICON.svg"
        alt="V.PACK Logo"
        width={sizeNum}
        height={sizeNum}
        style={{
          filter: useColorModeValue(
            `hue-rotate(${currentColors.brand500 === '#3182CE' ? '0deg' : '180deg'})`,
            'brightness(0.9) contrast(1.1)'
          ),
          opacity: 0.9,
        }}
        priority={true}
      />
    </Box>
  );
};

export default VPackIcon;