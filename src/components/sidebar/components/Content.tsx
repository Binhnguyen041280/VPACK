'use client';
// chakra imports
import {
  Box,
  Button,
  Flex,
  Icon,
  Menu,
  MenuButton,
  MenuList,
  Stack,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import NavLink from '@/components/link/NavLink';
//   Custom components
import avatar4 from '/public/img/avatars/avatar4.png';
import { NextAvatar } from '@/components/image/Avatar';
import Brand from '@/components/sidebar/components/Brand';
import Links from '@/components/sidebar/components/Links';
import SidebarCard from '@/components/sidebar/components/SidebarCard';
import { RoundedChart } from '@/components/icons/Icons';
import { PropsWithChildren } from 'react';
import { IRoute } from '@/types/navigation';
import { IoMdPerson } from 'react-icons/io';
import { FiLogOut, FiSidebar } from 'react-icons/fi';
import { MdOutlineManageAccounts, MdOutlineSettings } from 'react-icons/md';

// FUNCTIONS

interface SidebarContent extends PropsWithChildren {
  routes: IRoute[];
  collapsed?: boolean;
  onToggle?: () => void;
  [x: string]: any;
}

function SidebarContent(props: SidebarContent) {
  const { routes, collapsed = false, onToggle } = props;
  const textColor = useColorModeValue('navy.700', 'white');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.300');
  const bgColor = useColorModeValue('white', 'navy.700');
  const shadow = useColorModeValue(
    '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
    '14px 17px 40px 4px rgba(12, 44, 55, 0.18)',
  );
  const iconColor = useColorModeValue('navy.700', 'white');
  const shadowPillBar = useColorModeValue(
    '4px 17px 40px 4px rgba(112, 144, 176, 0.08)',
    'none',
  );
  const gray = useColorModeValue('gray.500', 'white');
  // SIDEBAR
  return (
    <Flex
      direction="column"
      height="100%"
      pt="20px"
      pb="26px"
      borderRadius="30px"
      maxW="256px"
      px={collapsed ? "10px" : "20px"}
    >
      <Brand collapsed={collapsed} />
      <Stack direction="column" mb="auto" mt="8px">
        <Box ps="0px" pe={{ md: '0px', '2xl': '0px' }}>
          <Links routes={routes} collapsed={collapsed} />
        </Box>
      </Stack>

{!collapsed && (
        <Box mt="60px" width={'100%'} display={'flex'} justifyContent={'center'}>
          <SidebarCard />
        </Box>
      )}
      
      {collapsed ? (
        // Collapsed state: only avatar
        <Flex
          mt="auto"
          mb="18px"
          justifyContent="center"
          alignItems="center"
          flexShrink={0}
        >
          <NextAvatar 
            h="27px" 
            w="27px" 
            src={avatar4} 
            style={{
              aspectRatio: '1',
              objectFit: 'cover',
              flexShrink: 0
            }}
          />
        </Flex>
      ) : (
        // Expanded state: full bottom section
        <Flex
          mt="8px"
          justifyContent="center"
          alignItems="center"
          boxShadow={shadowPillBar}
          borderRadius="30px"
          p="14px"
          flexShrink={0}
          minH="62px"
        >
          <NextAvatar 
            h="34px" 
            w="34px" 
            src={avatar4} 
            me="10px" 
            style={{
              aspectRatio: '1',
              objectFit: 'cover',
              flexShrink: 0
            }}
          />
          <Text color={textColor} fontSize="xs" fontWeight="600" me="10px">
            Adela Parkson
          </Text>
          <Menu>
            <MenuButton
              as={Button}
              variant="transparent"
              aria-label=""
              border="1px solid"
              borderColor={borderColor}
              borderRadius="full"
              w="34px"
              h="34px"
              px="0px"
              p="0px"
              minW="34px"
              maxW="34px"
              minH="34px"
              maxH="34px"
              me="10px"
              justifyContent={'center'}
              alignItems="center"
              color={iconColor}
              flexShrink={0}
            >
              <Flex align="center" justifyContent="center">
                <Icon
                  as={MdOutlineSettings}
                  width="18px"
                  height="18px"
                  color="inherit"
                />
              </Flex>
            </MenuButton>
            <MenuList
              ms="-20px"
              py="25px"
              ps="20px"
              pe="20px"
              w="246px"
              borderRadius="16px"
              transform="translate(-19px, -62px)!important"
              border="0px"
              boxShadow={shadow}
              bg={bgColor}
            >
              <Box mb="30px">
                <Flex align="center" w="100%" cursor={'not-allowed'}>
                  <Icon
                    as={MdOutlineManageAccounts}
                    width="24px"
                    height="24px"
                    color={gray}
                    me="12px"
                    opacity={'0.4'}
                  />
                  <Text
                    color={gray}
                    fontWeight="500"
                    fontSize="sm"
                    opacity={'0.4'}
                  >
                    Profile Settings
                  </Text>
                </Flex>
              </Box>
              <Box mb="30px">
                <Flex cursor={'not-allowed'} align="center">
                  <Icon
                    as={RoundedChart}
                    width="24px"
                    height="24px"
                    color={gray}
                    opacity="0.4"
                    me="12px"
                  />
                  <Text color={gray} fontWeight="500" fontSize="sm" opacity="0.4">
                    Usage
                  </Text>
                </Flex>
              </Box>
              <Box mb="30px">
                <Flex cursor={'not-allowed'} align="center">
                  <Icon
                    as={IoMdPerson}
                    width="24px"
                    height="24px"
                    color={gray}
                    opacity="0.4"
                    me="12px"
                  />
                  <Text color={gray} fontWeight="500" fontSize="sm" opacity="0.4">
                    My Plan
                  </Text>
                </Flex>
              </Box>
              <Box>
                <Flex cursor={'not-allowed'} align="center">
                  <Icon
                    as={FiLogOut}
                    width="24px"
                    height="24px"
                    color={gray}
                    opacity="0.4"
                    me="12px"
                  />
                  <Text color={gray} fontWeight="500" fontSize="sm" opacity="0.4">
                    Logout
                  </Text>
                </Flex>
              </Box>
            </MenuList>
          </Menu>
          <Button
            variant="transparent"
            border="1px solid"
            borderColor={borderColor}
            borderRadius="full"
            w="34px"
            h="34px"
            px="0px"
            minW="34px"
            maxW="34px"
            minH="34px"
            maxH="34px"
            justifyContent={'center'}
            alignItems="center"
            onClick={onToggle}
            flexShrink={0}
          >
            <Icon as={FiSidebar} width="16px" height="16px" color="inherit" />
          </Button>
        </Flex>
      )}
    </Flex>
  );
}

export default SidebarContent;
