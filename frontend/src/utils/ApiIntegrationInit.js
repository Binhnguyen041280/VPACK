import { createTimezoneAwareFetch } from './TimezoneAwareFetch';

/**
 * Initialize API integration with timezone awareness
 * Call this early in the application lifecycle
 */
export const initializeApiIntegration = () => {
  console.log('Initializing timezone-aware API integration...');
  
  // Override global fetch for timezone awareness
  const restoreFetch = createTimezoneAwareFetch();
  
  // Store restore function for cleanup if needed
  window._restoreOriginalFetch = restoreFetch;
  
  console.log('Timezone-aware API integration initialized');
  
  return {
    cleanup: restoreFetch
  };
};

/**
 * Cleanup API integration (for testing or hot reload)
 */
export const cleanupApiIntegration = () => {
  if (window._restoreOriginalFetch) {
    window._restoreOriginalFetch();
    delete window._restoreOriginalFetch;
    console.log('API integration cleaned up');
  }
};

export default {
  initialize: initializeApiIntegration,
  cleanup: cleanupApiIntegration
};