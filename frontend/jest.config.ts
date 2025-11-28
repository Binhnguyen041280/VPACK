import type { Config } from 'jest'
import nextJest from 'next/jest'

/**
 * Jest Configuration for Next.js 15 + TypeScript + Chakra UI
 *
 * Target Coverage: 55-60% for frontend components/services
 */

const createJestConfig = nextJest({
  // Path to your Next.js app
  dir: './',
})

const config: Config = {
  // Test environment
  testEnvironment: 'jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],

  // Module path mapping (match tsconfig.json paths)
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/components/(.*)$': '<rootDir>/src/components/$1',
    '^@/contexts/(.*)$': '<rootDir>/src/contexts/$1',
    '^@/services/(.*)$': '<rootDir>/src/services/$1',
    '^@/utils/(.*)$': '<rootDir>/src/utils/$1',
    '^@/types/(.*)$': '<rootDir>/src/types/$1',
    '^@/config/(.*)$': '<rootDir>/src/config/$1',
    '^@/hooks/(.*)$': '<rootDir>/src/hooks/$1',

    // Mock CSS/style imports
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',

    // Mock static assets
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/tests/__mocks__/fileMock.js',
  },

  // Test match patterns
  testMatch: [
    '<rootDir>/tests/__tests__/**/*.test.{ts,tsx}',
    '<rootDir>/tests/__tests__/**/*.spec.{ts,tsx}',
  ],

  // Coverage collection
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    'app/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/dist/**',
    '!**/coverage/**',
  ],

  // Coverage thresholds
  coverageThresholds: {
    global: {
      branches: 55,
      functions: 60,
      lines: 60,
      statements: 60,
    },
  },

  // Coverage reporters
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json',
  ],

  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react',
      },
    }],
  },

  // Module file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/out/',
  ],

  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(uuid|@chakra-ui)/)',
  ],

  // Globals
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react',
      },
    },
  },

  // Test timeout
  testTimeout: 10000,

  // Clear mocks between tests
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,

  // Verbose output
  verbose: true,
}

export default createJestConfig(config)
