"""
Unified phone number handling using phonenumbers library.
Replaces scattered phone number logic throughout the codebase.
"""

import re
import logging
from typing import List, Optional, Dict, Any
import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat

logger = logging.getLogger(__name__)


class PhoneNumberProcessor:
    """Centralized phone number processing using phonenumbers library."""
    
    def __init__(self, default_region: str = "US"):
        self.default_region = default_region
        
        # Reserved toll-free prefixes not yet in phonenumbers database
        self.reserved_toll_free_prefixes = {
            "822", "880", "881", "882", "883", "884", "885", "886", "887", "889"
        }
    
    def is_valid_phone_number(self, phone_number: str, filter_non_phone: bool = False) -> bool:
        """
        Unified phone number validation with enhanced filtering.
        
        Args:
            phone_number: Phone number string to validate
            filter_non_phone: If True, filter out short codes, toll-free, and non-US numbers
            
        Returns:
            bool: True if phone number is valid according to criteria
        """
        if not phone_number:
            return False

        # Convert to string if it's not already
        if not isinstance(phone_number, str):
            phone_number = str(phone_number)

        # Clean the phone number
        cleaned = phone_number.strip()
        if not cleaned:
            return False

        # Handle special cases first
        if self._is_special_case(cleaned):
            return True

        # Skip if it's clearly not a phone number (contains letters)
        if re.search(r"[a-zA-Z]", cleaned):
            return False

        # Enhanced filtering for non-phone numbers when enabled
        if filter_non_phone:
            if not self._passes_enhanced_filtering(cleaned):
                return False

        # Use phonenumbers library for validation first
        try:
            parsed = phonenumbers.parse(cleaned, self.default_region)
            if phonenumbers.is_valid_number(parsed):
                return True
        except Exception as e:
            logger.debug(f"Failed to parse phone number '{cleaned}': {e}")
        
        # Fall back to basic validation for edge cases
        return self._basic_validation_fallback(cleaned)
    
    def _basic_validation_fallback(self, phone_number: str) -> bool:
        """Basic validation fallback when phonenumbers parsing fails or returns invalid."""
        # Remove all non-digits
        digits_only = re.sub(r"[^0-9]", "", phone_number)
        
        # Must be at least 10 digits for US numbers
        if len(digits_only) < 10:
            return False
        
        # Must be at most 15 digits (international limit)
        if len(digits_only) > 15:
            return False
        
        # Check for reasonable US patterns
        if len(digits_only) == 10:
            # 10-digit US number without country code
            # Check if area code is reasonable (not 000, 111, etc.)
            area_code = digits_only[:3]
            if area_code in ["000", "111", "222", "333", "444", "555", "666", "777", "888", "999"]:
                return False  # These are typically invalid
            return True
        
        elif len(digits_only) == 11 and digits_only.startswith("1"):
            # 11-digit US number with country code
            area_code = digits_only[1:4]
            if area_code in ["000", "111", "222", "333", "444", "555", "666", "777", "888", "999"]:
                return False
            return True
        
        elif len(digits_only) > 11 and digits_only.startswith("1"):
            # Longer US number with country code
            return True
        
        return False
    
    def _is_special_case(self, phone_number: str) -> bool:
        """Check if phone number is a special case that should always be valid."""
        # Skip if it's a fallback conversation ID (old format)
        if phone_number.startswith("unknown_"):
            return True

        # Handle hash-based fallback numbers (UN_ prefix) for conversation management
        if phone_number.startswith("UN_"):
            return True

        # Handle names (allow them as valid "phone numbers" for conversation purposes)
        if re.match(r"^[A-Za-z\s\-\.]+$", phone_number) and len(phone_number.strip()) > 2:
            # Names should have spaces to be considered valid
            if " " in phone_number:
                return True

        return False
    
    def _passes_enhanced_filtering(self, phone_number: str) -> bool:
        """Apply enhanced filtering for non-phone numbers."""
        try:
            parsed = phonenumbers.parse(phone_number, self.default_region)
            
            # Filter out short codes (4-6 digits)
            if phonenumbers.is_possible_short_number(parsed):
                return False
            
            # Filter out toll-free numbers
            if self.is_toll_free_number(phone_number):
                return False
            
            # Filter out non-US numbers
            if not phonenumbers.is_valid_number_for_region(parsed, "US"):
                return False
            
            return True
            
        except Exception:
            # If parsing fails, fall back to basic checks
            return self._basic_filtering_fallback(phone_number)
    
    def _basic_filtering_fallback(self, phone_number: str) -> bool:
        """Basic filtering fallback when phonenumbers parsing fails."""
        # Filter out short codes (4-6 digits)
        if re.match(r"^[0-9]+$", phone_number) and 4 <= len(phone_number) <= 6:
            return False
        
        # Filter out toll-free numbers using regex fallback
        toll_free_patterns = [
            r"^\+?1?8[0-9]{2}",  # 800-809
            r"^\+?1?8[7-9][0-9]",  # 870-899
        ]
        
        for pattern in toll_free_patterns:
            if re.match(pattern, phone_number):
                return False
        
        # Filter out non-US numbers (don't start with +1 or 1)
        if not re.match(r"^\+?1", phone_number):
            return False
        
        return True
    
    def is_toll_free_number(self, phone_number: str) -> bool:
        """
        Enhanced toll-free detection using phonenumbers library + reserved prefixes.
        
        Args:
            phone_number: Phone number string to check
            
        Returns:
            bool: True if number is toll-free
        """
        try:
            parsed = phonenumbers.parse(phone_number, self.default_region)
            
            # Use library's built-in toll-free detection
            if phonenumbers.number_type(parsed) == PhoneNumberType.TOLL_FREE:
                return True
                
        except Exception:
            pass
        
        # Check reserved prefixes not yet in library database
        return self._is_reserved_toll_free(phone_number)
    
    def _is_reserved_toll_free(self, phone_number: str) -> bool:
        """Check reserved toll-free prefixes (822, 880-887, 889)."""
        # Remove all non-digits
        digits_only = re.sub(r"[^0-9]", "", phone_number)
        
        # Remove country code if present
        if digits_only.startswith("1") and len(digits_only) > 10:
            digits_only = digits_only[1:]
        
        # Check if it starts with any reserved prefix
        return any(digits_only.startswith(prefix) for prefix in self.reserved_toll_free_prefixes)
    
    def extract_phone_numbers_from_text(self, text: str) -> List[str]:
        """
        Extract phone numbers using phonenumbers PhoneNumberMatcher + regex fallback.
        
        Args:
            text: Text content to search for phone numbers
            
        Returns:
            List[str]: List of found phone numbers
        """
        phone_numbers = []
        
        # Use library's built-in number matcher for accuracy
        try:
            matcher = phonenumbers.PhoneNumberMatcher(text, self.default_region)
            for match in matcher:
                phone_numbers.append(match.raw_string)
                
        except Exception as e:
            logger.warning(f"Failed to extract phone numbers using PhoneNumberMatcher: {e}")
        
        # Also check for tel: links (common in HTML)
        try:
            tel_pattern = re.compile(r'tel:([+\d\s\-\(\)]+)')
            tel_matches = tel_pattern.findall(text)
            for match in tel_matches:
                if match not in phone_numbers:
                    phone_numbers.append(match)
                    
        except Exception as e:
            logger.warning(f"Failed to extract tel: links: {e}")
        
        # Fallback regex extraction for formats that PhoneNumberMatcher might miss
        try:
            # Pattern for international numbers
            intl_pattern = re.compile(r'\+\d{1,3}\s?\d{1,14}')
            intl_matches = intl_pattern.findall(text)
            for match in intl_matches:
                if match not in phone_numbers:
                    phone_numbers.append(match)
            
            # Pattern for US domestic numbers
            us_pattern = re.compile(r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})')
            us_matches = us_pattern.findall(text)
            for match in us_matches:
                if len(match) == 3:
                    us_number = f"+1{match[0]}{match[1]}{match[2]}"
                    if us_number not in phone_numbers:
                        phone_numbers.append(us_number)
                        
        except Exception as e:
            logger.warning(f"Failed to extract phone numbers using regex fallback: {e}")
        
        return phone_numbers
    
    def normalize_phone_number(self, phone_number: str) -> str:
        """
        Normalize phone number to E.164 format.
        
        Args:
            phone_number: Phone number string to normalize
            
        Returns:
            str: E.164 formatted phone number or original if normalization fails
        """
        try:
            parsed = phonenumbers.parse(phone_number, self.default_region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, PhoneNumberFormat.E164
                )
        except Exception as e:
            logger.debug(f"Failed to normalize phone number '{phone_number}': {e}")
        
        # Fallback normalization for common US formats
        try:
            # Remove all non-digits
            digits_only = re.sub(r"[^0-9]", "", phone_number)
            
            # Handle 10-digit US numbers
            if len(digits_only) == 10:
                return f"+1{digits_only}"
            
            # Handle 11-digit US numbers starting with 1
            elif len(digits_only) == 11 and digits_only.startswith("1"):
                return f"+{digits_only}"
            
            # Handle longer numbers starting with 1
            elif len(digits_only) > 11 and digits_only.startswith("1"):
                return f"+{digits_only}"
                
        except Exception as e:
            logger.debug(f"Failed to normalize phone number '{phone_number}' with fallback: {e}")
        
        return phone_number
    
    def get_number_type_info(self, phone_number: str) -> Dict[str, Any]:
        """
        Get comprehensive information about phone number type.
        
        Args:
            phone_number: Phone number string to analyze
            
        Returns:
            Dict[str, Any]: Information about the phone number
        """
        try:
            parsed = phonenumbers.parse(phone_number, self.default_region)
            
            info = {
                "is_valid": phonenumbers.is_valid_number(parsed),
                "is_possible": phonenumbers.is_possible_number(parsed),
                "number_type": phonenumbers.number_type(parsed),
                "number_type_name": str(phonenumbers.number_type(parsed)),
                "is_toll_free": self.is_toll_free_number(phone_number),
                "is_short_number": phonenumbers.is_possible_short_number(parsed),
                "is_mobile": phonenumbers.number_type(parsed) == PhoneNumberType.MOBILE,
                "is_fixed_line": phonenumbers.number_type(parsed) == PhoneNumberType.FIXED_LINE,
                "country_code": parsed.country_code,
                "national_number": str(parsed.national_number),
                "e164_format": phonenumbers.format_number(parsed, PhoneNumberFormat.E164),
                "national_format": phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL),
                "international_format": phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL),
            }
            
            return info
            
        except Exception as e:
            logger.debug(f"Failed to get number type info for '{phone_number}': {e}")
            return {
                "is_valid": False,
                "error": str(e)
            }


