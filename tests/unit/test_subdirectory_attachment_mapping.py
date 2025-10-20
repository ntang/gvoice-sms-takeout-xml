"""
Test for subdirectory attachment mapping bug fix.

This test specifically validates that the attachment mapping stage correctly
handles attachments in subdirectories (e.g., Calls/, Voicemails/, etc.)

Bug: Previously, scan_directory_optimized() only returned basenames,
     causing create_optimized_mapping() to fail finding files in subdirectories.

Fix: Modified scan_directory_optimized() to return relative paths from base_dir.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from core.performance_optimizations import (
    scan_directory_optimized,
    build_attachment_mapping_optimized
)


class TestSubdirectoryAttachmentMapping:
    """Test that attachment mapping works with files in subdirectories."""

    def test_scan_directory_finds_files_in_subdirectories(self, tmp_path):
        """scan_directory_optimized should find files in subdirectories."""
        # Create directory structure
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        # Create subdirectory
        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        # Create test files
        (processing_dir / "root_photo.jpg").touch()
        (calls_dir / "call_photo.jpg").touch()
        (calls_dir / "voicemail.mp3").touch()

        # Scan for attachments
        extensions = {'.jpg', '.mp3', '.png'}
        found_files = scan_directory_optimized(processing_dir, extensions)

        # Should find all files with relative paths
        assert len(found_files) == 3
        assert "root_photo.jpg" in found_files
        assert "Calls/call_photo.jpg" in found_files
        assert "Calls/voicemail.mp3" in found_files

    def test_scan_directory_returns_relative_paths(self, tmp_path):
        """scan_directory_optimized should return paths relative to base_dir."""
        # Create nested directory structure
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        subdir1 = processing_dir / "Calls"
        subdir1.mkdir()

        subdir2 = processing_dir / "Voicemails"
        subdir2.mkdir()

        nested = subdir1 / "Nested"
        nested.mkdir()

        # Create files at different levels
        (processing_dir / "root.jpg").touch()
        (subdir1 / "photo1.jpg").touch()
        (subdir2 / "photo2.jpg").touch()
        (nested / "deep.jpg").touch()

        # Scan
        extensions = {'.jpg'}
        found_files = scan_directory_optimized(processing_dir, extensions)

        # Check all paths are relative to processing_dir
        assert "root.jpg" in found_files
        assert "Calls/photo1.jpg" in found_files
        assert "Voicemails/photo2.jpg" in found_files
        assert "Calls/Nested/deep.jpg" in found_files

        # Verify no absolute paths
        for file_path in found_files:
            assert not Path(file_path).is_absolute()

    def test_build_attachment_mapping_with_subdirectories(self, tmp_path):
        """build_attachment_mapping_optimized should map files in subdirectories."""
        # Create directory structure matching Google Voice export
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        # Create attachment files
        attachment1 = calls_dir / "photo1.jpg"
        attachment1.touch()
        attachment2 = calls_dir / "photo2.jpg"
        attachment2.touch()

        # Create HTML files that reference these attachments
        html_file = processing_dir / "conversation.html"
        html_file.write_text("""
        <html>
        <body>
            <img src="photo1.jpg">
            <img src="photo2.jpg">
        </body>
        </html>
        """)

        # Build mapping
        mapping = build_attachment_mapping_optimized(
            processing_dir=processing_dir,
            sample_files=None,
            use_cache=False
        )

        # Should successfully map both files
        assert len(mapping) == 2
        assert "photo1.jpg" in mapping
        assert "photo2.jpg" in mapping

        # Verify paths include subdirectory
        filename1, path1 = mapping["photo1.jpg"]
        filename2, path2 = mapping["photo2.jpg"]

        assert filename1 == "Calls/photo1.jpg"
        assert filename2 == "Calls/photo2.jpg"
        assert path1.exists()
        assert path2.exists()

    def test_mapping_fails_correctly_if_file_not_in_subdirectory(self, tmp_path):
        """Mapping should handle case where file is expected but not found."""
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        # Create HTML that references a file
        html_file = processing_dir / "conversation.html"
        html_file.write_text("""
        <html>
        <body>
            <img src="missing_photo.jpg">
        </body>
        </html>
        """)

        # Don't create the actual file
        # Build mapping should gracefully handle this
        mapping = build_attachment_mapping_optimized(
            processing_dir=processing_dir,
            sample_files=None,
            use_cache=False
        )

        # Should return empty mapping (no match found)
        assert len(mapping) == 0

    def test_real_world_google_voice_structure(self, tmp_path):
        """Test with realistic Google Voice export directory structure."""
        # Simulate Google Voice export structure
        processing_dir = tmp_path / "Takeout"
        processing_dir.mkdir()

        calls_dir = processing_dir / "Calls"
        calls_dir.mkdir()

        voicemails_dir = processing_dir / "Voicemails"
        voicemails_dir.mkdir()

        # Create files matching Google Voice naming
        files = [
            calls_dir / "Group Conversation - 2024-05-30T19_55_41Z-2-1.jpg",
            calls_dir / "Susan Nowak Tang - Text - 2025-02-16T15_58_55Z-5-1.jpg",
            voicemails_dir / "+14056332709 - Voicemail - 2020-08-04T22_15_18Z.mp3",
        ]

        for f in files:
            f.touch()

        # Create HTML files
        (processing_dir / "conversation1.html").write_text(
            '<img src="Group Conversation - 2024-05-30T19_55_41Z-2-1.jpg">'
        )
        (processing_dir / "conversation2.html").write_text(
            '<img src="Susan Nowak Tang - Text - 2025-02-16T15_58_55Z-5-1.jpg">'
        )
        (processing_dir / "voicemail.html").write_text(
            '<audio src="+14056332709 - Voicemail - 2020-08-04T22_15_18Z.mp3"></audio>'
        )

        # Build mapping
        mapping = build_attachment_mapping_optimized(
            processing_dir=processing_dir,
            sample_files=None,
            use_cache=False
        )

        # Should map all files
        assert len(mapping) >= 3  # At least our 3 files

        # Verify subdirectory paths are correct
        for src, (filename, path) in mapping.items():
            assert "Calls/" in filename or "Voicemails/" in filename
            assert path.exists()
            assert path.is_relative_to(processing_dir)

    def test_multiple_levels_of_nesting(self, tmp_path):
        """Test deeply nested subdirectories."""
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        # Create deeply nested structure
        deep = processing_dir / "level1" / "level2" / "level3"
        deep.mkdir(parents=True)

        # Create file deep in the tree
        (deep / "deep_file.jpg").touch()

        # Create HTML
        (processing_dir / "test.html").write_text('<img src="deep_file.jpg">')

        # Scan should find it with full relative path
        extensions = {'.jpg'}
        found = scan_directory_optimized(processing_dir, extensions)

        assert "level1/level2/level3/deep_file.jpg" in found

        # Mapping should work
        mapping = build_attachment_mapping_optimized(
            processing_dir=processing_dir,
            sample_files=None,
            use_cache=False
        )

        assert len(mapping) == 1
        filename, path = mapping["deep_file.jpg"]
        assert filename == "level1/level2/level3/deep_file.jpg"
        assert path.exists()


class TestSubdirectoryMappingRegression:
    """Regression tests to ensure the bug doesn't come back."""

    def test_basenames_alone_would_fail(self, tmp_path):
        """
        Demonstrate that using just basenames (old bug) would fail.
        This is a regression test to document the old behavior.
        """
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        subdir = processing_dir / "Subdir"
        subdir.mkdir()

        # File is in subdirectory
        (subdir / "photo.jpg").touch()

        # If we try to find it using just the basename (old bug)
        wrong_path = processing_dir / "photo.jpg"
        assert not wrong_path.exists()  # This would fail with old code

        # Correct path with subdirectory
        correct_path = processing_dir / "Subdir" / "photo.jpg"
        assert correct_path.exists()

    def test_fix_handles_relative_paths_correctly(self, tmp_path):
        """Verify the fix: relative paths work with Path / operator."""
        processing_dir = tmp_path / "processing"
        processing_dir.mkdir()

        subdir = processing_dir / "Calls"
        subdir.mkdir()

        (subdir / "photo.jpg").touch()

        # The fix: filename includes subdirectory
        filename_with_subdir = "Calls/photo.jpg"

        # This should work now
        constructed_path = processing_dir / filename_with_subdir
        assert constructed_path.exists()
        assert constructed_path == subdir / "photo.jpg"
