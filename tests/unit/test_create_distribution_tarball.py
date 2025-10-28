"""
TDD tests for create-distribution-tarball command.

These tests verify the functionality for creating clean distribution tarballs
that contain only conversations referenced in index.html and their associated
attachments.

Test Strategy:
- Phase 1 (RED): Write failing tests first
- Phase 2 (GREEN): Implement features to make tests pass
- Phase 3 (REFACTOR): Improve code quality while keeping tests green
"""

import pytest
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil


class TestExtractConversationsFromIndex:
    """Test extracting conversation file list from index.html."""

    def test_extract_conversations_from_index(self, tmp_path):
        """RED: Test extracting conversation file list from index.html.

        This test will FAIL initially because _extract_conversations_from_index()
        doesn't exist yet.
        """
        # Create mock index.html with 3 conversation links
        index_html = tmp_path / "index.html"
        index_html.write_text("""
            <!DOCTYPE html>
            <html>
            <head><title>SMS Conversations Index</title></head>
            <body>
                <h1>SMS Conversations</h1>
                <table>
                    <thead>
                        <tr><th>Conversation</th><th>Messages</th></tr>
                    </thead>
                    <tbody>
                        <tr><td><a href="Ed_Harbur.html">Ed Harbur</a></td><td>42</td></tr>
                        <tr><td><a href="+12025948401.html">+12025948401</a></td><td>17</td></tr>
                        <tr><td><a href="Mike_Daddio.html">Mike Daddio</a></td><td>8</td></tr>
                    </tbody>
                </table>
            </body>
            </html>
        """)

        # Import and call the function we're about to implement
        from cli import _extract_conversations_from_index

        # Extract conversation list
        conversations = _extract_conversations_from_index(index_html)

        # Verify returns correct list of conversation files
        assert len(conversations) == 3, f"Expected 3 conversations, got {len(conversations)}"
        assert "Ed_Harbur.html" in conversations
        assert "+12025948401.html" in conversations
        assert "Mike_Daddio.html" in conversations

    def test_extract_conversations_excludes_archived_files(self, tmp_path):
        """RED: Test that .archived.html files are excluded from extraction."""
        # Create index.html with mix of .html and .archived.html links
        index_html = tmp_path / "index.html"
        index_html.write_text("""
            <!DOCTYPE html>
            <html>
            <body>
                <table>
                    <tr><td><a href="Keep.html">Keep</a></td></tr>
                    <tr><td><a href="Archived.archived.html">Archived</a></td></tr>
                    <tr><td><a href="Also_Keep.html">Also Keep</a></td></tr>
                </table>
            </body>
            </html>
        """)

        from cli import _extract_conversations_from_index

        conversations = _extract_conversations_from_index(index_html)

        # Should only get non-archived files
        assert len(conversations) == 2
        assert "Keep.html" in conversations
        assert "Also_Keep.html" in conversations
        assert "Archived.archived.html" not in conversations

    def test_extract_conversations_handles_missing_table(self, tmp_path):
        """RED: Test graceful handling when index.html has no table."""
        index_html = tmp_path / "index.html"
        index_html.write_text("""
            <!DOCTYPE html>
            <html><body><h1>No table here</h1></body></html>
        """)

        from cli import _extract_conversations_from_index

        conversations = _extract_conversations_from_index(index_html)

        # Should return empty list, not crash
        assert conversations == []


