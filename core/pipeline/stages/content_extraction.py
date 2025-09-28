"""
Content Extraction Stage

Extracts structured data from HTML files, parsing messages, timestamps,
participants, and attachments into normalized data structures.
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from bs4 import BeautifulSoup

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class ContentExtractionStage(PipelineStage):
    """Extracts structured content from HTML files."""
    
    def __init__(self, max_files_per_batch: int = 1000):
        super().__init__("content_extraction")
        self.max_files_per_batch = max_files_per_batch
        
        # Regex patterns for data extraction
        self.timestamp_patterns = [
            r'(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',  # Jan 15, 2023 2:30:45 PM
            r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',      # 1/15/2023 2:30:45 PM
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',                    # 2023-01-15 14:30:45
        ]
        
        self.phone_pattern = r'\+?1?[0-9]{10,15}'
        
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute content extraction stage.
        
        Args:
            context: Pipeline context
            
        Returns:
            StageResult: Extraction results
        """
        start_time = time.time()
        
        try:
            logger.info("Starting content extraction from HTML files")
            
            # Load file inventory from discovery stage
            file_inventory = self._load_file_inventory(context)
            if not file_inventory:
                raise ValueError("File inventory not found - run file discovery stage first")
                
            files_to_process = file_inventory.get("files", [])
            logger.info(f"Processing {len(files_to_process)} files for content extraction")
            
            # Extract content in batches
            extracted_content = self._extract_content_batch(files_to_process, context)
            
            # Save extracted content
            output_file = context.output_dir / "extracted_content.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(extracted_content, f, indent=2, default=str)
                
            execution_time = time.time() - start_time
            
            # Calculate statistics
            total_messages = sum(len(conv.get("messages", [])) for conv in extracted_content.get("conversations", []))
            total_participants = len(set().union(*(
                conv.get("participants", []) for conv in extracted_content.get("conversations", [])
            )))
            
            result = StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=len(files_to_process),
                output_files=[output_file],
                metadata={
                    "files_processed": len(files_to_process),
                    "conversations_extracted": len(extracted_content.get("conversations", [])),
                    "total_messages": total_messages,
                    "total_participants": total_participants,
                    "extraction_errors": len(extracted_content.get("extraction_errors", []))
                }
            )
            
            logger.info(f"Content extraction completed in {execution_time:.2f}s")
            logger.info(f"Extracted {total_messages} messages from {len(extracted_content.get('conversations', []))} conversations")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Content extraction failed: {e}", exc_info=True)
            
            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Content extraction failed: {str(e)}"]
            )
            
    def _load_file_inventory(self, context: PipelineContext) -> Optional[Dict[str, Any]]:
        """Load file inventory from discovery stage."""
        inventory_file = context.output_dir / "file_inventory.json"
        
        if not inventory_file.exists():
            return None
            
        try:
            with open(inventory_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load file inventory: {e}")
            return None
            
    def _extract_content_batch(self, files_to_process: List[Dict[str, Any]], context: PipelineContext) -> Dict[str, Any]:
        """Extract content from a batch of files."""
        extracted_content = {
            "extraction_metadata": {
                "extraction_date": datetime.now().isoformat(),
                "files_processed": 0,
                "extraction_errors": 0
            },
            "conversations": [],
            "extraction_errors": []
        }
        
        processed_count = 0
        error_count = 0
        
        for file_info in files_to_process:
            if processed_count >= self.max_files_per_batch:
                logger.info(f"Reached batch limit of {self.max_files_per_batch} files")
                break
                
            try:
                file_path = Path(file_info["path"])
                if not file_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue
                    
                # Extract content based on file type
                file_type = file_info.get("type", "unknown")
                
                if file_type == "sms_mms":
                    conversation = self._extract_sms_mms_content(file_path, file_info)
                elif file_type == "calls":
                    conversation = self._extract_call_content(file_path, file_info)
                elif file_type == "voicemails":
                    conversation = self._extract_voicemail_content(file_path, file_info)
                else:
                    logger.debug(f"Skipping unknown file type: {file_type} for {file_path}")
                    continue
                    
                if conversation:
                    extracted_content["conversations"].append(conversation)
                    
                processed_count += 1
                
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} files...")
                    
            except Exception as e:
                error_count += 1
                error_info = {
                    "file_path": file_info.get("path", "unknown"),
                    "error": str(e),
                    "file_type": file_info.get("type", "unknown")
                }
                extracted_content["extraction_errors"].append(error_info)
                logger.warning(f"Failed to extract content from {file_info.get('path')}: {e}")
                
        extracted_content["extraction_metadata"]["files_processed"] = processed_count
        extracted_content["extraction_metadata"]["extraction_errors"] = error_count
        
        return extracted_content
        
    def _extract_sms_mms_content(self, file_path: Path, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract content from SMS/MMS HTML files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            soup = BeautifulSoup(content, 'html.parser')
            
            conversation = {
                "conversation_id": file_path.stem,
                "file_path": str(file_path),
                "file_type": "sms_mms",
                "participants": [],
                "messages": [],
                "metadata": {
                    "file_size": file_info.get("size_bytes", 0),
                    "extraction_time": datetime.now().isoformat()
                }
            }
            
            # Extract conversation title/participants
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                if title_text and title_text != "Google Voice":
                    conversation["participants"] = [title_text]
                    
            # Extract messages
            messages = self._extract_messages_from_soup(soup, "sms_mms")
            conversation["messages"] = messages
            
            # Extract unique participants from messages
            participants = set(conversation["participants"])
            for message in messages:
                if message.get("sender"):
                    participants.add(message["sender"])
            conversation["participants"] = list(participants)
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to extract SMS/MMS content from {file_path}: {e}")
            return None
            
    def _extract_call_content(self, file_path: Path, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract content from call log HTML files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            soup = BeautifulSoup(content, 'html.parser')
            
            conversation = {
                "conversation_id": file_path.stem,
                "file_path": str(file_path),
                "file_type": "calls",
                "participants": [],
                "messages": [],  # Call logs treated as messages
                "metadata": {
                    "file_size": file_info.get("size_bytes", 0),
                    "extraction_time": datetime.now().isoformat()
                }
            }
            
            # Extract call log entries
            messages = self._extract_messages_from_soup(soup, "calls")
            conversation["messages"] = messages
            
            # Extract participants
            participants = set()
            for message in messages:
                if message.get("sender"):
                    participants.add(message["sender"])
            conversation["participants"] = list(participants)
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to extract call content from {file_path}: {e}")
            return None
            
    def _extract_voicemail_content(self, file_path: Path, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract content from voicemail HTML files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            soup = BeautifulSoup(content, 'html.parser')
            
            conversation = {
                "conversation_id": file_path.stem,
                "file_path": str(file_path),
                "file_type": "voicemails",
                "participants": [],
                "messages": [],
                "metadata": {
                    "file_size": file_info.get("size_bytes", 0),
                    "extraction_time": datetime.now().isoformat()
                }
            }
            
            # Extract voicemail entries
            messages = self._extract_messages_from_soup(soup, "voicemails")
            conversation["messages"] = messages
            
            # Extract participants
            participants = set()
            for message in messages:
                if message.get("sender"):
                    participants.add(message["sender"])
            conversation["participants"] = list(participants)
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to extract voicemail content from {file_path}: {e}")
            return None
            
    def _extract_messages_from_soup(self, soup: BeautifulSoup, content_type: str) -> List[Dict[str, Any]]:
        """Extract messages from BeautifulSoup object."""
        messages = []
        
        # Look for common message container patterns
        message_containers = []
        
        # Try different selectors based on content type
        if content_type == "sms_mms":
            message_containers.extend(soup.find_all(['div', 'span'], class_=lambda x: x and any(
                term in str(x).lower() for term in ['message', 'text', 'chat', 'hchatlog']
            )))
        elif content_type in ["calls", "voicemails"]:
            message_containers.extend(soup.find_all(['div', 'tr', 'span'], class_=lambda x: x and any(
                term in str(x).lower() for term in ['call', 'voicemail', 'log', 'entry']
            )))
            
        # Also try to find table rows which might contain structured data
        message_containers.extend(soup.find_all('tr'))
        
        for i, container in enumerate(message_containers[:500]):  # Limit to first 500 to avoid huge files
            try:
                message = self._extract_message_from_container(container, content_type)
                if message:
                    message["message_id"] = i
                    messages.append(message)
            except Exception as e:
                logger.debug(f"Failed to extract message from container: {e}")
                continue
                
        return messages
        
    def _extract_message_from_container(self, container, content_type: str) -> Optional[Dict[str, Any]]:
        """Extract a single message from a container element."""
        text_content = container.get_text().strip()
        
        if not text_content or len(text_content) < 3:
            return None
            
        message = {
            "content": text_content,
            "sender": None,
            "timestamp": None,
            "message_type": content_type,
            "attachments": []
        }
        
        # Try to extract timestamp
        for pattern in self.timestamp_patterns:
            match = re.search(pattern, text_content)
            if match:
                message["timestamp"] = match.group(1)
                break
                
        # Try to extract sender (phone number or name)
        phone_match = re.search(self.phone_pattern, text_content)
        if phone_match:
            message["sender"] = phone_match.group(0)
            
        # Look for attachment indicators
        if any(term in text_content.lower() for term in ['attachment', 'image', 'audio', 'video']):
            # Try to find attachment links
            links = container.find_all('a')
            for link in links:
                href = link.get('href', '')
                if href and any(ext in href.lower() for ext in ['.jpg', '.png', '.mp3', '.mp4', '.pdf']):
                    message["attachments"].append({
                        "type": "link",
                        "url": href,
                        "text": link.get_text().strip()
                    })
                    
        return message
        
    def get_dependencies(self) -> List[str]:
        """Content extraction depends on file discovery."""
        return ["file_discovery"]
        
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate prerequisites for content extraction.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        # Check that file inventory exists (from discovery stage)
        inventory_file = context.output_dir / "file_inventory.json"
        if not inventory_file.exists():
            logger.error("File inventory not found - run file discovery stage first")
            return False
            
        return True
