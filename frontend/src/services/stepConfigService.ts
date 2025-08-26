/**
 * Step Configuration Service
 * Handles API calls for step-by-step configuration
 */

interface BrandnameResponse {
  success: boolean;
  data: {
    brand_name: string;
    changed?: boolean;
  };
  message?: string;
  error?: string;
}

class StepConfigService {
  private baseUrl = 'http://localhost:8080/api/config';

  /**
   * Fetch current brandname from backend
   */
  async fetchBrandnameState(): Promise<BrandnameResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/brandname`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching brandname state:', error);
      throw error;
    }
  }

  /**
   * Update brandname if changed
   */
  async updateBrandnameState(brandName: string): Promise<BrandnameResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/brandname`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_name: brandName.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating brandname state:', error);
      throw error;
    }
  }
}

export const stepConfigService = new StepConfigService();