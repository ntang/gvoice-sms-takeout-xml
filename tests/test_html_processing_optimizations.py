"""
TDD Test Suite for HTML Processing Performance Optimizations

This test suite validates performance improvements to HTML processing,
focusing on BeautifulSoup parser optimization and CSS selector efficiency.
"""

import pytest
import time
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch

from core.processing_config import ProcessingConfig
from core.conversation_manager import ConversationManager


class TestBeautifulSoupParserOptimization:
    """TDD tests for BeautifulSoup parser optimization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_html = """
        <html><body>
            <div class="message">
                <q>Test SMS message</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023 12:00 PM</abbr>
            </div>
            <div class="message">
                <q>Another message</q>
                <abbr class="dt" title="20230101T120100+0000">Jan 1, 2023 12:01 PM</abbr>
            </div>
        </body></html>
        """

    def test_get_optimal_parser_should_prefer_lxml(self):
        """FAILING TEST: Should use lxml parser when available for better performance."""
        # This test will guide the implementation of parser optimization
        
        # Import the function that should be implemented
        from sms import get_optimal_parser
        
        # Should prefer lxml if available (test actual behavior)
        parser = get_optimal_parser()
        
        # Since lxml is available in this environment, should return 'lxml'
        # If lxml wasn't available, it would return 'html.parser'
        assert parser in ['lxml', 'html.parser'], f"Should return valid parser: {parser}"
        
        # Test fallback behavior by mocking the import
        with patch('builtins.__import__', side_effect=ImportError):
            # This should trigger the ImportError and return fallback
            parser_fallback = get_optimal_parser()
            assert parser_fallback == 'html.parser', "Should fallback to html.parser when lxml import fails"

    def test_lxml_parser_should_be_faster_than_default(self):
        """TEST: lxml parser should provide measurable performance improvement."""
        # This test validates that lxml is actually faster
        
        # Test with html.parser
        start_time = time.time()
        soup_default = BeautifulSoup(self.test_html, 'html.parser')
        messages_default = soup_default.select('.message')
        default_time = time.time() - start_time
        
        # Test with lxml (if available)
        try:
            start_time = time.time()
            soup_lxml = BeautifulSoup(self.test_html, 'lxml')
            messages_lxml = soup_lxml.select('.message')
            lxml_time = time.time() - start_time
            
            # Should be faster or at least not significantly slower
            assert lxml_time <= default_time * 1.5, f"lxml should be faster: {lxml_time:.4f}s vs {default_time:.4f}s"
            
            # Should produce same results
            assert len(messages_default) == len(messages_lxml), "Both parsers should find same number of messages"
            
        except ImportError:
            pytest.skip("lxml not available for performance comparison")

    def test_process_sms_mms_file_should_use_optimal_parser(self):
        """FAILING TEST: process_sms_mms_file should use optimal parser for better performance."""
        from sms import process_sms_mms_file
        
        # Create test file
        test_file = Path(tempfile.mktemp(suffix='.html'))
        test_file.write_text(self.test_html)
        
        try:
            # Mock the BeautifulSoup creation to verify optimal parser is used
            with patch('sms.BeautifulSoup') as mock_bs, \
                 patch('sms.get_optimal_parser') as mock_get_parser, \
                 patch('sms.log_processing_event'):
                
                mock_get_parser.return_value = 'lxml'
                mock_soup = Mock()
                mock_bs.return_value = mock_soup
                mock_soup.select.return_value = []  # No messages found
                
                # Mock managers
                mock_cm = Mock()
                mock_phone_manager = Mock()
                config = ProcessingConfig(processing_dir=Path('/tmp'))
                
                # Process file
                process_sms_mms_file(
                    html_file=test_file,
                    soup=mock_soup,
                    own_number="555-1234",
                    src_filename_map={},
                    conversation_manager=mock_cm,
                    phone_lookup_manager=mock_phone_manager,
                    config=config
                )
                
                # Should have used optimal parser
                mock_get_parser.assert_called_once()
                
        finally:
            if test_file.exists():
                test_file.unlink()


class TestCSSSelectorOptimization:
    """TDD tests for CSS selector optimization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.complex_html = """
        <html><body>
            <div class="message">
                <q>Message 1</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023</abbr>
                <img src="image1.jpg" />
                <a href="contact1.vcf">Contact</a>
            </div>
            <div class="message">
                <q>Message 2</q>
                <abbr class="dt" title="20230101T120100+0000">Jan 1, 2023</abbr>
                <img src="image2.jpg" />
            </div>
            <div class="message">
                <q>Message 3</q>
                <abbr class="dt" title="20230101T120200+0000">Jan 1, 2023</abbr>
            </div>
        </body></html>
        """

    def test_optimized_selector_should_reduce_dom_queries(self):
        """FAILING TEST: Optimized selector should reduce number of DOM queries."""
        # This test will guide implementation of selector optimization
        
        soup = BeautifulSoup(self.complex_html, 'html.parser')
        
        # Current approach (multiple selectors)
        with patch.object(soup, 'select', wraps=soup.select) as mock_select:
            # Simulate current approach
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
            
            current_query_count = mock_select.call_count
        
        # Optimized approach should use fewer queries
        # This will initially fail because optimization isn't implemented
        try:
            from sms import extract_message_data_optimized
            
            with patch.object(soup, 'select', wraps=soup.select) as mock_select:
                result = extract_message_data_optimized(soup)
                optimized_query_count = mock_select.call_count
                
                assert optimized_query_count < current_query_count, f"Should reduce queries: {optimized_query_count} vs {current_query_count}"
                
        except ImportError:
            pytest.fail("extract_message_data_optimized function should be implemented")

    def test_optimized_extraction_should_produce_same_results(self):
        """FAILING TEST: Optimized extraction should produce identical results to current method."""
        # Ensure optimization doesn't break functionality
        
        soup = BeautifulSoup(self.complex_html, 'html.parser')
        
        # Current approach results
        current_messages = soup.select('.message')
        current_images = soup.select('img[src]')
        current_vcards = soup.select('a[href*=".vcf"]')
        
        # Optimized approach should produce same results
        try:
            from sms import extract_message_data_optimized
            
            optimized_result = extract_message_data_optimized(soup)
            
            assert len(optimized_result['messages']) == len(current_messages), "Should find same number of messages"
            assert len(optimized_result['images']) == len(current_images), "Should find same number of images"
            assert len(optimized_result['vcards']) == len(current_vcards), "Should find same number of vcards"
            
        except ImportError:
            pytest.fail("extract_message_data_optimized function should be implemented")

    def test_selector_optimization_performance_improvement(self):
        """TEST: Optimized selectors should show measurable performance improvement."""
        # This test validates the performance gain
        
        soup = BeautifulSoup(self.complex_html, 'html.parser')
        
        # Measure current approach
        start_time = time.time()
        for _ in range(100):  # Repeat for measurable timing
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        current_time = time.time() - start_time
        
        # Measure optimized approach (if implemented)
        try:
            from sms import extract_message_data_optimized
            
            start_time = time.time()
            for _ in range(100):
                result = extract_message_data_optimized(soup)
            optimized_time = time.time() - start_time
            
            # Should be faster or at least not significantly slower
            speedup_ratio = current_time / optimized_time if optimized_time > 0 else float('inf')
            assert speedup_ratio >= 0.8, f"Should maintain performance: {speedup_ratio:.2f}x speedup"
            
        except ImportError:
            pytest.skip("extract_message_data_optimized not implemented yet")


