/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: false,
  devIndicators: false,
  basePath: process.env.NEXT_PUBLIC_BASE_PATH,
  assetPrefix: process.env.NEXT_PUBLIC_BASE_PATH,
  images: {
    domains: [
      'images.unsplash.com',
      'i.ibb.co',
      'scontent.fotp8-1.fna.fbcdn.net',
    ],
    // Make ENV
    unoptimized: true,
  },
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Disable React Dev Overlay
      config.resolve.alias = {
        ...config.resolve.alias,
        '@next/react-dev-overlay/lib/client': false,
        '@next/react-dev-overlay': false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
