"""
Phone Lookup Stage

Performs batch phone number lookup using various APIs and services
to identify spam, commercial numbers, and enrich contact information.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.parse
import urllib.error

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class PhoneLookupStage(PipelineStage):
    """Performs phone number lookup and enrichment."""
    
    def __init__(self, api_provider: str = "ipqualityscore", api_key: Optional[str] = None):
        super().__init__("phone_lookup")
        self.api_provider = api_provider.lower()
        self.api_key = api_key
        
        # API configurations
        self.api_configs = {
            "ipqualityscore": {
                "base_url": "https://ipqualityscore.com/api/json/phone",
                "requires_key": True,
                "rate_limit": 100,  # requests per minute
                "free_limit": 5000  # total free requests
            },
            "truecaller": {
                "base_url": "https://api.truecaller.com/v1/lookup",
                "requires_key": True,
                "rate_limit": 60,
                "free_limit": 0
            },
            "manual": {
                "base_url": None,
                "requires_key": False,
                "rate_limit": 0,
                "free_limit": float('inf')
            }
        }
        
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute phone lookup stage.
        
        Args:
            context: Pipeline context
            
        Returns:
            StageResult: Lookup results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting phone lookup using provider: {self.api_provider}")
            
            # Load phone inventory from discovery stage
            inventory = self._load_phone_inventory(context)
            if not inventory:
                raise ValueError("Phone inventory not found - run phone discovery first")
                
            unknown_numbers = inventory.get("unknown_numbers", [])
            logger.info(f"Processing {len(unknown_numbers)} unknown phone numbers")
            
            # Initialize or load phone directory database
            db_path = context.output_dir / "phone_directory.sqlite"
            self._init_phone_directory(db_path)
            
            # Perform lookups
            lookup_results = []
            processed_count = 0
            
            if self.api_provider == "manual":
                # Manual lookup - export CSV for user processing
                csv_path = self._export_unknown_numbers_csv(unknown_numbers, context.output_dir)
                logger.info(f"Exported unknown numbers to {csv_path} for manual lookup")
                processed_count = len(unknown_numbers)
            else:
                # API-based lookup
                lookup_results = self._perform_api_lookups(unknown_numbers, db_path)
                processed_count = len(lookup_results)
                
            # Update phone directory
            self._update_phone_directory(db_path, lookup_results)
            
            # Load existing phone lookup file and update it
            self._update_phone_lookup_file(context, lookup_results)
            
            execution_time = time.time() - start_time
            
            result = StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=processed_count,
                output_files=[db_path],
                metadata={
                    "api_provider": self.api_provider,
                    "numbers_processed": processed_count,
                    "unknown_numbers_total": len(unknown_numbers),
                    "lookup_success_rate": processed_count / len(unknown_numbers) if unknown_numbers else 0
                }
            )
            
            logger.info(f"Phone lookup completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Phone lookup failed: {e}", exc_info=True)
            
            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Phone lookup failed: {str(e)}"]
            )
            
    def _load_phone_inventory(self, context: PipelineContext) -> Optional[Dict[str, Any]]:
        """Load phone inventory from discovery stage."""
        inventory_file = context.output_dir / "phone_inventory.json"
        
        if not inventory_file.exists():
            return None
            
        try:
            with open(inventory_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load phone inventory: {e}")
            return None
            
    def _init_phone_directory(self, db_path: Path) -> None:
        """Initialize the phone directory SQLite database."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phone_directory (
                    phone_number TEXT PRIMARY KEY,
                    display_name TEXT,
                    source TEXT,  -- 'manual', 'api', 'carrier'
                    is_spam BOOLEAN,
                    spam_confidence REAL,
                    line_type TEXT,  -- 'mobile', 'landline', 'voip'
                    carrier TEXT,
                    location TEXT,
                    lookup_date TIMESTAMP,
                    api_provider TEXT,
                    api_response TEXT,  -- JSON blob for audit trail
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phone_number 
                ON phone_directory(phone_number)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_spam 
                ON phone_directory(is_spam)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_lookup_date 
                ON phone_directory(lookup_date)
            """)
            
    def _perform_api_lookups(self, phone_numbers: List[str], db_path: Path) -> List[Dict[str, Any]]:
        """Perform API lookups for phone numbers."""
        results = []
        
        # Check if we have API key when required
        config = self.api_configs.get(self.api_provider, {})
        if config.get("requires_key") and not self.api_key:
            logger.error(f"API key required for {self.api_provider} but not provided")
            return results
            
        for phone_number in phone_numbers:
            try:
                # Check if we already have this number in the database
                if self._is_number_in_database(phone_number, db_path):
                    logger.debug(f"Skipping {phone_number} - already in database")
                    continue
                    
                # Perform API lookup
                if self.api_provider == "ipqualityscore":
                    lookup_result = self._lookup_ipqualityscore(phone_number)
                elif self.api_provider == "truecaller":
                    lookup_result = self._lookup_truecaller(phone_number)
                else:
                    logger.warning(f"Unknown API provider: {self.api_provider}")
                    continue
                    
                if lookup_result:
                    results.append(lookup_result)
                    logger.debug(f"Lookup completed for {phone_number}")
                    
                # Respect rate limits
                time.sleep(1)  # Basic rate limiting
                
            except Exception as e:
                logger.warning(f"Lookup failed for {phone_number}: {e}")
                continue
                
        return results
        
    def _is_number_in_database(self, phone_number: str, db_path: Path) -> bool:
        """Check if phone number already exists in database."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM phone_directory WHERE phone_number = ?
            """, (phone_number,))
            return cursor.fetchone() is not None
            
    def _lookup_ipqualityscore(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Perform lookup using IPQualityScore API."""
        if not self.api_key:
            return None
            
        try:
            # Format phone number for API (remove + and any formatting)
            clean_number = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            url = f"https://ipqualityscore.com/api/json/phone/{self.api_key}/{clean_number}"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            # Parse IPQualityScore response
            return {
                "phone_number": phone_number,
                "display_name": None,
                "source": "api",
                "is_spam": data.get("fraud_score", 0) > 75,
                "spam_confidence": data.get("fraud_score", 0) / 100.0,
                "line_type": data.get("line_type", "unknown").lower(),
                "carrier": data.get("carrier", ""),
                "location": f"{data.get('city', '')}, {data.get('region', '')}, {data.get('country', '')}".strip(', '),
                "lookup_date": datetime.now().isoformat(),
                "api_provider": "ipqualityscore",
                "api_response": json.dumps(data)
            }
            
        except Exception as e:
            logger.error(f"IPQualityScore lookup failed for {phone_number}: {e}")
            return None
            
    def _lookup_truecaller(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Perform lookup using Truecaller API."""
        # Placeholder for Truecaller implementation
        # This would require Truecaller API credentials and implementation
        logger.warning("Truecaller API not implemented yet")
        return None
        
    def _update_phone_directory(self, db_path: Path, lookup_results: List[Dict[str, Any]]) -> None:
        """Update phone directory database with lookup results."""
        if not lookup_results:
            return
            
        with sqlite3.connect(db_path) as conn:
            for result in lookup_results:
                conn.execute("""
                    INSERT OR REPLACE INTO phone_directory 
                    (phone_number, display_name, source, is_spam, spam_confidence,
                     line_type, carrier, location, lookup_date, api_provider, api_response, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result["phone_number"],
                    result.get("display_name"),
                    result["source"], 
                    result.get("is_spam", False),
                    result.get("spam_confidence", 0.0),
                    result.get("line_type"),
                    result.get("carrier"),
                    result.get("location"),
                    result["lookup_date"],
                    result.get("api_provider"),
                    result.get("api_response"),
                    datetime.now().isoformat()
                ))
                
        logger.info(f"Updated phone directory with {len(lookup_results)} entries")
        
    def _update_phone_lookup_file(self, context: PipelineContext, lookup_results: List[Dict[str, Any]]) -> None:
        """Update the traditional phone lookup file with new entries."""
        if not lookup_results:
            return
            
        # Find the phone lookup file
        phone_lookup_file = context.processing_dir / "phone_lookup.txt"
        if not phone_lookup_file.exists():
            phone_lookup_file = context.processing_dir.parent / "phone_lookup.txt"
            
        if phone_lookup_file.exists():
            try:
                # Read existing entries
                existing_entries = []
                with open(phone_lookup_file, 'r', encoding='utf-8') as f:
                    existing_entries = f.readlines()
                    
                # Add new entries
                with open(phone_lookup_file, 'a', encoding='utf-8') as f:
                    for result in lookup_results:
                        phone = result["phone_number"]
                        
                        # Generate alias based on lookup results
                        if result.get("is_spam"):
                            alias = f"SPAM_{result.get('api_provider', 'API')}"
                            filter_status = "filter"
                        else:
                            carrier = result.get("carrier", "Unknown")
                            alias = f"{carrier}_{phone[-4:]}"  # Last 4 digits
                            filter_status = ""
                            
                        # Format: +1234567890:Alias:filter_status
                        entry = f"{phone}:{alias}:{filter_status}\n"
                        f.write(entry)
                        
                logger.info(f"Updated phone lookup file with {len(lookup_results)} new entries")
                
            except Exception as e:
                logger.error(f"Failed to update phone lookup file: {e}")
                
    def _export_unknown_numbers_csv(self, unknown_numbers: List[str], output_dir: Path) -> Path:
        """Export unknown numbers to CSV for manual lookup."""
        csv_path = output_dir / "unknown_numbers.csv"
        
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("phone_number,display_name,is_spam,notes\n")
            for phone in unknown_numbers:
                f.write(f"{phone},,false,\n")
                
        return csv_path
        
    def get_dependencies(self) -> List[str]:
        """Phone lookup depends on phone discovery."""
        return ["phone_discovery"]
        
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate prerequisites for phone lookup.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        # Check that phone inventory exists (from discovery stage)
        inventory_file = context.output_dir / "phone_inventory.json"
        if not inventory_file.exists():
            logger.error("Phone inventory not found - run phone discovery stage first")
            return False
            
        # Check API key if required
        config = self.api_configs.get(self.api_provider, {})
        if config.get("requires_key") and not self.api_key:
            logger.warning(f"No API key provided for {self.api_provider} - will skip API lookups")
            
        return True