class TestExtractAttachmentsFromConversation:
    """Test extracting attachment references from conversation HTML."""

    def test_extract_attachments_from_conversation(self, tmp_path):
        """RED: Test extracting attachment references from conversation HTML.

        This test will FAIL initially because _extract_attachments_from_conversation()
        doesn't exist yet.
        """
        # Create mock conversation HTML with 2 attachments
        conversation_html = tmp_path / "test_conversation.html"
        conversation_html.write_text("""
            <!DOCTYPE html>
            <html>
            <body>
                <table>
                    <tr>
                        <td class="timestamp">2024-01-15 10:30:00</td>
                        <td class="sender">Alice</td>
                        <td class="message">Check out this photo!</td>
                        <td class="attachments">
                            <a class="attachment" href="attachments/photo1.jpg">photo1.jpg</a>
                        </td>
                    </tr>
                    <tr>
                        <td class="timestamp">2024-01-15 10:35:00</td>
                        <td class="sender">Bob</td>
                        <td class="message">Here's another one</td>
                        <td class="attachments">
                            <a class="attachment" href="attachments/photo2.jpg">photo2.jpg</a>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
        """)

        from cli import _extract_attachments_from_conversation

        # Extract attachment list
        attachments = _extract_attachments_from_conversation(conversation_html)

        # Verify returns correct list of attachment paths
        assert len(attachments) == 2
        assert "attachments/photo1.jpg" in attachments
        assert "attachments/photo2.jpg" in attachments

    def test_extract_attachments_deduplicates(self, tmp_path):
        """RED: Test that duplicate attachments are deduplicated."""
        conversation_html = tmp_path / "test_conversation.html"
        conversation_html.write_text("""
            <!DOCTYPE html>
            <html>
            <body>
                <table>
                    <tr>
                        <td class="attachments">
                            <a class="attachment" href="attachments/photo.jpg">photo.jpg</a>
                        </td>
                    </tr>
                    <tr>
                        <td class="attachments">
                            <a class="attachment" href="attachments/photo.jpg">photo.jpg</a>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
        """)

        from cli import _extract_attachments_from_conversation

        attachments = _extract_attachments_from_conversation(conversation_html)

        # Should only return unique attachments
        assert len(attachments) == 1
        assert "attachments/photo.jpg" in attachments

    def test_extract_attachments_handles_no_attachments(self, tmp_path):
        """RED: Test conversation with no attachments."""
        conversation_html = tmp_path / "test_conversation.html"
        conversation_html.write_text("""
            <!DOCTYPE html>
            <html>
            <body>
                <table>
                    <tr>
                        <td class="message">Just text</td>
                        <td class="attachments"></td>
                    </tr>
                </table>
            </body>
            </html>
        """)

        from cli import _extract_attachments_from_conversation

        attachments = _extract_attachments_from_conversation(conversation_html)

        # Should return empty list
        assert attachments == []


