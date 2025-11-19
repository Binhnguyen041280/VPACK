"""
Step 1 Brandname Service Layer for ePACK Configuration.

Handles business logic for brandname configuration including 
validation, change detection, and database operations.
"""

import json
from typing import Dict, Any, Tuple, Optional
from ..shared import (
    safe_connection_wrapper,
    execute_with_change_detection,
    validate_brand_name,
    sanitize_input,
    log_step_operation
)


class Step1BrandnameService:
    """Service class for Step 1 Brandname configuration operations."""
    
    DEFAULT_BRAND_NAME = "Alan_go"
    
    def get_current_brandname(self) -> Dict[str, Any]:
        """
        Get current brandname from database with fallback to default.
        
        Returns:
            Dict containing current brandname data
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT brand_name FROM general_info WHERE id = 1")
                row = cursor.fetchone()
                
                brand_name = row[0] if row and row[0] else self.DEFAULT_BRAND_NAME
                
                log_step_operation("1", "get_brandname", {"brand_name": brand_name})
                
                return {
                    "brand_name": brand_name,
                    "is_default": brand_name == self.DEFAULT_BRAND_NAME
                }
                
        except Exception as e:
            log_step_operation("1", "get_brandname", {"error": str(e)}, False)
            # Return default on error
            return {
                "brand_name": self.DEFAULT_BRAND_NAME,
                "is_default": True,
                "error": str(e)
            }
    
    def validate_brandname(self, brand_name: str) -> Tuple[bool, str]:
        """
        Validate brandname input with business rules.
        
        Args:
            brand_name: Brand name to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Sanitize input first
        brand_name = sanitize_input(brand_name, max_length=100)
        
        # Apply validation rules
        return validate_brand_name(brand_name)
    
    def update_brandname_if_changed(self, new_brand_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Update brandname only if different from current value.
        
        Args:
            new_brand_name: New brand name to set
            
        Returns:
            Tuple of (success: bool, result_data: dict)
        """
        try:
            # Sanitize and validate input
            new_brand_name = sanitize_input(new_brand_name, max_length=100)
            is_valid, validation_error = self.validate_brandname(new_brand_name)
            
            if not is_valid:
                return False, {"error": validation_error}
            
            # Check for changes using shared utility
            changed, current_data = execute_with_change_detection(
                table_name="general_info",
                record_id=1,
                new_data={"brand_name": new_brand_name}
            )
            
            if not changed:
                # No changes detected
                current_brand_name = current_data.get("brand_name", self.DEFAULT_BRAND_NAME)
                log_step_operation("1", "update_brandname", {"changed": False})
                
                return True, {
                    "brand_name": current_brand_name,
                    "changed": False,
                    "message": "No changes detected"
                }
            
            # Perform update with preservation of existing data
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO general_info (
                        id, brand_name, country, timezone, language, working_days, from_time, to_time
                    ) VALUES (
                        1, ?, 
                        COALESCE((SELECT country FROM general_info WHERE id = 1), 'Vietnam'),
                        COALESCE((SELECT timezone FROM general_info WHERE id = 1), 'Asia/Ho_Chi_Minh'),
                        COALESCE((SELECT language FROM general_info WHERE id = 1), 'English (en-US)'),
                        COALESCE((SELECT working_days FROM general_info WHERE id = 1), '["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]'),
                        COALESCE((SELECT from_time FROM general_info WHERE id = 1), '07:00'),
                        COALESCE((SELECT to_time FROM general_info WHERE id = 1), '23:00')
                    )
                """, (new_brand_name,))
                
                conn.commit()
                
                log_step_operation("1", "update_brandname", {
                    "brand_name": new_brand_name, 
                    "changed": True
                })
                
                return True, {
                    "brand_name": new_brand_name,
                    "changed": True,
                    "message": "Brand name updated successfully"
                }
                
        except Exception as e:
            log_step_operation("1", "update_brandname", {"error": str(e)}, False)
            return False, {"error": f"Failed to update brandname: {str(e)}"}
    
    def get_brandname_statistics(self) -> Dict[str, Any]:
        """
        Get brandname-related statistics for monitoring.
        
        Returns:
            Dict with brandname statistics
        """
        try:
            current_data = self.get_current_brandname()
            
            stats = {
                "current_brand_name": current_data["brand_name"],
                "is_default": current_data["is_default"],
                "character_count": len(current_data["brand_name"]),
                "is_valid": True
            }
            
            # Additional validation check
            is_valid, _ = self.validate_brandname(current_data["brand_name"])
            stats["is_valid"] = is_valid
            
            return stats
            
        except Exception as e:
            return {"error": f"Failed to get brandname statistics: {str(e)}"}


# Create singleton instance for import
step1_brandname_service = Step1BrandnameService()