"""
Phone Discovery Stage

Extracts all phone numbers from HTML files and identifies unknown numbers
that need lookup/verification.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Any

from bs4 import BeautifulSoup

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class PhoneDiscoveryStage(PipelineStage):
    """Discovers and catalogs phone numbers from HTML files."""
    
    def __init__(self):
        super().__init__("phone_discovery")
        
        # Phone number regex patterns
        self.phone_patterns = [
            r'\+1[0-9]{10}',           # +1xxxxxxxxxx
            r'\+1 \([0-9]{3}\) [0-9]{3}-[0-9]{4}',  # +1 (xxx) xxx-xxxx
            r'\([0-9]{3}\) [0-9]{3}-[0-9]{4}',      # (xxx) xxx-xxxx
            r'[0-9]{3}-[0-9]{3}-[0-9]{4}',          # xxx-xxx-xxxx
            r'[0-9]{10}',                           # xxxxxxxxxx
            r'\+[0-9]{10,15}',                      # International numbers
        ]
        
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute phone discovery stage.
        
        Args:
            context: Pipeline context
            
        Returns:
            StageResult: Discovery results
        """
        start_time = time.time()
        
        try:
            logger.info("Starting phone number discovery")
            
            # Find all HTML files
            html_files = self._find_html_files(context.processing_dir)
            logger.info(f"Found {len(html_files)} HTML files to process")
            
            # Extract phone numbers
            discovered_numbers = self._extract_phone_numbers(html_files)
            logger.info(f"Discovered {len(discovered_numbers)} unique phone numbers")
            
            # Load existing phone lookup data
            known_numbers = self._load_known_numbers(context)
            logger.info(f"Found {len(known_numbers)} known phone numbers")
            
            # Categorize numbers
            unknown_numbers = discovered_numbers - known_numbers
            logger.info(f"Identified {len(unknown_numbers)} unknown phone numbers")
            
            # Create phone inventory
            inventory = {
                "discovery_metadata": {
                    "scan_date": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "processing_dir": str(context.processing_dir),
                    "html_files_processed": len(html_files),
                    "scan_duration_ms": int((time.time() - start_time) * 1000)
                },
                "discovered_numbers": sorted(list(discovered_numbers)),
                "known_numbers": sorted(list(known_numbers & discovered_numbers)),
                "unknown_numbers": sorted(list(unknown_numbers)),
                "discovery_stats": {
                    "total_discovered": len(discovered_numbers),
                    "known_count": len(known_numbers & discovered_numbers),
                    "unknown_count": len(unknown_numbers),
                    "files_processed": len(html_files)
                }
            }
            
            # Save phone inventory
            output_file = context.output_dir / "phone_inventory.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(inventory, f, indent=2)
                
            execution_time = time.time() - start_time
            
            result = StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=len(discovered_numbers),
                output_files=[output_file],
                metadata={
                    "discovered_count": len(discovered_numbers),
                    "unknown_count": len(unknown_numbers),
                    "known_count": len(known_numbers & discovered_numbers),
                    "files_processed": len(html_files)
                }
            )
            
            logger.info(f"Phone discovery completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Phone discovery failed: {e}", exc_info=True)
            
            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Phone discovery failed: {str(e)}"]
            )
            
    def _find_html_files(self, processing_dir: Path) -> List[Path]:
        """Find all HTML files in the processing directory."""
        html_files = []
        
        # Look for HTML files in common subdirectories
        search_dirs = [
            processing_dir,
            processing_dir / "Calls",
            processing_dir / "Texts", 
            processing_dir / "Voicemails"
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                html_files.extend(search_dir.glob("*.html"))
                
        return html_files
        
    def _extract_phone_numbers(self, html_files: List[Path]) -> Set[str]:
        """Extract phone numbers from HTML files."""
        discovered_numbers = set()
        
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Parse HTML to extract text content
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text()
                
                # Extract phone numbers using regex patterns
                for pattern in self.phone_patterns:
                    matches = re.findall(pattern, text_content)
                    for match in matches:
                        normalized = self._normalize_phone_number(match)
                        if normalized:
                            discovered_numbers.add(normalized)
                            
                # Also check for phone numbers in specific HTML elements
                # that might contain contact information
                phone_elements = soup.find_all(['a', 'span'], href=re.compile(r'tel:'))
                for element in phone_elements:
                    href = element.get('href', '')
                    if href.startswith('tel:'):
                        phone = href[4:]  # Remove 'tel:' prefix
                        normalized = self._normalize_phone_number(phone)
                        if normalized:
                            discovered_numbers.add(normalized)
                            
            except Exception as e:
                logger.warning(f"Failed to process {html_file}: {e}")
                continue
                
        return discovered_numbers
        
    def _normalize_phone_number(self, phone: str) -> str:
        """
        Normalize phone number to consistent format.
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Normalized phone number or empty string if invalid
        """
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Handle different formats
        if cleaned.startswith('+1') and len(cleaned) == 12:
            # +1xxxxxxxxxx -> +1xxxxxxxxxx
            return cleaned
        elif cleaned.startswith('+') and len(cleaned) >= 11:
            # International number
            return cleaned
        elif len(cleaned) == 10:
            # xxxxxxxxxx -> +1xxxxxxxxxx
            return f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            # 1xxxxxxxxxx -> +1xxxxxxxxxx
            return f"+{cleaned}"
        else:
            # Invalid or unsupported format
            return ""
            
    def _load_known_numbers(self, context: PipelineContext) -> Set[str]:
        """Load known phone numbers from phone lookup file."""
        known_numbers = set()
        
        # Try to find phone lookup file
        phone_lookup_files = [
            context.processing_dir / "phone_lookup.txt",
            context.processing_dir.parent / "phone_lookup.txt",
            Path("phone_lookup.txt")
        ]
        
        for phone_file in phone_lookup_files:
            if phone_file.exists():
                try:
                    with open(phone_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Parse phone lookup format: +1234567890:Alias:filter_status
                                parts = line.split(':')
                                if parts:
                                    phone = parts[0].strip()
                                    normalized = self._normalize_phone_number(phone)
                                    if normalized:
                                        known_numbers.add(normalized)
                except Exception as e:
                    logger.warning(f"Failed to load phone lookup from {phone_file}: {e}")
                break
                
        return known_numbers
        
    def get_dependencies(self) -> List[str]:
        """Phone discovery has no dependencies."""
        return []
        
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate prerequisites for phone discovery.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        if not context.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {context.processing_dir}")
            return False
            
        # Check for HTML files
        html_files = self._find_html_files(context.processing_dir)
        if not html_files:
            logger.warning(f"No HTML files found in {context.processing_dir}")
            # Don't fail - this might be intentional for testing
            
        return True