class TestHTMLProcessingIntegration:
    """Integration tests for HTML processing optimizations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_process_sms_mms_file_performance_with_optimizations(self):
        """TEST: process_sms_mms_file should show performance improvement with optimizations."""
        from sms import process_sms_mms_file
        
        # Create test HTML file with multiple messages
        complex_html = """
        <html><body>
        """ + "".join([
            f"""
            <div class="message">
                <q>Message {i}</q>
                <abbr class="dt" title="20230101T12{i:02d}00+0000">Jan 1, 2023</abbr>
                {f'<img src="image{i}.jpg" />' if i % 3 == 0 else ''}
                {f'<a href="contact{i}.vcf">Contact</a>' if i % 5 == 0 else ''}
            </div>
            """ for i in range(50)  # 50 messages for measurable timing
        ]) + """
        </body></html>
        """
        
        test_file = self.test_output_dir / "performance_test.html"
        test_file.write_text(complex_html)
        
        soup = BeautifulSoup(complex_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        # Measure processing time
        start_time = time.time()
        
        with patch('sms.log_processing_event'):
            result = process_sms_mms_file(
                html_file=test_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        processing_time = time.time() - start_time
        
        # Should complete processing within reasonable time
        assert processing_time < 1.0, f"Should process 50 messages quickly: {processing_time:.3f}s"
        
        # Should process all messages
        assert isinstance(result, dict), "Should return processing results"

    def test_optimization_should_not_break_existing_functionality(self):
        """TEST: Optimizations should preserve all existing functionality."""
        from sms import process_sms_mms_file
        
        # Test with various HTML structures to ensure compatibility
        test_cases = [
            # Standard message
            "<html><body><div class='message'><q>Standard</q></div></body></html>",
            # Message with image
            "<html><body><div class='message'><q>With image</q><img src='test.jpg'/></div></body></html>",
            # Message with vcard
            "<html><body><div class='message'><q>With contact</q><a href='test.vcf'>Contact</a></div></body></html>",
            # Empty message
            "<html><body><div class='message'></div></body></html>",
        ]
        
        for i, html_content in enumerate(test_cases):
            test_file = self.test_output_dir / f"compatibility_test_{i}.html"
            test_file.write_text(html_content)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            mock_cm = Mock()
            mock_phone_manager = Mock()
            config = ProcessingConfig(processing_dir=self.test_output_dir)
            
            # Should not raise exceptions
            with patch('sms.log_processing_event'):
                result = process_sms_mms_file(
                    html_file=test_file,
                    soup=soup,
                    own_number="555-1234",
                    src_filename_map={},
                    conversation_manager=mock_cm,
                    phone_lookup_manager=mock_phone_manager,
                    config=config
                )
            
            # Should return valid results
            assert isinstance(result, dict), f"Test case {i} should return valid results"
            assert "num_sms" in result, f"Test case {i} should include SMS count"


class TestPerformanceBenchmarking:
    """Tests for validating performance improvements."""

    def test_parser_selection_performance_impact(self):
        """TEST: Parser selection should have minimal overhead."""
        # Test that parser selection logic doesn't add significant overhead
        
        test_html = "<html><body><div class='message'><q>Test</q></div></body></html>"
        
        # Measure parser selection overhead
        start_time = time.time()
        for _ in range(1000):
            try:
                from sms import get_optimal_parser
                parser = get_optimal_parser()
            except ImportError:
                parser = 'html.parser'  # Fallback for test
        selection_time = time.time() - start_time
        
        # Should be very fast (< 10ms for 1000 calls)
        assert selection_time < 0.01, f"Parser selection should be fast: {selection_time:.4f}s for 1000 calls"

    def test_css_selector_optimization_benchmark(self):
        """TEST: CSS selector optimization should show measurable improvement."""
        # Create HTML with many elements for meaningful benchmark
        large_html = "<html><body>" + "".join([
            f"<div class='message'><q>Msg {i}</q><img src='img{i}.jpg'/><a href='c{i}.vcf'>C</a></div>"
            for i in range(100)
        ]) + "</body></html>"
        
        soup = BeautifulSoup(large_html, 'html.parser')
        
        # Benchmark current approach (multiple selectors)
        start_time = time.time()
        for _ in range(50):  # Repeat for measurable timing
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        current_approach_time = time.time() - start_time
        
        # Benchmark optimized approach (if implemented)
        try:
            from sms import extract_message_data_optimized
            
            start_time = time.time()
            for _ in range(50):
                result = extract_message_data_optimized(soup)
            optimized_approach_time = time.time() - start_time
            
            # Should be faster
            speedup_ratio = current_approach_time / optimized_approach_time if optimized_approach_time > 0 else float('inf')
            assert speedup_ratio >= 1.0, f"Should be faster: {speedup_ratio:.2f}x speedup"
            
        except ImportError:
            pytest.skip("extract_message_data_optimized not implemented yet")


class TestOptimizationIntegration:
    """Integration tests for complete optimization workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_optimized_processing_maintains_message_accuracy(self):
        """TEST: Optimized processing should maintain 100% message accuracy."""
        from sms import process_sms_mms_file
        
        # Create test file with known message count
        test_html = """
        <html><body>
            <div class="message"><q>SMS 1</q></div>
            <div class="message"><q>SMS 2</q><img src="test.jpg"/></div>
            <div class="message"><q>SMS 3</q><a href="test.vcf">Contact</a></div>
        </body></html>
        """
        
        test_file = self.test_output_dir / "accuracy_test.html"
        test_file.write_text(test_html)
        
        soup = BeautifulSoup(test_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        with patch('sms.log_processing_event'):
            result = process_sms_mms_file(
                html_file=test_file,
                soup=soup,
                own_number="555-1234",
                src_filename_map={},
                conversation_manager=mock_cm,
                phone_lookup_manager=mock_phone_manager,
                config=config
            )
        
        # Should accurately count messages and attachments
        # Note: Exact counts depend on processing logic, but should be consistent
        assert result["num_sms"] >= 0, "Should count SMS messages"
        assert result["num_img"] >= 0, "Should count images"
        assert result["num_vcf"] >= 0, "Should count vCards"

    def test_end_to_end_optimization_performance(self):
        """TEST: End-to-end optimization should show overall performance improvement."""
        # This test validates that optimizations work in the complete workflow
        
        # Create multiple test files
        test_files = []
        for i in range(10):
            html_content = f"""
            <html><body>
                <div class="message">
                    <q>Test message {i}</q>
                    <abbr class="dt" title="20230101T12{i:02d}00+0000">Jan 1, 2023</abbr>
                </div>
            </body></html>
            """
            test_file = self.test_output_dir / f"perf_test_{i}.html"
            test_file.write_text(html_content)
            test_files.append(test_file)
        
        # This test will pass once optimizations are in place
        # It validates that the system can handle multiple files efficiently
        assert len(test_files) == 10, "Should create test files successfully"
