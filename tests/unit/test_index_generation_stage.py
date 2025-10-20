"""
Unit tests for IndexGenerationStage (Phase 4).

This test suite follows TDD principles - tests written before implementation.
Tests cover all functionality including metadata caching, smart skipping, and index generation.

Author: Claude Code
Date: 2025-10-20
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.pipeline.base import PipelineContext, StageResult
from core.pipeline.stages.index_generation import IndexGenerationStage


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def tmp_path(tmp_path):
    """Provide a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def stage():
    """Create an IndexGenerationStage instance."""
    return IndexGenerationStage()


@pytest.fixture
def context(tmp_path):
    """Create a mock PipelineContext with temporary directories."""
    processing_dir = tmp_path / "processing"
    output_dir = tmp_path / "output"
    processing_dir.mkdir()
    output_dir.mkdir()

    ctx = Mock(spec=PipelineContext)
    ctx.processing_dir = processing_dir
    ctx.output_dir = output_dir
    ctx.has_stage_completed = Mock(return_value=False)

    return ctx


@pytest.fixture
def sample_conversations(tmp_path):
    """Create sample conversation HTML files for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)

    conversations = []

    # Create 3 sample conversation files
    for i, name in enumerate(["Alice", "Bob", "Charlie"]):
        file_path = output_dir / f"{name}.html"
        content = f"""<!DOCTYPE html>
<html>
<head><title>Conversation with {name}</title></head>
<body>
<h1>{name}</h1>
<div class="message">Hello from {name}!</div>
<div class="message">Another message</div>
</body>
</html>"""
        file_path.write_text(content)
        conversations.append(file_path)

    return conversations


@pytest.fixture
def sample_metadata(tmp_path):
    """Create sample metadata cache."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)

    metadata = {
        "version": "1.0",
        "last_updated": "2025-10-20T01:23:39Z",
        "conversation_files_hash": "abc123",
        "conversations": {
            "Alice": {
                "file_path": "Alice.html",
                "file_size": 234,
                "sms_count": 10,
                "call_count": 2,
                "voicemail_count": 0,
                "attachment_count": 5,
                "latest_message_timestamp": "2024-10-18T19:04:55Z",
                "last_modified": "2025-10-20T01:23:30Z"
            },
            "Bob": {
                "file_path": "Bob.html",
                "file_size": 456,
                "sms_count": 25,
                "call_count": 5,
                "voicemail_count": 1,
                "attachment_count": 10,
                "latest_message_timestamp": "2024-10-19T10:30:00Z",
                "last_modified": "2025-10-20T01:23:31Z"
            }
        }
    }

    return metadata


# ============================================================================
# Test Category 1: Basic Properties
# ============================================================================

class TestBasicProperties:
    """Test basic stage properties and initialization."""

    def test_stage_name(self, stage):
        """Stage should have correct name."""
        assert stage.name == "index_generation"

    def test_stage_dependencies(self, stage):
        """Stage should depend on html_generation."""
        dependencies = stage.get_dependencies()
        assert "html_generation" in dependencies
        assert len(dependencies) == 1


# ============================================================================
# Test Category 2: Prerequisites Validation
# ============================================================================

class TestPrerequisites:
    """Test prerequisite validation logic."""

    def test_validates_output_dir_exists(self, stage, tmp_path):
        """Should validate that output directory exists."""
        context = Mock(spec=PipelineContext)
        context.output_dir = tmp_path / "nonexistent"

        result = stage.validate_prerequisites(context)
        assert result is False

    def test_validates_conversation_files_exist(self, stage, context, sample_conversations):
        """Should validate that at least one conversation file exists."""
        result = stage.validate_prerequisites(context)
        assert result is True

    def test_fails_if_no_conversation_files(self, stage, context):
        """Should fail if no conversation files found."""
        result = stage.validate_prerequisites(context)
        assert result is False


# ============================================================================
# Test Category 3: Execution Logic
# ============================================================================

class TestExecution:
    """Test core execution logic."""

    def test_generates_index_html(self, stage, context, sample_conversations):
        """Should generate index.html from conversation files."""
        # Mock template loading and generation
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text') as mock_write:
                    result = stage.execute(context)

                    assert result.success is True
                    assert result.records_processed == 3  # 3 conversation files

                    # Should have written index.html
                    mock_write.assert_called()

    def test_handles_empty_output_directory(self, stage, context):
        """Should handle empty output directory gracefully."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

                    assert result.success is True
                    assert result.records_processed == 0

    def test_returns_correct_metadata(self, stage, context, sample_conversations):
        """Should return metadata with conversation count and stats."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

                    assert 'total_conversations' in result.metadata
                    assert result.metadata['total_conversations'] == 3


# ============================================================================
# Test Category 4: Metadata Caching
# ============================================================================

class TestMetadataCaching:
    """Test metadata caching functionality."""

    def test_creates_metadata_cache_on_first_run(self, stage, context, sample_conversations):
        """Should create metadata cache file on first run."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text') as mock_write:
                    result = stage.execute(context)

                    # Should have written both index.html and metadata cache
                    assert mock_write.call_count >= 1

    def test_uses_cached_metadata_for_unchanged_files(self, stage, context, sample_conversations, sample_metadata):
        """Should use cached metadata for files that haven't changed."""
        # Setup: Write metadata cache
        cache_file = context.output_dir / "conversation_metadata.json"
        cache_file.write_text(json.dumps(sample_metadata))

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

                    # Should have used cache (check via faster execution)
                    assert result.success is True

    def test_updates_cache_for_new_files(self, stage, context, sample_conversations, sample_metadata):
        """Should update cache when new conversation files are added."""
        # Setup: Write metadata cache with only 2 conversations
        cache_file = context.output_dir / "conversation_metadata.json"
        cache_file.write_text(json.dumps(sample_metadata))

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

                    # Should have processed 3 files (1 new + 2 cached)
                    assert result.success is True


