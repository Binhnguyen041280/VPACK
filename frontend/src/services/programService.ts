/**
 * Program Service for V_Track Video Processing System
 *
 * This service handles all API communications between the frontend and backend
 * for program control operations including starting/stopping programs,
 * monitoring progress, and managing processing configurations.
 */

import { retryOperation, parseApiError } from '../utils/errorHandler';

export interface StartProgramParams {
  programType: 'first' | 'default' | 'custom';
  action: 'run' | 'stop';
  days?: number;
  customPath?: string;
}

export interface ProgramResponse {
  success?: boolean;
  current_running: string | null;
  days?: number | null;
  custom_path?: string | null;
  error?: string;
}

export interface ProgramStatus {
  current_running: string | null;
  days?: number | null;
  custom_path?: string | null;
}

export interface ProgressData {
  files: Array<{
    file: string;
    status: string;
  }>;
  error?: string;
}

export interface FirstRunStatus {
  first_run_completed: boolean;
  error?: string;
}

export interface Camera {
  name: string;
  path: string;
  stream_url?: string;
  resolution?: string;
  codec?: string;
  source_type?: string;
  source_name?: string;
  is_selected?: boolean;
}

export interface CameraResponse {
  success: boolean;
  cameras: Camera[];
  count: number;
  error?: string;
}

class ProgramService {
  private readonly baseUrl = 'http://localhost:8080/api';

  /**
   * Map frontend program types to backend program names
   */
  private mapProgramType(programType: string): string {
    const mapping: Record<string, string> = {
      'first': 'Lần đầu',
      'default': 'Mặc định',
      'custom': 'Chỉ định'
    };
    return mapping[programType] || programType;
  }

  /**
   * Start or stop a video processing program
   */
  async startProgram(params: StartProgramParams): Promise<ProgramResponse> {
    return retryOperation(async () => {
      const response = await fetch(`${this.baseUrl}/program`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          card: this.mapProgramType(params.programType),
          action: params.action,
          days: params.days,
          custom_path: params.customPath
        })
      });

      const data = await response.json();

      if (!response.ok) {
        const error = parseApiError({
          message: data.error || `Failed to ${params.action} program`,
          statusCode: response.status,
          details: data
        });
        throw error;
      }

      return data;
    }, 2); // Max 2 retries for program operations
  }

  /**
   * Stop the currently running program
   */
  async stopProgram(): Promise<ProgramResponse> {
    return this.startProgram({
      programType: 'default', // This will be ignored for stop action
      action: 'stop'
    });
  }

  /**
   * Get current program execution status
   */
  async getProgramStatus(): Promise<ProgramStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/program`, {
        method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to get program status`);
      }

      return data;
    } catch (error) {
      console.error('Error getting program status:', error);
      throw error;
    }
  }

  /**
   * Get real-time processing progress
   */
  async getProgramProgress(): Promise<ProgressData> {
    try {
      const response = await fetch(`${this.baseUrl}/program-progress`, {
        method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to get program progress`);
      }

      return data;
    } catch (error) {
      console.error('Error getting program progress:', error);
      throw error;
    }
  }

  /**
   * Check if the first run has been completed
   */
  async checkFirstRun(): Promise<FirstRunStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/check-first-run`, {
        method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to check first run status`);
      }

      return data;
    } catch (error) {
      console.error('Error checking first run status:', error);
      throw error;
    }
  }

  /**
   * Get configured cameras list
   */
  async getCameras(): Promise<Camera[]> {
    try {
      const response = await fetch(`${this.baseUrl}/get-cameras`, {
        method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to get cameras`);
      }

      const cameras = data.cameras || [];

      // Handle both array of strings and array of objects
      if (Array.isArray(cameras)) {
        return cameras.map((camera: any) => {
          if (typeof camera === 'string') {
            // Backend returns array of strings
            return {
              name: camera,
              path: camera, // Use name as path fallback
              source_type: 'local'
            };
          } else {
            // Backend returns array of objects
            return camera;
          }
        });
      }

      return [];
    } catch (error) {
      console.error('Error getting cameras:', error);
      throw error;
    }
  }

  /**
   * Get available camera folders
   */
  async getCameraFolders(): Promise<Array<{name: string, path: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/get-camera-folders`, {
        method: 'GET',
        credentials: 'include',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to get camera folders`);
      }

      return data.folders || [];
    } catch (error) {
      console.error('Error getting camera folders:', error);
      throw error;
    }
  }

  /**
   * Confirm and execute a processing program
   */
  async confirmRun(programType: string): Promise<{program_type: string}> {
    try {
      const response = await fetch(`${this.baseUrl}/confirm-run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          card: this.mapProgramType(programType)
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: Failed to confirm run`);
      }

      return data;
    } catch (error) {
      console.error('Error confirming run:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const programService = new ProgramService();
export default programService;