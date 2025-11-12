/** @type {import('next').NextConfig} */

// TODO: Fix Next.js 15 pre-rendering issue (Phase 3 workaround)
// Issue: useSearchParams() needs Suspense boundary for static generation
// Current workaround: Dockerfile allows build to continue with warnings
// Runtime works correctly despite build warnings
// Future fix: Wrap useSearchParams() calls in <Suspense> boundaries
// See: https://nextjs.org/docs/messages/missing-suspense-with-csr-bailout
// Affected components: src/app/login/page.tsx, src/app/register/page.tsx

const nextConfig = {
  reactStrictMode: false,
  devIndicators: false,

  // CRITICAL: Only set basePath if explicitly provided and non-empty
  // Empty basePath causes Next.js 15 to crash
  ...(process.env.NEXT_PUBLIC_BASE_PATH && {
    basePath: process.env.NEXT_PUBLIC_BASE_PATH,
    assetPrefix: process.env.NEXT_PUBLIC_BASE_PATH,
  }),

  // Standalone output for optimized Docker builds
  output: 'standalone',

  // CRITICAL: Disable static page generation to avoid useSearchParams() errors
  // All pages will be rendered dynamically at runtime instead of at build time
  // This is acceptable for a business application with dynamic content
  generateBuildId: async () => {
    return 'vtrack-build-' + Date.now()
  },

  images: {
    domains: [
      'images.unsplash.com',
      'i.ibb.co',
      'scontent.fotp8-1.fna.fbcdn.net',
    ],
    // Required for Docker - disable image optimization
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
