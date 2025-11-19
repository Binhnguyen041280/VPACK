'use client';

import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Input,
  Textarea,
  Button,
  FormControl,
  FormLabel,
  useToast,
  Flex,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);

interface CTASectionProps {
  t: any;
}

export default function CTASection({ t }: CTASectionProps) {
  const toast = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    message: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate form submission
    await new Promise((resolve) => setTimeout(resolve, 1000));

    toast({
      title: t.cta.form.success,
      status: 'success',
      duration: 5000,
      isClosable: true,
      position: 'top',
    });

    setFormData({
      name: '',
      email: '',
      company: '',
      phone: '',
      message: '',
    });
    setIsSubmitting(false);
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <Box
      id="cta"
      py={{ base: '80px', md: '120px' }}
      position="relative"
      bg="rgba(11, 20, 55, 0.5)"
    >
      {/* Background Effects */}
      <Box
        position="absolute"
        top="0"
        left="0"
        right="0"
        bottom="0"
        bgGradient="linear(to-b, transparent, rgba(74, 37, 225, 0.1), transparent)"
        pointerEvents="none"
      />

      <Container maxW="1200px" px={{ base: 4, md: 8 }} position="relative">
        <Flex
          direction={{ base: 'column', lg: 'row' }}
          gap={{ base: 10, lg: 16 }}
          align="center"
        >
          {/* Left Content */}
          <VStack
            flex="1"
            align={{ base: 'center', lg: 'flex-start' }}
            textAlign={{ base: 'center', lg: 'left' }}
            spacing={6}
          >
            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
            >
              <Heading
                fontSize={{ base: '2xl', md: '3xl', lg: '4xl' }}
                fontWeight="bold"
                color="white"
                mb={4}
              >
                {t.cta.title}
              </Heading>
              <Text
                fontSize={{ base: 'md', md: 'lg' }}
                color="whiteAlpha.600"
                maxW="500px"
              >
                {t.cta.subtitle}
              </Text>
            </MotionBox>
          </VStack>

          {/* Right - Form */}
          <MotionBox
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            viewport={{ once: true }}
            flex="1"
            w="100%"
            maxW={{ base: '100%', lg: '500px' }}
          >
            <Box
              as="form"
              onSubmit={handleSubmit}
              bg="whiteAlpha.50"
              borderRadius="20px"
              p={{ base: 6, md: 8 }}
              border="1px solid"
              borderColor="whiteAlpha.100"
            >
              <VStack spacing={4}>
                <HStack spacing={4} w="100%">
                  <FormControl isRequired>
                    <FormLabel
                      fontSize="sm"
                      color="whiteAlpha.700"
                      mb={1}
                    >
                      {t.cta.form.name}
                    </FormLabel>
                    <Input
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      bg="whiteAlpha.50"
                      border="1px solid"
                      borderColor="whiteAlpha.200"
                      borderRadius="12px"
                      color="white"
                      _placeholder={{ color: 'whiteAlpha.400' }}
                      _hover={{ borderColor: 'whiteAlpha.300' }}
                      _focus={{
                        borderColor: '#7B5AFF',
                        boxShadow: '0 0 0 1px #7B5AFF',
                      }}
                    />
                  </FormControl>

                  <FormControl isRequired>
                    <FormLabel
                      fontSize="sm"
                      color="whiteAlpha.700"
                      mb={1}
                    >
                      {t.cta.form.email}
                    </FormLabel>
                    <Input
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      bg="whiteAlpha.50"
                      border="1px solid"
                      borderColor="whiteAlpha.200"
                      borderRadius="12px"
                      color="white"
                      _placeholder={{ color: 'whiteAlpha.400' }}
                      _hover={{ borderColor: 'whiteAlpha.300' }}
                      _focus={{
                        borderColor: '#7B5AFF',
                        boxShadow: '0 0 0 1px #7B5AFF',
                      }}
                    />
                  </FormControl>
                </HStack>

                <HStack spacing={4} w="100%">
                  <FormControl>
                    <FormLabel
                      fontSize="sm"
                      color="whiteAlpha.700"
                      mb={1}
                    >
                      {t.cta.form.company}
                    </FormLabel>
                    <Input
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      bg="whiteAlpha.50"
                      border="1px solid"
                      borderColor="whiteAlpha.200"
                      borderRadius="12px"
                      color="white"
                      _placeholder={{ color: 'whiteAlpha.400' }}
                      _hover={{ borderColor: 'whiteAlpha.300' }}
                      _focus={{
                        borderColor: '#7B5AFF',
                        boxShadow: '0 0 0 1px #7B5AFF',
                      }}
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel
                      fontSize="sm"
                      color="whiteAlpha.700"
                      mb={1}
                    >
                      {t.cta.form.phone}
                    </FormLabel>
                    <Input
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      bg="whiteAlpha.50"
                      border="1px solid"
                      borderColor="whiteAlpha.200"
                      borderRadius="12px"
                      color="white"
                      _placeholder={{ color: 'whiteAlpha.400' }}
                      _hover={{ borderColor: 'whiteAlpha.300' }}
                      _focus={{
                        borderColor: '#7B5AFF',
                        boxShadow: '0 0 0 1px #7B5AFF',
                      }}
                    />
                  </FormControl>
                </HStack>

                <FormControl>
                  <FormLabel
                    fontSize="sm"
                    color="whiteAlpha.700"
                    mb={1}
                  >
                    {t.cta.form.message}
                  </FormLabel>
                  <Textarea
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    bg="whiteAlpha.50"
                    border="1px solid"
                    borderColor="whiteAlpha.200"
                    borderRadius="12px"
                    color="white"
                    rows={4}
                    _placeholder={{ color: 'whiteAlpha.400' }}
                    _hover={{ borderColor: 'whiteAlpha.300' }}
                    _focus={{
                      borderColor: '#7B5AFF',
                      boxShadow: '0 0 0 1px #7B5AFF',
                    }}
                  />
                </FormControl>

                <Button
                  type="submit"
                  w="100%"
                  size="lg"
                  bgGradient="linear(to-r, #4A25E1, #7B5AFF)"
                  color="white"
                  isLoading={isSubmitting}
                  _hover={{
                    bgGradient: 'linear(to-r, #5B36F2, #8C6BFF)',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 10px 30px rgba(74, 37, 225, 0.4)',
                  }}
                  transition="all 0.3s"
                >
                  {t.cta.form.submit}
                </Button>
              </VStack>
            </Box>
          </MotionBox>
        </Flex>
      </Container>
    </Box>
  );
}
