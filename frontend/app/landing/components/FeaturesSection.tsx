'use client';

import React from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  SimpleGrid,
  VStack,
  Icon,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import {
  MdAutoGraph,
  MdRemoveRedEye,
  MdAnalytics,
  MdIntegrationInstructions,
} from 'react-icons/md';

const MotionBox = motion(Box);

interface FeaturesSectionProps {
  t: any;
}

const icons = [
  MdAutoGraph,
  MdRemoveRedEye,
  MdAnalytics,
  MdIntegrationInstructions,
];

export default function FeaturesSection({ t }: FeaturesSectionProps) {
  return (
    <Box
      id="features"
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
            {t.features.title}
          </Heading>
          <Text
            fontSize={{ base: 'md', md: 'lg' }}
            color="whiteAlpha.600"
            maxW="600px"
          >
            {t.features.subtitle}
          </Text>
        </VStack>

        {/* Features Grid */}
        <SimpleGrid
          columns={{ base: 1, md: 2, lg: 4 }}
          spacing={{ base: 6, md: 8 }}
        >
          {t.features.items.map((feature: any, index: number) => (
            <MotionBox
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
            >
              <Box
                bg="whiteAlpha.50"
                borderRadius="20px"
                p={8}
                h="100%"
                border="1px solid"
                borderColor="whiteAlpha.100"
                _hover={{
                  bg: 'whiteAlpha.100',
                  transform: 'translateY(-8px)',
                  boxShadow: '0 20px 40px rgba(74, 37, 225, 0.2)',
                  borderColor: 'whiteAlpha.200',
                }}
                transition="all 0.3s"
                cursor="pointer"
              >
                <VStack align="flex-start" spacing={4}>
                  {/* Icon */}
                  <Box
                    p={3}
                    borderRadius="14px"
                    bgGradient="linear(to-br, #4A25E1, #7B5AFF)"
                  >
                    <Icon
                      as={icons[index]}
                      boxSize={6}
                      color="white"
                    />
                  </Box>

                  {/* Title */}
                  <Heading
                    fontSize="lg"
                    fontWeight="600"
                    color="white"
                  >
                    {feature.title}
                  </Heading>

                  {/* Description */}
                  <Text
                    fontSize="sm"
                    color="whiteAlpha.600"
                    lineHeight="1.7"
                  >
                    {feature.description}
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
