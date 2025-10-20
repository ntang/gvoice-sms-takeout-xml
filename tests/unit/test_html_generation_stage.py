"""
Unit tests for HtmlGenerationStage pipeline stage (Phase 3a).

Following TDD principles: These tests are written BEFORE implementation.
They should fail initially, then pass once the stage is properly implemented.

Phase 3a Focus:
- File-level resumability (track which files processed)
- Skip already-processed files on resume
- Finalize all conversations at end (same as current behavior)
- Preserve statistics across resumptions
- No conversation-level granularity (simpler approach)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from core.pipeline.base import PipelineContext, StageResult
from core.pipeline.stages.html_generation import HtmlGenerationStage


class TestHtmlGenerationStageBasics:
    """Test basic stage properties and initialization."""

    def test_stage_has_correct_name(self):
        """Stage should be named 'html_generation'."""
        stage = HtmlGenerationStage()
        assert stage.name == "html_generation"

    def test_stage_depends_on_attachment_stages(self):
        """Stage should depend on attachment_mapping and attachment_copying."""
        stage = HtmlGenerationStage()
        deps = stage.get_dependencies()
        assert "attachment_mapping" in deps
        assert "attachment_copying" in deps

    def test_stage_validates_attachment_mapping_exists(self, tmp_path):
        """Stage should fail validation if attachment_mapping.json doesn't exist."""
        stage = HtmlGenerationStage()

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

    def test_stage_validates_attachments_directory_exists(self, tmp_path):
        """Stage should fail validation if attachments directory doesn't exist."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create mapping but no attachments dir
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        assert stage.validate_prerequisites(context) is False

    def test_stage_validates_prerequisites_passes(self, tmp_path):
        """Stage should pass validation if all prerequisites met."""
        stage = HtmlGenerationStage()

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

        # Create attachments dir
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        assert stage.validate_prerequisites(context) is True


class TestFileProcessingStateTracking:
    """Test file-level state tracking for resumability."""

    def test_tracks_processed_files(self, tmp_path):
        """Stage should track which files have been processed."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup prerequisites
        self._setup_prerequisites(processing_dir, output_dir)

        # Create test HTML files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "file1.html").write_text("<html></html>")
        (calls_dir / "file2.html").write_text("<html></html>")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock the processing function
        with patch('sms.process_html_files_param') as mock_process:
            mock_process.return_value = {
                'num_sms': 10,
                'num_img': 2,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            }

            with patch('core.conversation_manager.ConversationManager'):
                result = stage.execute(context)

        # Should track processed files in state
        state_file = output_dir / "html_processing_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            state = json.load(f)

        assert 'files_processed' in state
        assert len(state['files_processed']) == 2

    def test_skips_already_processed_files(self, tmp_path):
        """Stage should skip files that were already processed."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        self._setup_prerequisites(processing_dir, output_dir)

        # Create test files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        file1 = calls_dir / "file1.html"
        file2 = calls_dir / "file2.html"
        file1.write_text("<html></html>")
        file2.write_text("<html></html>")

        # Create state showing file1 already processed
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            'files_processed': [str(file1)],
            'stats': {
                'num_sms': 5,
                'num_img': 1,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock processing
        with patch('sms.process_html_files_param') as mock_process:
            mock_process.return_value = {
                'num_sms': 3,
                'num_img': 1,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            }

            with patch('core.conversation_manager.ConversationManager'):
                result = stage.execute(context)

                # Should only process file2 (file1 already processed)
                # Verify by checking call arguments
                call_args = mock_process.call_args
                limited_files = call_args.kwargs.get('limited_files')

                # Should only have file2 in limited files
                assert limited_files is not None
                assert len(limited_files) == 1
                assert str(file2) in [str(f) for f in limited_files]

    def test_accumulates_statistics_across_runs(self, tmp_path):
        """Stage should accumulate stats from previous runs."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        self._setup_prerequisites(processing_dir, output_dir)

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "file1.html").write_text("<html></html>")

        # Previous run stats
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            'files_processed': [],
            'stats': {
                'num_sms': 100,
                'num_img': 10,
                'num_vcf': 2,
                'num_calls': 5,
                'num_voicemails': 3
            }
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('sms.process_html_files_param') as mock_process:
            # New run adds more stats
            mock_process.return_value = {
                'num_sms': 50,
                'num_img': 5,
                'num_vcf': 1,
                'num_calls': 2,
                'num_voicemails': 1
            }

            with patch('core.conversation_manager.ConversationManager'):
                result = stage.execute(context)

        # Should accumulate stats
        assert result.metadata['total_sms'] == 150  # 100 + 50
        assert result.metadata['total_img'] == 15   # 10 + 5
        assert result.metadata['total_vcf'] == 3    # 2 + 1

    def _setup_prerequisites(self, processing_dir, output_dir):
        """Helper to setup required files."""
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir()


