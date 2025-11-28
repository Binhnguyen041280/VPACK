/**
 * Unit tests for LicenseContext
 * Tests license state management and provider functionality
 */

import React from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { LicenseProvider, useLicense } from '@/contexts/LicenseContext'
import { PaymentService } from '@/services/paymentService'

// Mock PaymentService
jest.mock('@/services/paymentService')

describe('LicenseContext', () => {
  const mockGetLicenseStatus = PaymentService.getLicenseStatus as jest.MockedFunction<
    typeof PaymentService.getLicenseStatus
  >

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('useLicense hook', () => {
    it('should throw error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

      expect(() => {
        renderHook(() => useLicense())
      }).toThrow('useLicense must be used within LicenseProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('LicenseProvider', () => {
    it('should provide initial loading state', () => {
      mockGetLicenseStatus.mockResolvedValue({
        success: true,
        license: null
      } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      expect(result.current.license.isLoading).toBe(true)
      expect(result.current.license.hasValidLicense).toBe(false)
    })

    it('should fetch and set valid license on mount', async () => {
      const mockLicenseData = {
        success: true,
        license: {
          license_key: 'VTRACK-PRO-TEST',
          customer_email: 'test@example.com',
          package_type: 'pro_1m',
          expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          status: 'active',
          features: ['full_access'],
          is_trial: false
        }
      }

      mockGetLicenseStatus.mockResolvedValue(mockLicenseData as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.hasValidLicense).toBe(true)
      expect(result.current.license.licenseType).toBe('pro_1m')
      expect(result.current.license.isExpired).toBe(false)
    })

    it('should handle trial license', async () => {
      const mockTrialData = {
        success: true,
        license: {
          license_key: 'VTRACK-TRIAL-TEST',
          package_type: 'trial_14d',
          expires_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
          status: 'active',
          is_trial: true
        },
        trial_status: {
          is_trial: true,
          days_left: 14
        }
      }

      mockGetLicenseStatus.mockResolvedValue(mockTrialData as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.isTrialActive).toBe(true)
      expect(result.current.license.daysRemaining).toBeGreaterThan(0)
    })

    it('should handle expired license', async () => {
      const mockExpiredData = {
        success: true,
        license: {
          license_key: 'VTRACK-EXPIRED',
          expires_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          status: 'expired'
        }
      }

      mockGetLicenseStatus.mockResolvedValue(mockExpiredData as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.isExpired).toBe(true)
      expect(result.current.license.hasValidLicense).toBe(false)
    })

    it('should handle no license', async () => {
      mockGetLicenseStatus.mockResolvedValue({
        success: true,
        license: null
      } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.hasValidLicense).toBe(false)
      expect(result.current.license.licenseType).toBeNull()
    })

    it('should handle API errors', async () => {
      mockGetLicenseStatus.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.error).toBeTruthy()
      expect(result.current.license.hasValidLicense).toBe(false)
    })

    it('should provide refreshLicense function', async () => {
      mockGetLicenseStatus.mockResolvedValue({
        success: true,
        license: null
      } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(typeof result.current.refreshLicense).toBe('function')
    })

    it('should refresh license when refreshLicense is called', async () => {
      mockGetLicenseStatus
        .mockResolvedValueOnce({
          success: true,
          license: null
        } as any)
        .mockResolvedValueOnce({
          success: true,
          license: {
            license_key: 'VTRACK-NEW',
            package_type: 'starter_1m',
            status: 'active'
          }
        } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.hasValidLicense).toBe(false)

      await result.current.refreshLicense()

      await waitFor(() => {
        expect(result.current.license.hasValidLicense).toBe(true)
      })
    })

    it('should set feature flags for Pro package', async () => {
      mockGetLicenseStatus.mockResolvedValue({
        success: true,
        license: {
          package_type: 'pro_1m',
          status: 'active',
          features: ['full_access']
        }
      } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.features.default_mode).toBe(true)
      expect(result.current.license.features.max_cameras).toBe(10)
    })

    it('should set feature flags for Starter package', async () => {
      mockGetLicenseStatus.mockResolvedValue({
        success: true,
        license: {
          package_type: 'starter_1m',
          status: 'active'
        }
      } as any)

      const { result } = renderHook(() => useLicense(), {
        wrapper: LicenseProvider
      })

      await waitFor(() => {
        expect(result.current.license.isLoading).toBe(false)
      })

      expect(result.current.license.features.default_mode).toBe(false)
      expect(result.current.license.features.custom_mode).toBe(true)
      expect(result.current.license.features.max_cameras).toBe(5)
    })
  })
})
