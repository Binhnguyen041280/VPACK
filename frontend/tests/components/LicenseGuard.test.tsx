/**
 * Unit tests for LicenseGuard component
 * Tests license protection and UI states
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '../testUtils'
import { LicenseGuard } from '@/components/license/LicenseGuard'
import { useLicense } from '@/contexts/LicenseContext'
import { useRouter } from 'next/navigation'

// Mock dependencies
jest.mock('@/contexts/LicenseContext')
jest.mock('next/navigation', () => ({
  useRouter: jest.fn()
}))

describe('LicenseGuard', () => {
  const mockUseLicense = useLicense as jest.MockedFunction<typeof useLicense>
  const mockPush = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner when license is loading', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: true,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('Checking license...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should show error message when license check fails', () => {
      const mockRefresh = jest.fn()
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: 'Network error',
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: mockRefresh
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('License Check Failed')).toBeInTheDocument()
      expect(screen.getByText('Network error')).toBeInTheDocument()
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('should call refreshLicense when retry button is clicked', () => {
      const mockRefresh = jest.fn()
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: 'Network error',
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: mockRefresh
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      fireEvent.click(screen.getByText('Retry'))
      expect(mockRefresh).toHaveBeenCalledTimes(1)
    })
  })

  describe('Valid License', () => {
    it('should render children when license is valid', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: true,
          isTrialActive: false,
          daysRemaining: 30,
          expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          isExpired: false,
          licenseType: 'pro_1m',
          error: null,
          features: {
            default_mode: true,
            custom_mode: true,
            max_cameras: 10
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
      expect(screen.queryByText('License Required')).not.toBeInTheDocument()
    })
  })

  describe('Invalid License States', () => {
    it('should show upgrade prompt when no license', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard feature="Trace">
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('License Required')).toBeInTheDocument()
      expect(screen.getByText(/Access to Trace requires an active license/)).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('should show expired message when license is expired', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: -5,
          expiryDate: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          isExpired: true,
          licenseType: 'starter_1m',
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard feature="this feature">
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('License Expired')).toBeInTheDocument()
      expect(screen.getByText(/Your license has expired/)).toBeInTheDocument()
    })

    it('should navigate to plan page when "Go to Plan" is clicked', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      fireEvent.click(screen.getByText('Go to Plan'))
      expect(mockPush).toHaveBeenCalledWith('/plan')
    })

    it('should show features list in upgrade prompt', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText('✨ With a license you get:')).toBeInTheDocument()
      expect(screen.getByText('✓ Full access to Trace features')).toBeInTheDocument()
      expect(screen.getByText('✓ Query and filter events by tracking code')).toBeInTheDocument()
    })
  })

  describe('Custom Feature Name', () => {
    it('should use custom feature name in message', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard feature="Video Export">
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText(/Access to Video Export requires an active license/)).toBeInTheDocument()
    })

    it('should use default feature name if not provided', () => {
      mockUseLicense.mockReturnValue({
        license: {
          isLoading: false,
          hasValidLicense: false,
          isTrialActive: false,
          daysRemaining: null,
          expiryDate: null,
          isExpired: false,
          licenseType: null,
          error: null,
          features: {
            default_mode: false,
            custom_mode: true,
            max_cameras: 5
          }
        },
        refreshLicense: jest.fn()
      })

      render(
        <LicenseGuard>
          <div>Protected Content</div>
        </LicenseGuard>
      )

      expect(screen.getByText(/Access to this feature requires an active license/)).toBeInTheDocument()
    })
  })
})
