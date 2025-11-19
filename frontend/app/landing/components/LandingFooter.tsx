'use client';

import React from 'react';
import {
  Box,
  Container,
  Text,
  VStack,
  HStack,
  SimpleGrid,
  Link,
  Image,
  Divider,
  Icon,
} from '@chakra-ui/react';
import {
  MdEmail,
  MdPhone,
  MdLocationOn,
} from 'react-icons/md';
import {
  IoLogoFacebook,
  IoLogoLinkedin,
  IoLogoYoutube,
} from 'react-icons/io5';

interface LandingFooterProps {
  t: any;
}

export default function LandingFooter({ t }: LandingFooterProps) {
  return (
    <Box
      as="footer"
      bg="rgba(11, 20, 55, 0.8)"
      borderTop="1px solid"
      borderColor="whiteAlpha.100"
      py={{ base: 12, md: 16 }}
    >
      <Container maxW="1400px" px={{ base: 4, md: 8 }}>
        <SimpleGrid
          columns={{ base: 1, md: 2, lg: 4 }}
          spacing={{ base: 8, md: 12 }}
          mb={12}
        >
          {/* Brand Column */}
          <VStack align="flex-start" spacing={4}>
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
            <Text
              fontSize="sm"
              color="whiteAlpha.600"
              lineHeight="1.7"
              maxW="280px"
            >
              {t.footer.description}
            </Text>
            <HStack spacing={3} pt={2}>
              <Link
                href="#"
                isExternal
                p={2}
                borderRadius="full"
                bg="whiteAlpha.100"
                _hover={{ bg: 'whiteAlpha.200' }}
                transition="all 0.2s"
              >
                <Icon as={IoLogoFacebook} color="whiteAlpha.800" boxSize={4} />
              </Link>
              <Link
                href="#"
                isExternal
                p={2}
                borderRadius="full"
                bg="whiteAlpha.100"
                _hover={{ bg: 'whiteAlpha.200' }}
                transition="all 0.2s"
              >
                <Icon as={IoLogoLinkedin} color="whiteAlpha.800" boxSize={4} />
              </Link>
              <Link
                href="#"
                isExternal
                p={2}
                borderRadius="full"
                bg="whiteAlpha.100"
                _hover={{ bg: 'whiteAlpha.200' }}
                transition="all 0.2s"
              >
                <Icon as={IoLogoYoutube} color="whiteAlpha.800" boxSize={4} />
              </Link>
            </HStack>
          </VStack>

          {/* Product Column */}
          <VStack align="flex-start" spacing={3}>
            <Text
              fontSize="sm"
              fontWeight="600"
              color="white"
              textTransform="uppercase"
              letterSpacing="1px"
              mb={2}
            >
              {t.footer.product}
            </Text>
            {['features', 'pricing', 'demo'].map((item) => (
              <Link
                key={item}
                href="#"
                fontSize="sm"
                color="whiteAlpha.600"
                _hover={{ color: 'white' }}
                transition="color 0.2s"
              >
                {t.footer.links[item]}
              </Link>
            ))}
          </VStack>

          {/* Company Column */}
          <VStack align="flex-start" spacing={3}>
            <Text
              fontSize="sm"
              fontWeight="600"
              color="white"
              textTransform="uppercase"
              letterSpacing="1px"
              mb={2}
            >
              {t.footer.company}
            </Text>
            {['about', 'careers', 'contact'].map((item) => (
              <Link
                key={item}
                href="#"
                fontSize="sm"
                color="whiteAlpha.600"
                _hover={{ color: 'white' }}
                transition="color 0.2s"
              >
                {t.footer.links[item]}
              </Link>
            ))}
          </VStack>

          {/* Support Column */}
          <VStack align="flex-start" spacing={3}>
            <Text
              fontSize="sm"
              fontWeight="600"
              color="white"
              textTransform="uppercase"
              letterSpacing="1px"
              mb={2}
            >
              {t.footer.support}
            </Text>
            {['docs', 'help', 'privacy'].map((item) => (
              <Link
                key={item}
                href="#"
                fontSize="sm"
                color="whiteAlpha.600"
                _hover={{ color: 'white' }}
                transition="color 0.2s"
              >
                {t.footer.links[item]}
              </Link>
            ))}
          </VStack>
        </SimpleGrid>

        <Divider borderColor="whiteAlpha.100" />

        {/* Bottom Bar */}
        <HStack
          justify="space-between"
          pt={8}
          flexDirection={{ base: 'column', md: 'row' }}
          spacing={4}
        >
          <Text fontSize="sm" color="whiteAlpha.500">
            {t.footer.copyright}
          </Text>
          <HStack spacing={6}>
            <HStack spacing={2} color="whiteAlpha.500">
              <Icon as={MdEmail} boxSize={4} />
              <Text fontSize="sm">contact@epack.vn</Text>
            </HStack>
            <HStack spacing={2} color="whiteAlpha.500">
              <Icon as={MdPhone} boxSize={4} />
              <Text fontSize="sm">+84 28 1234 5678</Text>
            </HStack>
          </HStack>
        </HStack>
      </Container>
    </Box>
  );
}