# Global instance for backward compatibility
_global_processor = PhoneNumberProcessor()


def is_valid_phone_number(phone_number: str, filter_non_phone: bool = False) -> bool:
    """
    Backward compatibility function for existing code.
    
    Args:
        phone_number: Phone number string to validate
        filter_non_phone: If True, filter out short codes, toll-free, and non-US numbers
        
    Returns:
        bool: True if phone number is valid according to criteria
    """
    return _global_processor.is_valid_phone_number(phone_number, filter_non_phone)


def normalize_phone_number(phone_number: str) -> str:
    """
    Backward compatibility function for existing code.
    
    Args:
        phone_number: Phone number string to normalize
        
    Returns:
        str: E.164 formatted phone number or original if normalization fails
    """
    return _global_processor.normalize_phone_number(phone_number)


def is_toll_free_number(phone_number: str) -> bool:
    """
    Backward compatibility function for existing code.
    
    Args:
        phone_number: Phone number string to check
        
    Returns:
        bool: True if number is toll-free
    """
    return _global_processor.is_toll_free_number(phone_number)


def extract_phone_numbers_from_text(text: str) -> List[str]:
    """
    Backward compatibility function for existing code.
    
    Args:
        text: Text content to search for phone numbers
        
    Returns:
        List[str]: List of found phone numbers
    """
    return _global_processor.extract_phone_numbers_from_text(text)

