"""
Filtering Service Module for SMS/MMS processing system.

This module implements the FilteringService class that provides centralized,
dependency-injection based filtering logic to replace global variable dependencies.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FilteringService:
    """
    Centralized filtering service that provides date and phone filtering logic.
    
    This class eliminates global variable dependencies by accepting configuration
    explicitly through the ProcessingConfig object.
    
    Attributes:
        config: ProcessingConfig object containing all filtering settings
    """
    
    config: 'ProcessingConfig'  # Forward reference to avoid circular imports
    
    def should_skip_by_date(self, message_timestamp: int) -> bool:
        """
        Determine if a message should be skipped based on date filtering settings.
        
        Args:
            message_timestamp: Unix timestamp in milliseconds
            
        Returns:
            bool: True if message should be skipped due to date filtering, False otherwise
        """
        # Check if any date filtering is enabled (new or old field names)
        if self.config is None:
            return False
        
        has_new_filters = (self.config.exclude_older_than is not None or self.config.exclude_newer_than is not None)
        has_old_filters = (self.config.older_than is not None or self.config.newer_than is not None)
        
        if not has_new_filters and not has_old_filters:
            return False  # No date filtering enabled
        
        # Convert timestamp to datetime for comparison
        try:
            message_date = datetime.fromtimestamp(message_timestamp / 1000.0)
            
            # Check new field names (preferred)
            if self.config.exclude_older_than and message_date < self.config.exclude_older_than:
                logger.debug(f"Message skipped due to exclude_older_than filter: {message_date} < {self.config.exclude_older_than}")
                return True
            
            if self.config.exclude_newer_than and message_date > self.config.exclude_newer_than:
                logger.debug(f"Message skipped due to exclude_newer_than filter: {message_date} > {self.config.exclude_newer_than}")
                return True
            
            # Check old field names for backward compatibility
            if self.config.older_than and message_date < self.config.older_than:
                logger.debug(f"Message skipped due to older_than filter: {message_date} < {self.config.older_than}")
                return True
            
            if self.config.newer_than and message_date > self.config.newer_than:
                logger.debug(f"Message skipped due to newer_than filter: {message_date} > {self.config.newer_than}")
                return True
                
        except (ValueError, OSError) as e:
            logger.warning(f"Invalid timestamp {message_timestamp}: {e}")
            return False  # Don't skip messages with invalid timestamps
        
        return False
    
    def should_skip_by_phone(self, phone_number: str, phone_lookup_manager) -> bool:
        """
        Determine if a message should be skipped based on phone filtering settings.
        
        Args:
            phone_number: Phone number to check
            phone_lookup_manager: PhoneLookupManager instance for alias checking
            
        Returns:
            bool: True if message should be skipped due to phone filtering, False otherwise
        """
        # Handle None or empty phone numbers
        if not phone_number:
            return False
        
        # Check if config is None (backward compatibility)
        if self.config is None:
            return False
        
        # Check if phone lookup manager is available
        if phone_lookup_manager is None:
            # Can't perform phone filtering without lookup manager
            return False
        
        # Filter numbers without aliases if enabled
        if self.config.filter_numbers_without_aliases:
            try:
                has_alias = phone_lookup_manager.has_alias(str(phone_number))
                if not has_alias:
                    logger.debug(f"Message skipped due to no alias for number: {phone_number}")
                    return True
            except Exception as e:
                logger.warning(f"Error checking alias for {phone_number}: {e}")
                # Don't skip on error - assume it's valid
        
        # Filter non-phone numbers if enabled
        if self.config.filter_non_phone_numbers:
            if self._is_non_phone_number(phone_number):
                logger.debug(f"Message skipped due to non-phone number: {phone_number}")
                return True
        
        # Filter service codes if not included
        if not self.config.include_service_codes:
            if self._is_service_code(phone_number):
                logger.debug(f"Message skipped due to service code: {phone_number}")
                return True
        
        return False
    
    def should_skip_message(self, message_timestamp: int, phone_number: str, phone_lookup_manager) -> bool:
        """
        Determine if a message should be skipped based on all filtering criteria.
        
        This method combines date and phone filtering logic.
        
        Args:
            message_timestamp: Unix timestamp in milliseconds
            phone_number: Phone number to check
            phone_lookup_manager: PhoneLookupManager instance for alias checking
            
        Returns:
            bool: True if message should be skipped due to any filtering criteria, False otherwise
        """
        # Check date filtering first (faster)
        if self.should_skip_by_date(message_timestamp):
            return True
        
        # Check phone filtering
        if self.should_skip_by_phone(phone_number, phone_lookup_manager):
            return True
        
        return False
    
    def _is_non_phone_number(self, phone_number: str) -> bool:
        """
        Check if a number is a non-phone number (like short codes).
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            bool: True if the number is a non-phone number, False otherwise
        """
        # Remove common formatting
        clean_number = phone_number.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
        
        # Check for short codes (typically 5-6 digits)
        if len(clean_number) <= 6 and clean_number.isdigit():
            return True
        
        # Check for service codes (contains letters or special patterns)
        if any(char.isalpha() for char in clean_number):
            return True
        
        # Check for common non-phone patterns
        non_phone_patterns = ["SHORT", "CODE", "SERVICE", "INFO"]
        if any(pattern in phone_number.upper() for pattern in non_phone_patterns):
            return True
        
        return False
    
    def _is_service_code(self, phone_number: str) -> bool:
        """
        Check if a number is a service code.
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            bool: True if the number is a service code, False otherwise
        """
        # Service codes typically contain letters or are very short
        if len(phone_number) <= 6:
            return True
        
        # Check for service code patterns
        service_patterns = ["SERVICE", "CODE", "INFO", "HELP"]
        if any(pattern in phone_number.upper() for pattern in service_patterns):
            return True
        
        return False
    
    def get_filtering_summary(self) -> dict:
        """
        Get a summary of current filtering settings.
        
        Returns:
            dict: Summary of filtering configuration
        """
        return {
            "date_filtering": {
                "older_than": self.config.older_than.isoformat() if self.config.older_than else None,
                "newer_than": self.config.newer_than.isoformat() if self.config.newer_than else None,
                "enabled": self.config.older_than is not None or self.config.newer_than is not None
            },
            "phone_filtering": {
                "filter_numbers_without_aliases": self.config.filter_numbers_without_aliases,
                "filter_non_phone_numbers": self.config.filter_non_phone_numbers,
                "include_service_codes": self.config.include_service_codes,
                "skip_filtered_contacts": self.config.skip_filtered_contacts,
                "enabled": (self.config.filter_numbers_without_aliases or 
                           self.config.filter_non_phone_numbers or 
                           not self.config.include_service_codes)
            },
            "group_filtering": {
                "filter_groups_with_all_filtered": self.config.filter_groups_with_all_filtered
            }
        }
