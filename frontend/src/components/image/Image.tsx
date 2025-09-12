'use client'
import { Box, BoxProps } from '@chakra-ui/react';
import NextImage, { ImageProps } from 'next/image';
import { ComponentProps } from 'react';

type ChakraNextImageProps = Partial<ImageProps> &
    Partial<BoxProps> & {
        nextProps?: Partial<ComponentProps<typeof NextImage>>;
    };

function parseAssetPrefix(image: string) {
    if (!image || typeof image !== 'string') return image || '';
    
    const alreadyHasHttp = image.match('http');
    if (alreadyHasHttp) return image;

    const prefix = process.env.NEXT_PUBLIC_BASE_PATH || '';
    const alreadyHasPrefix = image.match(prefix);

    const finalUrl = alreadyHasPrefix ? image : `${prefix}${image}`;
    return finalUrl;
}

export function Image(props: ChakraNextImageProps) {
    const { src, alt, nextProps = {}, ...rest } = props;

    const imageUrl =
        typeof src === 'string' ? src : ((src as any)?.src as string);
    
    // Handle empty or null sources
    const processedSrc = parseAssetPrefix(imageUrl);
    if (!processedSrc || processedSrc === '') {
        return (
            <Box 
                overflow={'hidden'} 
                position="relative" 
                display="flex"
                alignItems="center"
                justifyContent="center"
                bg="gray.200"
                color="gray.500"
                fontSize="xl"
                {...rest}
            >
                👤
            </Box>
        );
    }
    
    return (
        <Box overflow={'hidden'} position="relative" {...rest}>
            <NextImage
                fill
                style={{ objectFit: 'fill' }}
                src={processedSrc}
                alt={alt}
                {...nextProps}
            />
        </Box>
    );
}
