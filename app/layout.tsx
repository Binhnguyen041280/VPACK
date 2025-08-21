'use client';
import React, { ReactNode, useState } from 'react';
import type { AppProps } from 'next/app';
import { ChakraProvider, Box, Portal, useDisclosure } from '@chakra-ui/react';
import theme from '@/theme/theme';
import routes from '@/routes';
import Sidebar from '@/components/sidebar/Sidebar';
import Footer from '@/components/footer/FooterAdmin';
import Navbar from '@/components/navbar/NavbarAdmin';
import { getActiveRoute, getActiveNavbar } from '@/utils/navigation';
import { usePathname } from 'next/navigation';
import '@/styles/App.css';
import '@/styles/Contact.css';
import '@/styles/Plugins.css';
import '@/styles/MiniCalendar.css';
import '@/styles/cursor.css';
import AppWrappers from './AppWrappers';
import { ColorThemeProvider } from '@/contexts/ColorThemeContext';

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <html lang="en">
      <body id={'root'}>
        <ColorThemeProvider>
          <AppWrappers>
          {/* <ChakraProvider theme={theme}> */}
          {pathname?.includes('register') || pathname?.includes('sign-in') ? (
            children
          ) : (
            <Box>
              <Sidebar routes={routes} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
              <Box
                pt={{ base: '60px', md: '100px' }}
                float="right"
                minHeight="100vh"
                height="100%"
                overflow="auto"
                position="relative"
                maxHeight="100%"
                w={{ 
                  base: '100%', 
                  xl: sidebarCollapsed ? 'calc( 100% - 79px )' : 'calc( 100% - 272px )' 
                }}
                maxWidth={{ 
                  base: '100%', 
                  xl: sidebarCollapsed ? 'calc( 100% - 79px )' : 'calc( 100% - 272px )' 
                }}
                transition="all 0.33s cubic-bezier(0.685, 0.0473, 0.346, 1)"
                transitionDuration=".2s, .2s, .35s"
                transitionProperty="top, bottom, width"
                transitionTimingFunction="linear, linear, ease"
              >
                <Portal>
                  <Box>
                    <Navbar
                      onOpen={onOpen}
                      logoText={'V.PACK Dashboard'}
                      brandText={getActiveRoute(routes, pathname)}
                      secondary={getActiveNavbar(routes, pathname)}
                    />
                  </Box>
                </Portal>
                <Box
                  mx="auto"
                  p={{ base: '20px', md: '30px' }}
                  pe="20px"
                  minH="100vh"
                  pt="50px"
                >
                  {children}
                  {/* <Component apiKeyApp={apiKey} {...pageProps} /> */}
                </Box>
                <Box>
                  <Footer />
                </Box>
              </Box>
            </Box>
          )}
          {/* </ChakraProvider> */}
        </AppWrappers>
        </ColorThemeProvider>
      </body>
    </html>
  );
}
