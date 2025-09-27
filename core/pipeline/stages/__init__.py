"""
Pipeline Stages

Individual pipeline stages for the modular SMS processing system.
"""

# Phase 2: Phone Processing Stages
from .phone_discovery import PhoneDiscoveryStage
from .phone_lookup import PhoneLookupStage

# Phase 3: File Discovery & Content Extraction Stages
from .file_discovery import FileDiscoveryStage
from .content_extraction import ContentExtractionStage

# Future stages (will be implemented in later phases)
# from .attachments import AttachmentStage  
# from .html_generation import HtmlGenerationStage
# from .index_generation import IndexGenerationStage

__all__ = [
    # Phase 2: Phone Processing
    'PhoneDiscoveryStage',
    'PhoneLookupStage',
    # Phase 3: File Discovery & Content Extraction
    'FileDiscoveryStage',
    'ContentExtractionStage',
    # Future stages will be added here
]
