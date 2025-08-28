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
    // UPSERT pattern fields
    current_source?: {
      id: number;
      source_type: string;
      name: string;
      path: string;
      created_at: string;
      original_source_type?: string;
    };
    detected_folders?: { name: string; path: string }[];
    selected_tree_folders?: any[];
    camera_count?: number;
    statistics?: any;
    single_source_mode?: boolean;
    backward_compatibility?: any;
    // Cloud storage fields
    selectedTreeFoldersCount?: number;
    defaultSyncPath?: string;
    upsert_operation?: boolean;
    videoSourceId?: number;
    videoSourceName?: string;
  };
  message?: string;
  error?: string;
}

/**
 * Step 5 Timing/Storage Configuration Interfaces
 */
interface TimingStorageData {
  min_packing_time: number;
  max_packing_time: number;
  video_buffer: number;
  storage_duration: number;
  frame_rate: number;
  frame_interval: number;
  output_path: string;
}

interface TimingStorageResponse {
  success: boolean;
  data: TimingStorageData & {
    changed?: boolean;
  };
  message?: string;
  warning?: string;
  error?: string;
}

interface TimingValidationResponse {
  success: boolean;
  valid: boolean;
  data: Partial<TimingStorageData>;
  validation_details?: {
    basic_validation: 'passed' | 'failed' | 'pending';
    business_rules: 'passed' | 'failed' | 'pending';
    field_checks: Record<string, {
      value: any;
      type: string;
      valid: boolean;
      range_check: {
        in_range: boolean;
        min: number;
        max: number;
        value: number;
      };
    }>;
    performance_analysis: {
      processing_fps: number;
      processing_load_percent: number;
      performance_level: string;
    };
    path_validation?: {
      valid: boolean;
      error?: string;
      exists: boolean;
    };
    recommendations: string[];
  };
  error?: string;
}

interface TimingStatisticsResponse {
  success: boolean;
  data: {
    current_config: TimingStorageData;
    packing_time_range: {
      min: number;
      max: number;
      range_seconds: number;
      gap_adequate: boolean;
    };
    performance_metrics: {
      frame_rate: number;
      frame_interval: number;
      processing_fps: number;
      processing_load_percent: number;
      performance_category: string;
      frames_skipped_percent: number;
    };
    storage_settings: {
      storage_duration_days: number;
      video_buffer_seconds: number;
      output_path: string;
      output_path_exists: boolean;
    };
    system_impact: {
      daily_storage_reduction_percent: number;
      estimated_daily_frames_processed: number;
      recommended_adjustments: string[];
    };
    validation_status: {
      valid: boolean;
      error?: string;
    };
  };
  message?: string;
  error?: string;
}

interface TimingDefaultsResponse {
  success: boolean;
  data: TimingStorageData;
  message?: string;
  error?: string;
}

interface PerformanceEstimateRequest {
  frame_rate: number;
  frame_interval: number;
  video_duration_hours?: number;
}