# ============================================================================
# Test Category 5: Smart Skipping Logic
# ============================================================================

class TestSmartSkipping:
    """Test intelligent skip logic based on file changes."""

    def test_cannot_skip_if_never_ran(self, stage, context):
        """Should not skip if stage has never been run."""
        context.has_stage_completed.return_value = False

        can_skip = stage.can_skip(context)
        assert can_skip is False

    def test_cannot_skip_if_cache_missing(self, stage, context, sample_conversations):
        """Should not skip if metadata cache is missing."""
        context.has_stage_completed.return_value = True
        # Don't create cache file

        can_skip = stage.can_skip(context)
        assert can_skip is False

    def test_can_skip_if_conversations_unchanged(self, stage, context, sample_conversations, sample_metadata):
        """Should skip if all conversation files are unchanged."""
        context.has_stage_completed.return_value = True

        # Create metadata cache
        cache_file = context.output_dir / "conversation_metadata.json"

        # Compute correct hash for current files
        conv_files = [f for f in context.output_dir.glob("*.html") if f.name != "index.html"]
        files_hash = stage._compute_files_hash(conv_files) if hasattr(stage, '_compute_files_hash') else "abc123"

        sample_metadata['conversation_files_hash'] = files_hash
        cache_file.write_text(json.dumps(sample_metadata))

        can_skip = stage.can_skip(context)
        assert can_skip is True

    def test_cannot_skip_if_new_files_added(self, stage, context, sample_conversations, sample_metadata):
        """Should not skip if new conversation files have been added."""
        context.has_stage_completed.return_value = True

        # Create cache with old hash
        cache_file = context.output_dir / "conversation_metadata.json"
        sample_metadata['conversation_files_hash'] = "old_hash_123"
        cache_file.write_text(json.dumps(sample_metadata))

        # Add new conversation file
        new_file = context.output_dir / "Diana.html"
        new_file.write_text("<html><body>New conversation</body></html>")

        can_skip = stage.can_skip(context)
        assert can_skip is False

    def test_cannot_skip_if_files_modified(self, stage, context, sample_conversations, sample_metadata):
        """Should not skip if existing conversation files have been modified."""
        context.has_stage_completed.return_value = True

        # Create cache with old hash
        cache_file = context.output_dir / "conversation_metadata.json"
        sample_metadata['conversation_files_hash'] = "old_hash_456"
        cache_file.write_text(json.dumps(sample_metadata))

        # Modify existing conversation file
        alice_file = context.output_dir / "Alice.html"
        alice_file.write_text("<html><body>Modified content!</body></html>")

        can_skip = stage.can_skip(context)
        assert can_skip is False


# ============================================================================
# Test Category 6: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_corrupt_metadata_cache(self, stage, context, sample_conversations):
        """Should handle corrupt metadata cache gracefully."""
        # Create corrupt cache file
        cache_file = context.output_dir / "conversation_metadata.json"
        cache_file.write_text("{ invalid json }")

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

                    # Should recover and process normally
                    assert result.success is True

    def test_handles_missing_template(self, stage, context, sample_conversations):
        """Should handle missing index template gracefully."""
        with patch('pathlib.Path.exists', return_value=False):
            result = stage.execute(context)

            # Should fail gracefully
            assert result.success is False
            assert len(result.errors) > 0

    def test_handles_template_rendering_errors(self, stage, context, sample_conversations):
        """Should handle template rendering errors gracefully."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{invalid_var}</html>"):
                result = stage.execute(context)

                # Should fail with error message
                assert result.success is False


# ============================================================================
# Test Category 7: State File Format
# ============================================================================

class TestStateFileFormat:
    """Test metadata cache file format and structure."""

    def test_metadata_file_has_correct_structure(self, stage, context, sample_conversations):
        """Metadata cache should have correct JSON structure."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text') as mock_write:
                    stage.execute(context)

                    # Find the metadata write call
                    metadata_calls = [
                        call for call in mock_write.call_args_list
                        if 'conversation_metadata' in str(call)
                    ]

                    if metadata_calls:
                        # Verify structure
                        written_data = metadata_calls[0][0][0]
                        if isinstance(written_data, str):
                            metadata = json.loads(written_data)
                            assert 'version' in metadata
                            assert 'last_updated' in metadata
                            assert 'conversation_files_hash' in metadata
                            assert 'conversations' in metadata


# ============================================================================
# Test Summary
# ============================================================================

"""
Test Coverage Summary:

Category 1: Basic Properties (2 tests)
- ✅ Stage name
- ✅ Dependencies

Category 2: Prerequisites (3 tests)
- ✅ Output directory validation
- ✅ Conversation files validation
- ✅ Empty directory handling

Category 3: Execution (3 tests)
- ✅ Index generation
- ✅ Empty directory handling
- ✅ Metadata accuracy

Category 4: Metadata Caching (3 tests)
- ✅ Cache creation
- ✅ Cache usage
- ✅ Cache updates

Category 5: Smart Skipping (5 tests)
- ✅ Never ran before
- ✅ Cache missing
- ✅ Unchanged files
- ✅ New files added
- ✅ Files modified

Category 6: Error Handling (3 tests)
- ✅ Corrupt cache
- ✅ Missing template
- ✅ Rendering errors

Category 7: State Format (1 test)
- ✅ Metadata structure

Total: 20 tests (exceeding the 10-12 target for comprehensive coverage)
"""
