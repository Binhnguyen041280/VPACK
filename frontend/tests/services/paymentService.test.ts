/**
 * Unit tests for PaymentService
 * Tests payment API interactions and utility functions
 */

import { PaymentService } from '@/services/paymentService'

// Mock fetch globally
global.fetch = jest.fn()

describe('PaymentService', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(global.fetch as jest.Mock).mockClear()
  })

  describe('getPackages', () => {
    it('should fetch and return packages successfully', async () => {
      const mockPackages = {
        success: true,
        packages: {
          starter_1m: { name: 'Starter', price: 999 },
          pro_1m: { name: 'Pro', price: 1999 }
        }
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPackages
      })

      const result = await PaymentService.getPackages()

      expect(result).toEqual(mockPackages)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/payment/packages')
      )
    })

    it('should throw error when HTTP request fails', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      await expect(PaymentService.getPackages()).rejects.toThrow('HTTP 500')
    })

    it('should throw error when success is false', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Server error'
        })
      })

      await expect(PaymentService.getPackages()).rejects.toThrow('Server error')
    })
  })

  describe('getUpgradePackages', () => {
    it('should fetch upgrade packages with correct query param', async () => {
      const mockPackages = {
        success: true,
        packages: { pro_1m: { name: 'Pro', price: 1999 } }
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPackages
      })

      const result = await PaymentService.getUpgradePackages()

      expect(result).toEqual(mockPackages)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/payment/packages?for_upgrade=true')
      )
    })

    it('should handle upgrade packages fetch error', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404
      })

      await expect(PaymentService.getUpgradePackages()).rejects.toThrow('HTTP 404')
    })
  })

  describe('createPayment', () => {
    it('should create payment with correct payload', async () => {
      const mockRequest = {
        customer_email: 'test@example.com',
        package_type: 'starter_1m'
      }

      const mockResponse = {
        success: true,
        payment_url: 'https://payment.example.com',
        order_code: 'ORDER123',
        amount: 999
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await PaymentService.createPayment(mockRequest)

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/payment/create'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('payos') // Default provider
        })
      )
    })

    it('should include custom provider if specified', async () => {
      const mockRequest = {
        customer_email: 'test@example.com',
        package_type: 'pro_1m',
        provider: 'custom_provider'
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      await PaymentService.createPayment(mockRequest)

      const callArgs = (global.fetch as jest.Mock).mock.calls[0]
      const body = JSON.parse(callArgs[1].body)
      expect(body.provider).toBe('custom_provider')
    })

    it('should throw error when payment creation fails', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Invalid package type'
        })
      })

      await expect(
        PaymentService.createPayment({
          customer_email: 'test@example.com',
          package_type: 'invalid'
        })
      ).rejects.toThrow('Invalid package type')
    })
  })

  describe('getLicenseStatus', () => {
    it('should fetch license status successfully', async () => {
      const mockStatus = {
        success: true,
        license: {
          license_key: 'VTRACK-S1M-TEST',
          status: 'active',
          expires_at: '2026-01-01T00:00:00Z'
        }
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const result = await PaymentService.getLicenseStatus()

      expect(result).toEqual(mockStatus)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/payment/license-status'),
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      )
    })

    it('should handle license status fetch error', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Server Error'
      })

      await expect(PaymentService.getLicenseStatus()).rejects.toThrow('HTTP 500')
    })
  })

  describe('activateLicense', () => {
    it('should activate license successfully', async () => {
      const mockRequest = { license_key: 'VTRACK-S1M-TEST123' }
      const mockResponse = {
        success: true,
        data: {
          license_key: 'VTRACK-S1M-TEST123',
          status: 'activated'
        }
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await PaymentService.activateLicense(mockRequest)

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/payment/activate-license'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockRequest)
        })
      )
    })

    it('should throw error when activation fails', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Invalid license key'
        })
      })

      await expect(
        PaymentService.activateLicense({ license_key: 'INVALID' })
      ).rejects.toThrow('Invalid license key')
    })
  })

  describe('formatPrice', () => {
    it('should format price in Vietnamese Dong', () => {
      expect(PaymentService.formatPrice(1000000)).toBe('1.000.000 ₫')
    })

    it('should format zero correctly', () => {
      expect(PaymentService.formatPrice(0)).toBe('0 ₫')
    })

    it('should format decimal values', () => {
      expect(PaymentService.formatPrice(999.99)).toBe('1.000 ₫')
    })
  })

  describe('getBadgeForPackage', () => {
    it('should return RECOMMENDED for Pro packages', () => {
      expect(PaymentService.getBadgeForPackage('pro_1m')).toBe('RECOMMENDED')
      expect(PaymentService.getBadgeForPackage('PRO_1Y')).toBe('RECOMMENDED')
    })

    it('should return POPULAR for legacy personal package', () => {
      expect(PaymentService.getBadgeForPackage('personal_1y')).toBe('POPULAR')
    })

    it('should return BEST VALUE for legacy business package', () => {
      expect(PaymentService.getBadgeForPackage('business_1y')).toBe('BEST VALUE')
    })

    it('should return TRIAL for trial packages', () => {
      expect(PaymentService.getBadgeForPackage('trial_24h')).toBe('TRIAL')
      expect(PaymentService.getBadgeForPackage('trial_7d')).toBe('TRIAL')
    })

    it('should return null for unknown packages', () => {
      expect(PaymentService.getBadgeForPackage('unknown_package')).toBeNull()
      expect(PaymentService.getBadgeForPackage('')).toBeNull()
    })
  })

  describe('formatDuration', () => {
    it('should format 1 day as "24 giờ"', () => {
      expect(PaymentService.formatDuration(1)).toBe('24 giờ')
    })

    it('should format 30 days', () => {
      expect(PaymentService.formatDuration(30)).toBe('30 ngày')
    })

    it('should format 365 days', () => {
      expect(PaymentService.formatDuration(365)).toBe('365 ngày')
    })

    it('should format custom duration', () => {
      expect(PaymentService.formatDuration(14)).toBe('14 ngày')
      expect(PaymentService.formatDuration(90)).toBe('90 ngày')
    })
  })

  describe('openPayOSPopup', () => {
    let mockPopup: any
    let addEventListenerSpy: jest.SpyInstance
    let removeEventListenerSpy: jest.SpyInstance

    beforeEach(() => {
      mockPopup = {
        closed: false,
        close: jest.fn()
      }

      window.open = jest.fn(() => mockPopup)
      addEventListenerSpy = jest.spyOn(window, 'addEventListener')
      removeEventListenerSpy = jest.spyOn(window, 'removeEventListener')

      jest.useFakeTimers()
    })

    afterEach(() => {
      jest.useRealTimers()
      addEventListenerSpy.mockRestore()
      removeEventListenerSpy.mockRestore()
    })

    it('should open popup with correct parameters', () => {
      const onComplete = jest.fn()
      PaymentService.openPayOSPopup('https://payment.example.com', onComplete)

      expect(window.open).toHaveBeenCalledWith(
        'https://payment.example.com',
        'payos_payment',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      )
    })

    it('should throw error when popup is blocked', () => {
      window.open = jest.fn(() => null)

      expect(() => {
        PaymentService.openPayOSPopup('https://payment.example.com', jest.fn())
      }).toThrow('Please allow popups to complete payment')
    })

    it('should handle payment completed message', () => {
      const onComplete = jest.fn()
      PaymentService.openPayOSPopup('https://payment.example.com', onComplete)

      const messageEvent = new MessageEvent('message', {
        origin: 'http://localhost:8080',
        data: {
          type: 'payment_flow_completed',
          status: 'success',
          orderCode: 'ORDER123'
        }
      })

      window.dispatchEvent(messageEvent)

      expect(onComplete).toHaveBeenCalledWith({
        status: 'success',
        orderCode: 'ORDER123'
      })
    })

    it('should handle popup close', () => {
      const onComplete = jest.fn()
      PaymentService.openPayOSPopup('https://payment.example.com', onComplete)

      mockPopup.closed = true
      jest.advanceTimersByTime(1000)

      expect(onComplete).toHaveBeenCalledWith({
        status: 'closed',
        message: 'Payment window was closed'
      })
    })
  })
})