interface PerformanceEstimateResponse {
  success: boolean;
  data: {
    frame_processing: {
      frames_per_second_original: number;
      frames_per_second_processed: number;
      processing_load_percentage: number;
      frames_skipped_percentage: number;
    };
    daily_estimates: {
      total_frames_24h: number;
      processed_frames_24h: number;
      estimated_storage_reduction: string;
    };
    performance_category: string;
    recommendations: string[];
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
   * Fetch processing_config selected_cameras for Step 4 Packing Area Canvas
   * This specifically gets the cameras from processing_config table
   */
  async fetchProcessingConfigCameras(): Promise<{
    success: boolean;
    data: {
      selectedCameras?: string[];
      inputPath?: string;
      cameraCount?: number;
    };
    message?: string;
    error?: string;
  }> {
    try {
      console.log('🔍 StepConfigService - Fetching cameras from processing_config...');
      
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

      const result = await response.json();
      console.log('📡 StepConfigService - Raw response:', result);

      if (result.success && result.data && result.data.backward_compatibility) {
        const processingConfig = result.data.backward_compatibility;
        const selectedCameras = processingConfig.processing_config_selected_cameras || [];
        const inputPath = processingConfig.processing_config_input_path || '';
        
        console.log('✅ StepConfigService - Processing config cameras:', selectedCameras);
        
        return {
          success: true,
          data: {
            selectedCameras,
            inputPath,
            cameraCount: selectedCameras.length
          },
          message: 'Successfully fetched cameras from processing_config'
        };
      } else {
        console.log('⚠️ StepConfigService - No processing_config data found');
        return {
          success: true,
          data: {
            selectedCameras: [],
            inputPath: '',
            cameraCount: 0
          },
          message: 'No processing_config data available'
        };
      }
    } catch (error) {
      console.error('❌ StepConfigService - Error fetching processing_config cameras:', error);
      return {
        success: false,
        data: {
          selectedCameras: [],
          inputPath: '',
          cameraCount: 0
        },
        error: `Failed to fetch processing_config cameras: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    }
  }

  /**
   * Update video source configuration if changed (UPSERT pattern)
   */
  async updateVideoSourceState(videoSourceData: {
    sourceType: string;
    inputPath?: string;
    detectedFolders?: { name: string; path: string }[];
    selectedCameras?: string[];
    selected_tree_folders?: any[];  // For cloud storage
  }): Promise<VideoSourceResponse> {
    try {
      // Debug logging
      console.log('🔍 StepConfigService - Sending payload:', JSON.stringify(videoSourceData, null, 2));
      
      const response = await fetch(`${this.baseUrl}/step/video-source`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(videoSourceData),
      });

      console.log('📡 StepConfigService - Response status:', response.status);

      if (!response.ok) {
        // Try to get error details from response
        let errorDetail = `HTTP error! status: ${response.status}`;
        try {
          const errorResponse = await response.json();
          if (errorResponse.error) {
            errorDetail = `HTTP ${response.status}: ${errorResponse.error}`;
          }
        } catch (parseError) {
          // Response isn't JSON, keep original error
        }
        throw new Error(errorDetail);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Success response:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error updating video source state:', error);
      throw error;
    }
  }

  // ==============================================
  // STEP 5: TIMING/STORAGE CONFIGURATION METHODS
  // ==============================================

  /**
   * Fetch current timing/storage configuration from backend
   */
  async fetchTimingStorageState(): Promise<TimingStorageResponse> {
    try {
      console.log('🔍 StepConfigService - Fetching timing/storage state...');
      
      const response = await fetch(`${this.baseUrl}/step/timing`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('📡 StepConfigService - Timing GET response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Timing state fetched:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error fetching timing/storage state:', error);
      throw error;
    }
  }

  /**
   * Update timing/storage configuration if changed
   */
  async updateTimingStorageState(timingData: Partial<TimingStorageData>): Promise<TimingStorageResponse> {
    try {
      console.log('🔍 StepConfigService - Updating timing/storage state:', JSON.stringify(timingData, null, 2));
      
      const response = await fetch(`${this.baseUrl}/step/timing`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(timingData),
      });

      console.log('📡 StepConfigService - Timing PUT response status:', response.status);

      if (!response.ok) {
        // Try to get error details from response
        let errorDetail = `HTTP error! status: ${response.status}`;
        try {
          const errorResponse = await response.json();
          if (errorResponse.error) {
            errorDetail = `HTTP ${response.status}: ${errorResponse.error}`;
          }
        } catch (parseError) {
          // Response isn't JSON, keep original error
        }
        throw new Error(errorDetail);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Timing state updated:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error updating timing/storage state:', error);
      throw error;
    }
  }

  /**
   * Validate timing/storage configuration without saving
   */
  async validateTimingSettings(timingData: Partial<TimingStorageData>): Promise<TimingValidationResponse> {
    try {
      console.log('🔍 StepConfigService - Validating timing settings:', JSON.stringify(timingData, null, 2));
      
      const response = await fetch(`${this.baseUrl}/step/timing/validate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(timingData),
      });

      console.log('📡 StepConfigService - Timing validation response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Timing validation result:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error validating timing settings:', error);
      throw error;
    }
  }

