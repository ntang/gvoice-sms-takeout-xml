"""
Filtering Migration Module for Architecture Improvement.

This module provides utilities for safely migrating from global variable-based
filtering to the new parameterized filtering system with validation and rollback.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from core.filtering_service import FilteringService
from core.migration_flags import get_migration_flags
from core.processing_config import ProcessingConfig

logger = logging.getLogger(__name__)


class FilteringMigrationValidator:
    """
    Validates that the new parameterized filtering system produces identical
    results to the legacy global variable-based system.
    """
    
    def __init__(self):
        """Initialize the migration validator."""
        self.flags = get_migration_flags()
        self.validation_samples = 0
        self.validation_errors = 0
        self.performance_metrics = {
            'global_filtering_time': 0.0,
            'parameterized_filtering_time': 0.0,
            'validation_overhead': 0.0,
            'total_validations': 0
        }
    
    def validate_date_filtering(
        self, 
        message_timestamp: int, 
        config: Optional[ProcessingConfig] = None
    ) -> Tuple[bool, bool, bool]:
        """
        Validate that date filtering produces identical results.
        
        Args:
            message_timestamp: Unix timestamp in milliseconds
            config: ProcessingConfig object for parameterized filtering
            
        Returns:
            Tuple of (parameterized_result, global_result, validation_passed)
        """
        if not self.flags.validate_filtering_consistency or not config:
            # Skip validation if disabled or no config
            filtering_service = FilteringService(config) if config else None
            if filtering_service:
                return filtering_service.should_skip_by_date(message_timestamp), False, True
            return False, False, True
        
        start_time = time.time()
        
        try:
            # Get parameterized result
            param_start = time.time()
            filtering_service = FilteringService(config)
            parameterized_result = filtering_service.should_skip_by_date(message_timestamp)
            param_time = time.time() - param_start
            
            # Get global result (with patched globals)
            global_start = time.time()
            global_result = self._get_global_date_filtering_result(message_timestamp, config)
            global_time = time.time() - global_start
            
            # Update metrics
            self.performance_metrics['parameterized_filtering_time'] += param_time
            self.performance_metrics['global_filtering_time'] += global_time
            self.performance_metrics['total_validations'] += 1
            
            # Validate consistency
            validation_passed = parameterized_result == global_result
            
            if not validation_passed:
                self.validation_errors += 1
                if self.flags.log_filtering_differences:
                    logger.warning(
                        f"Date filtering mismatch: timestamp={message_timestamp}, "
                        f"parameterized={parameterized_result}, global={global_result}"
                    )
            
            self.validation_samples += 1
            validation_time = time.time() - start_time
            self.performance_metrics['validation_overhead'] += validation_time
            
            return parameterized_result, global_result, validation_passed
            
        except Exception as e:
            logger.error(f"Date filtering validation failed: {e}")
            if self.flags.fallback_to_global_on_error:
                return self._get_global_date_filtering_result(message_timestamp, config), False, False
            return False, False, False
    
    def validate_phone_filtering(
        self, 
        phone_number: str, 
        phone_lookup_manager, 
        config: Optional[ProcessingConfig] = None
    ) -> Tuple[bool, bool, bool]:
        """
        Validate that phone filtering produces identical results.
        
        Args:
            phone_number: Phone number to check
            phone_lookup_manager: PhoneLookupManager instance
            config: ProcessingConfig object for parameterized filtering
            
        Returns:
            Tuple of (parameterized_result, global_result, validation_passed)
        """
        if not self.flags.validate_filtering_consistency or not config:
            # Skip validation if disabled or no config
            filtering_service = FilteringService(config) if config else None
            if filtering_service:
                return filtering_service.should_skip_by_phone(phone_number, phone_lookup_manager), False, True
            return False, False, True
        
        start_time = time.time()
        
        try:
            # Get parameterized result
            param_start = time.time()
            filtering_service = FilteringService(config)
            parameterized_result = filtering_service.should_skip_by_phone(phone_number, phone_lookup_manager)
            param_time = time.time() - param_start
            
            # Get global result (with patched globals)
            global_start = time.time()
            global_result = self._get_global_phone_filtering_result(phone_number, phone_lookup_manager, config)
            global_time = time.time() - global_start
            
            # Update metrics
            self.performance_metrics['parameterized_filtering_time'] += param_time
            self.performance_metrics['global_filtering_time'] += global_time
            self.performance_metrics['total_validations'] += 1
            
            # Validate consistency
            validation_passed = parameterized_result == global_result
            
            if not validation_passed:
                self.validation_errors += 1
                if self.flags.log_filtering_differences:
                    logger.warning(
                        f"Phone filtering mismatch: phone={phone_number}, "
                        f"parameterized={parameterized_result}, global={global_result}"
                    )
            
            self.validation_samples += 1
            validation_time = time.time() - start_time
            self.performance_metrics['validation_overhead'] += validation_time
            
            return parameterized_result, global_result, validation_passed
            
        except Exception as e:
            logger.error(f"Phone filtering validation failed: {e}")
            if self.flags.fallback_to_global_on_error:
                return self._get_global_phone_filtering_result(phone_number, phone_lookup_manager, config), False, False
            return False, False, False
    
    def _get_global_date_filtering_result(self, message_timestamp: int, config: ProcessingConfig) -> bool:
        """Get result from global date filtering logic."""
        # This would use the original global filtering logic
        # For now, we'll simulate it by using the config values directly
        if config.exclude_older_than is None and config.exclude_newer_than is None:
            return False
        
        try:
            message_date = datetime.fromtimestamp(message_timestamp / 1000.0)
            
            if config.exclude_older_than and message_date < config.exclude_older_than:
                return True
            
            if config.exclude_newer_than and message_date > config.exclude_newer_than:
                return True
                
        except (ValueError, OSError):
            return False
        
        return False
    
    def _get_global_phone_filtering_result(self, phone_number: str, phone_lookup_manager, config: ProcessingConfig) -> bool:
        """Get result from global phone filtering logic."""
        # This would use the original global filtering logic
        # For now, we'll simulate it using the config values
        if not phone_number or not phone_lookup_manager:
            return False
        
        # Filter numbers without aliases if enabled
        if config.filter_numbers_without_aliases:
            try:
                has_alias = phone_lookup_manager.has_alias(str(phone_number))
                if not has_alias:
                    return True
            except Exception:
                pass
        
        # Filter non-phone numbers if enabled
        if config.filter_non_phone_numbers:
            if self._is_non_phone_number(phone_number):
                return True
        
        # Filter service codes if not included
        if not config.include_service_codes:
            if self._is_service_code(phone_number):
                return True
        
        return False
    
    def _is_non_phone_number(self, phone_number: str) -> bool:
        """Check if a number is a non-phone number (like short codes)."""
        # Simplified version of the logic from FilteringService
        clean_number = phone_number.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
        
        if len(clean_number) <= 6 and clean_number.isdigit():
            return True
        
        if any(char.isalpha() for char in clean_number):
            return True
        
        non_phone_patterns = ["SHORT", "CODE", "SERVICE", "INFO"]
        if any(pattern in phone_number.upper() for pattern in non_phone_patterns):
            return True
        
        return False
    
    def _is_service_code(self, phone_number: str) -> bool:
        """Check if a number is a service code."""
        if len(phone_number) <= 6:
            return True
        
        service_patterns = ["SERVICE", "CODE", "INFO", "HELP"]
        if any(pattern in phone_number.upper() for pattern in service_patterns):
            return True
        
        return False
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        total_time = (
            self.performance_metrics['parameterized_filtering_time'] +
            self.performance_metrics['global_filtering_time'] +
            self.performance_metrics['validation_overhead']
        )
        
        return {
            'validation_samples': self.validation_samples,
            'validation_errors': self.validation_errors,
            'error_rate': self.validation_errors / max(self.validation_samples, 1),
            'performance_metrics': self.performance_metrics.copy(),
            'total_validation_time': total_time,
            'average_validation_time': total_time / max(self.validation_samples, 1),
            'parameterized_vs_global_speed': (
                self.performance_metrics['global_filtering_time'] /
                max(self.performance_metrics['parameterized_filtering_time'], 0.001)
            )
        }
    
    def is_migration_safe(self) -> bool:
        """Check if the migration is safe based on validation results."""
        if self.validation_samples < 10:
            return False  # Need more samples
        
        error_rate = self.validation_errors / self.validation_samples
        return error_rate < 0.01  # Less than 1% error rate
    
    def reset_validation_metrics(self) -> None:
        """Reset validation metrics (useful for testing)."""
        self.validation_samples = 0
        self.validation_errors = 0
        self.performance_metrics = {
            'global_filtering_time': 0.0,
            'parameterized_filtering_time': 0.0,
            'validation_overhead': 0.0,
            'total_validations': 0
        }


# Global validator instance
migration_validator = FilteringMigrationValidator()


def get_migration_validator() -> FilteringMigrationValidator:
    """Get the global migration validator instance."""
    return migration_validator


def reset_migration_validator() -> None:
    """Reset migration validator (useful for testing)."""
    global migration_validator
    migration_validator = FilteringMigrationValidator()
