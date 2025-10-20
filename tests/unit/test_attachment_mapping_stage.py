"""
Unit tests for AttachmentMappingStage pipeline stage.

Following TDD principles: These tests are written BEFORE implementation.
They should fail initially, then pass once the stage is properly implemented.
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch

from core.pipeline.base import PipelineContext, StageResult
from core.pipeline.stages.attachment_mapping import AttachmentMappingStage


class TestAttachmentMappingStageBasics:
    """Test basic stage properties and initialization."""

    def test_stage_has_correct_name(self):
        """Stage should be named 'attachment_mapping'."""
        stage = AttachmentMappingStage()
        assert stage.name == "attachment_mapping"

    def test_stage_has_no_dependencies(self):
        """Stage should be able to run independently."""
        stage = AttachmentMappingStage()
        assert stage.get_dependencies() == []

    def test_stage_validates_processing_dir_exists(self, tmp_path):
        """Stage should fail validation if processing directory doesn't exist."""
        stage = AttachmentMappingStage()

        # Create context with non-existent directory
        missing_dir = tmp_path / "does_not_exist"
        context = PipelineContext(
            processing_dir=missing_dir,
            output_dir=tmp_path / "output"
        )

        # Should fail validation
        assert stage.validate_prerequisites(context) is False

    def test_stage_validates_processing_dir_exists_passes(self, tmp_path):
        """Stage should pass validation if processing directory exists."""
        stage = AttachmentMappingStage()

        # Create actual directory
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=tmp_path / "output"
        )

        # Should pass validation
        assert stage.validate_prerequisites(context) is True


class TestAttachmentMappingStageExecution:
    """Test stage execution logic."""

    def test_execute_creates_output_file(self, tmp_path):
        """Stage should create attachment_mapping.json in output directory."""
        stage = AttachmentMappingStage()

        # Setup directories
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock the actual mapping function to avoid needing real files
        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.return_value = {
                "img/photo.jpg": ("photo.jpg", processing_dir / "photo.jpg")
            }

            result = stage.execute(context)

            # Should succeed
            assert result.success is True

            # Should create output file
            output_file = output_dir / "attachment_mapping.json"
            assert output_file.exists()

    def test_execute_with_empty_directory(self, tmp_path):
        """Stage should handle empty directory gracefully (no attachments)."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock empty mapping
        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.return_value = {}

            result = stage.execute(context)

            # Should still succeed (just with 0 mappings)
            assert result.success is True
            assert result.records_processed == 0

    def test_execute_returns_correct_metadata(self, tmp_path):
        """Stage result should include mapping count in metadata."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.return_value = {
                f"img/photo{i}.jpg": (f"photo{i}.jpg", processing_dir / f"photo{i}.jpg")
                for i in range(100)
            }

            result = stage.execute(context)

            assert result.success is True
            assert result.records_processed == 100
            assert result.metadata['total_mappings'] == 100
            assert 'directory_hash' in result.metadata


class TestAttachmentMappingStageOutputFormat:
    """Test output file format and content."""

    def test_output_json_has_correct_structure(self, tmp_path):
        """Output JSON should have metadata and mappings sections."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.return_value = {
                "img/photo.jpg": ("photo.jpg", processing_dir / "photo.jpg")
            }

            stage.execute(context)

            # Load and validate JSON
            output_file = output_dir / "attachment_mapping.json"
            with open(output_file) as f:
                data = json.load(f)

            # Should have required sections
            assert "metadata" in data
            assert "mappings" in data

            # Metadata should have required fields
            assert "created_at" in data["metadata"]
            assert "total_mappings" in data["metadata"]
            assert "processing_dir" in data["metadata"]
            assert "directory_hash" in data["metadata"]
            assert "file_count" in data["metadata"]

    def test_paths_are_serialized_as_strings(self, tmp_path):
        """Path objects should be converted to strings in JSON."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        test_path = processing_dir / "photo.jpg"

        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.return_value = {
                "img/photo.jpg": ("photo.jpg", test_path)
            }

            stage.execute(context)

            output_file = output_dir / "attachment_mapping.json"
            with open(output_file) as f:
                data = json.load(f)

            # Path should be string, not Path object
            mapping = data["mappings"]["img/photo.jpg"]
            assert isinstance(mapping["source_path"], str)
            assert mapping["source_path"] == str(test_path)


