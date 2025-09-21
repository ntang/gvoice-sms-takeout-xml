"""
Performance Investigation Test Suite for Phase 2.

This test suite follows TDD principles to identify performance bottlenecks
and create a foundation for architectural refactoring.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
import subprocess
import signal
from unittest.mock import patch, MagicMock

# Import the modules we need to test
from core.shared_constants import LIMITED_HTML_FILES, TEST_MODE, TEST_LIMIT
from core.processing_context import ProcessingContext, create_processing_context
from core.processing_config import ProcessingConfig


class TestPerformanceInvestigation:
    """Test class to investigate performance bottlenecks."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Reset global state
        global LIMITED_HTML_FILES, TEST_MODE, TEST_LIMIT
        LIMITED_HTML_FILES = None
        TEST_MODE = False
        TEST_LIMIT = 100
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.processing_dir = Path(self.temp_dir)
        self.calls_dir = self.processing_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        
        # Create required Phones.vcf file
        phones_vcf = self.processing_dir / "Phones.vcf"
        phones_vcf.write_text("""BEGIN:VCARD
VERSION:3.0
FN:Test Contact
TEL:+1234567890
END:VCARD
""")
        
        # Create test HTML files
        self.create_test_html_files(count=50)
    
    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_html_files(self, count: int):
        """Create test HTML files in the Calls directory."""
        for i in range(count):
            html_file = self.calls_dir / f"conversation_{i:03d}.html"
            html_file.write_text(f"""
            <html>
            <head><title>Conversation {i}</title></head>
            <body>
                <div class="conversation">
                    <div class="message">
                        <div class="sender">+1234567890</div>
                        <div class="content">Test message {i}</div>
                        <div class="timestamp">2023-01-{i%28+1:02d} 12:00:00</div>
                    </div>
                </div>
            </body>
            </html>
            """)
    
    def test_conversion_performance_baseline(self):
        """Test that conversion completes within reasonable time for small dataset.
        
        This test establishes a performance baseline for small datasets.
        """
        # Create a small test dataset
        self.create_test_html_files(count=5)
        
        config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=5
        )
        
        context = create_processing_context(config)
        
        # Test conversion performance
        start_time = time.time()
        
        # Simulate the conversion process
        try:
            from sms import main as sms_main
            sms_main(config, context)
            execution_time = time.time() - start_time
            
            # Performance assertion
            assert execution_time < 10, f"Conversion took {execution_time:.2f}s, expected < 10s"
            
        except Exception as e:
            # If conversion fails, that's also important to know
            pytest.fail(f"Conversion failed: {e}")
    
    def test_identify_performance_bottleneck(self):
        """Test to identify which component is slow.
        
        This test profiles each major component to identify bottlenecks.
        """
        # Create test dataset
        self.create_test_html_files(count=20)
        
        config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=5
        )
        
        context = create_processing_context(config)
        
        # Profile attachment processing
        attachment_start = time.time()
        try:
            from core.attachment_manager_new import build_attachment_mapping_with_progress_new
            from core.path_manager import PathManager
            
            path_manager = PathManager(
                processing_dir=self.processing_dir,
                output_dir=self.processing_dir / "conversations"
            )
            
            src_filename_map = build_attachment_mapping_with_progress_new(path_manager)
            attachment_time = time.time() - attachment_start
            
        except Exception as e:
            attachment_time = float('inf')
            print(f"Attachment processing failed: {e}")
        
        # Profile phone lookup processing
        phone_lookup_start = time.time()
        try:
            from core.phone_lookup import PhoneLookupManager
            
            phone_manager = PhoneLookupManager(
                lookup_file=self.processing_dir / "phone_lookup.txt",
                enable_prompts=False
            )
            phone_lookup_time = time.time() - phone_lookup_start
            
        except Exception as e:
            phone_lookup_time = float('inf')
            print(f"Phone lookup processing failed: {e}")
        
        # Profile HTML processing
        html_processing_start = time.time()
        try:
            from sms import get_limited_file_list
            
            limited_files = get_limited_file_list(5)
            html_processing_time = time.time() - html_processing_start
            
        except Exception as e:
            html_processing_time = float('inf')
            print(f"HTML processing failed: {e}")
        
        # Identify the slowest component
        times = {
            'attachment_processing': attachment_time,
            'phone_lookup': phone_lookup_time,
            'html_processing': html_processing_time
        }
        
        slowest_component = max(times, key=times.get)
        slowest_time = times[slowest_component]
        
        print(f"Performance profiling results:")
        for component, exec_time in times.items():
            print(f"  {component}: {exec_time:.3f}s")
        
        print(f"Slowest component: {slowest_component} ({slowest_time:.3f}s)")
        
        # Assert that no single component takes too long
        assert slowest_time < 5, f"Component {slowest_component} took {slowest_time:.3f}s, expected < 5s"
    
    def test_cli_performance_with_timeout(self):
        """Test CLI performance with timeout to identify bottlenecks."""
        # Create test dataset
        self.create_test_html_files(count=10)
        
        def timeout_handler(signum, frame):
            raise TimeoutError('Command timed out')
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)  # 15 second timeout
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 
                '--processing-dir', str(self.processing_dir),
                '--test-mode', '--test-limit', '5', 
                '--debug', '--verbose', 'convert'
            ], capture_output=True, text=True, timeout=15)
            
            signal.alarm(0)  # Cancel timeout
            
            execution_successful = result.returncode == 0
            execution_time = 15  # We know it completed within timeout
            
            print(f"CLI execution successful: {execution_successful}")
            print(f"Exit code: {result.returncode}")
            
            if result.stdout:
                print("STDOUT (last 500 chars):")
                print(result.stdout[-500:])
            
            if result.stderr:
                print("STDERR (last 500 chars):")
                print(result.stderr[-500:])
            
            # Assert that CLI completes successfully
            assert execution_successful, f"CLI execution failed with exit code {result.returncode}"
            
        except TimeoutError:
            signal.alarm(0)
            pytest.fail("CLI execution timed out after 15 seconds - there is a performance bottleneck")
        except subprocess.TimeoutExpired:
            signal.alarm(0)
            pytest.fail("CLI execution timed out after 15 seconds - there is a performance bottleneck")
        except Exception as e:
            signal.alarm(0)
            pytest.fail(f"CLI execution failed with error: {e}")
    
    def test_memory_usage_during_conversion(self):
        """Test memory usage during conversion to identify memory bottlenecks."""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Record initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create test dataset
        self.create_test_html_files(count=20)
        
        config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=10
        )
        
        context = create_processing_context(config)
        
        # Record memory usage during processing
        memory_usage = []
        
        try:
            from sms import main as sms_main
            
            # Start conversion
            sms_main(config, context)
            
            # Record final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"Memory usage:")
            print(f"  Initial: {initial_memory:.2f} MB")
            print(f"  Final: {final_memory:.2f} MB")
            print(f"  Increase: {memory_increase:.2f} MB")
            
            # Assert reasonable memory usage
            assert memory_increase < 100, f"Memory usage increased by {memory_increase:.2f} MB, expected < 100 MB"
            
        except Exception as e:
            pytest.fail(f"Memory usage test failed: {e}")


