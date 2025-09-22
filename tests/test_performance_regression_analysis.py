"""
Performance Regression Analysis for HTML Processing Optimizations

This test suite isolates which specific optimization is causing the performance regression
and provides data to guide selective optimization.
"""

import pytest
import time
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch

from core.processing_config import ProcessingConfig


class TestParserPerformanceIsolation:
    """Isolate parser performance impact."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create realistic HTML content similar to Google Voice exports
        self.realistic_html = """
        <html>
        <head><title>SMS with John Doe</title></head>
        <body>
            <div class="message">
                <q>Hey, how are you doing?</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023 12:00 PM</abbr>
                <cite class="sender vcard">
                    <a class="tel" href="tel:+15551234567">
                        <abbr class="fn" title="">John Doe</abbr>
                    </a>
                </cite>
            </div>
            <div class="message">
                <q>I'm good, thanks for asking!</q>
                <abbr class="dt" title="20230101T120100+0000">Jan 1, 2023 12:01 PM</abbr>
                <cite class="sender vcard">
                    <a class="tel" href="tel:+15551234567">
                        <abbr class="fn" title="">Me</abbr>
                    </a>
                </cite>
            </div>
            <div class="message">
                <q>Check out this photo</q>
                <abbr class="dt" title="20230101T120200+0000">Jan 1, 2023 12:02 PM</abbr>
                <img src="photo.jpg" alt="Photo"/>
                <cite class="sender vcard">
                    <a class="tel" href="tel:+15551234567">
                        <abbr class="fn" title="">John Doe</abbr>
                    </a>
                </cite>
            </div>
        </body>
        </html>
        """

    def test_parser_performance_comparison(self):
        """Compare performance between html.parser and lxml parser."""
        iterations = 100  # Enough for measurable timing
        
        # Test html.parser performance
        start_time = time.time()
        for _ in range(iterations):
            soup = BeautifulSoup(self.realistic_html, 'html.parser')
            messages = soup.select('.message')
        html_parser_time = time.time() - start_time
        
        # Test lxml parser performance (if available)
        try:
            start_time = time.time()
            for _ in range(iterations):
                soup = BeautifulSoup(self.realistic_html, 'lxml')
                messages = soup.select('.message')
            lxml_parser_time = time.time() - start_time
            
            # Calculate performance difference
            speedup_ratio = html_parser_time / lxml_parser_time if lxml_parser_time > 0 else float('inf')
            
            print(f"\n🔍 Parser Performance Analysis:")
            print(f"  html.parser: {html_parser_time:.4f}s ({iterations} iterations)")
            print(f"  lxml parser: {lxml_parser_time:.4f}s ({iterations} iterations)")
            print(f"  Speedup ratio: {speedup_ratio:.2f}x")
            
            if speedup_ratio < 1.0:
                print(f"  ⚠️  lxml is SLOWER than html.parser by {1/speedup_ratio:.2f}x")
            else:
                print(f"  ✅ lxml is faster than html.parser by {speedup_ratio:.2f}x")
                
            # Test should help identify the issue
            assert True, f"Parser comparison: lxml {speedup_ratio:.2f}x vs html.parser"
            
        except ImportError:
            pytest.skip("lxml not available for comparison")

    def test_parser_overhead_with_file_io(self):
        """Test parser performance with actual file I/O (more realistic)."""
        # Create temporary file
        test_file = Path(tempfile.mktemp(suffix='.html'))
        test_file.write_text(self.realistic_html)
        
        try:
            iterations = 50  # Fewer iterations due to file I/O
            
            # Test html.parser with file I/O
            start_time = time.time()
            for _ in range(iterations):
                with open(test_file, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    messages = soup.select('.message')
            html_parser_file_time = time.time() - start_time
            
            # Test lxml parser with file I/O
            try:
                start_time = time.time()
                for _ in range(iterations):
                    with open(test_file, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'lxml')
                        messages = soup.select('.message')
                lxml_parser_file_time = time.time() - start_time
                
                speedup_ratio = html_parser_file_time / lxml_parser_file_time if lxml_parser_file_time > 0 else float('inf')
                
                print(f"\n🔍 Parser Performance with File I/O:")
                print(f"  html.parser: {html_parser_file_time:.4f}s ({iterations} files)")
                print(f"  lxml parser: {lxml_parser_file_time:.4f}s ({iterations} files)")
                print(f"  Speedup ratio: {speedup_ratio:.2f}x")
                
                assert True, f"File I/O comparison: lxml {speedup_ratio:.2f}x vs html.parser"
                
            except ImportError:
                pytest.skip("lxml not available")
                
        finally:
            if test_file.exists():
                test_file.unlink()


class TestCSSSelectorPerformanceIsolation:
    """Isolate CSS selector performance impact."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create HTML with many elements to test selector efficiency
        self.complex_html = "<html><body>" + "".join([
            f"""
            <div class="message">
                <q>Message {i}</q>
                <abbr class="dt" title="20230101T12{i%60:02d}00+0000">Jan 1, 2023</abbr>
                <cite class="sender vcard">
                    <a class="tel" href="tel:+1555{i:04d}">Contact {i}</a>
                </cite>
                {f'<img src="image{i}.jpg" alt="Photo"/>' if i % 3 == 0 else ''}
                {f'<a href="contact{i}.vcf">Contact</a>' if i % 5 == 0 else ''}
            </div>
            """ for i in range(100)  # 100 messages for meaningful test
        ]) + "</body></html>"

    def test_original_vs_optimized_selector_performance(self):
        """Compare original multiple selectors vs optimized single selector."""
        soup = BeautifulSoup(self.complex_html, 'html.parser')
        iterations = 50
        
        # Test original approach (multiple selectors)
        start_time = time.time()
        for _ in range(iterations):
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        original_selector_time = time.time() - start_time
        
        # Test optimized approach
        from sms import extract_message_data_optimized
        
        start_time = time.time()
        for _ in range(iterations):
            result = extract_message_data_optimized(soup)
        optimized_selector_time = time.time() - start_time
        
        # Calculate performance difference
        speedup_ratio = original_selector_time / optimized_selector_time if optimized_selector_time > 0 else float('inf')
        
        print(f"\n🔍 CSS Selector Performance Analysis:")
        print(f"  Original (3 selectors): {original_selector_time:.4f}s ({iterations} iterations)")
        print(f"  Optimized (1 selector): {optimized_selector_time:.4f}s ({iterations} iterations)")
        print(f"  Speedup ratio: {speedup_ratio:.2f}x")
        
        if speedup_ratio < 1.0:
            print(f"  ⚠️  Optimized selector is SLOWER by {1/speedup_ratio:.2f}x")
        else:
            print(f"  ✅ Optimized selector is faster by {speedup_ratio:.2f}x")
            
        # Verify same results
        original_messages = soup.select('.message')
        original_images = soup.select('img[src]')
        original_vcards = soup.select('a[href*=".vcf"]')
        
        optimized_result = extract_message_data_optimized(soup)
        
        assert len(original_messages) == len(optimized_result['messages']), "Should find same number of messages"
        assert len(original_images) == len(optimized_result['images']), "Should find same number of images"
        assert len(original_vcards) == len(optimized_result['vcards']), "Should find same number of vcards"
        
        assert True, f"Selector comparison: optimized {speedup_ratio:.2f}x vs original"

    def test_selector_complexity_analysis(self):
        """Analyze the complexity of different selector approaches."""
        soup = BeautifulSoup(self.complex_html, 'html.parser')
        
        # Test various selector strategies
        selectors = {
            'simple_class': '.message',
            'simple_img': 'img[src]',
            'simple_vcard': 'a[href*=".vcf"]',
            'complex_combined': '.message, .message img[src], .message a[href*=".vcf"], img[src], a[href*=".vcf"]',
            'descendant_only': '.message img[src], .message a[href*=".vcf"]'
        }
        
        results = {}
        iterations = 100
        
        for name, selector in selectors.items():
            start_time = time.time()
            for _ in range(iterations):
                elements = soup.select(selector)
            elapsed = time.time() - start_time
            results[name] = elapsed
            
        print(f"\n🔍 Selector Complexity Analysis:")
        for name, elapsed in results.items():
            print(f"  {name}: {elapsed:.4f}s ({iterations} iterations)")
            
        # Identify fastest approach
        fastest = min(results.items(), key=lambda x: x[1])
        slowest = max(results.items(), key=lambda x: x[1])
        
        print(f"\n  ✅ Fastest: {fastest[0]} ({fastest[1]:.4f}s)")
        print(f"  ⚠️  Slowest: {slowest[0]} ({slowest[1]:.4f}s)")
        print(f"  Performance ratio: {slowest[1]/fastest[1]:.2f}x difference")


