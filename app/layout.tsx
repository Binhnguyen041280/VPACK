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
import '@/styles/chatgpt-theme.css';
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
            <Box 
              className={`fixed-sidebar-layout ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}
              position="relative" 
              minHeight="100vh"
            >
              {/* Fixed Sidebar - Always visible and positioned */}
              <Box
                className="fixed-sidebar"
                position="fixed"
                top="0"
                left="0"
                height="100vh"
                zIndex="1000"
                transition="all 0.3s cubic-bezier(0.685, 0.0473, 0.346, 1)"
              >
                <Sidebar routes={routes} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
              </Box>
              
              {/* Toggle Buttons */}
              <ToggleButtons />
              
              {/* Main Content Area - Dynamic margin based on sidebar state */}
              <Box
                className="main-content-area zoom-responsive-canvas"
                minHeight="100vh"
                overflow="auto"
                marginLeft={{ 
                  base: '0px', 
                  xl: sidebarCollapsed ? '79px' : '272px' 
                }}
                transition="margin-left 0.3s cubic-bezier(0.685, 0.0473, 0.346, 1)"
                position="relative"
                width="auto"
                maxWidth="none"
              >
                <Box
                  className="zoom-responsive-forms"
                  p={{ base: '20px', md: '30px' }}
                  pe="20px"
                  minHeight="100vh"
                  maxWidth="100%"
                  overflow="auto"
                >
                  {children}
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
