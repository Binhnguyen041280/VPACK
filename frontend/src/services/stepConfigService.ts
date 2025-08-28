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

interface LocationTimeResponse {
  success: boolean;
  data: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
    changed?: boolean;
  };
  message?: string;
  error?: string;
}

interface VideoSourceResponse {
  success: boolean;
  data: {
    sourceType?: string;
    inputPath?: string;
    selectedCameras?: string[];
    cameraPathsCount?: number;
    changed?: boolean;
    active_sources?: any[];
    camera_paths?: { [key: string]: string };
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

  /**
   * Fetch current location/time configuration from backend
   */
  async fetchLocationTimeState(): Promise<LocationTimeResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/location-time`, {
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
      console.error('Error fetching location-time state:', error);
      throw error;
    }
  }

  /**
   * Update location/time configuration if changed
   */
  async updateLocationTimeState(locationTimeData: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  }): Promise<LocationTimeResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/location-time`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(locationTimeData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating location-time state:', error);
      throw error;
    }
  }

  /**
   * Fetch current video source configuration from backend
   */
  async fetchVideoSourceState(): Promise<VideoSourceResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/video-source`, {
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
      console.error('Error fetching video source state:', error);
      throw error;
    }
  }

  /**
   * Update video source configuration if changed
   */
  async updateVideoSourceState(videoSourceData: {
    sourceType: string;
    inputPath?: string;
    detectedFolders?: { name: string; path: string }[];
    selectedCameras?: string[];
  }): Promise<VideoSourceResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/step/video-source`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(videoSourceData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating video source state:', error);
      throw error;
    }
  }
}

export const stepConfigService = new StepConfigService();