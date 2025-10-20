"""
Unit tests for AttachmentCopyingStage pipeline stage.

Following TDD principles: These tests are written BEFORE implementation.
They should fail initially, then pass once the stage is properly implemented.

Phase 2 Focus:
- Copy attachments from processing_dir to output_dir
- Preserve directory structure (Calls/, Voicemails/, etc.)
- Implement resumability for partial copies
- Track copied files for idempotency
- Handle errors gracefully (missing files, permission issues)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
import shutil

from core.pipeline.base import PipelineContext, StageResult
from core.pipeline.stages.attachment_copying import AttachmentCopyingStage


class TestAttachmentCopyingStageBasics:
    """Test basic stage properties and initialization."""

    def test_stage_has_correct_name(self):
        """Stage should be named 'attachment_copying'."""
        stage = AttachmentCopyingStage()
        assert stage.name == "attachment_copying"

    def test_stage_depends_on_attachment_mapping(self):
        """Stage should depend on attachment_mapping stage."""
        stage = AttachmentCopyingStage()
        assert stage.get_dependencies() == ["attachment_mapping"]

    def test_stage_validates_attachment_mapping_exists(self, tmp_path):
        """Stage should fail validation if attachment_mapping.json doesn't exist."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # No attachment_mapping.json exists
        assert stage.validate_prerequisites(context) is False

    def test_stage_validates_attachment_mapping_exists_passes(self, tmp_path):
        """Stage should pass validation if attachment_mapping.json exists."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create attachment_mapping.json
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        assert stage.validate_prerequisites(context) is True


class TestAttachmentCopyingStageExecution:
    """Test stage execution logic."""

    def test_execute_copies_attachments_to_output_dir(self, tmp_path):
        """Stage should copy attachments from processing_dir to output_dir."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source attachment
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        source_file = calls_dir / "photo.jpg"
        source_file.write_text("fake image data")

        # Create attachment mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(source_file)
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Should succeed
        assert result.success is True

        # Should copy file to output_dir/attachments/Calls/photo.jpg
        dest_file = output_dir / "attachments" / "Calls" / "photo.jpg"
        assert dest_file.exists()
        assert dest_file.read_text() == "fake image data"

    def test_execute_preserves_directory_structure(self, tmp_path):
        """Stage should preserve subdirectory structure when copying."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create files in different subdirectories
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        voicemails_dir = processing_dir / "Voicemails"
        voicemails_dir.mkdir()

        call_photo = calls_dir / "call.jpg"
        call_photo.write_text("call data")
        voicemail_mp3 = voicemails_dir / "vm.mp3"
        voicemail_mp3.write_text("audio data")

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 2},
            "mappings": {
                "call.jpg": {
                    "filename": "Calls/call.jpg",
                    "source_path": str(call_photo)
                },
                "vm.mp3": {
                    "filename": "Voicemails/vm.mp3",
                    "source_path": str(voicemail_mp3)
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        assert result.success is True

        # Check directory structure preserved
        assert (output_dir / "attachments" / "Calls" / "call.jpg").exists()
        assert (output_dir / "attachments" / "Voicemails" / "vm.mp3").exists()

    def test_execute_with_empty_mapping(self, tmp_path):
        """Stage should handle empty mapping gracefully."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Empty mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Should succeed (nothing to copy)
        assert result.success is True
        assert result.records_processed == 0

    def test_execute_returns_correct_metadata(self, tmp_path):
        """Stage result should include copy count and paths in metadata."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create 5 test files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        mappings = {}
        for i in range(5):
            file = calls_dir / f"photo{i}.jpg"
            file.write_text(f"data{i}")
            mappings[f"photo{i}.jpg"] = {
                "filename": f"Calls/photo{i}.jpg",
                "source_path": str(file)
            }

        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 5},
            "mappings": mappings
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        assert result.success is True
        assert result.records_processed == 5
        assert result.metadata['total_copied'] == 5
        assert result.metadata['total_skipped'] == 0
        assert 'output_dir' in result.metadata


class TestAttachmentCopyingStageResumability:
    """Test resumability for partial copies (critical feature)."""

    def test_skips_already_copied_files(self, tmp_path):
        """Stage should skip files that were already copied in a previous run."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source file
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        source_file = calls_dir / "photo.jpg"
        source_file.write_text("original data")

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(source_file)
                }
            }
        }))

        # Manually create destination file (simulating previous partial run)
        dest_file = output_dir / "attachments" / "Calls" / "photo.jpg"
        dest_file.parent.mkdir(parents=True)
        dest_file.write_text("already copied")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Should succeed
        assert result.success is True

        # Should skip the file (already exists)
        assert result.metadata['total_copied'] == 0
        assert result.metadata['total_skipped'] == 1

        # File should remain unchanged
        assert dest_file.read_text() == "already copied"

    def test_tracks_copied_files_in_state(self, tmp_path):
        """Stage should track which files were copied in pipeline state."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source file
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        source_file = calls_dir / "photo.jpg"
        source_file.write_text("data")

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(source_file)
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        assert result.success is True

        # Metadata should track copied files
        assert 'copied_files' in result.metadata
        assert "Calls/photo.jpg" in result.metadata['copied_files']

    def test_can_resume_after_partial_copy(self, tmp_path):
        """Stage should resume copying after interruption."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create 3 source files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        files = []
        mappings = {}
        for i in range(3):
            file = calls_dir / f"photo{i}.jpg"
            file.write_text(f"data{i}")
            files.append(file)
            mappings[f"photo{i}.jpg"] = {
                "filename": f"Calls/photo{i}.jpg",
                "source_path": str(file)
            }

        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 3},
            "mappings": mappings
        }))

        # Simulate partial copy (only first file copied)
        attachments_dir = output_dir / "attachments" / "Calls"
        attachments_dir.mkdir(parents=True)
        (attachments_dir / "photo0.jpg").write_text("data0")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        assert result.success is True

        # Should copy 2 new files, skip 1 existing
        assert result.metadata['total_copied'] == 2
        assert result.metadata['total_skipped'] == 1

        # All 3 files should exist
        assert (attachments_dir / "photo0.jpg").exists()
        assert (attachments_dir / "photo1.jpg").exists()
        assert (attachments_dir / "photo2.jpg").exists()


class TestAttachmentCopyingStageErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_missing_source_file(self, tmp_path):
        """Stage should handle missing source files gracefully."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping pointing to non-existent file
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "missing.jpg": {
                    "filename": "Calls/missing.jpg",
                    "source_path": str(processing_dir / "Calls" / "missing.jpg")
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Should still succeed (skip missing files)
        assert result.success is True
        assert result.metadata['total_errors'] == 1
        assert len(result.errors) == 1
        assert "missing.jpg" in result.errors[0]

    def test_handles_permission_errors(self, tmp_path):
        """Stage should handle permission errors gracefully."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source file
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        source_file = calls_dir / "photo.jpg"
        source_file.write_text("data")

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(source_file)
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock shutil.copy2 to raise PermissionError
        with patch('shutil.copy2') as mock_copy:
            mock_copy.side_effect = PermissionError("Permission denied")

            result = stage.execute(context)

            # Should record error but continue
            assert result.success is True
            assert result.metadata['total_errors'] == 1
            assert len(result.errors) == 1

    def test_handles_disk_full_error(self, tmp_path):
        """Stage should handle disk full errors gracefully."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source file
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        source_file = calls_dir / "photo.jpg"
        source_file.write_text("data")

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(source_file)
                }
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock shutil.copy2 to raise OSError (disk full)
        with patch('shutil.copy2') as mock_copy:
            mock_copy.side_effect = OSError("No space left on device")

            result = stage.execute(context)

            # Should record error
            assert result.success is True
            assert result.metadata['total_errors'] == 1


class TestAttachmentCopyingStageSmartSkipping:
    """Test smart can_skip() validation."""

    def test_cannot_skip_if_never_ran(self, tmp_path):
        """Stage should not skip if it has never run before."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Should not skip (never ran)
        assert stage.can_skip(context) is False

    def test_cannot_skip_if_attachments_dir_missing(self, tmp_path):
        """Stage should not skip if attachments directory doesn't exist."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(processing_dir / "Calls" / "photo.jpg")
                }
            }
        }))

        # Context says stage completed
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_copying", {
            'completed': True,
            'total_copied': 1
        })

        # But attachments dir doesn't exist
        # Should not skip (output missing)
        assert stage.can_skip(context) is False

    def test_can_skip_if_everything_valid(self, tmp_path):
        """Stage should skip if completed and all files copied."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 1},
            "mappings": {
                "photo.jpg": {
                    "filename": "Calls/photo.jpg",
                    "source_path": str(processing_dir / "Calls" / "photo.jpg")
                }
            }
        }))

        # Create attachments directory with file
        attachments_dir = output_dir / "attachments" / "Calls"
        attachments_dir.mkdir(parents=True)
        (attachments_dir / "photo.jpg").write_text("data")

        # Context says stage completed with same count
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_copying", {
            'completed': True,
            'total_copied': 1,
            'copied_files': ["Calls/photo.jpg"]
        })

        # Should skip (everything valid)
        assert stage.can_skip(context) is True

    def test_cannot_skip_if_file_count_changed(self, tmp_path):
        """Stage should not skip if mapping file count changed."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping with 2 files (changed from 1)
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 2},
            "mappings": {
                "photo1.jpg": {
                    "filename": "Calls/photo1.jpg",
                    "source_path": str(processing_dir / "Calls" / "photo1.jpg")
                },
                "photo2.jpg": {
                    "filename": "Calls/photo2.jpg",
                    "source_path": str(processing_dir / "Calls" / "photo2.jpg")
                }
            }
        }))

        # Create attachments directory
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(parents=True)

        # Context says stage completed with only 1 file
        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("attachment_copying", {
            'completed': True,
            'total_copied': 1,  # Was 1, now 2 in mapping!
            'copied_files': ["Calls/photo1.jpg"]
        })

        # Should not skip (file count changed)
        assert stage.can_skip(context) is False


class TestAttachmentCopyingStageOutputFormat:
    """Test metadata and state tracking format."""

    def test_metadata_has_correct_structure(self, tmp_path):
        """Stage result metadata should have all required fields."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Should have required metadata fields
        assert 'total_copied' in result.metadata
        assert 'total_skipped' in result.metadata
        assert 'total_errors' in result.metadata
        assert 'output_dir' in result.metadata
        assert 'copied_files' in result.metadata

    def test_copied_files_list_is_accurate(self, tmp_path):
        """Metadata should track exact list of copied files."""
        stage = AttachmentCopyingStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create source files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        mappings = {}
        for i in range(3):
            file = calls_dir / f"photo{i}.jpg"
            file.write_text(f"data{i}")
            mappings[f"photo{i}.jpg"] = {
                "filename": f"Calls/photo{i}.jpg",
                "source_path": str(file)
            }

        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 3},
            "mappings": mappings
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        result = stage.execute(context)

        # Copied files should match exactly
        assert len(result.metadata['copied_files']) == 3
        assert "Calls/photo0.jpg" in result.metadata['copied_files']
        assert "Calls/photo1.jpg" in result.metadata['copied_files']
        assert "Calls/photo2.jpg" in result.metadata['copied_files']
