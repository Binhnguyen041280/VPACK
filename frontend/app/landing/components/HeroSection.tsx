'use client';

import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  HStack,
  VStack,
  Image,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { MdPlayArrow } from 'react-icons/md';

const MotionBox = motion(Box);
const MotionHeading = motion(Heading);
const MotionText = motion(Text);

interface HeroSectionProps {
  t: any;
}

export default function HeroSection({ t }: HeroSectionProps) {
  return (
    <Box
      id="hero"
      pt={{ base: '120px', md: '140px' }}
      pb={{ base: '80px', md: '120px' }}
      position="relative"
      overflow="hidden"
    >
      {/* Background Effects */}
      <Box
        position="absolute"
        top="-50%"
        right="-20%"
        width="800px"
        height="800px"
        borderRadius="full"
        bg="radial-gradient(circle, rgba(74, 37, 225, 0.3) 0%, transparent 70%)"
        filter="blur(60px)"
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-30%"
        left="-10%"
        width="600px"
        height="600px"
        borderRadius="full"
        bg="radial-gradient(circle, rgba(123, 90, 255, 0.2) 0%, transparent 70%)"
        filter="blur(60px)"
        pointerEvents="none"
      />

      <Container maxW="1400px" px={{ base: 4, md: 8 }}>
        <Flex
          direction={{ base: 'column', lg: 'row' }}
          align="center"
          justify="space-between"
          gap={{ base: 10, lg: 16 }}
        >
          {/* Left Content */}
          <VStack
            align={{ base: 'center', lg: 'flex-start' }}
            spacing={6}
            maxW={{ base: '100%', lg: '50%' }}
            textAlign={{ base: 'center', lg: 'left' }}
          >
            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Text
                fontSize="sm"
                fontWeight="600"
                color="#7B5AFF"
                textTransform="uppercase"
                letterSpacing="2px"
              >
                {t.hero.tagline}
              </Text>
            </MotionBox>

            <MotionHeading
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              fontSize={{ base: '3xl', md: '4xl', lg: '5xl' }}
              fontWeight="bold"
              color="white"
              lineHeight="1.2"
            >
              {t.hero.headline}{' '}
              <Text
                as="span"
                bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                bgClip="text"
              >
                {t.hero.headlineHighlight}
              </Text>
            </MotionHeading>

            <MotionText
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              fontSize={{ base: 'md', md: 'lg' }}
              color="whiteAlpha.700"
              maxW="500px"
            >
              {t.hero.description}
            </MotionText>

            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <HStack spacing={4} pt={4}>
                <Button
                  size="lg"
                  bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                  color="white"
                  px={8}
                  _hover={{
                    bgGradient: 'linear(to-r, #5B36F2, #8C6BFF)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 20px 40px rgba(74, 37, 225, 0.4)',
                  }}
                  transition="all 0.3s"
                  onClick={() => {
                    const element = document.getElementById('cta');
                    element?.scrollIntoView({ behavior: 'smooth' });
                  }}
                >
                  {t.hero.cta}
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  borderColor="whiteAlpha.300"
                  color="white"
                  leftIcon={<MdPlayArrow />}
                  _hover={{
                    bg: 'whiteAlpha.100',
                    borderColor: 'whiteAlpha.500',
                    transform: 'translateY(-2px)',
                  }}
                  transition="all 0.3s"
                >
                  {t.hero.secondaryCta}
                </Button>
              </HStack>
            </MotionBox>

            {/* Trust Badge */}
            <MotionBox
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              pt={8}
            >
              <Text fontSize="xs" color="whiteAlpha.500" mb={3}>
                {t.hero.trustedBy}
              </Text>
              <HStack spacing={6} opacity={0.5}>
                {/* Placeholder for company logos */}
                {[1, 2, 3, 4].map((i) => (
                  <Box
                    key={i}
                    w="60px"
                    h="24px"
                    bg="whiteAlpha.200"
                    borderRadius="md"
                  />
                ))}
              </HStack>
            </MotionBox>
          </VStack>

          {/* Right Content - Product Screenshot */}
          <MotionBox
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            flex="1"
            maxW={{ base: '100%', lg: '50%' }}
          >
            <Box
              position="relative"
              borderRadius="20px"
              overflow="hidden"
              boxShadow="0 40px 80px rgba(0, 0, 0, 0.5)"
              border="1px solid"
              borderColor="whiteAlpha.100"
            >
              {/* Mock Dashboard UI */}
              <Box
                bg="navy.800"
                p={4}
                minH="400px"
                position="relative"
              >
                {/* Top Bar */}
                <HStack spacing={2} mb={4}>
                  <Box w="12px" h="12px" borderRadius="full" bg="red.500" />
                  <Box w="12px" h="12px" borderRadius="full" bg="orange.500" />
                  <Box w="12px" h="12px" borderRadius="full" bg="green.500" />
                </HStack>

                {/* Mock Content */}
                <VStack spacing={4} align="stretch">
                  <HStack justify="space-between">
                    <Box>
                      <Text fontSize="xs" color="whiteAlpha.500">
                        Total Count
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="white">
                        12,847
                      </Text>
                    </Box>
                    <Box
                      px={3}
                      py={1}
                      borderRadius="full"
                      bg="green.500"
                      color="white"
                      fontSize="xs"
                    >
                      +12.5%
                    </Box>
                  </HStack>

                  {/* Mock Chart */}
                  <Box h="200px" position="relative">
                    <Box
                      position="absolute"
                      bottom="0"
                      left="0"
                      right="0"
                      h="150px"
                      bgGradient="linear(to-t, rgba(74, 37, 225, 0.3), transparent)"
                      borderRadius="md"
                    />
                    {/* Chart bars */}
                    <HStack
                      position="absolute"
                      bottom="0"
                      left="0"
                      right="0"
                      justify="space-around"
                      align="flex-end"
                      h="150px"
                      px={4}
                    >
                      {[60, 80, 45, 90, 70, 85, 95].map((h, i) => (
                        <Box
                          key={i}
                          w="20px"
                          h={`${h}%`}
                          bgGradient="linear(to-t, #4A25E1, #7B5AFF)"
                          borderRadius="md"
                        />
                      ))}
                    </HStack>
                  </Box>

                  {/* Status */}
                  <HStack justify="space-between" pt={2}>
                    <HStack>
                      <Box w="8px" h="8px" borderRadius="full" bg="green.500" />
                      <Text fontSize="xs" color="whiteAlpha.700">
                        Live Tracking
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="whiteAlpha.500">
                      Updated 2s ago
                    </Text>
                  </HStack>
                </VStack>
              </Box>
            </Box>
          </MotionBox>
        </Flex>
      </Container>
    </Box>
  );
}