class TestBehaviorPreservation:
    """Test class to ensure behavior preservation during refactoring."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Reset global state
        global LIMITED_HTML_FILES, TEST_MODE, TEST_LIMIT
        LIMITED_HTML_FILES = None
        TEST_MODE = False
        TEST_LIMIT = 100
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.processing_dir = Path(self.temp_dir)
        self.calls_dir = self.processing_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        
        # Create required Phones.vcf file
        phones_vcf = self.processing_dir / "Phones.vcf"
        phones_vcf.write_text("""BEGIN:VCARD
VERSION:3.0
FN:Test Contact
TEL:+1234567890
END:VCARD
""")
        
        # Create test HTML files
        self.create_test_html_files(count=20)
    
    def teardown_method(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_html_files(self, count: int):
        """Create test HTML files in the Calls directory."""
        for i in range(count):
            html_file = self.calls_dir / f"conversation_{i:03d}.html"
            html_file.write_text(f"""
            <html>
            <head><title>Conversation {i}</title></head>
            <body>
                <div class="conversation">
                    <div class="message">
                        <div class="sender">+1234567890</div>
                        <div class="content">Test message {i}</div>
                        <div class="timestamp">2023-01-{i%28+1:02d} 12:00:00</div>
                    </div>
                </div>
            </body>
            </html>
            """)
    
    def test_get_limited_file_list_behavior(self):
        """Test that get_limited_file_list behaves consistently."""
        from sms import get_limited_file_list
        
        # Test with different limits
        for limit in [1, 5, 10]:
            files = get_limited_file_list(limit)
            
            # Assert behavior consistency
            assert len(files) <= limit, f"Returned {len(files)} files, expected <= {limit}"
            assert all(f.suffix == '.html' for f in files), "All files should be HTML files"
            assert all(f.exists() for f in files), "All returned files should exist"
    
    def test_process_html_files_behavior(self):
        """Test that process_html_files behaves consistently."""
        from sms import process_html_files
        
        # Create test configuration
        config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=5
        )
        
        context = create_processing_context(config)
        
        # Test with empty src_filename_map
        src_filename_map = {}
        
        try:
            stats = process_html_files(src_filename_map, config, context)
            
            # Assert behavior consistency
            assert isinstance(stats, dict), "Should return a dictionary"
            assert 'num_sms' in stats, "Should include num_sms in stats"
            assert 'num_img' in stats, "Should include num_img in stats"
            assert 'num_vcf' in stats, "Should include num_vcf in stats"
            assert 'num_calls' in stats, "Should include num_calls in stats"
            assert 'num_voicemails' in stats, "Should include num_voicemails in stats"
            
        except Exception as e:
            pytest.fail(f"process_html_files failed: {e}")
    
    def test_configuration_consistency(self):
        """Test that context and global configs produce consistent results."""
        config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=5
        )
        
        context = create_processing_context(config)
        
        # Test context configuration
        assert context.test_mode == config.test_mode, "Context test_mode should match config"
        assert context.test_limit == config.test_limit, "Context test_limit should match config"
        assert context.processing_dir == config.processing_dir, "Context processing_dir should match config"
        
        # Test that context has all required fields
        required_fields = [
            'test_mode', 'test_limit', 'limited_html_files',
            'skip_filtered_contacts', 'include_service_codes',
            'processing_dir', 'output_dir'
        ]
        
        for field in required_fields:
            assert hasattr(context, field), f"Context should have {field} field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])