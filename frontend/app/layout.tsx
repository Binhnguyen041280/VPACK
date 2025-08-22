'use client';
import React, { ReactNode, useState } from 'react';
import type { AppProps } from 'next/app';
import { ChakraProvider, Box, useDisclosure } from '@chakra-ui/react';
import theme from '@/theme/theme';
import routes from '@/routes';
import Sidebar from '@/components/sidebar/Sidebar';
import ToggleButtons from '@/components/ToggleButtons';
import { SidebarContext } from '@/contexts/SidebarContext';
import { usePathname } from 'next/navigation';
import '@/styles/App.css';
import '@/styles/Contact.css';
import '@/styles/Plugins.css';
import '@/styles/MiniCalendar.css';
import '@/styles/cursor.css';
import AppWrappers from './AppWrappers';
import { ColorThemeProvider } from '@/contexts/ColorThemeContext';
import { UserProvider } from '@/contexts/UserContext';
import { RouteProvider } from '@/contexts/RouteContext';

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
          <UserProvider>
            <RouteProvider>
              <AppWrappers>
          {/* <ChakraProvider theme={theme}> */}
          {pathname?.includes('register') || pathname?.includes('sign-in') ? (
            children
          ) : (
            <SidebarContext.Provider value={{ 
              toggleSidebar: sidebarCollapsed, 
              setToggleSidebar: setSidebarCollapsed 
            }}>
            <Box>
              <Sidebar routes={routes} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
              <ToggleButtons />
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
                <Box
                  mx="auto"
                  p={{ base: '20px', md: '30px' }}
                  pe="20px"
                  minH="100vh"
                >
                  {children}
                  {/* <Component apiKeyApp={apiKey} {...pageProps} /> */}
                </Box>
              </Box>
            </Box>
            </SidebarContext.Provider>
          )}
          {/* </ChakraProvider> */}
              </AppWrappers>
            </RouteProvider>
          </UserProvider>
        </ColorThemeProvider>
      </body>
    </html>
  );
}
