"""
Index Generation Stage - Phase 4 of Pipeline Architecture

This stage generates index.html from conversation HTML files with metadata caching
for fast regeneration.

Features:
- Generates index.html from conversation files
- Metadata caching for fast reruns
- Smart skip logic when conversations unchanged
- Incremental updates for new conversations
- Multiple output formats (HTML, JSON metadata)

Dependencies: html_generation stage

Author: Claude Code
Date: 2025-10-20
"""

import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from core.pipeline.base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class IndexGenerationStage(PipelineStage):
    """
    Pipeline stage that generates index files from conversation HTML files.

    Input:
        - Conversation HTML files in output_dir
        - Statistics from html_generation stage (optional)

    Output:
        - index.html (browsable conversation list)
        - conversation_metadata.json (cached metadata)

    Features:
        - Smart caching of conversation metadata
        - Incremental index updates
        - Fast regeneration (<1s for cached data)
    """

    def __init__(self):
        """Initialize the index generation stage."""
        super().__init__("index_generation")

    def get_dependencies(self) -> List[str]:
        """Return list of stage names this stage depends on."""
        return ["html_generation"]

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that prerequisites are met.

        Required:
            - output_dir exists
            - At least one conversation HTML file exists

        Args:
            context: Pipeline context with output directory

        Returns:
            True if prerequisites met, False otherwise
        """
        if not context.output_dir.exists():
            logger.error(f"❌ Prerequisite failed: {context.output_dir} does not exist")
            return False

        # Check for conversation files
        conversation_files = list(context.output_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]

        if not conversation_files:
            logger.error("❌ Prerequisite failed: No conversation HTML files found")
            logger.error("   Run 'html-generation' stage first")
            return False

        return True

    def can_skip(self, context: PipelineContext) -> bool:
        """
        Determine if stage can be skipped (smart caching).

        Skip if:
            - Stage has completed before
            - Metadata cache exists and is valid
            - No new or modified conversation files

        Args:
            context: Pipeline context with state data

        Returns:
            True if stage can be safely skipped, False otherwise
        """
        # 1. Did stage ever complete?
        if not context.has_stage_completed(self.name):
            logger.debug("Cannot skip: stage never completed")
            return False

        # 2. Load metadata cache
        cache_file = context.output_dir / "conversation_metadata.json"
        if not cache_file.exists():
            logger.debug("Cannot skip: metadata cache missing")
            return False

        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Cannot skip: error reading cache: {e}")
            return False

        # 3. Get current conversation files (exclude index.html and .archived.html files)
        current_files = list(context.output_dir.glob("*.html"))
        current_files = [
            f for f in current_files
            if f.name != "index.html" and not f.name.endswith(".archived.html")
        ]

        if not current_files:
            logger.debug("Can skip: no conversation files")
            return True

        # 4. Compute hash of current files
        current_hash = self._compute_files_hash(current_files)
        cached_hash = cache.get("conversation_files_hash", "")

        if current_hash != cached_hash:
            logger.debug(f"Cannot skip: files changed (cached: {cached_hash[:8]}, current: {current_hash[:8]})")
            return False

        logger.debug("Can skip: all conversations unchanged")
        return True

    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute index generation.

        Process:
            1. Scan output_dir for conversation HTML files
            2. Load metadata cache (if exists)
            3. Extract metadata for new/modified files
            4. Generate index.html using template
            5. Save updated metadata cache

        Args:
            context: Pipeline context

        Returns:
            StageResult with success status, counts, and metadata
        """
        start_time = time.time()

        logger.info("🔍 Starting index generation...")

        try:
            # 1. Get conversation files (exclude index.html and .archived.html files)
            conv_files = list(context.output_dir.glob("*.html"))
            conv_files = [
                f for f in conv_files
                if f.name != "index.html" and not f.name.endswith(".archived.html")
            ]
            conv_files.sort(key=lambda x: x.name)

            logger.info(f"   Found {len(conv_files)} conversation files")

            if len(conv_files) == 0:
                logger.info("   No conversation files found - generating empty index")

                # Generate empty index
                self._generate_empty_index(context.output_dir)

                return StageResult(
                    success=True,
                    records_processed=0,
                    metadata={
                        'total_conversations': 0,
                        'files_skipped': 0
                    },
                    execution_time=time.time() - start_time
                )

            # 2. Load metadata cache
            cache_file = context.output_dir / "conversation_metadata.json"
            cached_metadata = self._load_metadata_cache(cache_file)

            # 3. Load statistics from HTML generation stage
            html_state_file = context.output_dir / "html_processing_state.json"
            html_state = self._load_html_state(html_state_file)
            stats = html_state.get('stats', {})
            conversation_stats = html_state.get('conversations', {})

            # 3a. Calculate stats for DISPLAYED conversations only (excludes .archived.html)
            displayed_stats = {
                'num_sms': 0,
                'num_calls': 0,
                'num_voicemails': 0,
                'num_img': 0,
                'num_vcf': 0
            }

            for conv_file in conv_files:
                conv_id = conv_file.stem
                if conv_id in conversation_stats:
                    conv_stat = conversation_stats[conv_id]
                    displayed_stats['num_sms'] += conv_stat.get('sms_count', 0)
                    displayed_stats['num_calls'] += conv_stat.get('call_count', 0)
                    displayed_stats['num_voicemails'] += conv_stat.get('voicemail_count', 0)
                    displayed_stats['num_img'] += conv_stat.get('attachment_count', 0)
                    # Note: num_vcf tracking would need separate field in conversation_stats

            # Log the difference for verification
            global_sms = stats.get('num_sms', 0)
            displayed_sms = displayed_stats['num_sms']
            archived_sms = global_sms - displayed_sms
            logger.info(f"📊 Stats calculation:")
            logger.info(f"   Displayed conversations: {len(conv_files)}")
            logger.info(f"   Displayed SMS: {displayed_sms:,}")
            logger.info(f"   Global SMS (includes archived): {global_sms:,}")
            logger.info(f"   Archived SMS: {archived_sms:,}")

            # 4. Extract metadata for all files (use cache when possible, merge with stats)
            metadata = self._build_conversation_metadata(
                conv_files,
                cached_metadata.get('conversations', {}),
                conversation_stats  # NEW: Pass per-conversation stats
            )

            # 5. Generate index.html (use displayed_stats instead of global stats)
            self._generate_index_html(
                context.output_dir,
                conv_files,
                metadata,
                displayed_stats  # Changed from stats to displayed_stats
            )

            # 6. Save metadata cache
            files_hash = self._compute_files_hash(conv_files)
            self._save_metadata_cache(cache_file, metadata, files_hash)

            elapsed_time = time.time() - start_time

            logger.info(f"✅ Index generation completed in {elapsed_time:.2f}s")
            logger.info(f"   📊 Total conversations: {len(conv_files)}")
            logger.info(f"   💾 Output: {context.output_dir / 'index.html'}")

            return StageResult(
                success=True,
                records_processed=len(conv_files),
                metadata={
                    'total_conversations': len(conv_files),
                    'files_skipped': 0
                },
                execution_time=elapsed_time
            )

        except Exception as e:
            error_msg = f"Index generation failed: {e}"
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

    def _load_metadata_cache(self, cache_file: Path) -> Dict:
        """Load metadata cache from JSON file."""
        if not cache_file.exists():
            return {'conversations': {}}

        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load metadata cache (will rebuild): {e}")
            return {'conversations': {}}

    def _load_html_state(self, state_file: Path) -> Dict:
        """Load complete state from HTML processing state file."""
        default_state = {
            'stats': {
                'num_sms': 0,
                'num_img': 0,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            },
            'conversations': {}
        }

        if not state_file.exists():
            logger.warning("HTML processing state file not found - using empty state")
            return default_state

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

                # Ensure required keys exist
                if 'stats' not in state:
                    logger.warning("No global stats found in state file")
                    state['stats'] = default_state['stats']

                if 'conversations' not in state:
                    logger.warning("No per-conversation stats found in state file")
                    state['conversations'] = {}

                return state
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load HTML state: {e}")
            return default_state

    def _save_metadata_cache(self, cache_file: Path, metadata: Dict, files_hash: str):
        """Save metadata cache to JSON file (atomic write)."""
        try:
            cache_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'conversation_files_hash': files_hash,
                'conversations': metadata
            }

            # Atomic write: write to temp file, then rename
            temp_file = cache_file.with_suffix('.tmp')

            with open(temp_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            # Atomic rename
            temp_file.replace(cache_file)

            logger.debug(f"Saved metadata cache: {len(metadata)} conversations")

        except OSError as e:
            logger.error(f"Failed to save metadata cache: {e}")
            # Don't raise - allow processing to continue

    def _build_conversation_metadata(
        self,
        conv_files: List[Path],
        cached_metadata: Dict,
        conversation_stats: Dict  # NEW parameter
    ) -> Dict:
        """
        Build metadata for all conversation files.

        Uses cached metadata for unchanged files, extracts new metadata for changed files,
        and merges with per-conversation statistics from HTML generation.

        Args:
            conv_files: List of conversation HTML file paths
            cached_metadata: Previously cached metadata
            conversation_stats: Per-conversation stats from HTML generation stage

        Returns:
            Dictionary mapping conversation ID to metadata
        """
        metadata = {}

        for file_path in conv_files:
            conversation_id = file_path.stem

            # Check if we have valid cached metadata
            cached = cached_metadata.get(conversation_id, {})
            cached_mtime = cached.get('last_modified')
            current_mtime = file_path.stat().st_mtime

            # Use cache if file hasn't been modified
            if cached_mtime:
                try:
                    # Handle both string (ISO format) and numeric timestamps
                    if isinstance(cached_mtime, str):
                        # Skip comparison for string timestamps (legacy format)
                        # Always re-extract to ensure consistent format
                        file_meta = self._extract_file_metadata(file_path)
                    elif abs(float(cached_mtime) - current_mtime) < 1.0:
                        file_meta = cached
                    else:
                        file_meta = self._extract_file_metadata(file_path)
                except (ValueError, TypeError):
                    # Invalid cached timestamp, re-extract
                    file_meta = self._extract_file_metadata(file_path)
            else:
                # Extract metadata from file
                file_meta = self._extract_file_metadata(file_path)

            # Merge with per-conversation stats from Phase 3a
            conv_stats = conversation_stats.get(conversation_id, {})
            if conv_stats:
                file_meta.update({
                    'sms_count': conv_stats.get('sms_count', 0),
                    'call_count': conv_stats.get('call_count', 0),
                    'voicemail_count': conv_stats.get('voicemail_count', 0),
                    'attachment_count': conv_stats.get('attachment_count', 0),
                    'latest_message_timestamp': conv_stats.get('latest_message_timestamp')
                })

            metadata[conversation_id] = file_meta

        return metadata

    def _extract_file_metadata(self, file_path: Path) -> Dict:
        """
        Extract metadata from a conversation HTML file.

        Args:
            file_path: Path to conversation HTML file

        Returns:
            Dictionary with file metadata
        """
        try:
            stat = file_path.stat()

            return {
                'file_path': file_path.name,
                'file_size': stat.st_size,
                'sms_count': 0,  # Would need to parse HTML to get accurate counts
                'call_count': 0,
                'voicemail_count': 0,
                'attachment_count': 0,
                'latest_message_timestamp': None,
                'last_modified': stat.st_mtime
            }
        except OSError as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
            return {
                'file_path': file_path.name,
                'file_size': 0,
                'sms_count': 0,
                'call_count': 0,
                'voicemail_count': 0,
                'attachment_count': 0,
                'latest_message_timestamp': None,
                'last_modified': 0
            }

    def _generate_index_html(self, output_dir: Path, conv_files: List[Path], metadata: Dict, stats: Dict):
        """
        Generate index.html using template.

        Args:
            output_dir: Output directory
            conv_files: List of conversation files
            metadata: Conversation metadata dictionary
            stats: Statistics from HTML generation stage
        """
        # Load template (located in project root /templates/)
        # Path: /Users/.../gvoice-sms-takeout-xml/templates/index.html
        template_path = Path(__file__).parent.parent.parent.parent / "templates" / "index.html"

        if not template_path.exists():
            raise FileNotFoundError(f"Index template not found: {template_path}")

        template_content = template_path.read_text()

        # Build conversation rows (pass output_dir for summaries.json)
        conversation_rows = self._build_conversation_rows(conv_files, metadata, output_dir)

        # Use statistics from HTML generation stage
        total_sms = stats.get('num_sms', 0)
        total_calls = stats.get('num_calls', 0)
        total_voicemails = stats.get('num_voicemails', 0)
        total_img = stats.get('num_img', 0)
        total_vcf = stats.get('num_vcf', 0)
        total_messages = total_sms + total_calls + total_voicemails

        # Format template variables
        template_vars = {
            'elapsed_time': '0.00',  # Placeholder
            'total_conversations': len(conv_files),
            'num_sms': total_sms,
            'num_calls': total_calls,
            'num_voicemails': total_voicemails,
            'num_img': total_img,
            'num_vcf': total_vcf,
            'total_messages': total_messages,
            'conversation_rows': conversation_rows,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Replace template variables
        html_content = template_content.format(**template_vars)

        # Write index file
        index_file = output_dir / "index.html"
        index_file.write_text(html_content, encoding='utf-8')

        logger.info(f"Generated index.html with {len(conv_files)} conversations")

    def _build_conversation_rows(self, conv_files: List[Path], metadata: Dict, output_dir: Path) -> str:
        """
        Build HTML table rows for conversation files.

        Args:
            conv_files: List of conversation file paths
            metadata: Conversation metadata
            output_dir: Output directory (for loading summaries.json)

        Returns:
            HTML string with table rows
        """
        if not conv_files:
            return "<tr><td colspan='9'><em>No conversation files found</em></td></tr>"

        # Load AI summaries if available
        summaries_path = output_dir / 'summaries.json'
        summaries = {}
        if summaries_path.exists():
            try:
                with open(summaries_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    summaries = data.get('summaries', {})
                    logger.debug(f"Loaded {len(summaries)} AI summaries from summaries.json")
            except Exception as e:
                logger.warning(f"Could not load summaries.json: {e}")

        rows = []
        for file_path in conv_files:
            conversation_id = file_path.stem
            meta = metadata.get(conversation_id, {})

            file_size = meta.get('file_size', 0)
            file_size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else "0 KB"

            # Get AI summary
            summary_text = "No AI summary available"
            if conversation_id in summaries:
                summary_text = summaries[conversation_id]['summary']

            row = f"""
                <tr>
                    <td><a href='{file_path.name}' class='file-link'>{conversation_id}</a></td>
                    <td>HTML</td>
                    <td>{file_size_str}</td>
                    <td>{meta.get('sms_count', 0)}</td>
                    <td>{meta.get('call_count', 0)}</td>
                    <td>{meta.get('voicemail_count', 0)}</td>
                    <td>{meta.get('attachment_count', 0)}</td>
                    <td>{meta.get('latest_message_timestamp', 'N/A')}</td>
                    <td class='summary-cell'>{summary_text}</td>
                </tr>"""
            rows.append(row)

        return "\n".join(rows)

    def _generate_empty_index(self, output_dir: Path):
        """Generate index.html for empty conversation directory."""
        # Load template (located in project root /templates/)
        # Path: /Users/.../gvoice-sms-takeout-xml/templates/index.html
        template_path = Path(__file__).parent.parent.parent.parent / "templates" / "index.html"

        if not template_path.exists():
            raise FileNotFoundError(f"Index template not found: {template_path}")

        template_content = template_path.read_text()

        # Format with zero values
        template_vars = {
            'elapsed_time': '0.00',
            'total_conversations': 0,
            'num_sms': 0,
            'num_calls': 0,
            'num_voicemails': 0,
            'num_img': 0,
            'num_vcf': 0,
            'total_messages': 0,
            'conversation_rows': "<tr><td colspan='9'><em>No conversation files found</em></td></tr>",
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        html_content = template_content.format(**template_vars)

        index_file = output_dir / "index.html"
        index_file.write_text(html_content, encoding='utf-8')

    def _compute_files_hash(self, files: List[Path]) -> str:
        """
        Compute hash of conversation files for change detection.

        Uses file paths and modification times to detect changes.

        Args:
            files: List of file paths

        Returns:
            Hash string
        """
        hasher = hashlib.md5()

        for file_path in sorted(files, key=lambda x: x.name):
            # Hash filename and modification time
            hasher.update(file_path.name.encode('utf-8'))
            hasher.update(str(file_path.stat().st_mtime).encode('utf-8'))

        return hasher.hexdigest()
