'use client';
/* eslint-disable */

import '../../../styles/animations.css';

// chakra imports
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Flex,
  HStack,
  Text,
  List,
  Icon,
  ListItem,
  useColorModeValue,
} from '@chakra-ui/react';
import { FaCircle } from 'react-icons/fa';
import { IoMdAdd } from 'react-icons/io';
import NavLink from '@/components/link/NavLink';
import { IRoute } from '@/types/navigation';
import { PropsWithChildren, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { useRoute } from '@/contexts/RouteContext';

interface SidebarLinksProps extends PropsWithChildren {
  routes: IRoute[];
  collapsed?: boolean;
}

export function SidebarLinks(props: SidebarLinksProps) {
  //   Chakra color mode
  const pathname = usePathname();
  const { currentColors } = useColorTheme();
  const { companyName, isAnimating, currentRoute } = useRoute();
  
  // Animation class for company name
  const getAnimationProps = (isCompanyRoute: boolean) => {
    if (isCompanyRoute && isAnimating) {
      return {
        className: 'company-name-blink',
        borderRadius: '4px',
        px: '8px',
        py: '2px',
        transition: 'all 0.2s ease'
      };
    }
    return {
      borderRadius: '4px',
      px: '0px',
      py: '0px',
      transition: 'all 0.2s ease'
    };
  };
  
  let activeColor = useColorModeValue('navy.700', 'white');
  let inactiveColor = useColorModeValue('gray.500', 'gray.500');
  let borderColor = useColorModeValue('gray.200', 'whiteAlpha.300');
  let activeIcon = useColorModeValue(currentColors.brand500, 'white');
  let iconColor = useColorModeValue('navy.700', 'white');
  let gray = useColorModeValue('gray.500', 'gray.500');

  const { routes, collapsed = false } = props;

  // verifies if routeName is the one active (in browser input or override)
  const activeRoute = useCallback(
    (routeName: string) => {
      // If currentRoute is set, use it for active detection
      if (currentRoute) {
        console.log('🔍 ActiveRoute check:', { routeName, currentRoute, result: currentRoute.includes(routeName) });
        return currentRoute.includes(routeName);
      }
      // Otherwise use pathname as before
      console.log('🔍 ActiveRoute check (pathname):', { routeName, pathname, result: pathname?.includes(routeName) });
      return pathname?.includes(routeName);
    },
    [pathname, currentRoute],
  );

  // this function creates the links and collapses that appear in the sidebar (left menu)
  const createLinks = (routes: IRoute[]) => {
    return routes.map((route, key) => {
      if (route.collapse && !route.invisible) {
        return (
          <Accordion defaultIndex={0} allowToggle key={key}>
            <Flex w="100%" justifyContent={'space-between'}>
              <AccordionItem isDisabled border="none" mb="14px" key={key}>
                <AccordionButton
                  display="flex"
                  alignItems="center"
                  mb="4px"
                  justifyContent="center"
                  _hover={{
                    bg: 'unset',
                  }}
                  _focus={{
                    boxShadow: 'none',
                  }}
                  borderRadius="8px"
                  w="100%"
                  py="0px"
                  ms={0}
                >
                  {route.icon ? (
                    <Flex
                      align="center"
                      justifyContent="space-between"
                      w="100%"
                    >
                      <HStack
                        spacing={
                          activeRoute(route.path.toLowerCase())
                            ? '22px'
                            : '26px'
                        }
                      >
                        <Flex
                          w="100%"
                          alignItems="center"
                          justifyContent="center"
                        >
                          <Box
                            color={
                              route.disabled
                                ? gray
                                : activeRoute(route.path.toLowerCase())
                                ? activeIcon
                                : inactiveColor
                            }
                            me="12px"
                            mt="6px"
                          >
                            {route.icon}
                          </Box>
                          <Text
                            cursor="not-allowed"
                            me="auto"
                            color={
                              route.disabled
                                ? gray
                                : activeRoute(route.path.toLowerCase())
                                ? activeColor
                                : 'gray.500'
                            }
                            fontWeight="500"
                            letterSpacing="0px"
                            fontSize="sm"
                            {...getAnimationProps(route.name === 'Alan_Go')}
                          >
                            {route.name === 'Alan_Go' ? companyName : route.name}
                          </Text>
                        </Flex>
                      </HStack>
                    </Flex>
                  ) : (
                    <Flex pt="0px" pb="10px" alignItems="center" w="100%">
                      <HStack
                        spacing={
                          activeRoute(route.path.toLowerCase())
                            ? '22px'
                            : '26px'
                        }
                        ps="32px"
                      >
                        <Text
                          cursor="not-allowed"
                          me="auto"
                          fontWeight="500"
                          letterSpacing="0px"
                          fontSize="sm"
                          {...getAnimationProps(route.name === 'Alan_Go')}
                        >
                          {route.name === 'Alan_Go' ? companyName : route.name}
                        </Text>
                      </HStack>
                      <AccordionIcon
                        ms="auto"
                        color={route.disabled ? gray : 'gray.500'}
                      />
                    </Flex>
                  )}
                </AccordionButton>
                <AccordionPanel py="0px" ps={'8px'}>
                  <List>
                    {
                      route.icon && route.items
                        ? createLinks(route.items) // for bullet accordion links
                        : route.items
                        ? createAccordionLinks(route.items)
                        : '' // for non-bullet accordion links
                    }
                  </List>
                </AccordionPanel>
              </AccordionItem>
            </Flex>
          </Accordion>
        );
      } else if (!route.invisible) {
        return (
          <div key={key}>
            {route.icon ? (
              <Flex
                align="center"
                justifyContent={collapsed ? "center" : "space-between"}
                w="100%"
                maxW="100%"
                ps={collapsed ? "0px" : "17px"}
                mb="0px"
                mx={collapsed ? "auto" : "0"}
              >
                <HStack
                  w="100%"
                  mb="14px"
                  spacing={collapsed ? "0px" : (
                    activeRoute(route.path.toLowerCase()) ? '22px' : '26px'
                  )}
                  justifyContent={collapsed ? "center" : "flex-start"}
                >
                  {(route.name === 'Alan_Go' || !route.disabled) ? (
                    <NavLink
                      href={
                        route.layout ? route.layout + route.path : route.path
                      }
                      key={key}
                      styles={{ 
                        width: collapsed ? 'auto' : '100%',
                        cursor: 'pointer'
                      }}
                    >
                      <Flex
                        w={collapsed ? "auto" : "100%"}
                        alignItems="center"
                        justifyContent={collapsed ? "center" : "center"}
                      >
                        <Box
                          color={
                            activeRoute(route.path.toLowerCase())
                              ? activeIcon
                              : inactiveColor
                          }
                          me={collapsed ? "0px" : "12px"}
                          mt="6px"
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                          flexShrink={0}
                        >
                          {route.icon}
                        </Box>
                        {!collapsed && (
                          <Text
                            me="auto"
                            color={
                              activeRoute(route.path.toLowerCase())
                                ? activeColor
                                : 'gray.500'
                            }
                            fontWeight="500"
                            letterSpacing="0px"
                            fontSize="sm"
                            {...getAnimationProps(route.name === 'Alan_Go')}
                          >
                            {route.name === 'Alan_Go' ? companyName : route.name}
                          </Text>
                        )}
                      </Flex>
                    </NavLink>
                  ) : (
                    <Flex
                      w={collapsed ? "auto" : "100%"}
                      alignItems="center"
                      justifyContent={collapsed ? "center" : "center"}
                      cursor="not-allowed"
                    >
                      <Box
                        opacity="0.4"
                        color={
                          route.disabled
                            ? gray
                            : activeRoute(route.path.toLowerCase())
                            ? activeIcon
                            : inactiveColor
                        }
                        me={collapsed ? "0px" : "12px"}
                        mt="6px"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        flexShrink={0}
                      >
                        {route.icon}
                      </Box>
                      {!collapsed && (
                        <Text
                          opacity="0.4"
                          me="auto"
                          color={
                            route.disabled
                              ? gray
                              : activeRoute(route.path.toLowerCase())
                              ? activeColor
                              : 'gray.500'
                          }
                          fontWeight="500"
                          letterSpacing="0px"
                          fontSize="sm"
                          {...getAnimationProps(route.name === 'Alan_Go')}
                        >
                          {route.name === 'Alan_Go' ? companyName : route.name}
                        </Text>
                      )}
                    </Flex>
                  )}
                </HStack>
              </Flex>
            ) : (
              <ListItem ms={0} cursor="not-allowed" opacity={'0.4'}>
                <Flex ps="32px" alignItems="center" mb="8px">
                  <Text
                    color={
                      route.disabled
                        ? gray
                        : activeRoute(route.path.toLowerCase())
                        ? activeColor
                        : inactiveColor
                    }
                    fontWeight="500"
                    fontSize="xs"
                    {...getAnimationProps(route.name === 'Alan_Go')}
                  >
                    {route.name === 'Alan_Go' ? companyName : route.name}
                  </Text>
                </Flex>
              </ListItem>
            )}
          </div>
        );
      }
    });
  };
  // this function creates the links from the secondary accordions (for example auth -> sign-in -> default)
  const createAccordionLinks = (routes: IRoute[]) => {
    return routes.map((route: IRoute, key: number) => {
      return (
        <ListItem
          ms="28px"
          display="flex"
          alignItems="center"
          mb="10px"
          key={key}
          cursor="not-allowed"
        >
          <Icon
            w="6px"
            h="6px"
            me="8px"
            as={FaCircle}
            color={route.disabled ? gray : activeIcon}
          />
          <Text
            color={
              route.disabled
                ? gray
                : activeRoute(route.path.toLowerCase())
                ? activeColor
                : inactiveColor
            }
            fontWeight={
              activeRoute(route.path.toLowerCase()) ? 'bold' : 'normal'
            }
            fontSize="sm"
            {...getAnimationProps(route.name === 'Alan_Go')}
          >
            {route.name === 'Alan_Go' ? companyName : route.name}
          </Text>
        </ListItem>
      );
    });
  };
  //  BRAND
  return <>{createLinks(routes)}</>;
}

export default SidebarLinks;
