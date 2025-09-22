/**
 * File processing utilities for handling user input and state management
 */

export interface FileProcessingMessage {
  id: string;
  type: 'file_processing';
  content: string;
  timestamp: Date;
  fileProcessingData: {
    fileContent: string;
    fileName: string;
    isExcel: boolean;
    stage: 'platform_selection' | 'headers' | 'column_selected' | 'platform_named' | 'parsed' | 'results' | 'error';
    selectedColumn?: string;
    platformName?: string;
    availablePlatforms?: Array<{name: string; column: string}>;
    waitingForInput?: 'platform_select' | 'column' | 'platform' | 'none';
    trackingCodes?: string[];
  };
}

export interface FileProcessingCommand {
  type: 'platform_select' | 'column_select' | 'platform_name' | 'restart' | 'help' | 'invalid';
  value?: string;
}

/**
 * Parse user input for file processing commands
 */
export function parseFileProcessingInput(input: string, context?: { stage?: string, maxColumns?: number }): FileProcessingCommand {
  const trimmed = input.trim().toLowerCase();

  // Special commands
  if (trimmed === 'back' || trimmed === 'restart') {
    return { type: 'restart' };
  }

  if (trimmed === 'help') {
    return { type: 'help' };
  }

  // Only check for column selection if we're in headers stage
  if (context?.stage === 'headers') {
    // Column selection (A-Z, AA-ZZ, etc.) - only valid Excel column names
    if (/^[a-z]+$/i.test(trimmed) && isValidExcelColumn(trimmed.toUpperCase(), context.maxColumns || 0)) {
      return {
        type: 'column_select',
        value: trimmed.toUpperCase()
      };
    }
  }

  // Platform name (2+ characters, not just numbers)
  if (trimmed.length >= 2 && !/^\d+$/.test(trimmed)) {
    return {
      type: 'platform_name',
      value: input.trim() // Keep original case for platform names
    };
  }

  return { type: 'invalid' };
}

/**
 * Check if a column name is valid for the given number of columns
 */
function isValidExcelColumn(columnName: string, maxColumns: number): boolean {
  if (maxColumns === 0) return false;

  const columnIndex = getColumnIndex(columnName);
  return columnIndex >= 0 && columnIndex < maxColumns;
}

/**
 * Generate help text for current file processing stage
 */
export function getFileProcessingHelp(stage: string, waitingFor?: string): string {
  switch (stage) {
    case 'headers':
      return `📋 Available commands:
• Type column letter (A, B, C...) to select tracking code column
• Type "help" to see this message`;

    case 'column_selected':
      return `📋 Available commands:
• Type platform name (e.g., "Shopee", "TikTok")
• Type "back" to choose different column
• Type "help" to see this message`;

    case 'error':
      return `📋 Available commands:
• Type "restart" to try again
• Type "help" to see this message`;

    default:
      return `📋 Available commands:
• Type "help" to see available commands
• Type "restart" to start over`;
  }
}

/**
 * Validate column letter input
 */
export function validateColumnInput(column: string, headers: string[]): { valid: boolean; error?: string } {
  if (!column || column.length !== 1) {
    return { valid: false, error: 'Please provide a single column letter (A, B, C...)' };
  }

  const columnIndex = column.charCodeAt(0) - 65; // A=0, B=1, etc.

  if (columnIndex < 0 || columnIndex >= headers.length) {
    return {
      valid: false,
      error: `Column ${column} doesn't exist. Available columns: ${headers.map((_, i) => String.fromCharCode(65 + i)).join(', ')}`
    };
  }

  return { valid: true };
}

/**
 * Validate platform name input
 */
export function validatePlatformInput(platform: string): { valid: boolean; error?: string } {
  if (!platform || platform.trim().length < 2) {
    return { valid: false, error: 'Platform name must be at least 2 characters' };
  }

  if (/^\d+$/.test(platform.trim())) {
    return { valid: false, error: 'Platform name cannot be just numbers' };
  }

  return { valid: true };
}

