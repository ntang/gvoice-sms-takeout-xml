"""
Pipeline Stages

Individual pipeline stages for the modular SMS processing system.
"""

# Phase 2: Phone Processing Stages
from .phone_discovery import PhoneDiscoveryStage
from .phone_lookup import PhoneLookupStage

# Future stages (will be implemented in later phases)
# from .discovery import DiscoveryStage
# from .attachments import AttachmentStage  
# from .content import ContentProcessingStage
# from .html_generation import HtmlGenerationStage
# from .index_generation import IndexGenerationStage

__all__ = [
    # Phase 2: Phone Processing
    'PhoneDiscoveryStage',
    'PhoneLookupStage',
    # Future stages will be added here
]
