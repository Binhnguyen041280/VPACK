import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from modules.db_utils.safe_connection import safe_db_connection
from datetime import datetime

logger = logging.getLogger(__name__)

class PlatformDetector:
    """
    Smart platform detection service for Excel/CSV files
    Analyzes file headers, tracking codes, and filenames to determine platform
    Uses machine learning approach with confidence scoring
    """

    def __init__(self):
        self.platforms = self._load_platform_configs()
        logger.info(f"PlatformDetector initialized with {len(self.platforms)} platform configurations")

    def _load_platform_configs(self) -> List[Dict]:
        """Load platform configurations from database"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT platform_name, column_letter, header_pattern,
                           tracking_code_pattern, file_name_pattern, usage_count,
                           confidence_threshold, last_used_at
                    FROM platform_column_mappings
                    WHERE is_active = 1
                    ORDER BY usage_count DESC, last_used_at DESC
                """)

                columns = [desc[0] for desc in cursor.description]
                platforms = []

                for row in cursor.fetchall():
                    platform = dict(zip(columns, row))

                    # Parse JSON header pattern safely
                    try:
                        if platform['header_pattern']:
                            platform['header_pattern'] = json.loads(platform['header_pattern'])
                        else:
                            platform['header_pattern'] = []
                    except (json.JSONDecodeError, TypeError):
                        platform['header_pattern'] = []

                    platforms.append(platform)

                return platforms

        except Exception as e:
            logger.error(f"Error loading platform configurations: {e}")
            return []

    def detect_platform(self, headers: List[str], sample_data: List[str],
                       filename: str) -> Dict:
        """
        Detect platform from file analysis

        Args:
            headers: List of column headers from the file
            sample_data: Sample values from tracking code column candidates
            filename: Original filename

        Returns:
            {
                'auto_detect': bool,
                'platform': str,
                'column': str,
                'confidence': float,
                'details': dict  # Debugging info
            }
        """
        try:
            if not self.platforms:
                logger.warning("No platform configurations available")
                return {'auto_detect': False, 'confidence': 0.0}

            scores = {}
            details = {}

            for platform in self.platforms:
                score_info = self._calculate_platform_score(
                    platform, headers, sample_data, filename
                )

                scores[platform['platform_name']] = {
                    'score': score_info['total_score'],
                    'column': platform['column_letter'],
                    'config': platform,
                    'breakdown': score_info['breakdown']
                }

                details[platform['platform_name']] = score_info

            if not scores:
                return {'auto_detect': False, 'confidence': 0.0}

            # Find best match
            best_match = max(scores.items(), key=lambda x: x[1]['score'])
            platform_name, match_details = best_match

            confidence = match_details['score']
            auto_detect = confidence >= 50.0

            result = {
                'auto_detect': auto_detect,
                'platform': platform_name if auto_detect else None,
                'column': match_details['column'] if auto_detect else None,
                'confidence': confidence,
                'details': {
                    'all_scores': {k: v['score'] for k, v in scores.items()},
                    'best_match_breakdown': match_details['breakdown'],
                    'threshold': 50.0
                }
            }

            logger.info(f"Platform detection result: {platform_name}={confidence:.1f}% (auto_detect={auto_detect})")
            return result

        except Exception as e:
            logger.error(f"Error in platform detection: {e}")
            return {'auto_detect': False, 'confidence': 0.0, 'error': str(e)}

    def _calculate_platform_score(self, platform: Dict, headers: List[str],
                                 sample_data: List[str], filename: str) -> Dict:
        """Calculate confidence score for platform match"""

        breakdown = {}

        # Header matching (40% weight)
        header_score = self._score_headers(platform.get('header_pattern', []), headers)
        breakdown['header_score'] = header_score

        # Tracking code format (40% weight)
        tracking_score = self._score_tracking_codes(
            platform.get('tracking_code_pattern'), sample_data
        )
        breakdown['tracking_score'] = tracking_score

        # Filename matching (20% weight)
        filename_score = self._score_filename(
            platform.get('file_name_pattern'), filename
        )
        breakdown['filename_score'] = filename_score

        # Calculate weighted total
        total_score = (header_score * 0.4) + (tracking_score * 0.4) + (filename_score * 0.2)

        # Bonus for high usage count (up to 5% boost)
        usage_bonus = min(platform.get('usage_count', 0) * 0.5, 5.0)
        total_score += usage_bonus
        breakdown['usage_bonus'] = usage_bonus

        # Cap at 100%
        total_score = min(total_score, 100.0)

        return {
            'total_score': total_score,
            'breakdown': breakdown
        }

    def _score_headers(self, expected_headers: List[str], actual_headers: List[str]) -> float:
        """Score header similarity (case-insensitive partial matching)"""
        if not expected_headers or not actual_headers:
            return 0.0

        # Convert to lowercase for comparison
        expected_lower = [h.lower() for h in expected_headers]
        actual_lower = [h.lower() for h in actual_headers]

        matches = 0
        for expected in expected_lower:
            # Check for exact matches first
            if expected in actual_lower:
                matches += 1
            else:
                # Check for partial matches (e.g., "tracking" in "tracking code")
                for actual in actual_lower:
                    if expected in actual or actual in expected:
                        matches += 0.7  # Partial match gets less score
                        break

        # Score based on percentage of expected headers found
        score = (matches / len(expected_headers)) * 100
        return min(score, 100.0)

    def _score_tracking_codes(self, pattern: Optional[str], sample_data: List[str]) -> float:
        """Score tracking code format matching"""
        if not pattern or not sample_data:
            return 0.0

        try:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = 0
            total_samples = 0

            for data in sample_data[:10]:  # Check first 10 samples
                if data and isinstance(data, str) and data.strip():
                    total_samples += 1
                    if regex.match(data.strip()):
                        matches += 1

            if total_samples == 0:
                return 0.0

            # Score based on percentage of samples that match
            score = (matches / total_samples) * 100
            return min(score, 100.0)

        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return 0.0

    def _score_filename(self, pattern: Optional[str], filename: str) -> float:
        """Score filename pattern matching"""
        if not pattern or not filename:
            return 0.0

        try:
            regex = re.compile(pattern, re.IGNORECASE)
            if regex.search(filename):
                return 100.0
            else:
                return 0.0

        except re.error as e:
            logger.warning(f"Invalid filename pattern '{pattern}': {e}")
            return 0.0

    def save_platform_preference(self, platform_name: str, column_letter: str,
                                headers: List[str], sample_data: List[str],
                                filename: str) -> bool:
        """Save new platform configuration based on user selection"""
        try:
            # Generate patterns from provided data
            header_pattern = json.dumps(headers)
            tracking_pattern = self._generate_tracking_pattern(sample_data)
            filename_pattern = self._generate_filename_pattern(filename)

            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Check if platform already exists
                cursor.execute("""
                    SELECT id, usage_count FROM platform_column_mappings
                    WHERE platform_name = ? AND column_letter = ?
                """, (platform_name, column_letter))

                existing = cursor.fetchone()

                if existing:
                    # Update existing platform
                    cursor.execute("""
                        UPDATE platform_column_mappings SET
                            header_pattern = ?,
                            tracking_code_pattern = ?,
                            file_name_pattern = ?,
                            usage_count = usage_count + 1,
                            last_used_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (header_pattern, tracking_pattern, filename_pattern, existing[0]))

                    logger.info(f"Updated existing platform: {platform_name} (usage: {existing[1] + 1})")
                else:
                    # Insert new platform
                    cursor.execute("""
                        INSERT INTO platform_column_mappings
                        (platform_name, column_letter, header_pattern,
                         tracking_code_pattern, file_name_pattern, usage_count, last_used_at)
                        VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """, (platform_name, column_letter, header_pattern,
                          tracking_pattern, filename_pattern))

                    logger.info(f"Created new platform: {platform_name}")

                conn.commit()

            # Reload configurations
            self.platforms = self._load_platform_configs()
            return True

        except Exception as e:
            logger.error(f"Failed to save platform preference: {e}")
            return False

    def _generate_tracking_pattern(self, sample_data: List[str]) -> Optional[str]:
        """Generate regex pattern from sample tracking codes"""
        try:
            if not sample_data:
                return None

            # Analyze first few samples to find common patterns
            valid_samples = [s.strip() for s in sample_data[:5] if s and isinstance(s, str) and s.strip()]

            if not valid_samples:
                return None

            # Simple pattern generation based on common formats
            first_sample = valid_samples[0]

            # Shopee pattern: SPXVN + 9 digits
            if first_sample.upper().startswith('SPX') and len(first_sample) >= 12:
                return r'^SPX[A-Z]{2}\d{9}$'

            # General alphanumeric pattern
            pattern_parts = []
            for char in first_sample:
                if char.isalpha():
                    pattern_parts.append('[A-Z]')
                elif char.isdigit():
                    pattern_parts.append('\\d')
                else:
                    pattern_parts.append(re.escape(char))

            # Create flexible pattern (allow ± 2 characters)
            min_length = max(len(first_sample) - 2, 1)
            max_length = len(first_sample) + 2

            base_pattern = ''.join(pattern_parts)
            return f'^{base_pattern}{{,{max_length}}}$'

        except Exception as e:
            logger.warning(f"Error generating tracking pattern: {e}")
            return None

    def _generate_filename_pattern(self, filename: str) -> Optional[str]:
        """Generate regex pattern from filename"""
        try:
            if not filename:
                return None

            # Extract platform hints from filename
            filename_lower = filename.lower()

            if 'shopee' in filename_lower or 'spx' in filename_lower:
                return r'(shopee|spx).*order.*\.(xlsx?|csv)$'
            elif 'tiktok' in filename_lower or 'ttshop' in filename_lower:
                return r'(tiktok|ttshop).*order.*\.(xlsx?|csv)$'
            elif 'lazada' in filename_lower:
                return r'lazada.*export.*\.(xlsx?|csv)$'

            # Generic pattern based on filename structure
            name_without_ext = filename_lower.rsplit('.', 1)[0]
            if 'order' in name_without_ext or 'export' in name_without_ext:
                return r'.*order.*\.(xlsx?|csv)$'

            return None

        except Exception as e:
            logger.warning(f"Error generating filename pattern: {e}")
            return None

    def update_usage_stats(self, platform_name: str, column_letter: str) -> bool:
        """Update usage statistics for successful detection"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE platform_column_mappings SET
                        usage_count = usage_count + 1,
                        last_used_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE platform_name = ? AND column_letter = ?
                """, (platform_name, column_letter))

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Updated usage stats for {platform_name}")
                    return True
                else:
                    logger.warning(f"Platform not found: {platform_name}")
                    return False

        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            return False

    def get_platform_suggestions(self, headers: List[str]) -> List[Dict]:
        """Get platform suggestions based on headers only (quick lookup)"""
        try:
            suggestions = []

            for platform in self.platforms:
                header_score = self._score_headers(platform.get('header_pattern', []), headers)

                if header_score > 30.0:  # Lower threshold for suggestions
                    suggestions.append({
                        'platform_name': platform['platform_name'],
                        'column_letter': platform['column_letter'],
                        'header_score': header_score,
                        'usage_count': platform.get('usage_count', 0)
                    })

            # Sort by header score, then usage count
            suggestions.sort(key=lambda x: (x['header_score'], x['usage_count']), reverse=True)
            return suggestions[:3]  # Return top 3 suggestions

        except Exception as e:
            logger.error(f"Error getting platform suggestions: {e}")
            return []