class TestFunctionCallOverheadAnalysis:
    """Analyze overhead from additional function calls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_html = """
        <html><body>
            <div class="message"><q>Test message</q></div>
            <img src="test.jpg"/>
            <a href="test.vcf">Contact</a>
        </body></html>
        """

    def test_function_call_overhead(self):
        """Measure overhead from extract_message_data_optimized function."""
        soup = BeautifulSoup(self.test_html, 'html.parser')
        iterations = 1000
        
        # Test direct selector calls (original approach)
        start_time = time.time()
        for _ in range(iterations):
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        direct_time = time.time() - start_time
        
        # Test function call approach (optimized approach)
        from sms import extract_message_data_optimized
        
        start_time = time.time()
        for _ in range(iterations):
            result = extract_message_data_optimized(soup)
        function_call_time = time.time() - start_time
        
        overhead_ratio = function_call_time / direct_time if direct_time > 0 else float('inf')
        
        print(f"\n🔍 Function Call Overhead Analysis:")
        print(f"  Direct selectors: {direct_time:.4f}s ({iterations} iterations)")
        print(f"  Function call: {function_call_time:.4f}s ({iterations} iterations)")
        print(f"  Overhead ratio: {overhead_ratio:.2f}x")
        
        if overhead_ratio > 1.1:
            print(f"  ⚠️  Function call adds {(overhead_ratio-1)*100:.1f}% overhead")
        else:
            print(f"  ✅ Function call overhead acceptable: {(overhead_ratio-1)*100:.1f}%")


class TestRealWorldPerformanceComparison:
    """Test with realistic Google Voice HTML structure."""

    def test_realistic_file_processing_comparison(self):
        """Compare performance with realistic Google Voice HTML structure."""
        # Create HTML that matches actual Google Voice export structure
        realistic_google_voice_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>SMS with Contact Name</title>
        </head>
        <body>
            <div class="header">
                <h1>SMS with Contact Name</h1>
                <p>Conversation started on Jan 1, 2023</p>
            </div>
            <div class="messages">
                <div class="message">
                    <div class="text">
                        <q>This is a test message with some content</q>
                    </div>
                    <div class="metadata">
                        <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023 12:00:00 PM UTC</abbr>
                        <cite class="sender vcard">
                            <a class="tel" href="tel:+15551234567">
                                <abbr class="fn" title="">Contact Name</abbr>
                            </a>
                        </cite>
                    </div>
                </div>
                <div class="message">
                    <div class="text">
                        <q>Here's a photo for you</q>
                    </div>
                    <div class="metadata">
                        <abbr class="dt" title="20230101T120100+0000">Jan 1, 2023 12:01:00 PM UTC</abbr>
                        <cite class="sender vcard">
                            <a class="tel" href="tel:+15551234567">
                                <abbr class="fn" title="">Contact Name</abbr>
                            </a>
                        </cite>
                    </div>
                    <div class="attachments">
                        <img src="attachments/photo_123.jpg" alt="Shared photo"/>
                    </div>
                </div>
                <div class="message">
                    <div class="text">
                        <q>And here's a contact card</q>
                    </div>
                    <div class="metadata">
                        <abbr class="dt" title="20230101T120200+0000">Jan 1, 2023 12:02:00 PM UTC</abbr>
                        <cite class="sender vcard">
                            <a class="tel" href="tel:+15551234567">
                                <abbr class="fn" title="">Me</abbr>
                            </a>
                        </cite>
                    </div>
                    <div class="attachments">
                        <a href="attachments/contact_456.vcf">Contact Card</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        iterations = 20  # Realistic number for larger HTML
        
        # Test with html.parser
        start_time = time.time()
        for _ in range(iterations):
            soup = BeautifulSoup(realistic_google_voice_html, 'html.parser')
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        original_realistic_time = time.time() - start_time
        
        # Test with lxml
        try:
            start_time = time.time()
            for _ in range(iterations):
                soup = BeautifulSoup(realistic_google_voice_html, 'lxml')
                messages = soup.select('.message')
                images = soup.select('img[src]')
                vcards = soup.select('a[href*=".vcf"]')
            lxml_realistic_time = time.time() - start_time
            
            speedup_ratio = original_realistic_time / lxml_realistic_time if lxml_realistic_time > 0 else float('inf')
            
            print(f"\n🔍 Realistic HTML Processing Analysis:")
            print(f"  html.parser: {original_realistic_time:.4f}s ({iterations} files)")
            print(f"  lxml parser: {lxml_realistic_time:.4f}s ({iterations} files)")
            print(f"  Speedup ratio: {speedup_ratio:.2f}x")
            
            # Test optimized selector approach
            from sms import extract_message_data_optimized
            
            start_time = time.time()
            for _ in range(iterations):
                soup = BeautifulSoup(realistic_google_voice_html, 'lxml')
                result = extract_message_data_optimized(soup)
            optimized_combined_time = time.time() - start_time
            
            combined_speedup = original_realistic_time / optimized_combined_time if optimized_combined_time > 0 else float('inf')
            
            print(f"  Combined optimization: {optimized_combined_time:.4f}s ({iterations} files)")
            print(f"  Combined speedup: {combined_speedup:.2f}x")
            
            if combined_speedup < 1.0:
                print(f"  ⚠️  REGRESSION: Combined optimization is {1/combined_speedup:.2f}x SLOWER")
            else:
                print(f"  ✅ IMPROVEMENT: Combined optimization is {combined_speedup:.2f}x faster")
                
        except ImportError:
            pytest.skip("lxml not available")


class TestOptimizationIsolation:
    """Isolate individual optimization components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_html = """
        <html><body>
        """ + "".join([
            f"""
            <div class="message">
                <q>Message {i}</q>
                <abbr class="dt" title="20230101T12{i%60:02d}00+0000">Jan 1, 2023</abbr>
                {f'<img src="image{i}.jpg"/>' if i % 4 == 0 else ''}
                {f'<a href="contact{i}.vcf">Contact</a>' if i % 6 == 0 else ''}
            </div>
            """ for i in range(50)
        ]) + "</body></html>"

    def test_parser_only_optimization(self):
        """Test parser optimization in isolation."""
        iterations = 30
        
        # Original: html.parser + original selectors
        start_time = time.time()
        for _ in range(iterations):
            soup = BeautifulSoup(self.test_html, 'html.parser')
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        original_time = time.time() - start_time
        
        # Parser-only optimization: lxml + original selectors
        try:
            start_time = time.time()
            for _ in range(iterations):
                soup = BeautifulSoup(self.test_html, 'lxml')
                messages = soup.select('.message')
                images = soup.select('img[src]')
                vcards = soup.select('a[href*=".vcf"]')
            parser_only_time = time.time() - start_time
            
            parser_speedup = original_time / parser_only_time if parser_only_time > 0 else float('inf')
            
            print(f"\n🔍 Parser-Only Optimization Analysis:")
            print(f"  Original (html.parser): {original_time:.4f}s")
            print(f"  Parser-only (lxml): {parser_only_time:.4f}s")
            print(f"  Parser speedup: {parser_speedup:.2f}x")
            
            if parser_speedup < 1.0:
                print(f"  ⚠️  Parser change SLOWS DOWN processing by {1/parser_speedup:.2f}x")
            
        except ImportError:
            pytest.skip("lxml not available")

    def test_selector_only_optimization(self):
        """Test selector optimization in isolation."""
        iterations = 30
        
        # Original: html.parser + original selectors  
        soup = BeautifulSoup(self.test_html, 'html.parser')
        
        start_time = time.time()
        for _ in range(iterations):
            messages = soup.select('.message')
            images = soup.select('img[src]')
            vcards = soup.select('a[href*=".vcf"]')
        original_selectors_time = time.time() - start_time
        
        # Selector-only optimization: html.parser + optimized selectors
        from sms import extract_message_data_optimized
        
        start_time = time.time()
        for _ in range(iterations):
            result = extract_message_data_optimized(soup)
        optimized_selectors_time = time.time() - start_time
        
        selector_speedup = original_selectors_time / optimized_selectors_time if optimized_selectors_time > 0 else float('inf')
        
        print(f"\n🔍 Selector-Only Optimization Analysis:")
        print(f"  Original selectors: {original_selectors_time:.4f}s")
        print(f"  Optimized selectors: {optimized_selectors_time:.4f}s")
        print(f"  Selector speedup: {selector_speedup:.2f}x")
        
        if selector_speedup < 1.0:
            print(f"  ⚠️  Selector optimization SLOWS DOWN processing by {1/selector_speedup:.2f}x")


