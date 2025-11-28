/**
 * Test Utilities
 *
 * Custom render functions with all necessary providers
 * for testing React components in V_Track frontend.
 */

import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { ChakraProvider } from '@chakra-ui/react'
import { LicenseProvider } from '@/contexts/LicenseContext'
import { UserProvider } from '@/contexts/UserContext'

// ============================================================================
// Provider Wrappers
// ============================================================================

interface AllProvidersProps {
  children: React.ReactNode
  initialLicenseState?: any
  initialUserState?: any
}

/**
 * Wrapper component with all necessary providers for testing.
 */
const AllProviders: React.FC<AllProvidersProps> = ({
  children,
  initialLicenseState,
  initialUserState,
}) => {
  return (
    <ChakraProvider>
      <UserProvider>
        <LicenseProvider>
          {children}
        </LicenseProvider>
      </UserProvider>
    </ChakraProvider>
  )
}

/**
 * Minimal wrapper with just Chakra UI (for component-only tests).
 */
const ChakraOnlyProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return <ChakraProvider>{children}</ChakraProvider>
}

// ============================================================================
// Custom Render Functions
// ============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialLicenseState?: any
  initialUserState?: any
  withoutProviders?: boolean
}

/**
 * Custom render function with all providers.
 *
 * Usage:
 *   render(<Component />)
 *   render(<Component />, { initialLicenseState: { ... } })
 *   render(<Component />, { withoutProviders: true })
 */
const customRender = (
  ui: ReactElement,
  options?: CustomRenderOptions
) => {
  const {
    initialLicenseState,
    initialUserState,
    withoutProviders = false,
    ...renderOptions
  } = options || {}

  if (withoutProviders) {
    return render(ui, renderOptions)
  }

  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders
        initialLicenseState={initialLicenseState}
        initialUserState={initialUserState}
      >
        {children}
      </AllProviders>
    ),
    ...renderOptions,
  })
}

/**
 * Render with only Chakra UI provider (no contexts).
 *
 * Useful for testing pure UI components.
 */
const renderWithChakra = (ui: ReactElement, options?: RenderOptions) => {
  return render(ui, {
    wrapper: ChakraOnlyProvider,
    ...options,
  })
}

// ============================================================================
// Mock Data Factories
// ============================================================================

/**
 * Create mock license data.
 */
export const createMockLicense = (overrides = {}) => ({
  hasValidLicense: true,
  isTrialActive: false,
  daysRemaining: 30,
  expiryDate: '2026-01-01T00:00:00Z',
  isExpired: false,
  isLoading: false,
  licenseType: 'annual_1y',
  error: null,
  features: {
    default_mode: true,
    custom_mode: true,
    max_cameras: 10,
  },
  ...overrides,
})

/**
 * Create mock user data.
 */
export const createMockUser = (overrides = {}) => ({
  email: 'test@example.com',
  name: 'Test User',
  isAuthenticated: true,
  ...overrides,
})

/**
 * Create mock payment package data.
 */
export const createMockPackage = (overrides = {}) => ({
  id: 'annual_1y',
  name: 'Annual Package',
  price: 2000000,
  formattedPrice: '2.000.000đ',
  duration: 365,
  features: {
    default_mode: true,
    custom_mode: true,
    max_cameras: 10,
  },
  ...overrides,
})

/**
 * Create mock payment response.
 */
export const createMockPaymentResponse = (overrides = {}) => ({
  success: true,
  order_url: 'https://payos.vn/order/123456',
  order_code: 123456,
  amount: 2000000,
  formatted_amount: '2.000.000đ',
  ...overrides,
})

/**
 * Create mock license activation response.
 */
export const createMockActivationResponse = (overrides = {}) => ({
  success: true,
  message: 'License activated successfully',
  license: createMockLicense(),
  ...overrides,
})

// ============================================================================
// Test Helpers
// ============================================================================

/**
 * Wait for async updates (useful for testing async state updates).
 */
export const waitForAsync = () => {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

/**
 * Create a deferred promise for testing async flows.
 */
export const createDeferred = <T = any>() => {
  let resolve: (value: T) => void
  let reject: (reason?: any) => void

  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })

  return {
    promise,
    resolve: resolve!,
    reject: reject!,
  }
}

/**
 * Flush all pending promises.
 */
export const flushPromises = () => {
  return new Promise((resolve) => setImmediate(resolve))
}

// ============================================================================
// Exports
// ============================================================================

// Re-export everything from Testing Library
export * from '@testing-library/react'
export { userEvent } from '@testing-library/user-event'

// Export custom render functions
export { customRender as render, renderWithChakra }

// Export mock factories
export {
  createMockLicense,
  createMockUser,
  createMockPackage,
  createMockPaymentResponse,
  createMockActivationResponse,
}

// Export helpers
export { waitForAsync, createDeferred, flushPromises }
