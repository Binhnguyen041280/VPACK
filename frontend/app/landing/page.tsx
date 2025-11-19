'use client';

import React, { useState } from 'react';
import { Box, ChakraProvider } from '@chakra-ui/react';
import theme from '@/theme/theme';
import { translations, Language } from './translations';

// Components
import LandingNavbar from './components/LandingNavbar';
import HeroSection from './components/HeroSection';
import FeaturesSection from './components/FeaturesSection';
import HowItWorksSection from './components/HowItWorksSection';
import StatsSection from './components/StatsSection';
import CTASection from './components/CTASection';
import LandingFooter from './components/LandingFooter';

export default function LandingPage() {
  const [language, setLanguage] = useState<Language>('vi');
  const t = translations[language];

  return (
    <ChakraProvider theme={theme}>
      <Box
        minH="100vh"
        bg="linear-gradient(180deg, #0b1437 0%, #1B254B 100%)"
        overflowX="hidden"
      >
        <LandingNavbar
          t={t}
          language={language}
          setLanguage={setLanguage}
        />
        <HeroSection t={t} />
        <FeaturesSection t={t} />
        <HowItWorksSection t={t} />
        <StatsSection t={t} />
        <CTASection t={t} />
        <LandingFooter t={t} />
      </Box>
    </ChakraProvider>
  );
}
