"""
HTML Generation Stage - Phase 3a of Pipeline Architecture

This stage processes HTML files and generates conversation HTML files.
Implements file-level resumability (simpler approach).

Features:
- Processes HTML files from processing_dir/Calls/
- Generates conversation HTML files in output_dir
- Tracks which files have been processed (file-level state)
- Skips already-processed files on resume
- Accumulates statistics across runs
- Finalizes all conversations at end (same as current behavior)

Dependencies: attachment_mapping, attachment_copying stages

Author: Claude Code
Date: 2025-10-20
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.pipeline.base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class HtmlGenerationStage(PipelineStage):
    """
    Pipeline stage that processes HTML files and generates conversation HTML.

    Input:
        - attachment_mapping.json (from attachment_mapping stage)
        - Copied attachments (from attachment_copying stage)
        - HTML files in processing_dir/Calls/

    Output:
        - Conversation HTML files in output_dir
        - index.html in output_dir
        - html_processing_state.json (for resumability)

    Resumability:
        - Tracks processed files in html_processing_state.json
        - Skips already-processed files on rerun
        - Accumulates statistics across runs
        - Can resume after interruption
    """

    def __init__(self):
        """Initialize the HTML generation stage."""
        super().__init__("html_generation")

    def get_dependencies(self) -> List[str]:
        """Return list of stage names this stage depends on."""
        return ["attachment_mapping", "attachment_copying"]

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that prerequisites are met.

        Required:
            - attachment_mapping.json exists
            - attachments directory exists

        Args:
            context: Pipeline context with processing and output directories

        Returns:
            True if prerequisites met, False otherwise
        """
        mapping_file = context.output_dir / "attachment_mapping.json"
        if not mapping_file.exists():
            logger.error(f"❌ Prerequisite failed: {mapping_file} does not exist")
            logger.error("   Run 'attachment-mapping' stage first")
            return False

        attachments_dir = context.output_dir / "attachments"
        if not attachments_dir.exists():
            logger.error(f"❌ Prerequisite failed: {attachments_dir} does not exist")
            logger.error("   Run 'attachment-copying' stage first")
            return False

        return True

    def can_skip(self, context: PipelineContext) -> bool:
        """
        Determine if stage can be skipped (smart caching).

        Skip if:
            - Stage has completed before
            - All HTML files have been processed
            - No new files added since last run

        Args:
            context: Pipeline context with state data

        Returns:
            True if stage can be safely skipped, False otherwise
        """
        # 1. Did stage ever complete?
        if not context.has_stage_completed(self.name):
            logger.debug("Cannot skip: stage never completed")
            return False

        # 2. Load processing state
        state_file = context.output_dir / "html_processing_state.json"
        if not state_file.exists():
            logger.debug("Cannot skip: state file missing")
            return False

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

            processed_files = set(state.get('files_processed', []))
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Cannot skip: error reading state file: {e}")
            return False

        # 3. Get current HTML files
        calls_dir = context.processing_dir / "Calls"
        if not calls_dir.exists():
            # No Calls directory - nothing to process
            logger.debug("Can skip: no Calls directory")
            return True

        current_files = set(str(f) for f in calls_dir.rglob("*.html"))

        # 4. Check if all files processed
        unprocessed_files = current_files - processed_files

        if unprocessed_files:
            logger.debug(f"Cannot skip: {len(unprocessed_files)} unprocessed files")
            return False

        logger.debug("Can skip: all files processed")
        return True

    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute HTML generation.

        Process:
            1. Load previous state (if exists)
            2. Load attachment mapping
            3. Get list of HTML files
            4. Filter out already-processed files
            5. Process remaining files
            6. Finalize all conversations
            7. Generate index.html
            8. Save updated state

        Args:
            context: Pipeline context

        Returns:
            StageResult with success status, counts, and metadata
        """
        start_time = time.time()

        logger.info("🔍 Starting HTML generation...")

        try:
            # 1. Load previous state
            state_file = context.output_dir / "html_processing_state.json"
            state = self._load_state(state_file)

            processed_files_set = set(state.get('files_processed', []))
            previous_stats = state.get('stats', {
                'num_sms': 0,
                'num_img': 0,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            })

            logger.info(f"   Previously processed: {len(processed_files_set)} files")

            # 2. Load attachment mapping
            mapping_file = context.output_dir / "attachment_mapping.json"
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)

            # Convert mapping to format expected by process_html_files_param
            src_filename_map = self._convert_mapping_to_dict(mapping_data)

            logger.info(f"   Loaded {len(src_filename_map)} attachment mappings")

            # 3. Get HTML files
            calls_dir = context.processing_dir / "Calls"
            if not calls_dir.exists():
                logger.info("   No Calls directory found - nothing to process")

                # Still need to save state
                self._save_state(state_file, {
                    'files_processed': list(processed_files_set),
                    'stats': previous_stats
                })

                return StageResult(
                    success=True,
                    records_processed=0,
                    metadata={
                        'total_sms': previous_stats.get('num_sms', 0),
                        'total_img': previous_stats.get('num_img', 0),
                        'total_vcf': previous_stats.get('num_vcf', 0),
                        'total_calls': previous_stats.get('num_calls', 0),
                        'total_voicemails': previous_stats.get('num_voicemails', 0),
                        'files_processed': 0,
                        'files_skipped': 0
                    },
                    execution_time=time.time() - start_time
                )

            all_html_files = list(calls_dir.rglob("*.html"))
            logger.info(f"   Found {len(all_html_files)} total HTML files")

            # 4. Filter out already-processed files
            files_to_process = [
                f for f in all_html_files
                if str(f) not in processed_files_set
            ]

            files_skipped = len(all_html_files) - len(files_to_process)
            logger.info(f"   Files to process: {len(files_to_process)}")
            logger.info(f"   Files skipped: {files_skipped}")

            if len(files_to_process) == 0:
                logger.info("✅ All files already processed!")

                return StageResult(
                    success=True,
                    records_processed=len(processed_files_set),
                    metadata={
                        'total_sms': previous_stats.get('num_sms', 0),
                        'total_img': previous_stats.get('num_img', 0),
                        'total_vcf': previous_stats.get('num_vcf', 0),
                        'total_calls': previous_stats.get('num_calls', 0),
                        'total_voicemails': previous_stats.get('num_voicemails', 0),
                        'files_processed': 0,
                        'files_skipped': files_skipped
                    },
                    execution_time=time.time() - start_time
                )

            # 5. Initialize ConversationManager
            from core.conversation_manager import ConversationManager
            from core.phone_lookup import PhoneLookupManager

            conversation_manager = ConversationManager(
                output_dir=context.output_dir,
                buffer_size=32768,  # Same as used in sms.py
                output_format="html"
            )

            # Initialize phone lookup manager
            phone_lookup_file = context.processing_dir / "phone_lookup.txt"
            phone_lookup_manager = PhoneLookupManager(phone_lookup_file)

            # 6. Process files
            from sms import process_html_files_param

            new_stats = process_html_files_param(
                processing_dir=context.processing_dir,
                src_filename_map=src_filename_map,
                conversation_manager=conversation_manager,
                phone_lookup_manager=phone_lookup_manager,
                config=None,  # Will use defaults
                context=None,
                limited_files=files_to_process  # Only process new files!
            )

            logger.info(f"   Processed: {new_stats.get('num_sms', 0)} SMS, "
                       f"{new_stats.get('num_img', 0)} images, "
                       f"{new_stats.get('num_vcf', 0)} vCards")

            # 7. Finalize all conversations
            logger.info("   Finalizing conversations...")
            conversation_manager.finalize_conversation_files(config=None)

            # 8. Generate index.html
            logger.info("   Generating index...")
            elapsed_time = time.time() - start_time

            # Accumulate stats
            total_stats = {
                'num_sms': previous_stats.get('num_sms', 0) + new_stats.get('num_sms', 0),
                'num_img': previous_stats.get('num_img', 0) + new_stats.get('num_img', 0),
                'num_vcf': previous_stats.get('num_vcf', 0) + new_stats.get('num_vcf', 0),
                'num_calls': previous_stats.get('num_calls', 0) + new_stats.get('num_calls', 0),
                'num_voicemails': previous_stats.get('num_voicemails', 0) + new_stats.get('num_voicemails', 0),
            }

            conversation_manager.generate_index_html(total_stats, elapsed_time)

            # 9. Update state
            processed_files_set.update(str(f) for f in files_to_process)

            self._save_state(state_file, {
                'files_processed': list(processed_files_set),
                'stats': total_stats
            })

            logger.info(f"✅ HTML generation completed in {elapsed_time:.2f}s")
            logger.info(f"   📊 Total files processed: {len(processed_files_set)}")
            logger.info(f"   📋 New files this run: {len(files_to_process)}")
            logger.info(f"   💾 Output: {context.output_dir}")

            return StageResult(
                success=True,
                records_processed=len(files_to_process),
                metadata={
                    'total_sms': total_stats['num_sms'],
                    'total_img': total_stats['num_img'],
                    'total_vcf': total_stats['num_vcf'],
                    'total_calls': total_stats['num_calls'],
                    'total_voicemails': total_stats['num_voicemails'],
                    'files_processed': len(files_to_process),
                    'files_skipped': files_skipped,
                    'total_files_ever_processed': len(processed_files_set)
                },
                execution_time=elapsed_time
            )

        except Exception as e:
            error_msg = f"HTML generation failed: {e}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.debug(traceback.format_exc())

            return StageResult(
                success=False,
                records_processed=0,
                metadata={},
                errors=[error_msg],
                execution_time=time.time() - start_time
            )

    def _load_state(self, state_file: Path) -> Dict:
        """Load processing state from JSON file."""
        if not state_file.exists():
            return {'files_processed': [], 'stats': {}}

        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load state file (will start fresh): {e}")
            return {'files_processed': [], 'stats': {}}

    def _save_state(self, state_file: Path, state: Dict):
        """Save processing state to JSON file (atomic write)."""
        try:
            # Atomic write: write to temp file, then rename
            temp_file = state_file.with_suffix('.tmp')

            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)

            # Atomic rename
            temp_file.replace(state_file)

            logger.debug(f"Saved state: {len(state.get('files_processed', []))} files processed")

        except OSError as e:
            logger.error(f"Failed to save state file: {e}")
            # Don't raise - allow processing to continue

    def _convert_mapping_to_dict(self, mapping_data: Dict) -> Dict[str, str]:
        """
        Convert attachment_mapping.json format to src_filename_map format.

        Input format (from attachment_mapping.json):
        {
            "metadata": {...},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": "/path/to/processing/Calls/photo.jpg"
                }
            }
        }

        Output format (for process_html_files_param):
        {
            "photo.jpg": "Calls/photo.jpg"
        }
        """
        mappings = mapping_data.get('mappings', {})
        return {
            src_ref: file_info['filename']
            for src_ref, file_info in mappings.items()
        }