class TestProcessingSMSFileRegressionAnalysis:
    """Analyze the specific regression in process_sms_mms_file."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_process_sms_mms_file_performance_regression(self):
        """Identify specific performance regression in process_sms_mms_file."""
        from sms import process_sms_mms_file
        
        # Create realistic test file
        test_html = """
        <html><body>
            <div class="message">
                <q>Performance test message</q>
                <abbr class="dt" title="20230101T120000+0000">Jan 1, 2023</abbr>
            </div>
        </body></html>
        """
        
        test_file = self.test_output_dir / "perf_test.html"
        test_file.write_text(test_html)
        
        soup = BeautifulSoup(test_html, 'html.parser')
        mock_cm = Mock()
        mock_phone_manager = Mock()
        config = ProcessingConfig(processing_dir=self.test_output_dir)
        
        # Measure current performance
        iterations = 10
        start_time = time.time()
        
        for _ in range(iterations):
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
        
        total_time = time.time() - start_time
        avg_time_per_call = total_time / iterations
        
        print(f"\n🔍 process_sms_mms_file Performance Analysis:")
        print(f"  Total time: {total_time:.4f}s ({iterations} calls)")
        print(f"  Average per call: {avg_time_per_call:.4f}s")
        print(f"  Extrapolated for 61,484 files: {avg_time_per_call * 61484:.1f}s")
        
        # This helps identify if the regression is in process_sms_mms_file specifically
        assert avg_time_per_call < 0.1, f"Each call should be fast: {avg_time_per_call:.4f}s per call"
