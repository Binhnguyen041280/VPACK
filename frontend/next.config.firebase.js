/** @type {import('next').NextConfig} */

// Firebase Hosting - Static Export Configuration
// Use this for deploying landing page to Firebase Hosting

const nextConfig = {
  reactStrictMode: false,

  // Static export for Firebase Hosting
  output: 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Trailing slash for Firebase routing
  trailingSlash: true,
};

module.exports = nextConfig;
