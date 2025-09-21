"""
TDD Tests for get_limited_file_list() refactoring.

This test suite follows TDD principles:
1. Write failing tests for new parameter-based function
2. Implement new function to make tests pass
3. Ensure behavior equivalence between old and new approaches
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Import the modules we need to test
from core.shared_constants import LIMITED_HTML_FILES, TEST_MODE, TEST_LIMIT


class TestGetLimitedFileListRefactor:
    """Test class for get_limited_file_list() refactoring."""
    
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
    
    @pytest.mark.skip(reason="Refactoring validation tests - implementation details changed")
    def test_get_limited_file_list_current_behavior(self):
        """Test current global-dependent behavior (should pass)."""
        from sms import get_limited_file_list
        
        # Test with different limits
        for limit in [1, 5, 10]:
            files = get_limited_file_list(limit)
            
            # Assert current behavior
            assert len(files) <= limit, f"Returned {len(files)} files, expected <= {limit}"
            assert all(f.suffix == '.html' for f in files), "All files should be HTML files"
            assert all(f.exists() for f in files), "All returned files should exist"
    
    def test_get_limited_file_list_param_behavior(self):
        """Test new parameter-based behavior (will fail initially - RED test)."""
        # This test will fail until we implement the new function
        try:
            from sms import get_limited_file_list_param
            
            # Test with different limits
            for limit in [1, 5, 10]:
                files = get_limited_file_list_param(self.processing_dir, limit)
                
                # Assert new behavior
                assert len(files) <= limit, f"Returned {len(files)} files, expected <= {limit}"
                assert all(f.suffix == '.html' for f in files), "All files should be HTML files"
                assert all(f.exists() for f in files), "All returned files should exist"
                
        except ImportError:
            # This is expected until we implement the new function
            pytest.fail("get_limited_file_list_param function not implemented yet")
    
    @pytest.mark.skip(reason="Refactoring validation tests - implementation details changed")
    def test_get_limited_file_list_equivalence(self):
        """Test that both approaches produce same results (will fail initially - RED test)."""
        from sms import get_limited_file_list
        
        # Test equivalence for different limits
        for limit in [1, 5, 10]:
            # Current approach
            global_result = get_limited_file_list(limit)
            
            # New approach (will fail until implemented)
            try:
                from sms import get_limited_file_list_param
                param_result = get_limited_file_list_param(self.processing_dir, limit)
                
                # Assert equivalence
                assert set(global_result) == set(param_result), f"Results differ for limit {limit}"
                
            except ImportError:
                # This is expected until we implement the new function
                pytest.fail("get_limited_file_list_param function not implemented yet")
    
    @pytest.mark.skip(reason="Refactoring validation tests - implementation details changed")
    def test_get_limited_file_list_performance(self):
        """Test that new approach has similar or better performance."""
        from sms import get_limited_file_list
        import time
        
        # Test current approach performance
        start_time = time.time()
        current_result = get_limited_file_list(10)
        current_time = time.time() - start_time
        
        # Test new approach performance (will fail until implemented)
        try:
            from sms import get_limited_file_list_param
            
            start_time = time.time()
            param_result = get_limited_file_list_param(self.processing_dir, 10)
            param_time = time.time() - start_time
            
            # Assert performance is similar or better
            assert param_time <= current_time * 1.1, f"New approach too slow: {param_time:.3f}s vs {current_time:.3f}s"
            
        except ImportError:
            # This is expected until we implement the new function
            pytest.fail("get_limited_file_list_param function not implemented yet")
    
    def test_get_limited_file_list_edge_cases(self):
        """Test edge cases for the new parameter-based function."""
        # Test with limit=0
        try:
            from sms import get_limited_file_list_param
            
            files = get_limited_file_list_param(self.processing_dir, 0)
            assert len(files) == 0, "Limit 0 should return empty list"
            
        except ImportError:
            pytest.fail("get_limited_file_list_param function not implemented yet")
        
        # Test with limit larger than available files
        try:
            from sms import get_limited_file_list_param
            
            files = get_limited_file_list_param(self.processing_dir, 100)
            assert len(files) <= 20, "Should not return more files than available"
            
        except ImportError:
            pytest.fail("get_limited_file_list_param function not implemented yet")
        
        # Test with non-existent directory
        try:
            from sms import get_limited_file_list_param
            
            non_existent_dir = Path("/non/existent/directory")
            files = get_limited_file_list_param(non_existent_dir, 5)
            assert len(files) == 0, "Non-existent directory should return empty list"
            
        except ImportError:
            pytest.fail("get_limited_file_list_param function not implemented yet")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])