/**
 * Create file upload input element
 */
export function createFileUploadInput(onFileSelected: (file: File) => void): void {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.xlsx,.xls,.csv';
  input.style.display = 'none';

  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) {
      onFileSelected(file);
    }
    // Clean up
    input.remove();
  };

  // Add to DOM temporarily and trigger click
  document.body.appendChild(input);
  input.click();
}

/**
 * Convert file to base64 string
 */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      if (reader.result) {
        // Convert ArrayBuffer to base64
        const arrayBuffer = reader.result as ArrayBuffer;
        const bytes = new Uint8Array(arrayBuffer);
        let binary = '';
        bytes.forEach(byte => binary += String.fromCharCode(byte));
        resolve(btoa(binary));
      } else {
        reject(new Error('Failed to read file'));
      }
    };

    reader.onerror = () => reject(new Error('File reading failed'));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Get file extension and determine if it's Excel
 */
export function getFileType(filename: string): { isExcel: boolean; extension: string } {
  const extension = filename.split('.').pop()?.toLowerCase() || '';
  const isExcel = ['xlsx', 'xls'].includes(extension);

  return { isExcel, extension };
}

/**
 * Generate file processing response messages
 */
export function generateFileProcessingResponse(
  command: FileProcessingCommand,
  currentStage: string,
  context?: any
): string {
  switch (command.type) {
    case 'help':
      return getFileProcessingHelp(currentStage, context?.waitingFor);

    case 'restart':
      return `🔄 Restarting file processing. Please select a column letter from the headers above.`;

    case 'column_select':
      return `✅ Column ${command.value} selected. Please provide the platform name (e.g., "Shopee", "TikTok").`;

    case 'platform_name':
      return `✅ Platform "${command.value}" set. Processing file...`;

    case 'invalid':
      return `❌ Invalid input. ${getFileProcessingHelp(currentStage, context?.waitingFor)}`;

    default:
      return `❌ Unknown command. Type "help" for available commands.`;
  }
}

/**
 * Convert column index to Excel column name (A, B, ..., Z, AA, AB, ...)
 */
function getExcelColumnName(colIndex: number): string {
  let result = '';
  let num = colIndex;
  while (num >= 0) {
    result = String.fromCharCode(65 + (num % 26)) + result;
    num = Math.floor(num / 26) - 1;
  }
  return result;
}

/**
 * Convert Excel column name to index (A=0, B=1, ..., Z=25, AA=26, AB=27, ...)
 */
export function getColumnIndex(colName: string): number {
  let result = 0;
  for (let i = 0; i < colName.length; i++) {
    result = result * 26 + (colName.charCodeAt(i) - 65 + 1);
  }
  return result - 1;
}

/**
 * Format headers for text display (3 columns per row) - display only
 */
export function formatHeadersAsText(headers: string[]): string {
  if (!headers || headers.length === 0) {
    return "No headers found in file.";
  }

  let text = "📋 File Headers: (Type column letter to select tracking codes)\n\n";

  for (let i = 0; i < headers.length; i += 3) {
    const row = headers.slice(i, i + 3);

    // Format each column with fixed width for alignment
    const formattedColumns = row.map((header, index) => {
      const columnLetter = getExcelColumnName(i + index);
      // Truncate headers to exactly 15 characters
      const truncatedHeader = header.length > 15 ? header.substring(0, 15) : header;
      // Create column with exact spacing - 30 characters apart
      const fullColumn = `🔹${columnLetter}: ${truncatedHeader}`;
      return fullColumn.padEnd(30, ' ');
    });

    // Join without separators
    text += `${formattedColumns.join('')}\n`;
  }

  return text;
}

/**
 * Format tracking codes preview for text display - inline style
 */
