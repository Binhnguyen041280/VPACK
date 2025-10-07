'use client';
import { ButtonProps } from '@chakra-ui/react';
import NextLink, { LinkProps as NextLinkProps } from 'next/link';

import { Button } from '@chakra-ui/react';

type LinkProps = ButtonProps & NextLinkProps;

function Link({ href, children, ...props }: LinkProps) {
  return (
    <Button as={NextLink} href={href} variant="a" {...props}>
      {children}
    </Button>
  );
}

export default Link;