  /**
   * Get timing/storage configuration statistics
   */
  async getTimingStatistics(): Promise<TimingStatisticsResponse> {
    try {
      console.log('🔍 StepConfigService - Fetching timing statistics...');
      
      const response = await fetch(`${this.baseUrl}/step/timing/statistics`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('📡 StepConfigService - Timing statistics response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Timing statistics fetched:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error fetching timing statistics:', error);
      throw error;
    }
  }

  /**
   * Get default values for timing/storage configuration
   */
  async getTimingDefaults(): Promise<TimingDefaultsResponse> {
    try {
      console.log('🔍 StepConfigService - Fetching timing defaults...');
      
      const response = await fetch(`${this.baseUrl}/step/timing/defaults`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('📡 StepConfigService - Timing defaults response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Timing defaults fetched:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error fetching timing defaults:', error);
      throw error;
    }
  }

  /**
   * Calculate performance estimates based on frame settings
   */
  async getPerformanceEstimate(estimateRequest: PerformanceEstimateRequest): Promise<PerformanceEstimateResponse> {
    try {
      console.log('🔍 StepConfigService - Calculating performance estimate:', JSON.stringify(estimateRequest, null, 2));
      
      const response = await fetch(`${this.baseUrl}/step/timing/performance-estimate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(estimateRequest),
      });

      console.log('📡 StepConfigService - Performance estimate response status:', response.status);

      if (!response.ok) {
        // Try to get error details from response
        let errorDetail = `HTTP error! status: ${response.status}`;
        try {
          const errorResponse = await response.json();
          if (errorResponse.error) {
            errorDetail = `HTTP ${response.status}: ${errorResponse.error}`;
          }
        } catch (parseError) {
          // Response isn't JSON, keep original error
        }
        throw new Error(errorDetail);
      }

      const result = await response.json();
      console.log('✅ StepConfigService - Performance estimate calculated:', result);
      return result;
    } catch (error) {
      console.error('❌ StepConfigService - Error calculating performance estimate:', error);
      throw error;
    }
  }

  /**
   * Reset timing/storage configuration to defaults
   */
  async resetTimingToDefaults(): Promise<TimingStorageResponse> {
    try {
      console.log('🔍 StepConfigService - Resetting timing to defaults...');
      
      // First get the defaults
      const defaultsResponse = await this.getTimingDefaults();
      if (!defaultsResponse.success) {
        throw new Error(defaultsResponse.error || 'Failed to get defaults');
      }

      // Then update with the default values
      return await this.updateTimingStorageState(defaultsResponse.data);
    } catch (error) {
      console.error('❌ StepConfigService - Error resetting timing to defaults:', error);
      throw error;
    }
  }

  /**
   * Utility method to check if timing configuration is optimal
   */
  isTimingConfigOptimal(config: TimingStorageData): {
    optimal: boolean;
    issues: string[];
    recommendations: string[];
  } {
    const issues: string[] = [];
    const recommendations: string[] = [];

    // Check packing time range
    const timeGap = config.max_packing_time - config.min_packing_time;
    if (timeGap < 10) {
      issues.push('Very small gap between min and max packing time');
      recommendations.push('Increase the gap between min and max packing time for better flexibility');
    }

    // Check processing load
    const processingFps = config.frame_rate / Math.max(1, config.frame_interval);
    const loadPercent = (processingFps / config.frame_rate) * 100;
    
    if (loadPercent > 80) {
      issues.push('High processing load may impact system performance');
      recommendations.push('Consider increasing frame_interval to reduce processing load');
    } else if (loadPercent < 20) {
      issues.push('Low processing rate may miss important events');
      recommendations.push('Consider decreasing frame_interval for better detection accuracy');
    }

    // Check video buffer relative to packing time
    if (config.video_buffer > config.min_packing_time / 2) {
      issues.push('Video buffer is large relative to minimum packing time');
      recommendations.push('Consider reducing video buffer or increasing minimum packing time');
    }

    // Check storage duration
    if (config.storage_duration > 90) {
      issues.push('Long storage duration may consume significant disk space');
      recommendations.push('Consider reducing storage duration if not required by business needs');
    }

    return {
      optimal: issues.length === 0,
      issues,
      recommendations
    };
  }
}

export const stepConfigService = new StepConfigService();

// Export types for use in components
export type {
  TimingStorageData,
  TimingStorageResponse,
  TimingValidationResponse,
  TimingStatisticsResponse,
  TimingDefaultsResponse,
  PerformanceEstimateRequest,
  PerformanceEstimateResponse
};