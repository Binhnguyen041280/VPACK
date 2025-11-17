'use client';

/**
 * License Context Provider
 * Created: 2025-10-09
 * Purpose: Global license state management for UI protection
 *
 * Provides:
 * - License status checking
 * - Auto-refresh on mount
 * - Simplified state for UI components
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { PaymentService } from '@/services/paymentService';

// License status interface
export interface LicenseStatus {
  hasValidLicense: boolean;
  isTrialActive: boolean;
  daysRemaining: number | null;
  isExpired: boolean;
  isLoading: boolean;
  licenseType: string | null;
  error: string | null;
}

// Context interface
interface LicenseContextType {
  license: LicenseStatus;
  refreshLicense: () => Promise<void>;
}

// Create context
const LicenseContext = createContext<LicenseContextType | undefined>(undefined);

// Provider props
interface LicenseProviderProps {
  children: ReactNode;
}

/**
 * License Provider Component
 * Wraps application to provide global license state
 */
export const LicenseProvider: React.FC<LicenseProviderProps> = ({ children }) => {
  const [license, setLicense] = useState<LicenseStatus>({
    hasValidLicense: false,
    isTrialActive: false,
    daysRemaining: null,
    isExpired: false,
    isLoading: true,
    licenseType: null,
    error: null
  });

  /**
   * Fetch license status from backend with retry logic
   * Retries up to 4 times with 3-second delay to handle async trial creation
   * Total wait time: ~12 seconds (enough for CloudFunction trial creation)
   */
  const refreshLicense = async (attempt: number = 1) => {
    const MAX_RETRIES = 4;
    const RETRY_DELAY = 3000; // 3 seconds

    try {
      setLicense(prev => ({ ...prev, isLoading: true, error: null }));

      const response = await PaymentService.getLicenseStatus();

      // Check if license exists in response
      if (response.license) {
        const { license: licenseData, trial_status } = response;

        // Calculate days remaining
        let daysRemaining = null;
        if (licenseData.expires_at) {
          const expiryDate = new Date(licenseData.expires_at);
          const now = new Date();
          daysRemaining = Math.ceil((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        }

        // Determine license validity
        const hasValidLicense = licenseData.is_active && (daysRemaining === null || daysRemaining > 0);
        const isTrialActive = !!(licenseData.is_trial && hasValidLicense);
        const isExpired = daysRemaining !== null && daysRemaining <= 0;

        setLicense({
          hasValidLicense,
          isTrialActive,
          daysRemaining,
          isExpired,
          isLoading: false,
          licenseType: licenseData.package_type || null,
          error: null
        });

        console.log(`✅ License loaded successfully on attempt ${attempt}/${MAX_RETRIES}`);
      } else {
        // No license found - retry if attempts remaining (trial might be creating)
        if (attempt < MAX_RETRIES) {
          console.log(`⏳ No license yet, waiting for trial creation... (attempt ${attempt}/${MAX_RETRIES}, retry in ${RETRY_DELAY/1000}s)`);

          // Keep loading state during retry
          setTimeout(() => {
            refreshLicense(attempt + 1);
          }, RETRY_DELAY);
        } else {
          // Max retries reached - no license found
          console.log(`❌ No license found after ${MAX_RETRIES} attempts (~${(MAX_RETRIES * RETRY_DELAY)/1000}s wait)`);
          setLicense({
            hasValidLicense: false,
            isTrialActive: false,
            daysRemaining: null,
            isExpired: false,
            isLoading: false,
            licenseType: null,
            error: null
          });
        }
      }
    } catch (error) {
      console.error('Failed to refresh license:', error);

      // Retry on error if attempts remaining
      if (attempt < MAX_RETRIES) {
        console.log(`⚠️ Error occurred, retrying in ${RETRY_DELAY/1000}s... (attempt ${attempt}/${MAX_RETRIES})`);
        setTimeout(() => {
          refreshLicense(attempt + 1);
        }, RETRY_DELAY);
      } else {
        setLicense(prev => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to load license'
        }));
      }
    }
  };

  // Load license on mount
  useEffect(() => {
    refreshLicense();
  }, []);

  const value: LicenseContextType = {
    license,
    refreshLicense
  };

  return (
    <LicenseContext.Provider value={value}>
      {children}
    </LicenseContext.Provider>
  );
};

/**
 * Hook to use license context
 *
 * Usage:
 *   const { license, refreshLicense } = useLicense();
 *   if (!license.hasValidLicense) {
 *     // Show upgrade prompt
 *   }
 */
export const useLicense = (): LicenseContextType => {
  const context = useContext(LicenseContext);

  if (context === undefined) {
    throw new Error('useLicense must be used within a LicenseProvider');
  }

  return context;
};

// Export types for use in other components
export type { LicenseContextType };
