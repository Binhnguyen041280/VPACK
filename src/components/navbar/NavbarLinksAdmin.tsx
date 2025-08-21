'use client';
// Chakra Imports
import {
  Button,
  Flex,
  Icon,
  useColorMode,
  useColorModeValue,
} from '@chakra-ui/react';
import { SidebarResponsive } from '@/components/sidebar/Sidebar';
import { IoMdMoon, IoMdSunny } from 'react-icons/io';
import { MdPalette } from 'react-icons/md';
import routes from '@/routes';
import { useColorTheme } from '@/contexts/ColorThemeContext';

export default function HeaderLinks(props: {
  secondary: boolean;
}) {
  const { secondary } = props;
  const { colorMode, toggleColorMode } = useColorMode();
  const { colorTheme, toggleColorTheme, currentColors } = useColorTheme();
  // Chakra Color Mode
  const navbarIcon = useColorModeValue('gray.500', 'white');
  let menuBg = useColorModeValue('white', 'navy.800');
  const shadow = useColorModeValue(
    '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
    '0px 41px 75px #081132',
  );

  return (
    <Flex
      zIndex="100"
      w={{ sm: '100%', md: 'auto' }}
      alignItems="center"
      flexDirection="row"
      bg={menuBg}
      flexWrap={secondary ? { base: 'wrap', md: 'nowrap' } : 'unset'}
      p="10px"
      borderRadius="30px"
      boxShadow={shadow}
    >
      <SidebarResponsive routes={routes} />

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
        me="8px"
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
