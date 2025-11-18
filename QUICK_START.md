# Quick Start Guide: Context Engineering Tool MCP Server

## What is an MCP Server?

**MCP (Model Context Protocol)** is like a bridge between AI assistants (like Gemini) and your tools/data. Think of it as:
- **MCP Server** = A service that provides tools and data to AI
- **MCP Client** = The AI assistant (Gemini CLI) that uses those tools

When you ask Gemini to "save this context" or "create a branch", it calls our MCP server's tools to do the actual work.

## How Our Server Works

### 1. The Basic Structure

```python
from fastmcp import FastMCP

# Create the server
mcp = FastMCP("Context Engineering Tool")

# Define tools (functions the AI can call)
@mcp.tool()
async def context_commit(branch: str, message: str, content: str):
    """Save a commit to a branch"""
    # ... implementation ...
    return {"success": True, "commit_id": "..."}

# Run the server
if __name__ == "__main__":
    mcp.run()
```

### 2. What Happens When You Run It

When you run `python server.py`, the server:
1. Starts listening on STDIO (standard input/output)
2. Waits for commands from the MCP client (Gemini CLI)
3. Executes tools when requested
4. Returns results back through STDIO

**Important**: The server communicates via JSON messages over STDIO, which is why we never use `print()` - it would break the communication!

### 3. The Tools Explained

#### Tool 1: `context_commit`
**What it does**: Saves content as a commit in a branch

```python
# Example: Save "I'm working on feature X" to branch "main"
result = await context_commit(
    branch="main",
    message="Working on feature X",
    content="I'm implementing the login system..."
)
# Creates: ./context/branches/main/commits/20250101_120000_123456.md
```

#### Tool 2: `context_branch`
**What it does**: Creates a new branch (like Git branches)

```python
# Example: Create a new branch called "feature-login"
result = await context_branch(
    name="feature-login",
    parent="main"  # Optional: copy from main branch
)
# Creates: ./context/branches/feature-login/
```

#### Tool 3: `context_merge`
**What it does**: Combines two branches together

```python
# Example: Merge feature-login into main
result = await context_merge(
    source_branch="feature-login",
    target_branch="main",
    merge_message="Completed login feature"
)
# Creates a merge commit in main branch
```

#### Tool 4: `context_retrieve`
**What it does**: Searches and retrieves past commits

```python
# Example: Find commits about "login"
result = await context_retrieve(
    branch="main",
    query="login",  # Search for this keyword
    limit=5  # Return max 5 results
)
# Returns matching commits
```

### 4. Resources (Direct Data Access)

Resources let the AI read files directly without calling tools:

```python
# Resource: context://main.md
# The AI can read this file directly
@mcp.resource("context://main.md")
async def get_main_context() -> str:
    return "Content of main.md"

# Resource: context://branches/{name}
# The AI can read any branch's data
@mcp.resource("context://branches/{name}")
async def get_branch_resource(name: str) -> str:
    return "Branch data..."
```

## How to Connect to Gemini CLI

### Step 1: Install Dependencies

```bash
cd /Users/omagr/Documents/Personal/Agents/GCC
pip install -r requirements.txt
```

### Step 2: Find Your Gemini CLI Settings File

The settings file location depends on your system:
- **macOS**: `~/Library/Application Support/google-gemini-cli/settings.json`
- **Linux**: `~/.config/google-gemini-cli/settings.json`
- **Windows**: `%APPDATA%\google-gemini-cli\settings.json`

### Step 3: Edit the Settings File

Open `settings.json` and add our server configuration:

```json
{
  "mcpServers": {
    "context-engineering-tool": {
      "command": "python",
      "args": ["/Users/omagr/Documents/Personal/Agents/GCC/server.py"]
    }
  }
}
```

**Important**: Replace the path with your actual path to `server.py`!

### Step 4: Test the Connection

1. Restart Gemini CLI (if it's running)
2. Start a new conversation
3. Try asking: "Can you save this to context: I'm working on a new feature"
4. The AI should call our `context_commit` tool automatically!

### Step 5: Verify It Works

Check that files are being created:

```bash
# List branches
ls -la ./context/branches/

# View a commit
cat ./context/branches/main/commits/*.md

# View branch metadata
cat ./context/branches/main/metadata.json
```

## Example Conversation Flow

**You**: "Save this context: I'm building a login system with OAuth"

**Gemini CLI** (internally):
1. Recognizes you want to save context
2. Calls `context_commit(branch="main", message="...", content="...")`
3. Our server creates the commit file
4. Returns success message

**Gemini CLI** (to you): "I've saved that context to the main branch."

**You**: "Create a branch called 'oauth-implementation'"

**Gemini CLI**:
1. Calls `context_branch(name="oauth-implementation", parent="main")`
2. Our server creates the branch directory
3. Returns success

**Gemini CLI**: "Created branch 'oauth-implementation' from 'main'."

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (needs 3.8+)
- Verify fastmcp is installed: `pip list | grep fastmcp`

### Gemini CLI can't find the server
- Check the path in `settings.json` is absolute and correct
- Make sure `server.py` is executable: `chmod +x server.py`
- Restart Gemini CLI after changing settings

### Tools not appearing
- Check Gemini CLI logs for errors
- Verify the server starts without errors: `python server.py` (should hang waiting for input - this is normal!)

### Permission errors
- Make sure the `./context/` directory is writable
- Check file permissions: `ls -la ./context/`

## Testing the Server Manually

You can test the server directly (though it's designed for STDIO):

```python
# test_server.py (for testing only)
import asyncio
from server import context_commit, context_branch

async def test():
    # Test creating a branch
    result = await context_branch("test-branch")
    print(result)
    
    # Test committing
    result = await context_commit(
        branch="test-branch",
        message="Test commit",
        content="This is a test"
    )
    print(result)

asyncio.run(test())
```

Run with: `python test_server.py`

## Next Steps

1. **Try it out**: Ask Gemini to save some context
2. **Create branches**: Organize your work into branches
3. **Retrieve context**: Ask Gemini to recall past work
4. **Merge branches**: Combine different lines of work

The AI will automatically use these tools when you ask it to manage context!