export function formatTrackingCodesPreview(codes: string[], selectedColumn: string, platformName?: string): string {
  const displayCodes = codes.slice(0, 5); // Show first 5
  const remaining = codes.length - 5;

  let text = `✅ **Column ${selectedColumn} selected** • 📊 **${codes.length} tracking codes found**\n\n`;
  text += "📋 **Preview:** ";

  // Display codes inline
  text += displayCodes.map(code => `\`${code}\``).join(", ");

  if (remaining > 0) {
    text += ` + ${remaining} more`;
  }

  if (platformName) {
    text += `\n\n🏷️ **Platform:** ${platformName}\n🔍 **Auto-querying database...** Please wait for results.`;
  } else {
    // Get platforms from database and show UI like header columns
    text += "\n\n💡 **Select platform for this file:**";
  }

  return text;
}

/**
 * Format final processing results for text display - inline style
 */
export function formatProcessingResults(
  fileName: string,
  platformName: string,
  selectedColumn: string,
  trackingCodes: string[],
  eventsFound: number
): string {
  let text = `📄 **Processing Complete:** ${fileName}\n`;
  text += `🏷️ **${platformName}** • 📋 **Column ${selectedColumn}** • 📊 **${trackingCodes.length} codes** • 🎯 **${eventsFound} events found**\n\n`;

  if (eventsFound > 0) {
    text += "✅ **Success!** Event results are displayed below.";
  } else {
    text += "⚠️ **No events found** for the provided tracking codes in the current time range.";
  }

  return text;
}

/**
 * Simple text-based platform detection (replaces complex auto-detection)
 * @param text - User input text to analyze
 * @returns Platform name if detected, null otherwise
 */
export function detectPlatformFromText(text: string): string | null {
  if (!text || typeof text !== 'string') {
    return null;
  }

  const platforms = ['shopee', 'tiktok', 'lazada', 'amazon'];
  const lowerText = text.toLowerCase();

  for (const platform of platforms) {
    if (lowerText.includes(platform)) {
      // Return with proper capitalization
      return platform.charAt(0).toUpperCase() + platform.slice(1);
    }
  }

  return null;
}

/**
 * Get available platforms from backend API
 * @returns Promise with array of platform objects
 */
export async function getAvailablePlatforms(): Promise<Array<{name: string; column: string}>> {
  try {
    const response = await fetch('http://localhost:8080/get-platform-list');
    if (!response.ok) {
      throw new Error(`Failed to fetch platforms: ${response.status}`);
    }
    const data = await response.json();
    return data.platforms || [];
  } catch (error) {
    console.error('Error fetching platforms:', error);
    // Return empty array if no platforms found - user will create from scratch
    return [];
  }
}

/**
 * Format platforms as text similar to header columns display
 * @param platforms - Array of platform objects
 * @returns Formatted text string for display
 */
export function formatPlatformsAsText(platforms: Array<{name: string; column: string}>): string {
  if (!platforms || platforms.length === 0) {
    return "📋 No saved platforms found. (Type 'A' to create new platform)\n\n🔹A: Create New Platform";
  }

  let text = "📋 Saved Platforms: (Type letter to select platform)\n\n";

  // Add existing platforms
  for (let i = 0; i < platforms.length; i += 3) {
    const row = platforms.slice(i, i + 3);

    // Format each platform with fixed width for alignment
    const formattedPlatforms = row.map((platform, index) => {
      const platformLetter = String.fromCharCode(65 + i + index); // A, B, C...
      // Create platform display with exact spacing - 30 characters apart
      const fullPlatform = `🔹${platformLetter}: ${platform.name} (Col ${platform.column})`;
      return fullPlatform.padEnd(30, ' ');
    });

    // Join row and add to text
    text += formattedPlatforms.join('') + '\n';
  }

  // Add "Create New Platform" option
  const newPlatformLetter = String.fromCharCode(65 + platforms.length);
  text += `\n🔹${newPlatformLetter}: Create New Platform`;

  return text;
}