class TestCreateDistributionTarball:
    """Test creating tarball from file lists."""

    def test_create_tarball_with_file_list(self, tmp_path):
        """RED: Test creating tarball from conversation and attachment lists.

        This test will FAIL initially because _create_distribution_tarball()
        doesn't exist yet.
        """
        # Create test conversations directory
        conversations_dir = tmp_path / "conversations"
        conversations_dir.mkdir()

        # Create index.html
        index_file = conversations_dir / "index.html"
        index_file.write_text("<html><body>Index</body></html>")

        # Create conversation files
        conv1 = conversations_dir / "conv1.html"
        conv1.write_text("<html><body>Conversation 1</body></html>")

        conv2 = conversations_dir / "conv2.html"
        conv2.write_text("<html><body>Conversation 2</body></html>")

        # Create attachments directory
        attachments_dir = conversations_dir / "attachments"
        attachments_dir.mkdir()

        # Create attachment files
        att1 = attachments_dir / "photo1.jpg"
        att1.write_bytes(b"fake image data 1")

        att2 = attachments_dir / "photo2.jpg"
        att2.write_bytes(b"fake image data 2")

        # Output tarball path
        output_tarball = tmp_path / "test_output.tar.gz"

        from cli import _create_distribution_tarball

        # Create tarball
        success = _create_distribution_tarball(
            conversations_dir,
            output_tarball,
            ["conv1.html", "conv2.html"],
            ["attachments/photo1.jpg", "attachments/photo2.jpg"]
        )

        # Verify success
        assert success is True
        assert output_tarball.exists()

        # Verify tarball contents
        with tarfile.open(output_tarball, 'r:gz') as tar:
            members = tar.getnames()
            assert "conversations/index.html" in members
            assert "conversations/conv1.html" in members
            assert "conversations/conv2.html" in members
            assert "conversations/attachments/photo1.jpg" in members
            assert "conversations/attachments/photo2.jpg" in members

    def test_tarball_excludes_archived_files(self, tmp_path):
        """RED: Test that .archived.html files are NOT included in tarball."""
        # Create conversations directory with archived file
        conversations_dir = tmp_path / "conversations"
        conversations_dir.mkdir()

        index_file = conversations_dir / "index.html"
        index_file.write_text("<html><body>Index</body></html>")

        keep = conversations_dir / "keep.html"
        keep.write_text("<html><body>Keep this</body></html>")

        archived = conversations_dir / "archived.archived.html"
        archived.write_text("<html><body>This is archived</body></html>")

        output_tarball = tmp_path / "test_output.tar.gz"

        from cli import _create_distribution_tarball

        # Create tarball - only include non-archived
        success = _create_distribution_tarball(
            conversations_dir,
            output_tarball,
            ["keep.html"],  # NOT including archived.archived.html
            []
        )

        assert success is True

        # Verify archived file NOT in tarball
        with tarfile.open(output_tarball, 'r:gz') as tar:
            members = tar.getnames()
            assert "conversations/keep.html" in members
            assert "conversations/archived.archived.html" not in members
            # Also verify no .archived.html in any member names
            archived_count = sum(1 for m in members if '.archived.html' in m)
            assert archived_count == 0

    def test_handle_missing_attachments(self, tmp_path):
        """RED: Test graceful handling when attachment file doesn't exist."""
        conversations_dir = tmp_path / "conversations"
        conversations_dir.mkdir()

        index_file = conversations_dir / "index.html"
        index_file.write_text("<html><body>Index</body></html>")

        conv = conversations_dir / "conv.html"
        conv.write_text("<html><body>Conversation</body></html>")

        # Create attachments dir but NOT the actual attachment file
        attachments_dir = conversations_dir / "attachments"
        attachments_dir.mkdir()

        output_tarball = tmp_path / "test_output.tar.gz"

        from cli import _create_distribution_tarball

        # Try to include non-existent attachment
        success = _create_distribution_tarball(
            conversations_dir,
            output_tarball,
            ["conv.html"],
            ["attachments/missing_photo.jpg"]  # This file doesn't exist
        )

        # Should still succeed (warning logged, file skipped)
        assert success is True
        assert output_tarball.exists()

        # Verify tarball created without the missing attachment
        with tarfile.open(output_tarball, 'r:gz') as tar:
            members = tar.getnames()
            assert "conversations/index.html" in members
            assert "conversations/conv.html" in members
            assert "conversations/attachments/missing_photo.jpg" not in members


