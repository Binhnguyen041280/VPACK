'use client';

import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

interface HowItWorksSectionProps {
  t: any;
}

export default function HowItWorksSection({ t }: HowItWorksSectionProps) {
  return (
    <Box
      id="how-it-works"
      py={{ base: '80px', md: '120px' }}
      position="relative"
      bg="rgba(11, 20, 55, 0.5)"
    >
      {/* Background Effect */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        width="600px"
        height="600px"
        borderRadius="full"
        bg="radial-gradient(circle, rgba(74, 37, 225, 0.15) 0%, transparent 70%)"
        filter="blur(60px)"
        pointerEvents="none"
      />

      <Container maxW="1400px" px={{ base: 4, md: 8 }} position="relative">
        {/* Section Header */}
        <VStack spacing={4} mb={16} textAlign="center">
          <Heading
            fontSize={{ base: '2xl', md: '3xl', lg: '4xl' }}
            fontWeight="bold"
            color="white"
          >
            {t.howItWorks.title}
          </Heading>
          <Text
            fontSize={{ base: 'md', md: 'lg' }}
            color="whiteAlpha.600"
            maxW="600px"
          >
            {t.howItWorks.subtitle}
          </Text>
        </VStack>

        {/* Steps */}
        <Flex
          direction={{ base: 'column', lg: 'row' }}
          justify="center"
          align={{ base: 'center', lg: 'stretch' }}
          gap={{ base: 8, lg: 0 }}
        >
          {t.howItWorks.steps.map((step: any, index: number) => (
            <MotionBox
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.2 }}
              viewport={{ once: true }}
              flex="1"
              position="relative"
            >
              {/* Connector Line */}
              {index < t.howItWorks.steps.length - 1 && (
                <Box
                  display={{ base: 'none', lg: 'block' }}
                  position="absolute"
                  top="40px"
                  right="-50%"
                  width="100%"
                  height="2px"
                  bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                  opacity={0.3}
                />
              )}

              <VStack
                spacing={4}
                textAlign="center"
                px={{ base: 4, lg: 8 }}
              >
                {/* Step Number */}
                <Box
                  position="relative"
                  w="80px"
                  h="80px"
                  borderRadius="full"
                  bgGradient="linear(to-br, #4A25E1, #7B5AFF)"
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  boxShadow="0 20px 40px rgba(74, 37, 225, 0.3)"
                >
                  <Text
                    fontSize="2xl"
                    fontWeight="bold"
                    color="white"
                  >
                    {step.step}
                  </Text>
                </Box>

                {/* Title */}
                <Heading
                  fontSize="xl"
                  fontWeight="600"
                  color="white"
                  pt={2}
                >
                  {step.title}
                </Heading>

                {/* Description */}
                <Text
                  fontSize="sm"
                  color="whiteAlpha.600"
                  lineHeight="1.7"
                  maxW="280px"
                >
                  {step.description}
                </Text>
              </VStack>
            </MotionBox>
          ))}
        </Flex>
      </Container>
    </Box>
  );
}
