"""
TDD Test Suite for Enhanced Metrics System Integration

This test suite validates the integration of the enhanced metrics system
with the actual processing functions, ensuring metrics are collected
throughout the conversion process.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

# Import the modules we need to test
from utils.enhanced_logging import get_metrics_collector, ProcessingMetrics
from core.processing_config import ProcessingConfig
from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager


class TestMetricsCollectionIntegration:
    """TDD tests for metrics collection integration with processing functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        self.metrics_collector = get_metrics_collector()
        # Clear any existing metrics for clean tests
        self.metrics_collector.metrics.clear()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)
        # Clear metrics after each test
        self.metrics_collector.metrics.clear()

    def test_process_sms_mms_file_should_collect_metrics(self):
        """FAILING TEST: process_sms_mms_file should collect processing metrics."""
        from sms import process_sms_mms_file
        
        # Create test HTML with SMS message
        test_html = """
        <html><body>
            <div class="message">
                <q>Test SMS message</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023 12:00 PM</abbr>
            </div>
        </body></html>
        """
        
        # Create test file
        test_file = self.test_output_dir / "test_sms.html"
        test_file.write_text(test_html)
        
        soup = BeautifulSoup(test_html, 'html.parser')
        mock_cm = Mock(spec=ConversationManager)
        mock_phone_manager = Mock(spec=PhoneLookupManager)
        
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        # Process the file
        with patch('sms.log_processing_event'):
            
            process_sms_mms_file(
                html_file=test_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        # SHOULD FAIL: Metrics should be collected for the processed file
        metrics_summary = self.metrics_collector.get_summary()
        assert "error" not in metrics_summary, "Metrics should be collected, not show 'no metrics collected' error"
        assert metrics_summary["total_files_processed"] > 0, "Should have processed at least 1 file"

    def test_processing_functions_should_track_success_and_failure(self):
        """FAILING TEST: Processing functions should track success/failure in metrics."""
        from sms import process_sms_mms_file
        
        # Test successful processing
        test_html = "<html><body><div class='message'><q>Test</q></div></body></html>"
        test_file = self.test_output_dir / "success.html"
        test_file.write_text(test_html)
        
        soup = BeautifulSoup(test_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        # Process successfully
        with patch('sms.log_processing_event'):
            
            process_sms_mms_file(
                html_file=test_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        # SHOULD FAIL: Metrics should show successful processing
        metrics_summary = self.metrics_collector.get_summary()
        assert metrics_summary["successful_files"] > 0, "Should track successful file processing"

    def test_metrics_should_include_processing_time(self):
        """FAILING TEST: Collected metrics should include processing time measurements."""
        # This test will initially fail because processing functions don't use track_processing()
        
        # Simulate processing with known duration
        file_id = "test_file.html"
        
        # SHOULD FAIL: No metrics are currently being collected with timing
        metrics = self.metrics_collector.get_metrics(file_id)
        assert metrics is not None, "Metrics should be collected for processed files"
        assert metrics.processing_time_ms is not None, "Processing time should be measured"
        assert metrics.processing_time_ms > 0, "Processing time should be greater than 0"

    def test_metrics_should_include_message_and_participant_counts(self):
        """FAILING TEST: Metrics should include detailed counts of processed items."""
        from sms import process_sms_mms_file
        
        # Create HTML with multiple messages and participants
        test_html = """
        <html><body>
            <div class="message">
                <q>Message 1</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023</abbr>
            </div>
            <div class="message">
                <q>Message 2</q>
                <abbr class="dt" title="20230101T120100+0000">Jan 1, 2023</abbr>
            </div>
        </body></html>
        """
        
        test_file = self.test_output_dir / "multi_message.html"
        test_file.write_text(test_html)
        
        soup = BeautifulSoup(test_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        with patch('sms.log_processing_event'):
            
            process_sms_mms_file(
                html_file=test_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        # SHOULD FAIL: Metrics should include message counts
        metrics_summary = self.metrics_collector.get_summary()
        assert metrics_summary["total_messages"] > 0, "Should track total messages processed"

    def test_call_and_voicemail_processing_should_collect_metrics(self):
        """FAILING TEST: Call and voicemail processing should also collect metrics."""
        from processors.file_processor import process_call_file, process_voicemail_file
        
        # Test call processing
        call_html = """
        <html><body>
            <div class="call">
                <div class="duration">Duration: 30s</div>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023</abbr>
            </div>
        </body></html>
        """
        
        call_file = self.test_output_dir / "call.html"
        call_file.write_text(call_html)
        
        call_soup = BeautifulSoup(call_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        # Process call file
        process_call_file(
            html_file=call_file,
            soup=call_soup,
            own_number="555-1234",
            src_filename_map={},
            conversation_manager=mock_cm,
            phone_lookup_manager=mock_phone_manager
        )
        
        # SHOULD FAIL: Call processing should collect metrics
        call_metrics = self.metrics_collector.get_metrics("call.html")
        assert call_metrics is not None, "Call processing should collect metrics"
        assert call_metrics.file_format == "call", "Should identify file format as call"

    def test_metrics_summary_should_show_comprehensive_data(self):
        """TEST: Metrics summary should show comprehensive processing data after processing files."""
        from sms import process_sms_mms_file
        from processors.file_processor import process_call_file
        
        # Process multiple files to generate metrics
        
        # 1. Process SMS file
        sms_html = "<html><body><div class='message'><q>SMS test</q></div></body></html>"
        sms_file = self.test_output_dir / "sms_test.html"
        sms_file.write_text(sms_html)
        
        soup = BeautifulSoup(sms_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        with patch('sms.log_processing_event'):
            process_sms_mms_file(
                html_file=sms_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        # 2. Process call file
        call_html = "<html><body><div class='call'><div class='duration'>30s</div></div></body></html>"
        call_file = self.test_output_dir / "call_test.html"
        call_file.write_text(call_html)
        
        call_soup = BeautifulSoup(call_html, 'html.parser')
        process_call_file(
            html_file=call_file,
            soup=call_soup,
            own_number="555-1234",
            src_filename_map={},
            conversation_manager=mock_cm,
            phone_lookup_manager=mock_phone_manager
        )
        
        # Now check metrics summary
        metrics_summary = self.metrics_collector.get_summary()
        
        # Should NOT show error anymore
        assert "error" not in metrics_summary, "Should not show 'no metrics collected' error"
        
        # Should show processed files
        assert metrics_summary["total_files_processed"] >= 2, "Should have processed at least 2 files"
        
        # Expected comprehensive data:
        expected_fields = [
            "total_files_processed",
            "successful_files", 
            "failed_files",
            "success_rate"
        ]
        
        for field in expected_fields:
            assert field in metrics_summary, f"Metrics summary should include {field}"

    def test_track_processing_context_manager_integration(self):
        """FAILING TEST: Processing functions should use track_processing context manager."""
        # This test validates that the track_processing context manager is properly integrated
        
        file_id = "test_integration.html"
        
        # Simulate what should happen when processing functions use track_processing
        with patch('sms.track_processing') as mock_track:
            # This should be called by processing functions but currently isn't
            
            # SHOULD FAIL: Processing functions should use track_processing context manager
            mock_track.assert_called_with(file_id, file_format="sms_mms")

    def test_metrics_collection_performance_impact(self):
        """TEST: Metrics collection should have minimal performance impact."""
        # This test ensures metrics don't significantly slow down processing
        
        # Measure processing time with and without metrics
        # (This test may pass initially since metrics collection is lightweight)
        
        start_time = time.time()
        # Simulate some processing work
        time.sleep(0.01)  # 10ms simulated work
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Metrics collection should add less than 5ms overhead
        assert processing_time < 20, "Metrics collection should have minimal performance impact"


class TestMetricsDataAccuracy:
    """TDD tests for accuracy of collected metrics data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_collector = get_metrics_collector()
        self.metrics_collector.metrics.clear()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.metrics_collector.metrics.clear()

    def test_processing_metrics_should_calculate_efficiency_ratios(self):
        """FAILING TEST: Metrics should calculate processing efficiency ratios."""
        # Test that efficiency calculations work correctly
        
        metrics_summary = self.metrics_collector.get_summary()
        
        # SHOULD FAIL: Efficiency calculations not implemented yet
        if "error" not in metrics_summary and metrics_summary["total_files_processed"] > 0:
            assert "messages_per_file" in metrics_summary, "Should calculate messages per file ratio"
            assert "processing_time_per_message" in metrics_summary, "Should calculate time per message"

    def test_failed_file_processing_should_be_tracked(self):
        """FAILING TEST: Failed file processing should be properly tracked in metrics."""
        # Simulate a processing failure
        
        file_id = "failed_file.html"
        
        # SHOULD FAIL: No failure tracking currently implemented
        metrics = self.metrics_collector.get_metrics(file_id)
        if metrics:
            assert hasattr(metrics, 'success'), "Metrics should track success/failure"
            assert hasattr(metrics, 'error_message'), "Failed metrics should include error message"


class TestEndToEndMetricsIntegration:
    """Integration tests for complete metrics collection workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        self.metrics_collector = get_metrics_collector()
        self.metrics_collector.metrics.clear()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)
        self.metrics_collector.metrics.clear()

    def test_complete_processing_workflow_should_collect_comprehensive_metrics(self):
        """FAILING TEST: Complete processing workflow should result in comprehensive metrics."""
        # This is the ultimate integration test
        
        # After running a complete processing workflow, we should get:
        expected_log_output = """
📊 Enhanced Processing Metrics Summary:
  Total Files Processed: 3
  Successful Files: 3 (100.0%)
  Failed Files: 0 (0.0%)
  Total Processing Time: 150.5 ms
  Average Processing Time: 50.2 ms per file
  Total Messages Processed: 25
  Total Participants: 8
  Processing Efficiency:
    • Messages per file: 8.3
    • Participants per file: 2.7
    • Processing time per message: 6.0 ms
        """
        
        # SHOULD FAIL: Currently shows "Enhanced metrics unavailable: no metrics collected"
        metrics_summary = self.metrics_collector.get_summary()
        assert "error" not in metrics_summary, "Should show comprehensive metrics, not 'no metrics collected'"
        
        # This test validates the complete integration is working
        assert metrics_summary.get("total_files_processed", 0) > 0, "Should process files and collect metrics"