class TestFullTarballWorkflow:
    """Integration test of complete tarball creation workflow."""

    def test_full_tarball_creation_workflow(self, tmp_path):
        """RED: Integration test of complete create-distribution-tarball workflow.

        This test will FAIL initially because the CLI command doesn't exist yet.
        """
        # Create full conversations directory structure
        conversations_dir = tmp_path / "conversations"
        conversations_dir.mkdir()

        # Create index.html with links to some conversations
        index_html = conversations_dir / "index.html"
        index_html.write_text("""
            <!DOCTYPE html>
            <html>
            <body>
                <table>
                    <tr><td><a href="keep1.html">Keep 1</a></td></tr>
                    <tr><td><a href="keep2.html">Keep 2</a></td></tr>
                </table>
            </body>
            </html>
        """)

        # Create conversation files (some referenced, some not)
        keep1 = conversations_dir / "keep1.html"
        keep1.write_text("""
            <html><body><table><tr>
                <td class="attachments">
                    <a class="attachment" href="attachments/keep_photo.jpg">Photo</a>
                </td>
            </tr></table></body></html>
        """)

        keep2 = conversations_dir / "keep2.html"
        keep2.write_text("<html><body>No attachments</body></html>")

        # Create archived conversation (should be excluded)
        archived = conversations_dir / "archived.archived.html"
        archived.write_text("""
            <html><body><table><tr>
                <td class="attachments">
                    <a class="attachment" href="attachments/archived_photo.jpg">Photo</a>
                </td>
            </tr></table></body></html>
        """)

        # Create attachments directory
        attachments_dir = conversations_dir / "attachments"
        attachments_dir.mkdir()

        # Create attachment files
        keep_photo = attachments_dir / "keep_photo.jpg"
        keep_photo.write_bytes(b"keep this photo")

        archived_photo = attachments_dir / "archived_photo.jpg"
        archived_photo.write_bytes(b"archived photo data")

        orphaned_photo = attachments_dir / "orphaned.jpg"
        orphaned_photo.write_bytes(b"not referenced by any conversation")

        # Output tarball
        output_tarball = tmp_path / "distribution.tar.gz"

        # Import and test the helpers (this will work once implemented)
        from cli import _extract_conversations_from_index
        from cli import _extract_attachments_from_conversation
        from cli import _create_distribution_tarball

        # Step 1: Extract conversations from index
        conversations = _extract_conversations_from_index(index_html)
        assert len(conversations) == 2
        assert "keep1.html" in conversations
        assert "keep2.html" in conversations

        # Step 2: Extract attachments from conversations
        all_attachments = set()
        for conv_file in conversations:
            conv_path = conversations_dir / conv_file
            attachments = _extract_attachments_from_conversation(conv_path)
            all_attachments.update(attachments)

        assert len(all_attachments) == 1
        assert "attachments/keep_photo.jpg" in all_attachments
        assert "attachments/archived_photo.jpg" not in all_attachments
        assert "attachments/orphaned.jpg" not in all_attachments

        # Step 3: Create tarball
        success = _create_distribution_tarball(
            conversations_dir,
            output_tarball,
            conversations,
            sorted(list(all_attachments))
        )

        assert success is True
        assert output_tarball.exists()

        # Step 4: Verify tarball contents
        with tarfile.open(output_tarball, 'r:gz') as tar:
            members = tar.getnames()

            # Should include
            assert "conversations/index.html" in members
            assert "conversations/keep1.html" in members
            assert "conversations/keep2.html" in members
            assert "conversations/attachments/keep_photo.jpg" in members

            # Should NOT include
            assert "conversations/archived.archived.html" not in members
            assert "conversations/attachments/archived_photo.jpg" not in members
            assert "conversations/attachments/orphaned.jpg" not in members

            # Verify no .archived.html files in tarball
            archived_count = sum(1 for m in members if '.archived.html' in m)
            assert archived_count == 0


class TestAttachmentExtractionRealFormat:
    """Test attachment extraction with REAL conversation HTML format."""
    
    def test_extract_attachments_with_real_html_format(self, tmp_path):
        """
        RED: Test attachment extraction with actual production HTML format.
        
        Current bug: Looking for <a class="attachment"> but real format is
        <span class="attachment"><a href="...">.
        
        This test will FAIL with current implementation.
        """
        conv_file = tmp_path / "test_conversation.html"
        
        # REAL format from production files
        conv_file.write_text("""
            <!DOCTYPE html>
            <html><body>
                <table>
                    <tr>
                        <td class="attachments">
                            <span class="attachment">📎 <a href='attachments/Calls/photo1.jpg' target='_blank'>📷 Image</a></span>
                        </td>
                    </tr>
                    <tr>
                        <td class="attachments">
                            <span class="attachment">📎 <a href='attachments/Calls/photo2.jpg' target='_blank'>📷 Image</a></span>
                        </td>
                    </tr>
                    <tr>
                        <td class="attachments">
                            <span class="attachment">📎 <a href='attachments/Calls/video.mp4' target='_blank'>🎥 Video</a></span>
                        </td>
                    </tr>
                </table>
            </body></html>
        """)
        
        from cli import _extract_attachments_from_conversation
        
        attachments = _extract_attachments_from_conversation(conv_file)
        
        # Should find all 3 attachments
        assert len(attachments) == 3, f"Expected 3 attachments, found {len(attachments)}"
        assert 'attachments/Calls/photo1.jpg' in attachments
        assert 'attachments/Calls/photo2.jpg' in attachments
        assert 'attachments/Calls/video.mp4' in attachments


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
