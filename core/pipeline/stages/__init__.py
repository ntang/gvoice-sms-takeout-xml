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

# Phase 1: Attachment Processing (Option A implementation)
from .attachment_mapping import AttachmentMappingStage
# Phase 2: Attachment Copying
from .attachment_copying import AttachmentCopyingStage
# Phase 3a: HTML Generation
from .html_generation import HtmlGenerationStage
# Phase 4: Index Generation
from .index_generation import IndexGenerationStage

__all__ = [
    # Phase 2: Phone Processing
    'PhoneDiscoveryStage',
    'PhoneLookupStage',
    # Phase 3: File Discovery & Content Extraction
    'FileDiscoveryStage',
    'ContentExtractionStage',
    # Phase 1: Attachment Processing
    'AttachmentMappingStage',
    # Phase 2: Attachment Copying
    'AttachmentCopyingStage',
    # Phase 3a: HTML Generation
    'HtmlGenerationStage',
    # Phase 4: Index Generation
    'IndexGenerationStage',
]
