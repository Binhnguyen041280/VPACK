'use client';

import React from 'react';
import {
  Box,
  Flex,
  HStack,
  Button,
  Image,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  useDisclosure,
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  DrawerBody,
  VStack,
} from '@chakra-ui/react';
import { HamburgerIcon } from '@chakra-ui/icons';
import { MdLanguage } from 'react-icons/md';
import { Language } from '../translations';

interface LandingNavbarProps {
  t: any;
  language: Language;
  setLanguage: (lang: Language) => void;
}

export default function LandingNavbar({
  t,
  language,
  setLanguage,
}: LandingNavbarProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
    onClose();
  };

  const navItems = [
    { label: t.nav.features, id: 'features' },
    { label: t.nav.howItWorks, id: 'how-it-works' },
    { label: t.nav.benefits, id: 'stats' },
    { label: t.nav.contact, id: 'cta' },
  ];

  return (
    <Box
      position="fixed"
      top="0"
      left="0"
      right="0"
      zIndex="1000"
      bg="rgba(11, 20, 55, 0.8)"
      backdropFilter="blur(20px)"
      borderBottom="1px solid"
      borderColor="whiteAlpha.100"
    >
      <Flex
        maxW="1400px"
        mx="auto"
        px={{ base: 4, md: 8 }}
        py={4}
        align="center"
        justify="space-between"
      >
        {/* Logo */}
        <HStack spacing={3}>
          <Image
            src="/logo.png"
            alt="ePACK Logo"
            h="40px"
            w="40px"
            objectFit="contain"
          />
          <Text
            fontSize="xl"
            fontWeight="bold"
            bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
            bgClip="text"
          >
            ePACK
          </Text>
        </HStack>

        {/* Desktop Navigation */}
        <HStack spacing={8} display={{ base: 'none', md: 'flex' }}>
          {navItems.map((item) => (
            <Text
              key={item.id}
              color="whiteAlpha.800"
              fontSize="sm"
              fontWeight="500"
              cursor="pointer"
              _hover={{ color: 'white' }}
              onClick={() => scrollToSection(item.id)}
              transition="color 0.2s"
            >
              {item.label}
            </Text>
          ))}
        </HStack>

        {/* Right Side */}
        <HStack spacing={4}>
          {/* Language Switcher */}
          <Menu>
            <MenuButton
              as={IconButton}
              icon={<MdLanguage />}
              variant="ghost"
              color="whiteAlpha.800"
              _hover={{ bg: 'whiteAlpha.100' }}
              aria-label="Change language"
            />
            <MenuList bg="navy.800" borderColor="whiteAlpha.200">
              <MenuItem
                bg={language === 'vi' ? 'whiteAlpha.100' : 'transparent'}
                _hover={{ bg: 'whiteAlpha.200' }}
                onClick={() => setLanguage('vi')}
              >
                🇻🇳 Tiếng Việt
              </MenuItem>
              <MenuItem
                bg={language === 'en' ? 'whiteAlpha.100' : 'transparent'}
                _hover={{ bg: 'whiteAlpha.200' }}
                onClick={() => setLanguage('en')}
              >
                🇺🇸 English
              </MenuItem>
            </MenuList>
          </Menu>

          {/* CTA Button */}
          <Button
            display={{ base: 'none', md: 'flex' }}
            size="sm"
            bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
            color="white"
            _hover={{
              bgGradient: 'linear(to-r, #5B36F2, #8C6BFF)',
              transform: 'translateY(-2px)',
              boxShadow: '0 10px 20px rgba(74, 37, 225, 0.3)',
            }}
            transition="all 0.2s"
            onClick={() => scrollToSection('cta')}
          >
            {t.nav.getStarted}
          </Button>

          {/* Mobile Menu Button */}
          <IconButton
            display={{ base: 'flex', md: 'none' }}
            icon={<HamburgerIcon />}
            variant="ghost"
            color="whiteAlpha.800"
            _hover={{ bg: 'whiteAlpha.100' }}
            onClick={onOpen}
            aria-label="Open menu"
          />
        </HStack>
      </Flex>

      {/* Mobile Drawer */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent bg="navy.900">
          <DrawerCloseButton color="white" />
          <DrawerBody pt={16}>
            <VStack spacing={6} align="stretch">
              {navItems.map((item) => (
                <Text
                  key={item.id}
                  color="whiteAlpha.800"
                  fontSize="lg"
                  fontWeight="500"
                  cursor="pointer"
                  _hover={{ color: 'white' }}
                  onClick={() => scrollToSection(item.id)}
                >
                  {item.label}
                </Text>
              ))}
              <Button
                mt={4}
                bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                color="white"
                _hover={{
                  bgGradient: 'linear(to-r, #5B36F2, #8C6BFF)',
                }}
                onClick={() => scrollToSection('cta')}
              >
                {t.nav.getStarted}
              </Button>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
}
