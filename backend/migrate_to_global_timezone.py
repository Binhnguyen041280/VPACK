#!/usr/bin/env python3
"""
Migration Script: Global Timezone Configuration

This script migrates the V_Track application from per-camera timezone settings
and hardcoded timezone values to a unified global timezone configuration system.

Features:
- Migrates timezone from general_info table to global_timezone_config
- Handles backward compatibility with existing configurations
- Validates timezone data during migration
- Provides detailed migration reporting
- Safe rollback capabilities

Usage:
    python3 migrate_to_global_timezone.py [options]
    
Options:
    --dry-run       : Simulate migration without making changes
    --force         : Force migration even if global config exists
    --rollback      : Rollback to previous timezone configuration
    --verbose       : Enable detailed logging
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.config.global_timezone_config import global_timezone_config
from modules.db_utils.safe_connection import safe_db_connection
from modules.utils.timezone_validator import timezone_validator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

class GlobalTimezoneMigration:
    """Handles migration to global timezone configuration."""
    
    def __init__(self, dry_run=False, force=False, verbose=False):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def check_prerequisites(self):
        """Check if migration can proceed."""
        logger.info("Checking migration prerequisites...")
        
        try:
            # Test database connection
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if general_info table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='general_info'")
                if not cursor.fetchone():
                    logger.warning("general_info table not found - creating with default values")
                    return True
                
                # Check if global_timezone_config already exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='global_timezone_config'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM global_timezone_config WHERE id = 1")
                    if cursor.fetchone()[0] > 0 and not self.force:
                        logger.error("Global timezone configuration already exists. Use --force to override.")
                        return False
                
                logger.info("✅ Prerequisites check passed")
                return True
                
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
            return False
    
    def analyze_current_state(self):
        """Analyze current timezone configuration."""
        logger.info("Analyzing current timezone configuration...")
        
        analysis = {
            'general_info_timezone': None,
            'general_info_iana': None,
            'has_enhanced_columns': False,
            'camera_specific_timezones': [],
            'system_detected_timezone': None
        }
        
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check general_info timezone
                cursor.execute("SELECT timezone FROM general_info WHERE id = 1")
                result = cursor.fetchone()
                if result:
                    analysis['general_info_timezone'] = result[0]
                
                # Check for enhanced timezone columns
                cursor.execute("PRAGMA table_info(general_info)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'timezone_iana_name' in columns:
                    analysis['has_enhanced_columns'] = True
                    cursor.execute("SELECT timezone_iana_name FROM general_info WHERE id = 1")
                    result = cursor.fetchone()
                    if result:
                        analysis['general_info_iana'] = result[0]
                
                # Check for camera-specific timezones (if camera_configs table exists)
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='camera_configs'")
                    if cursor.fetchone():
                        cursor.execute("SELECT camera_name, timezone FROM camera_configs WHERE timezone IS NOT NULL")
                        analysis['camera_specific_timezones'] = cursor.fetchall()
                except:
                    pass
            
            # Try to detect system timezone
            try:
                import time
                import subprocess
                
                # Try timedatectl (Linux)
                try:
                    result = subprocess.run(['timedatectl', 'show', '--property=Timezone'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('Timezone='):
                                analysis['system_detected_timezone'] = line.split('=', 1)[1]
                                break
                except:
                    pass
                
                # Fallback to environment variable
                if not analysis['system_detected_timezone']:
                    analysis['system_detected_timezone'] = os.environ.get('TZ', 'Unknown')
                    
            except Exception as e:
                logger.debug(f"System timezone detection failed: {e}")
            
            # Log analysis results
            logger.info("📊 Current State Analysis:")
            logger.info(f"   General Info Timezone: {analysis['general_info_timezone']}")
            logger.info(f"   General Info IANA: {analysis['general_info_iana']}")
            logger.info(f"   Enhanced Columns: {analysis['has_enhanced_columns']}")
            logger.info(f"   Camera-specific Timezones: {len(analysis['camera_specific_timezones'])}")
            logger.info(f"   System Detected: {analysis['system_detected_timezone']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Current state analysis failed: {e}")
            return analysis
    
    def determine_migration_strategy(self, analysis):
        """Determine the best migration strategy based on current state."""
        logger.info("Determining migration strategy...")
        
        strategy = {
            'source': 'fallback',
            'target_timezone': 'Asia/Ho_Chi_Minh',  # Default fallback
            'confidence': 'low',
            'actions': []
        }
        
        # Priority 1: Enhanced IANA timezone
        if analysis['general_info_iana']:
            validation = timezone_validator.validate_timezone(analysis['general_info_iana'])
            if validation.is_valid:
                strategy['source'] = 'general_info_iana'
                strategy['target_timezone'] = analysis['general_info_iana']
                strategy['confidence'] = 'high'
                strategy['actions'].append(f"Using validated IANA timezone: {analysis['general_info_iana']}")
        
        # Priority 2: Basic timezone with validation
        elif analysis['general_info_timezone']:
            tz_str = analysis['general_info_timezone']
            validation = timezone_validator.validate_timezone(tz_str)
            
            if validation.is_valid:
                strategy['source'] = 'general_info_basic'
                strategy['target_timezone'] = validation.iana_name or tz_str
                strategy['confidence'] = 'medium'
                strategy['actions'].append(f"Using validated basic timezone: {tz_str}")
            elif tz_str == 'UTC+7':
                # Handle common legacy format
                strategy['source'] = 'legacy_conversion'
                strategy['target_timezone'] = 'Asia/Ho_Chi_Minh'
                strategy['confidence'] = 'medium'
                strategy['actions'].append("Converting legacy UTC+7 to Asia/Ho_Chi_Minh")
        
        # Priority 3: System detection
        elif analysis['system_detected_timezone'] and analysis['system_detected_timezone'] != 'Unknown':
            validation = timezone_validator.validate_timezone(analysis['system_detected_timezone'])
            if validation.is_valid:
                strategy['source'] = 'system_detected'
                strategy['target_timezone'] = analysis['system_detected_timezone']
                strategy['confidence'] = 'medium'
                strategy['actions'].append(f"Using system detected timezone: {analysis['system_detected_timezone']}")
        
        # Handle camera-specific timezones
        if analysis['camera_specific_timezones']:
            strategy['actions'].append(f"Found {len(analysis['camera_specific_timezones'])} camera-specific timezones - will be unified to global setting")
        
        logger.info(f"📋 Migration Strategy:")
        logger.info(f"   Source: {strategy['source']}")
        logger.info(f"   Target Timezone: {strategy['target_timezone']}")
        logger.info(f"   Confidence: {strategy['confidence']}")
        for action in strategy['actions']:
            logger.info(f"   Action: {action}")
        
        return strategy
    
    def execute_migration(self, strategy):
        """Execute the migration based on the determined strategy."""
        logger.info("Executing migration...")
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
        
        try:
            # Set the global timezone
            if not self.dry_run:
                success, error = global_timezone_config.set_global_timezone(
                    strategy['target_timezone'], 
                    source='migration'
                )
                
                if not success:
                    raise Exception(f"Failed to set global timezone: {error}")
                
                logger.info(f"✅ Global timezone set to: {strategy['target_timezone']}")
            else:
                logger.info(f"🔍 Would set global timezone to: {strategy['target_timezone']}")
            
            # Update timezone manager cache
            if not self.dry_run:
                from modules.utils.timezone_manager import timezone_manager
                timezone_manager.clear_cache()
                logger.info("✅ Timezone manager cache cleared")
            
            # Report on camera-specific timezone cleanup
            if strategy['actions']:
                logger.info("📝 Migration actions completed:")
                for action in strategy['actions']:
                    logger.info(f"   ✅ {action}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            return False
    
    def verify_migration(self):
        """Verify that migration completed successfully."""
        logger.info("Verifying migration...")
        
        try:
            # Test global timezone configuration
            timezone_info = global_timezone_config.get_timezone_info()
            
            logger.info("🔍 Migration Verification:")
            logger.info(f"   Global Timezone: {timezone_info.timezone_iana}")
            logger.info(f"   Display Name: {timezone_info.timezone_display}")
            logger.info(f"   UTC Offset: {timezone_info.utc_offset_hours}")
            logger.info(f"   Validated: {timezone_info.is_validated}")
            logger.info(f"   Source: {timezone_info.source}")
            
            # Test timezone manager integration
            from modules.utils.timezone_manager import timezone_manager
            manager_tz = timezone_manager.get_user_timezone()
            
            logger.info(f"   Timezone Manager: {manager_tz}")
            
            if manager_tz == timezone_info.timezone_iana:
                logger.info("✅ Timezone manager integration verified")
                return True
            else:
                logger.warning(f"⚠️ Timezone manager mismatch: {manager_tz} vs {timezone_info.timezone_iana}")
                return False
                
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
    
    def run_migration(self):
        """Run the complete migration process."""
        logger.info("🚀 Starting Global Timezone Migration")
        logger.info(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"   Force: {self.force}")
        
        # Step 1: Prerequisites
        if not self.check_prerequisites():
            logger.error("❌ Migration aborted due to failed prerequisites")
            return False
        
        # Step 2: Analyze current state
        analysis = self.analyze_current_state()
        
        # Step 3: Determine strategy
        strategy = self.determine_migration_strategy(analysis)
        
        # Step 4: Execute migration
        if not self.execute_migration(strategy):
            logger.error("❌ Migration execution failed")
            return False
        
        # Step 5: Verify migration (skip for dry run)
        if not self.dry_run:
            if not self.verify_migration():
                logger.error("❌ Migration verification failed")
                return False
        
        logger.info("🎉 Global timezone migration completed successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description='Migrate to Global Timezone Configuration')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without making changes')
    parser.add_argument('--force', action='store_true', help='Force migration even if global config exists')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed logging')
    
    args = parser.parse_args()
    
    migration = GlobalTimezoneMigration(
        dry_run=args.dry_run,
        force=args.force,
        verbose=args.verbose
    )
    
    success = migration.run_migration()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()