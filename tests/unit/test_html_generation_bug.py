"""
Unit test to reproduce and verify fix for the undefined variable bug.

Bug: html_generation.py line 204 references `previous_state` which doesn't exist.
The variable should be `state`.

Test scenario: No Calls directory exists in processing_dir.
Expected behavior (before fix): NameError
Expected behavior (after fix): Success with preserved conversations
"""

import json
import pytest
from pathlib import Path
from core.pipeline.stages.html_generation import HtmlGenerationStage
from core.pipeline.base import PipelineContext


class TestHtmlGenerationMissingCallsDir:
    """Test HTML generation when Calls directory is missing."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        processing_dir = tmp_path / "processing"
        output_dir = tmp_path / "output"
        processing_dir.mkdir()
        output_dir.mkdir()
        
        # Note: We deliberately DO NOT create Calls/ directory
        # This triggers the bug on line 197-205
        
        return processing_dir, output_dir

    @pytest.fixture
    def context(self, temp_dirs):
        """Create pipeline context."""
        processing_dir, output_dir = temp_dirs
        
        # Create required prerequisite files
        # 1. attachment_mapping.json (required by validate_prerequisites)
        mapping_file = output_dir / "attachment_mapping.json"
        mapping_file.write_text(json.dumps({
            "metadata": {"version": "1.0"},
            "mappings": {}
        }))
        
        # 2. attachments directory (required by validate_prerequisites)
        (output_dir / "attachments").mkdir()
        
        # 3. Create a state file with existing data to preserve
        state_file = output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            "files_processed": ["/some/old/file.html"],
            "stats": {
                "num_sms": 100,
                "num_img": 10,
                "num_vcf": 1,
                "num_calls": 5,
                "num_voicemails": 2
            },
            "conversations": {
                "Alice": {
                    "sms_count": 50,
                    "call_count": 3,
                    "voicemail_count": 1,
                    "attachment_count": 5,
                    "latest_message_timestamp": "2024-10-18T19:04:55Z",
                    "file_path": "Alice.html"
                },
                "Bob": {
                    "sms_count": 50,
                    "call_count": 2,
                    "voicemail_count": 1,
                    "attachment_count": 5,
                    "latest_message_timestamp": "2024-10-19T10:30:00Z",
                    "file_path": "Bob.html"
                }
            }
        }))
        
        return PipelineContext(
            processing_dir=processing_dir,
            output_dir=output_dir
        )

    @pytest.fixture
    def stage(self):
        """Create HTML generation stage."""
        return HtmlGenerationStage()

    def test_missing_calls_dir_preserves_conversations(self, stage, context):
        """
        Test that when Calls directory is missing, the stage:
        1. Doesn't crash with NameError (the bug)
        2. Preserves existing conversation data from state file
        3. Returns success with zero records processed
        
        BUG: Line 204 uses undefined `previous_state` variable.
        FIX: Should use `state` variable instead.
        """
        # Execute stage - this should trigger the bug path (line 197-220)
        result = stage.execute(context)
        
        # Should succeed (not crash with NameError)
        assert result.success is True
        assert result.records_processed == 0
        
        # Verify state file was saved correctly
        state_file = context.output_dir / "html_processing_state.json"
        assert state_file.exists()
        
        # Load and verify state contents
        with open(state_file) as f:
            saved_state = json.load(f)
        
        # Should preserve conversations from original state
        assert "conversations" in saved_state
        assert "Alice" in saved_state["conversations"]
        assert "Bob" in saved_state["conversations"]
        assert saved_state["conversations"]["Alice"]["sms_count"] == 50
        assert saved_state["conversations"]["Bob"]["call_count"] == 2
        
        # Should preserve stats
        assert saved_state["stats"]["num_sms"] == 100
        assert saved_state["stats"]["num_calls"] == 5

    def test_missing_calls_dir_empty_state(self, stage, context):
        """
        Test missing Calls directory with empty initial state.
        Should handle gracefully even with no prior conversations.
        """
        # Overwrite state file with minimal data (no conversations field)
        state_file = context.output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps({
            "files_processed": [],
            "stats": {
                "num_sms": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0
            }
            # Note: No "conversations" field
        }))
        
        # Execute stage
        result = stage.execute(context)
        
        # Should succeed
        assert result.success is True
        
        # Should save empty conversations dict
        with open(state_file) as f:
            saved_state = json.load(f)
        
        assert "conversations" in saved_state
        assert saved_state["conversations"] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