class TestHtmlGenerationStageExecution:
    """Test stage execution logic."""

    def test_execute_processes_html_files(self, tmp_path):
        """Stage should process HTML files and generate conversations."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup
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
        (output_dir / "attachments").mkdir()

        # Create HTML files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "test.html").write_text("<html><body>Test SMS</body></html>")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock processing and conversation manager
        with patch('sms.process_html_files_param') as mock_process:
            with patch('core.conversation_manager.ConversationManager') as MockConvMgr:
                mock_conv_mgr = MockConvMgr.return_value

                mock_process.return_value = {
                    'num_sms': 5,
                    'num_img': 1,
                    'num_vcf': 0,
                    'num_calls': 0,
                    'num_voicemails': 0
                }

                result = stage.execute(context)

                # Should succeed
                assert result.success is True

                # Should call finalize_conversation_files
                mock_conv_mgr.finalize_conversation_files.assert_called_once()

                # Should call generate_index_html
                mock_conv_mgr.generate_index_html.assert_called_once()

    def test_execute_with_empty_directory(self, tmp_path):
        """Stage should handle empty Calls directory gracefully."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup prerequisites
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        # Create empty Calls dir
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('core.conversation_manager.ConversationManager'):
            result = stage.execute(context)

            # Should succeed with 0 files processed
            assert result.success is True
            assert result.records_processed == 0

    def test_execute_returns_correct_metadata(self, tmp_path):
        """Stage result should include processing stats in metadata."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "test.html").write_text("<html></html>")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('sms.process_html_files_param') as mock_process:
            mock_process.return_value = {
                'num_sms': 100,
                'num_img': 25,
                'num_vcf': 5,
                'num_calls': 10,
                'num_voicemails': 3
            }

            with patch('core.conversation_manager.ConversationManager'):
                result = stage.execute(context)

        # Should have statistics in metadata
        assert result.metadata['total_sms'] == 100
        assert result.metadata['total_img'] == 25
        assert result.metadata['total_vcf'] == 5
        assert result.metadata['total_calls'] == 10
        assert result.metadata['total_voicemails'] == 3
        assert 'files_processed' in result.metadata
        assert 'files_skipped' in result.metadata


class TestHtmlGenerationStageSmartSkipping:
    """Test smart can_skip() validation."""

    def test_cannot_skip_if_never_ran(self, tmp_path):
        """Stage should not skip if it has never run before."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # No state file exists
        assert stage.can_skip(context) is False

    def test_cannot_skip_if_state_incomplete(self, tmp_path):
        """Stage should not skip if not all files processed."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Create HTML files
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "file1.html").write_text("<html></html>")
        (calls_dir / "file2.html").write_text("<html></html>")

        # State shows only 1 file processed
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            'files_processed': [str(calls_dir / "file1.html")],
            'stats': {'num_sms': 5}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Should not skip (file2 not processed)
        assert stage.can_skip(context) is False

    def test_can_skip_if_all_files_processed(self, tmp_path):
        """Stage should skip if all files already processed."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        file1 = calls_dir / "file1.html"
        file2 = calls_dir / "file2.html"
        file1.write_text("<html></html>")
        file2.write_text("<html></html>")

        # State shows all files processed
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            'files_processed': [str(file1), str(file2)],
            'stats': {'num_sms': 10}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )
        context.set_stage_data("html_generation", {'completed': True})

        # Should skip (all files processed)
        assert stage.can_skip(context) is True

    def test_cannot_skip_if_new_files_added(self, tmp_path):
        """Stage should not skip if new HTML files were added."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        file1 = calls_dir / "file1.html"
        file2 = calls_dir / "file2.html"
        file3 = calls_dir / "file3.html"  # New file!
        file1.write_text("<html></html>")
        file2.write_text("<html></html>")
        file3.write_text("<html></html>")

        # State shows only file1 and file2
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            'files_processed': [str(file1), str(file2)],
            'stats': {'num_sms': 10}
        }))

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Should not skip (file3 is new)
        assert stage.can_skip(context) is False


class TestHtmlGenerationStageErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_missing_calls_directory(self, tmp_path):
        """Stage should handle missing Calls directory gracefully."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup prerequisites
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        # No Calls directory created

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('core.conversation_manager.ConversationManager'):
            result = stage.execute(context)

            # Should handle gracefully
            assert result.success is True
            assert result.records_processed == 0

    def test_handles_processing_errors(self, tmp_path):
        """Stage should handle processing errors gracefully."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "test.html").write_text("<html></html>")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Mock processing to raise error
        with patch('sms.process_html_files_param') as mock_process:
            mock_process.side_effect = RuntimeError("Processing failed!")

            with patch('core.conversation_manager.ConversationManager'):
                result = stage.execute(context)

                # Should return failure
                assert result.success is False
                assert len(result.errors) > 0

    def test_handles_corrupt_state_file(self, tmp_path):
        """Stage should handle corrupt state file gracefully."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Corrupt state file
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text("{ invalid json }")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        # Setup prerequisites
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        with patch('core.conversation_manager.ConversationManager'):
            result = stage.execute(context)

            # Should handle gracefully and start fresh
            assert result.success is True


class TestStateFileFormat:
    """Test state file format and persistence."""

    def test_state_file_has_correct_structure(self, tmp_path):
        """State file should have correct JSON structure."""
        stage = HtmlGenerationStage()

        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()
        output_dir = processing_dir / "conversations"
        output_dir.mkdir()

        # Setup
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"total_mappings": 0},
            "mappings": {}
        }))
        (output_dir / "attachments").mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "test.html").write_text("<html></html>")

        context = PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

        with patch('sms.process_html_files_param') as mock_process:
            mock_process.return_value = {'num_sms': 5, 'num_img': 1, 'num_vcf': 0, 'num_calls': 0, 'num_voicemails': 0}

            with patch('core.conversation_manager.ConversationManager'):
                stage.execute(context)

        # Verify state file structure
        state_file = output_dir / "html_processing_state.json"
        with open(state_file) as f:
            state = json.load(f)

        assert 'files_processed' in state
        assert 'stats' in state
        assert isinstance(state['files_processed'], list)
        assert isinstance(state['stats'], dict)
        assert 'num_sms' in state['stats']
