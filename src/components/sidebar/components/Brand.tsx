'use client';
// Chakra imports
import { Flex, useColorModeValue, Box, Text } from '@chakra-ui/react';

import { VPackIcon } from '@/components/icons/VPackIcon';
import { HSeparator } from '@/components/separator/Separator';

interface SidebarBrandProps {
  collapsed?: boolean;
}

export function SidebarBrand({ collapsed = false }: SidebarBrandProps) {
  //   Chakra color mode
  let logoColor = useColorModeValue('navy.700', 'white');

  if (collapsed) {
    return (
      <Flex alignItems="center" justifyContent="center" my="18px">
        <VPackIcon size="27px" collapsed={true} />
      </Flex>
    );
  }

  return (
    <Flex alignItems="center" flexDirection="column">
      <Box
        bg="linear-gradient(15.46deg, #4A25E1 26.3%, #7B5AFF 86.4%)"
        color="white"
        py="12px"
        px="20px"
        fontSize="sm"
        borderRadius="45px"
        my="30px"
        display="flex"
        alignItems="center"
        justifyContent="center"
        fontWeight="500"
        boxShadow="0px 21px 27px -10px rgba(96, 60, 255, 0.48)"
        minW="120px"
      >
        <Text fontWeight="bold" fontSize="md">V.PACK</Text>
      </Box>
      <HSeparator mb="20px" w="256px" />
    </Flex>
  );
}

export default SidebarBrand;
