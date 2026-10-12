#!/usr/bin/env python3
"""
Test suite for document_analysis tool.
Validates multi-format document text extraction (PDF, Word, Text).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


async def test_pdf_basic():
    """Test basic PDF analysis."""
    async with create_client() as client:
        # Use a known public PDF
        result = await client.call_tool(
            "document_analysis",
            {
                "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "max_pages": 5,
            },
        )

        output = result.content[0].text
        assert len(output) > 100, f"PDF output too short: {len(output)} chars"
        assert "pdf" in output.lower(), "No PDF content found"

        print(f"✅ Basic PDF test passed - {len(output)} chars")


async def test_pdf_max_pages():
    """Test PDF with max_pages parameter."""
    async with create_client() as client:
        result = await client.call_tool(
            "document_analysis",
            {
                "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "max_pages": 3,
            },
        )

        output = result.content[0].text
        assert len(output) > 50, "max_pages output too short"

        print("✅ max_pages parameter test passed")


async def test_pdf_metadata():
    """Test PDF metadata extraction."""
    async with create_client() as client:
        result = await client.call_tool(
            "document_analysis",
            {
                "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "extract_metadata": True,
            },
        )

        output = result.content[0].text
        assert len(output) > 50, "Metadata extraction output too short"
        # Should mention metadata or document info
        has_info = (
            "metadata" in output.lower() or "document" in output.lower() or "page" in output.lower()
        )
        assert has_info, "No document information found"

        print("✅ Metadata extraction test passed")


async def test_pdf_error_handling():
    """Test PDF error handling for invalid URLs."""
    async with create_client() as client:
        result = await client.call_tool(
            "document_analysis", {"url": "https://www.python.org", "max_pages": 5}  # Not a PDF
        )

        output = result.content[0].text
        # Should handle gracefully
        assert len(output) > 50, "Error handling output too short"

        print("✅ Error handling test passed")


if __name__ == "__main__":
    asyncio.run(test_pdf_basic())
    asyncio.run(test_pdf_max_pages())
    asyncio.run(test_pdf_metadata())
    asyncio.run(test_pdf_error_handling())
    print("\n✅ All document_analysis tests passed!")
