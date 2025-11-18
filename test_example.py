"""
Example script to test the MCP server tools directly.
This is for understanding/testing - the server normally runs via STDIO.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path to import server
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    ensure_context_structure,
    context_branch,
    context_commit,
    context_retrieve,
    context_merge,
)


async def main():
    """Test the MCP server tools."""
    print("🧪 Testing Git Context Controller MCP Server\n")
    
    # Ensure context structure exists
    ensure_context_structure()
    print("✅ Context structure initialized\n")
    
    # Test 1: Create a branch
    print("📦 Test 1: Creating branch 'test-feature'...")
    result = await context_branch(name="test-feature", parent="main")
    print(f"   Result: {result}\n")
    
    # Test 2: Make a commit
    print("💾 Test 2: Making a commit...")
    result = await context_commit(
        branch="test-feature",
        message="Initial test commit",
        content="This is a test commit to verify the system works.\n\nI'm testing the context management system."
    )
    print(f"   Result: {result}\n")
    
    # Test 3: Make another commit
    print("💾 Test 3: Making another commit...")
    result = await context_commit(
        branch="test-feature",
        message="Added more details",
        content="Here are more details about the feature:\n- Point 1\n- Point 2\n- Point 3"
    )
    print(f"   Result: {result}\n")
    
    # Test 4: Retrieve context
    print("🔍 Test 4: Retrieving context...")
    result = await context_retrieve(
        branch="test-feature",
        query="details",
        limit=5
    )
    print(f"   Found {result.get('commits_found', 0)} commits")
    for commit in result.get('commits', []):
        print(f"   - {commit['message']} ({commit['id']})")
    print()
    
    # Test 5: Create another branch and merge
    print("🌿 Test 5: Creating branch 'test-feature-2'...")
    result = await context_branch(name="test-feature-2", parent="test-feature")
    print(f"   Result: {result}\n")
    
    print("💾 Test 6: Making commit in branch 2...")
    result = await context_commit(
        branch="test-feature-2",
        message="Work in branch 2",
        content="This is work done in the second branch."
    )
    print(f"   Result: {result}\n")
    
    print("🔀 Test 7: Merging branches...")
    result = await context_merge(
        source_branch="test-feature-2",
        target_branch="test-feature",
        merge_message="Merged test-feature-2 into test-feature"
    )
    print(f"   Result: {result}\n")
    
    print("✅ All tests completed!")
    print("\n📁 Check the ./context/branches/ directory to see the created files")


if __name__ == "__main__":
    asyncio.run(main())

