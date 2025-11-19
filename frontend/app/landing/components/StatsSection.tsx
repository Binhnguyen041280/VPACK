'use client';

import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  SimpleGrid,
  VStack,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

interface StatsSectionProps {
  t: any;
}

export default function StatsSection({ t }: StatsSectionProps) {
  return (
    <Box
      id="stats"
      py={{ base: '80px', md: '120px' }}
      position="relative"
    >
      <Container maxW="1400px" px={{ base: 4, md: 8 }}>
        {/* Section Header */}
        <VStack spacing={4} mb={16} textAlign="center">
          <Heading
            fontSize={{ base: '2xl', md: '3xl', lg: '4xl' }}
            fontWeight="bold"
            color="white"
          >
            {t.stats.title}
          </Heading>
        </VStack>

        {/* Stats Grid */}
        <SimpleGrid
          columns={{ base: 2, md: 4 }}
          spacing={{ base: 6, md: 8 }}
        >
          {t.stats.items.map((stat: any, index: number) => (
            <MotionBox
              key={index}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
            >
              <Box
                bg="whiteAlpha.50"
                borderRadius="20px"
                p={{ base: 6, md: 8 }}
                textAlign="center"
                border="1px solid"
                borderColor="whiteAlpha.100"
                _hover={{
                  bg: 'whiteAlpha.100',
                  transform: 'translateY(-4px)',
                  boxShadow: '0 20px 40px rgba(74, 37, 225, 0.15)',
                }}
                transition="all 0.3s"
              >
                <VStack spacing={2}>
                  <Text
                    fontSize={{ base: '3xl', md: '4xl', lg: '5xl' }}
                    fontWeight="bold"
                    bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                    bgClip="text"
                  >
                    {stat.value}
                  </Text>
                  <Text
                    fontSize={{ base: 'sm', md: 'md' }}
                    color="whiteAlpha.600"
                    fontWeight="500"
                  >
                    {stat.label}
                  </Text>
                </VStack>
              </Box>
            </MotionBox>
          ))}
        </SimpleGrid>
      </Container>
    </Box>
  );
}
