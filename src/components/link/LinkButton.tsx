'use client';
import Link, { LinkProps } from 'next/link';
import { Button, ButtonProps } from '@chakra-ui/react';

type ChakraAndNextProps = ButtonProps & LinkProps;

export default function LinkButton({
  href,
  children,
  prefetch = true,
  ...props
}: ChakraAndNextProps) {
  return (
    <Button as={Link} href={href} prefetch={prefetch} variant="a" {...props}>
      {children}
    </Button>
  );
}
