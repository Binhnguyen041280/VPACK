#!/usr/bin/env python3
"""
Backend Country-Timezone Mapping Utility for ePACK

Provides server-side country-timezone mapping functionality to complement
the frontend implementation. This ensures consistency between frontend
and backend country/timezone handling.

Features:
- Country code to timezone mapping
- Timezone validation for countries
- API endpoints for country-timezone data
- Integration with existing timezone management system
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json

try:
    # Try to import pycountry if available
    import pycountry
    PYCOUNTRY_AVAILABLE = True
except ImportError:
    PYCOUNTRY_AVAILABLE = False
    print("Warning: pycountry not available. Using built-in country database.")

from modules.config.logging_config import get_logger
from modules.utils.timezone_manager import timezone_manager

logger = get_logger(__name__, {"module": "country_timezone_backend"})

class CountryTimezoneBackend:
    """Backend country-timezone mapping functionality."""
    
    def __init__(self):
        self.builtin_database = self._init_builtin_database()
        
    def _init_builtin_database(self) -> Dict[str, Dict]:
        """Initialize built-in country-timezone database."""
        return {
            # Asia-Pacific
            'AF': {'name': 'Afghanistan', 'timezone': 'Asia/Kabul'},
            'AU': {'name': 'Australia', 'timezone': 'Australia/Sydney'},
            'BD': {'name': 'Bangladesh', 'timezone': 'Asia/Dhaka'},
            'BN': {'name': 'Brunei', 'timezone': 'Asia/Brunei'},
            'KH': {'name': 'Cambodia', 'timezone': 'Asia/Phnom_Penh'},
            'CN': {'name': 'China', 'timezone': 'Asia/Shanghai'},
            'HK': {'name': 'Hong Kong', 'timezone': 'Asia/Hong_Kong'},
            'IN': {'name': 'India', 'timezone': 'Asia/Kolkata'},
            'ID': {'name': 'Indonesia', 'timezone': 'Asia/Jakarta'},
            'JP': {'name': 'Japan', 'timezone': 'Asia/Tokyo'},
            'KZ': {'name': 'Kazakhstan', 'timezone': 'Asia/Almaty'},
            'LA': {'name': 'Laos', 'timezone': 'Asia/Vientiane'},
            'MY': {'name': 'Malaysia', 'timezone': 'Asia/Kuala_Lumpur'},
            'MN': {'name': 'Mongolia', 'timezone': 'Asia/Ulaanbaatar'},
            'MM': {'name': 'Myanmar', 'timezone': 'Asia/Yangon'},
            'NP': {'name': 'Nepal', 'timezone': 'Asia/Kathmandu'},
            'NZ': {'name': 'New Zealand', 'timezone': 'Pacific/Auckland'},
            'KP': {'name': 'North Korea', 'timezone': 'Asia/Pyongyang'},
            'PK': {'name': 'Pakistan', 'timezone': 'Asia/Karachi'},
            'PH': {'name': 'Philippines', 'timezone': 'Asia/Manila'},
            'SG': {'name': 'Singapore', 'timezone': 'Asia/Singapore'},
            'KR': {'name': 'South Korea', 'timezone': 'Asia/Seoul'},
            'LK': {'name': 'Sri Lanka', 'timezone': 'Asia/Colombo'},
            'TW': {'name': 'Taiwan', 'timezone': 'Asia/Taipei'},
            'TH': {'name': 'Thailand', 'timezone': 'Asia/Bangkok'},
            'VN': {'name': 'Vietnam', 'timezone': 'Asia/Ho_Chi_Minh'},

            # Europe
            'AT': {'name': 'Austria', 'timezone': 'Europe/Vienna'},
            'BE': {'name': 'Belgium', 'timezone': 'Europe/Brussels'},
            'BG': {'name': 'Bulgaria', 'timezone': 'Europe/Sofia'},
            'HR': {'name': 'Croatia', 'timezone': 'Europe/Zagreb'},
            'CZ': {'name': 'Czech Republic', 'timezone': 'Europe/Prague'},
            'DK': {'name': 'Denmark', 'timezone': 'Europe/Copenhagen'},
            'EE': {'name': 'Estonia', 'timezone': 'Europe/Tallinn'},
            'FI': {'name': 'Finland', 'timezone': 'Europe/Helsinki'},
            'FR': {'name': 'France', 'timezone': 'Europe/Paris'},
            'DE': {'name': 'Germany', 'timezone': 'Europe/Berlin'},
            'GR': {'name': 'Greece', 'timezone': 'Europe/Athens'},
            'HU': {'name': 'Hungary', 'timezone': 'Europe/Budapest'},
            'IS': {'name': 'Iceland', 'timezone': 'Atlantic/Reykjavik'},
            'IE': {'name': 'Ireland', 'timezone': 'Europe/Dublin'},
            'IT': {'name': 'Italy', 'timezone': 'Europe/Rome'},
            'LV': {'name': 'Latvia', 'timezone': 'Europe/Riga'},
            'LT': {'name': 'Lithuania', 'timezone': 'Europe/Vilnius'},
            'LU': {'name': 'Luxembourg', 'timezone': 'Europe/Luxembourg'},
            'NL': {'name': 'Netherlands', 'timezone': 'Europe/Amsterdam'},
            'NO': {'name': 'Norway', 'timezone': 'Europe/Oslo'},
            'PL': {'name': 'Poland', 'timezone': 'Europe/Warsaw'},
            'PT': {'name': 'Portugal', 'timezone': 'Europe/Lisbon'},
            'RO': {'name': 'Romania', 'timezone': 'Europe/Bucharest'},
            'RU': {'name': 'Russia', 'timezone': 'Europe/Moscow'},
            'SK': {'name': 'Slovakia', 'timezone': 'Europe/Bratislava'},
            'SI': {'name': 'Slovenia', 'timezone': 'Europe/Ljubljana'},
            'ES': {'name': 'Spain', 'timezone': 'Europe/Madrid'},
            'SE': {'name': 'Sweden', 'timezone': 'Europe/Stockholm'},
            'CH': {'name': 'Switzerland', 'timezone': 'Europe/Zurich'},
            'TR': {'name': 'Turkey', 'timezone': 'Europe/Istanbul'},
            'UA': {'name': 'Ukraine', 'timezone': 'Europe/Kiev'},
            'GB': {'name': 'United Kingdom', 'timezone': 'Europe/London'},

            # Americas
            'AR': {'name': 'Argentina', 'timezone': 'America/Argentina/Buenos_Aires'},
            'BR': {'name': 'Brazil', 'timezone': 'America/Sao_Paulo'},
            'CA': {'name': 'Canada', 'timezone': 'America/Toronto'},
            'CL': {'name': 'Chile', 'timezone': 'America/Santiago'},
            'CO': {'name': 'Colombia', 'timezone': 'America/Bogota'},
            'MX': {'name': 'Mexico', 'timezone': 'America/Mexico_City'},
            'PE': {'name': 'Peru', 'timezone': 'America/Lima'},
            'US': {'name': 'United States', 'timezone': 'America/New_York'},
            'VE': {'name': 'Venezuela', 'timezone': 'America/Caracas'},

            # Africa
            'DZ': {'name': 'Algeria', 'timezone': 'Africa/Algiers'},
            'EG': {'name': 'Egypt', 'timezone': 'Africa/Cairo'},
            'ET': {'name': 'Ethiopia', 'timezone': 'Africa/Addis_Ababa'},
            'GH': {'name': 'Ghana', 'timezone': 'Africa/Accra'},
            'KE': {'name': 'Kenya', 'timezone': 'Africa/Nairobi'},
            'MA': {'name': 'Morocco', 'timezone': 'Africa/Casablanca'},
            'NG': {'name': 'Nigeria', 'timezone': 'Africa/Lagos'},
            'ZA': {'name': 'South Africa', 'timezone': 'Africa/Johannesburg'},
            'TN': {'name': 'Tunisia', 'timezone': 'Africa/Tunis'},

            # Middle East
            'IR': {'name': 'Iran', 'timezone': 'Asia/Tehran'},
            'IQ': {'name': 'Iraq', 'timezone': 'Asia/Baghdad'},
            'IL': {'name': 'Israel', 'timezone': 'Asia/Jerusalem'},
            'JO': {'name': 'Jordan', 'timezone': 'Asia/Amman'},
            'KW': {'name': 'Kuwait', 'timezone': 'Asia/Kuwait'},
            'LB': {'name': 'Lebanon', 'timezone': 'Asia/Beirut'},
            'QA': {'name': 'Qatar', 'timezone': 'Asia/Qatar'},
            'SA': {'name': 'Saudi Arabia', 'timezone': 'Asia/Riyadh'},
            'SY': {'name': 'Syria', 'timezone': 'Asia/Damascus'},
            'AE': {'name': 'United Arab Emirates', 'timezone': 'Asia/Dubai'}
        }
    
    def get_all_countries(self) -> List[Dict[str, str]]:
        """
        Get all available countries with their codes and timezones.
        
        Returns:
            List of country dictionaries with code, name, and timezone
        """
        countries = []
        
        if PYCOUNTRY_AVAILABLE:
            # Use pycountry if available for comprehensive country list
            for country in pycountry.countries:
                country_data = {
                    'code': country.alpha_2,
                    'name': country.name,
                    'timezone': self._get_timezone_for_country_code(country.alpha_2)
                }
                countries.append(country_data)
        else:
            # Use built-in database
            for code, data in self.builtin_database.items():
                countries.append({
                    'code': code,
                    'name': data['name'],
                    'timezone': data['timezone']
                })
        
        # Sort by name
        countries.sort(key=lambda x: x['name'])
        return countries
    
    def get_country_by_name(self, country_name: str) -> Optional[Dict[str, str]]:
        """
        Get country information by name.
        
        Args:
            country_name: English country name
            
        Returns:
            Country dictionary or None if not found
        """
        countries = self.get_all_countries()
        
        # Try exact match first
        for country in countries:
            if country['name'].lower() == country_name.lower():
                return country
        
        # Try partial match
        for country in countries:
            if country_name.lower() in country['name'].lower():
                return country
        
        return None
    
    def get_country_by_code(self, country_code: str) -> Optional[Dict[str, str]]:
        """
        Get country information by ISO country code.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code
            
        Returns:
            Country dictionary or None if not found
        """
        if PYCOUNTRY_AVAILABLE:
            try:
                country = pycountry.countries.get(alpha_2=country_code.upper())
                if country:
                    return {
                        'code': country.alpha_2,
                        'name': country.name,
                        'timezone': self._get_timezone_for_country_code(country.alpha_2)
                    }
            except Exception as e:
                logger.debug(f"Error getting country by code {country_code}: {e}")
        
        # Fallback to built-in database
        country_code = country_code.upper()
        if country_code in self.builtin_database:
            data = self.builtin_database[country_code]
            return {
                'code': country_code,
                'name': data['name'],
                'timezone': data['timezone']
            }
        
        return None
    
    def _get_timezone_for_country_code(self, country_code: str) -> str:
        """
        Get primary timezone for a country code.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code
            
        Returns:
            IANA timezone identifier
        """
        country_code = country_code.upper()
        
        # Check built-in database first
        if country_code in self.builtin_database:
            return self.builtin_database[country_code]['timezone']
        
        # Default fallback
        return 'UTC'
    
    def get_timezone_for_country(self, country_name: str) -> Optional[str]:
        """
        Get primary timezone for a country name.
        
        Args:
            country_name: English country name
            
        Returns:
            IANA timezone identifier or None if not found
        """
        country = self.get_country_by_name(country_name)
        return country['timezone'] if country else None
    
    def validate_country_timezone(self, country_name: str, timezone: str) -> bool:
        """
        Validate if a timezone is appropriate for a country.
        
        Args:
            country_name: English country name
            timezone: IANA timezone identifier
            
        Returns:
            True if timezone is valid for the country
        """
        expected_timezone = self.get_timezone_for_country(country_name)
        
        if not expected_timezone:
            return False
        
        # Check exact match
        if timezone == expected_timezone:
            return True
        
        # For countries with multiple timezones, check if it's a valid alternative
        multi_timezone_countries = {
            'United States': ['America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/Anchorage', 'Pacific/Honolulu'],
            'Canada': ['America/Toronto', 'America/Vancouver', 'America/Montreal', 'America/Calgary', 'America/Edmonton'],
            'Australia': ['Australia/Sydney', 'Australia/Melbourne', 'Australia/Perth', 'Australia/Brisbane', 'Australia/Adelaide', 'Australia/Darwin'],
            'Brazil': ['America/Sao_Paulo', 'America/Manaus', 'America/Fortaleza'],
            'Russia': ['Europe/Moscow', 'Asia/Yekaterinburg', 'Asia/Novosibirsk', 'Asia/Vladivostok'],
            'Indonesia': ['Asia/Jakarta', 'Asia/Jayapura', 'Asia/Makassar'],
            'Mexico': ['America/Mexico_City', 'America/Tijuana', 'America/Cancun']
        }
        
        if country_name in multi_timezone_countries:
            return timezone in multi_timezone_countries[country_name]
        
        return False
    
    def get_countries_by_timezone(self, timezone: str) -> List[str]:
        """
        Get all countries that use a specific timezone.
        
        Args:
            timezone: IANA timezone identifier
            
        Returns:
            List of country names
        """
        countries = []
        
        for country_data in self.get_all_countries():
            if country_data['timezone'] == timezone:
                countries.append(country_data['name'])
        
        return countries
    
    def convert_vietnamese_to_english(self, vietnamese_name: str) -> str:
        """
        Convert Vietnamese country name to English for backward compatibility.
        
        Args:
            vietnamese_name: Vietnamese country name
            
        Returns:
            English country name or original if no mapping found
        """
        vietnamese_to_english_map = {
            'Việt Nam': 'Vietnam',
            'Nhật Bản': 'Japan',
            'Hàn Quốc': 'South Korea',
            'Thái Lan': 'Thailand',
            'Singapore': 'Singapore',
            'Mỹ': 'United States',
            'Anh': 'United Kingdom',
            'Pháp': 'France',
            'Đức': 'Germany',
            'Úc': 'Australia'
        }
        
        return vietnamese_to_english_map.get(vietnamese_name, vietnamese_name)
    
    def get_timezone_offset_string(self, timezone: str) -> str:
        """
        Get UTC offset string for a timezone.
        
        Args:
            timezone: IANA timezone identifier
            
        Returns:
            UTC offset string (e.g., "UTC+7")
        """
        try:
            # Use timezone manager to get offset
            tz_obj = timezone_manager.get_timezone_object(timezone)
            if tz_obj:
                # Get current offset (considering DST)
                now = datetime.now(tz_obj)
                offset_seconds = now.utcoffset().total_seconds()
                offset_hours = offset_seconds / 3600
                
                if offset_hours >= 0:
                    return f"UTC+{int(offset_hours)}"
                else:
                    return f"UTC{int(offset_hours)}"
        except Exception as e:
            logger.debug(f"Error getting timezone offset for {timezone}: {e}")
        
        # Fallback to common mappings
        common_offsets = {
            'Asia/Ho_Chi_Minh': 'UTC+7',
            'Asia/Tokyo': 'UTC+9',
            'Asia/Seoul': 'UTC+9',
            'Asia/Bangkok': 'UTC+7',
            'Asia/Singapore': 'UTC+8',
            'America/New_York': 'UTC-5',
            'America/Los_Angeles': 'UTC-8',
            'Europe/London': 'UTC+0',
            'Europe/Paris': 'UTC+1',
            'Europe/Berlin': 'UTC+1',
            'Australia/Sydney': 'UTC+11'
        }
        
        return common_offsets.get(timezone, 'UTC+0')
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the country-timezone database.
        
        Returns:
            Dictionary with database statistics
        """
        countries = self.get_all_countries()
        timezones = set(country['timezone'] for country in countries)
        
        # Count by region
        regions = {
            'Asia': 0,
            'Europe': 0,
            'America': 0,
            'Africa': 0,
            'Pacific': 0,
            'Atlantic': 0
        }
        
        for country in countries:
            timezone = country['timezone']
            if timezone.startswith('Asia/'):
                regions['Asia'] += 1
            elif timezone.startswith('Europe/'):
                regions['Europe'] += 1
            elif timezone.startswith('America/'):
                regions['America'] += 1
            elif timezone.startswith('Africa/'):
                regions['Africa'] += 1
            elif timezone.startswith('Pacific/'):
                regions['Pacific'] += 1
            elif timezone.startswith('Atlantic/'):
                regions['Atlantic'] += 1
        
        return {
            'total_countries': len(countries),
            'total_timezones': len(timezones),
            'pycountry_available': PYCOUNTRY_AVAILABLE,
            'regions': regions,
            'builtin_database_size': len(self.builtin_database)
        }

# Create singleton instance
country_timezone_backend = CountryTimezoneBackend()

# Convenience functions
def get_all_countries():
    """Get all available countries."""
    return country_timezone_backend.get_all_countries()

def get_timezone_for_country(country_name: str):
    """Get timezone for a country name."""
    return country_timezone_backend.get_timezone_for_country(country_name)

def validate_country_timezone(country_name: str, timezone: str):
    """Validate country-timezone combination."""
    return country_timezone_backend.validate_country_timezone(country_name, timezone)