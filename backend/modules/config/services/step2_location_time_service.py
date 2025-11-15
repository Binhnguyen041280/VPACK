"""
Step 2 Location/Time Service Layer for V.PACK Configuration.

Handles business logic for location and time configuration including
timezone validation, working days management, and enhanced timezone support.
FIXED: Removes Vietnamese day name conversion - frontend sends English directly.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from modules.utils.simple_timezone import simple_validate_timezone

from ..shared import (
    ensure_column_exists,
    execute_with_change_detection,
    log_step_operation,
    safe_connection_wrapper,
    sanitize_input,
    validate_required_fields,
    validate_time_format,
    validate_working_days,
)


class Step2LocationTimeService:
    """Service class for Step 2 Location/Time configuration operations."""

    # Default values
    DEFAULT_COUNTRY = "Vietnam"
    DEFAULT_LANGUAGE = "English (en-US)"
    DEFAULT_WORKING_DAYS = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    DEFAULT_FROM_TIME = "07:00"
    DEFAULT_TO_TIME = "23:00"

    @property
    def DEFAULT_TIMEZONE(self):
        """Get default timezone from DB config."""
        from modules.utils.simple_timezone import get_system_timezone_from_db

        return get_system_timezone_from_db()

    def __init__(self):
        """Initialize service with timezone validator."""
        # Using simple_validate_timezone function instead of class

    def get_location_time_config(self) -> Dict[str, Any]:
        """
        Get current location/time configuration with enhanced timezone data.

        Returns:
            Dict containing current location/time configuration
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()

                # Check if language column exists
                cursor.execute("PRAGMA table_info(general_info)")
                existing_columns = [col[1] for col in cursor.fetchall()]
                has_language_column = "language" in existing_columns
                has_enhanced_timezone = "timezone_iana_name" in existing_columns

                if has_language_column:
                    base_query = """
                        SELECT country, timezone, language, working_days, from_time, to_time 
                        FROM general_info WHERE id = 1
                    """
                else:
                    base_query = """
                        SELECT country, timezone, working_days, from_time, to_time 
                        FROM general_info WHERE id = 1
                    """

                cursor.execute(base_query)
                row = cursor.fetchone()

                if row:
                    if has_language_column:
                        country, timezone, language, working_days_json, from_time, to_time = row
                    else:
                        country, timezone, working_days_json, from_time, to_time = row
                        language = self.DEFAULT_LANGUAGE

                    # Parse working_days JSON
                    try:
                        working_days = (
                            json.loads(working_days_json)
                            if working_days_json
                            else self.DEFAULT_WORKING_DAYS
                        )
                    except json.JSONDecodeError:
                        working_days = self.DEFAULT_WORKING_DAYS

                    config = {
                        "country": country or self.DEFAULT_COUNTRY,
                        "timezone": timezone or self.DEFAULT_TIMEZONE,
                        "language": language or self.DEFAULT_LANGUAGE,
                        "working_days": working_days,
                        "from_time": from_time or self.DEFAULT_FROM_TIME,
                        "to_time": to_time or self.DEFAULT_TO_TIME,
                    }
                else:
                    # No record exists - return defaults
                    config = {
                        "country": self.DEFAULT_COUNTRY,
                        "timezone": self.DEFAULT_TIMEZONE,
                        "language": self.DEFAULT_LANGUAGE,
                        "working_days": self.DEFAULT_WORKING_DAYS,
                        "from_time": self.DEFAULT_FROM_TIME,
                        "to_time": self.DEFAULT_TO_TIME,
                    }

                # Add enhanced timezone data if available
                if has_enhanced_timezone and row:
                    try:
                        cursor.execute(
                            """
                            SELECT timezone_iana_name, timezone_display_name, 
                                   timezone_utc_offset_hours, timezone_format_type, 
                                   timezone_validated
                            FROM general_info WHERE id = 1
                        """
                        )
                        tz_row = cursor.fetchone()

                        if tz_row and tz_row[0]:  # Has enhanced timezone data
                            config["timezone_enhanced"] = {
                                "iana_name": tz_row[0],
                                "display_name": tz_row[1],
                                "utc_offset_hours": tz_row[2],
                                "format_type": tz_row[3],
                                "validated": bool(tz_row[4]) if tz_row[4] is not None else False,
                            }
                    except Exception as tz_error:
                        print(f"⚠️ Enhanced timezone query error: {tz_error}")

                log_step_operation(
                    "2", "get_location_time", {"has_enhanced": has_enhanced_timezone}
                )
                return config

        except Exception as e:
            log_step_operation("2", "get_location_time", {"error": str(e)}, False)
            # Return defaults on error
            return {
                "country": self.DEFAULT_COUNTRY,
                "timezone": self.DEFAULT_TIMEZONE,
                "language": self.DEFAULT_LANGUAGE,
                "working_days": self.DEFAULT_WORKING_DAYS,
                "from_time": self.DEFAULT_FROM_TIME,
                "to_time": self.DEFAULT_TO_TIME,
                "error": str(e),
            }

    def validate_location_time_data(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate location/time configuration data.

        Args:
            data: Configuration data to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Check required fields
        required_fields = [
            "country",
            "timezone",
            "language",
            "working_days",
            "from_time",
            "to_time",
        ]
        is_valid, error = validate_required_fields(data, required_fields)
        if not is_valid:
            return False, error

        # Validate working days
        is_valid, error = validate_working_days(data["working_days"])
        if not is_valid:
            return False, error

        # Validate time formats
        is_valid, error = validate_time_format(data["from_time"], "from_time")
        if not is_valid:
            return False, error

        is_valid, error = validate_time_format(data["to_time"], "to_time")
        if not is_valid:
            return False, error

        return True, ""

    def validate_timezone_enhanced(
        self, timezone_input: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate timezone using enhanced timezone validator.

        Args:
            timezone_input: Timezone string to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str, timezone_data: dict)
        """
        try:
            timezone_result = simple_validate_timezone(timezone_input)

            if not timezone_result["valid"]:
                return False, timezone_result["error"], None

            timezone_data = {
                "iana_name": timezone_result["timezone"],
                "display_name": timezone_result["timezone"],
                "utc_offset_hours": 7,  # Asia/Ho_Chi_Minh is always UTC+7
                "format_type": "IANA",
                "validated": True,
                "updated_at": datetime.now().isoformat(),
                "warnings": [],
            }

            return True, "", timezone_data

        except Exception as e:
            return False, f"Timezone validation failed: {str(e)}", None

    def update_location_time_if_changed(
        self, new_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update location/time configuration only if different from current values.
        FIXED: No Vietnamese day conversion - frontend sends English directly.

        Args:
            new_data: New configuration data

        Returns:
            Tuple of (success: bool, result_data: dict)
        """
        try:
            # Sanitize inputs
            sanitized_data = {
                "country": sanitize_input(new_data.get("country", ""), 50),
                "timezone": sanitize_input(new_data.get("timezone", ""), 50),
                "language": sanitize_input(new_data.get("language", ""), 50),
                "working_days": new_data.get("working_days", []),
                "from_time": sanitize_input(new_data.get("from_time", ""), 10),
                "to_time": sanitize_input(new_data.get("to_time", ""), 10),
            }

            # Validate data
            is_valid, validation_error = self.validate_location_time_data(sanitized_data)
            if not is_valid:
                return False, {"error": validation_error}

            # FIXED: No Vietnamese conversion - working_days come as English from frontend
            working_days_en = sanitized_data["working_days"]  # Use directly, no conversion
            print(f"✅ Working days (no conversion needed): {working_days_en}")

            # Validate and process timezone with comprehensive validation
            timezone_valid, tz_error, timezone_data = self.validate_timezone_enhanced(
                sanitized_data["timezone"]
            )
            if not timezone_valid:
                return False, {"error": tz_error}

            # Prepare data for change detection
            check_data = {
                "country": sanitized_data["country"],
                "timezone": sanitized_data["timezone"],
                "language": sanitized_data["language"],
                "working_days": json.dumps(working_days_en, sort_keys=True),
                "from_time": sanitized_data["from_time"],
                "to_time": sanitized_data["to_time"],
            }

            # Check for changes
            changed, current_data = execute_with_change_detection(
                table_name="general_info", record_id=1, new_data=check_data
            )

            if not changed:
                # No changes detected
                log_step_operation("2", "update_location_time", {"changed": False})

                return True, {
                    "country": sanitized_data["country"],
                    "timezone": sanitized_data["timezone"],
                    "language": sanitized_data["language"],
                    "working_days": working_days_en,
                    "from_time": sanitized_data["from_time"],
                    "to_time": sanitized_data["to_time"],
                    "changed": False,
                    "message": "No changes detected",
                }

            # Ensure enhanced timezone columns exist
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()

                # Add enhanced timezone columns if they don't exist
                enhanced_columns = [
                    ("timezone_iana_name", "TEXT"),
                    ("timezone_display_name", "TEXT"),
                    ("timezone_utc_offset_hours", "REAL"),
                    ("timezone_format_type", "TEXT"),
                    ("timezone_validated", "INTEGER"),
                    ("timezone_updated_at", "TEXT"),
                    ("timezone_validation_warnings", "TEXT"),
                ]

                for col_name, col_type in enhanced_columns:
                    ensure_column_exists("general_info", col_name, col_type)

                # Perform update with enhanced timezone data
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO general_info (
                        id, country, timezone, language, working_days, from_time, to_time,
                        timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                        timezone_format_type, timezone_validated, timezone_updated_at,
                        timezone_validation_warnings, brand_name
                    ) VALUES (
                        1, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        COALESCE((SELECT brand_name FROM general_info WHERE id = 1), 'Alan_go')
                    )
                """,
                    (
                        sanitized_data["country"],
                        sanitized_data["timezone"],
                        sanitized_data["language"],
                        json.dumps(working_days_en),
                        sanitized_data["from_time"],
                        sanitized_data["to_time"],
                        timezone_data["iana_name"],
                        timezone_data["display_name"],
                        timezone_data["utc_offset_hours"],
                        timezone_data["format_type"],
                        1,
                        timezone_data["updated_at"],
                        json.dumps(timezone_data["warnings"]),
                    ),
                )

                conn.commit()

                log_step_operation(
                    "2",
                    "update_location_time",
                    {
                        "country": sanitized_data["country"],
                        "timezone": sanitized_data["timezone"],
                        "working_days_count": len(working_days_en),
                        "changed": True,
                        "enhanced_timezone": True,
                    },
                )

                result = {
                    "country": sanitized_data["country"],
                    "timezone": sanitized_data["timezone"],
                    "language": sanitized_data["language"],
                    "working_days": working_days_en,
                    "from_time": sanitized_data["from_time"],
                    "to_time": sanitized_data["to_time"],
                    "changed": True,
                    "message": "Location/time configuration updated successfully",
                    "timezone_enhanced": timezone_data,
                }

                return True, result

        except Exception as e:
            log_step_operation("2", "update_location_time", {"error": str(e)}, False)
            return False, {"error": f"Failed to update location/time configuration: {str(e)}"}


# Create singleton instance for import
step2_location_time_service = Step2LocationTimeService()