class TestAttachmentMappingStageSmartSkipping:
    """Test smart can_skip() validation (Option A implementation)."""

    def test_cannot_skip_if_never_ran(self, tmp_path):
        """Stage should not skip if it has never run before."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Context with no completion data
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Should not skip (never ran)
        assert stage.can_skip(context) is False

    def test_cannot_skip_if_output_file_missing(self, tmp_path):
        """Stage should not skip if output file doesn't exist."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Context that says stage completed
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_mapping", {
            'completed': True,
            'directory_hash': 'abc123',
            'file_count': 100
        })

        # But output file doesn't exist
        # Should not skip (output missing)
        assert stage.can_skip(context) is False

    def test_cannot_skip_if_directory_changed(self, tmp_path):
        """Stage should not skip if directory hash changed (files added/removed)."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create output file
        output_file = output_dir / "attachment_mapping.json"
        output_file.write_text(json.dumps({
            "metadata": {"total_mappings": 100},
            "mappings": {}
        }))

        # Context with OLD hash
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_mapping", {
            'completed': True,
            'directory_hash': 'old_hash_123',
            'file_count': 100
        })

        # Directory has changed (new files added)
        # Mock compute_directory_hash to return different hash
        with patch('core.pipeline.stages.attachment_mapping.compute_directory_hash') as mock_hash:
            mock_hash.return_value = 'new_hash_456'  # Different!

            # Should not skip (directory changed)
            assert stage.can_skip(context) is False

    def test_can_skip_if_everything_valid(self, tmp_path):
        """Stage should skip if completed, output exists, and directory unchanged."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create output file
        output_file = output_dir / "attachment_mapping.json"
        output_file.write_text(json.dumps({
            "metadata": {"total_mappings": 100},
            "mappings": {}
        }))

        current_hash = "abc123def456"

        # Context with matching hash
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_mapping", {
            'completed': True,
            'directory_hash': current_hash,
            'file_count': 100
        })

        # Mock hash to return same value AND count
        with patch('core.pipeline.stages.attachment_mapping.compute_directory_hash') as mock_hash:
            with patch('core.pipeline.stages.attachment_mapping.count_files_in_directory') as mock_count:
                mock_hash.return_value = current_hash  # Same!
                mock_count.return_value = 100  # Same as previous

                # Should skip (everything valid)
                assert stage.can_skip(context) is True

    def test_cannot_skip_if_file_count_changed_significantly(self, tmp_path):
        """Stage should not skip if file count changed by >10%."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create output file
        output_file = output_dir / "attachment_mapping.json"
        output_file.write_text(json.dumps({
            "metadata": {"total_mappings": 100},
            "mappings": {}
        }))

        current_hash = "abc123"

        # Context with old file count
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_mapping", {
            'completed': True,
            'directory_hash': current_hash,
            'file_count': 100  # Was 100
        })

        # Mock current count as 200 (100% increase)
        with patch('core.pipeline.stages.attachment_mapping.compute_directory_hash') as mock_hash:
            with patch('core.pipeline.stages.attachment_mapping.count_files_in_directory') as mock_count:
                mock_hash.return_value = current_hash
                mock_count.return_value = 200  # Doubled!

                # Should not skip (file count changed too much)
                assert stage.can_skip(context) is False


class TestAttachmentMappingStageErrorHandling:
    """Test error handling and edge cases."""

    def test_execute_handles_mapping_failure(self, tmp_path):
        """Stage should return failure result if mapping function raises exception."""
        stage = AttachmentMappingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock mapping to raise exception
        with patch('core.performance_optimizations.build_attachment_mapping_optimized') as mock_build:
            mock_build.side_effect = RuntimeError("Mapping failed!")

            result = stage.execute(context)

            # Should return failure
            assert result.success is False
            assert len(result.errors) > 0
            assert "Mapping failed" in result.errors[0]
