'use client';
import {
  Button,
  Flex,
  Icon,
  useColorMode,
  useColorModeValue,
} from '@chakra-ui/react';
import { IoMdMoon, IoMdSunny } from 'react-icons/io';
import { MdPalette } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

export default function ToggleButtons() {
  const { colorMode, toggleColorMode } = useColorMode();
  const { toggleColorTheme, currentColors } = useColorTheme();
  
  const navbarIcon = useColorModeValue('gray.500', 'white');
  const menuBg = useColorModeValue('white', 'navy.800');
  const shadow = useColorModeValue(
    '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
    '0px 41px 75px #081132',
  );

  return (
    <Flex
      position="fixed"
      top="20px"
      right="20px"
      zIndex="100"
      alignItems="center"
      flexDirection="row"
      bg={menuBg}
      p="10px"
      borderRadius="30px"
      boxShadow={shadow}
      gap="8px"
    >
      {/* Color Theme Toggle */}
      <Button
        variant="no-hover"
        bg="transparent"
        p="4px"
        minW="unset"
        minH="unset"
        h="20px"
        w="20px"
        borderRadius="full"
        onClick={toggleColorTheme}
        _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
      >
        <Icon
          h="10px"
          w="10px"
          color={currentColors.brand500}
          as={MdPalette}
        />
      </Button>

      {/* Dark/Light Mode Toggle */}
      <Button
        variant="no-hover"
        bg="transparent"
        p="4px"
        minW="unset"
        minH="unset"
        h="20px"
        w="20px"
        borderRadius="full"
        onClick={toggleColorMode}
        _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
      >
        <Icon
          h="10px"
          w="10px"
          color={navbarIcon}
          as={colorMode === 'light' ? IoMdMoon : IoMdSunny}
        />
      </Button>
    </Flex>
  );
}