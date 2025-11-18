# Code Walkthrough: Understanding server.py

This document explains the key parts of `server.py` with simple explanations.

## 1. Imports and Setup

```python
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Git Context Controller")
```

**What this does:**
- Imports the FastMCP library
- Creates a server instance named "Git Context Controller"
- This server will handle all communication with Gemini CLI

## 2. Directory Paths

```python
CONTEXT_DIR = Path("./context")
BRANCHES_DIR = CONTEXT_DIR / "branches"
MAIN_MD = CONTEXT_DIR / "main.md"
```

**What this does:**
- Defines where files will be stored
- Uses `Path` objects (better than strings for file paths)
- `CONTEXT_DIR / "branches"` creates `./context/branches/`

## 3. Helper Functions

### `ensure_context_structure()`

```python
def ensure_context_structure() -> None:
    """Ensure the context directory structure exists."""
    CONTEXT_DIR.mkdir(exist_ok=True)  # Create ./context/ if it doesn't exist
    BRANCHES_DIR.mkdir(exist_ok=True)  # Create ./context/branches/ if it doesn't exist
    if not MAIN_MD.exists():
        MAIN_MD.write_text("# Global Project Roadmap\n\n...")
```

**What this does:**
- Creates the folder structure if it doesn't exist
- Creates `main.md` with default content if missing
- Called before operations to ensure directories exist

### `validate_branch_name()`

```python
def validate_branch_name(branch_name: str) -> bool:
    """Validate branch name to prevent issues with filesystem."""
    if not branch_name or len(branch_name) == 0:
        return False
    # Prevent problematic characters
    invalid_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    return not any(char in branch_name for char in invalid_chars)
```

**What this does:**
- Prevents dangerous branch names like `../../../etc/passwd`
- Blocks characters that could break file paths
- Returns `True` if valid, `False` if invalid

## 4. The Tools (What Gemini Can Do)

### Tool 1: `context_commit`

```python
@mcp.tool()  # ← Makes this function available to Gemini
async def context_commit(
    branch: str,        # Which branch to save to
    message: str,       # Commit message
    content: str,       # The actual content to save
    metadata: Optional[str] = None  # Optional extra info
) -> dict[str, Any]:   # Returns a dictionary with results
```

**Step-by-step what happens:**

1. **Validate branch name**
   ```python
   if not validate_branch_name(branch):
       return {"error": "Invalid branch name"}
   ```

2. **Ensure directories exist**
   ```python
   ensure_context_structure()
   ```

3. **Read branch metadata** (or create new)
   ```python
   branch_metadata = await read_branch_metadata(branch)
   # Returns existing metadata or creates default structure
   ```

4. **Create unique commit ID**
   ```python
   commit_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
   # Example: "20250101_120000_123456"
   ```

5. **Create commit file**
   ```python
   commit_file = commits_dir / f"{commit_id}.md"
   # Creates: ./context/branches/main/commits/20250101_120000_123456.md
   ```

6. **Write content to file**
   ```python
   commit_content = f"# Commit: {message}\n\n..."
   await asyncio.to_thread(commit_file.write_text, commit_content)
   # Uses async to avoid blocking
   ```

7. **Update metadata**
   ```python
   branch_metadata["commits"].append({
       "id": commit_id,
       "message": message,
       "timestamp": datetime.now().isoformat(),
       "file": str(commit_file.relative_to(CONTEXT_DIR))
   })
   await write_branch_metadata(branch, branch_metadata)
   ```

8. **Return success**
   ```python
   return {
       "success": True,
       "commit_id": commit_id,
       "branch": branch,
       "message": message,
       "path": str(commit_file.relative_to(CONTEXT_DIR))
   }
   ```

### Tool 2: `context_branch`

```python
@mcp.tool()
async def context_branch(
    name: str,              # Name of new branch
    parent: Optional[str] = None  # Optional parent branch
) -> dict[str, Any]:
```

**What it does:**
1. Validates the branch name
2. Checks if branch already exists (prevents overwrites)
3. Creates branch directory structure:
   ```
   ./context/branches/{name}/
   ├── commits/
   └── metadata.json
   ```
4. Initializes metadata with parent info
5. Returns creation confirmation

**Key code:**
```python
branch_dir = get_branch_dir(name)
if branch_dir.exists():
    return {"error": f"Branch '{name}' already exists"}  # Prevent overwrite

branch_dir.mkdir(parents=True, exist_ok=True)  # Create directory
```

### Tool 3: `context_merge`

```python
@mcp.tool()
async def context_merge(
    source_branch: str,      # Branch to merge FROM
    target_branch: str,      # Branch to merge INTO
    merge_message: Optional[str] = None
) -> dict[str, Any]:
```

**What it does:**
1. Reads commits from both branches
2. Combines them into a merge commit
3. Creates a synthesis document
4. Updates target branch metadata

**Key code:**
```python
# Read source commits
for commit_info in source_metadata.get("commits", []):
    commit_file = CONTEXT_DIR / commit_info["file"]
    content = await asyncio.to_thread(commit_file.read_text)
    source_commits_content.append({
        "id": commit_info["id"],
        "message": commit_info["message"],
        "content": content
    })

# Create merge commit with combined content
merge_content = f"# Merge: {source_branch} into {target_branch}\n\n"
merge_content += "## Source Branch Commits\n\n"
# ... add source commits ...
merge_content += "## Target Branch Commits\n\n"
# ... add target commits ...
merge_content += "## Synthesis\n\n"
```

### Tool 4: `context_retrieve`

```python
@mcp.tool()
async def context_retrieve(
    branch: str,
    query: Optional[str] = None,  # Search term
    limit: int = 10               # Max results
) -> dict[str, Any]:
```

**What it does:**
1. Reads branch metadata
2. Filters commits by query (if provided)
3. Reads commit file contents
4. Returns matching commits

**Key code:**
```python
# Filter commits if query provided
if query:
    query_lower = query.lower()
    filtered_commits = [
        c for c in commits
        if query_lower in c.get("message", "").lower()
    ]
    commits = filtered_commits

# Limit results
commits = commits[-limit:] if limit > 0 else commits

# Read commit contents
for commit_info in commits:
    commit_file = CONTEXT_DIR / commit_info["file"]
    if commit_file.exists():
        content = await asyncio.to_thread(commit_file.read_text)
        commit_contents.append({
            "id": commit_info["id"],
            "message": commit_info["message"],
            "content": content
        })
```

## 5. Resources (Direct Data Access)

### Resource 1: `context://main.md`

```python
@mcp.resource("context://main.md")
async def get_main_context() -> str:
    """Get the main context file content."""
    ensure_context_structure()
    if MAIN_MD.exists():
        return await asyncio.to_thread(MAIN_MD.read_text)
    return "# Global Project Roadmap\n\n..."
```

**What this does:**
- Exposes `main.md` as a readable resource
- Gemini can read it directly without calling a tool
- Returns file content as a string

### Resource 2: `context://branches/{name}`

```python
@mcp.resource("context://branches/{name}")
async def get_branch_resource(name: str) -> str:
    """Get branch metadata and recent commits as a resource."""
```

**What this does:**
- `{name}` is a path parameter (dynamic)
- When Gemini requests `context://branches/main`, `name="main"`
- Returns JSON string with branch metadata and recent commits

**Key code:**
```python
# Read branch metadata
branch_metadata = await read_branch_metadata(name)

# Include recent commits (last 5)
commits_summary = []
for commit_info in branch_metadata.get("commits", [])[-5:]:
    commit_file = CONTEXT_DIR / commit_info["file"]
    if commit_file.exists():
        content = await asyncio.to_thread(commit_file.read_text)
        commits_summary.append({
            "id": commit_info["id"],
            "message": commit_info["message"],
            "content": content[:500]  # First 500 chars
        })

# Return as JSON
return json.dumps({
    "branch": branch_metadata,
    "recent_commits": commits_summary
}, indent=2)
```

## 6. The Entry Point

```python
if __name__ == "__main__":
    ensure_context_structure()  # Create directories
    mcp.run()                   # Start the server
```

**What `mcp.run()` does:**
- Starts listening on stdin (standard input)
- Waits for JSON-RPC messages from Gemini CLI
- When a message arrives:
  1. Parses the JSON
  2. Calls the appropriate tool function
  3. Serializes the result to JSON
  4. Writes response to stdout (standard output)

## Key Concepts Explained

### Async/Await

```python
# Synchronous (blocks):
content = file.read_text()  # Waits until file is read

# Asynchronous (non-blocking):
content = await asyncio.to_thread(file.read_text)  # Doesn't block
```

**Why use async?** The server can handle multiple requests without freezing.

### Type Hints

```python
def function(param: str) -> dict[str, Any]:
    # param: str means "param is a string"
    # -> dict[str, Any] means "returns a dictionary"
```

**Why use type hints?** Helps Gemini understand what to send/receive.

### Docstrings

```python
def context_commit(...) -> dict[str, Any]:
    """
    Save current state as a timestamped commit...
    
    Args:
        branch: The branch name to commit to
        message: Commit message describing the changes
    """
```

**Why docstrings?** Gemini reads these to understand what each tool does.

## Flow Diagram: Complete Request

```
1. Gemini CLI sends JSON:
   {
     "method": "tools/call",
     "params": {
       "name": "context_commit",
       "arguments": {"branch": "main", "message": "...", "content": "..."}
     }
   }

2. FastMCP receives on stdin
   ↓
3. FastMCP parses JSON
   ↓
4. FastMCP calls: context_commit(branch="main", message="...", content="...")
   ↓
5. Our function executes:
   - Validates input
   - Creates commit file
   - Updates metadata
   - Returns result
   ↓
6. FastMCP serializes result to JSON
   ↓
7. FastMCP writes to stdout:
   {
     "result": {"success": true, "commit_id": "..."}
   }
   ↓
8. Gemini CLI receives response
   ↓
9. Gemini CLI shows result to user
```

## Summary

- **`@mcp.tool()`** = Makes a function callable by Gemini
- **`@mcp.resource()`** = Makes data readable by Gemini
- **`async/await`** = Non-blocking operations
- **Type hints** = Help Gemini understand data types
- **Docstrings** = Help Gemini understand what tools do
- **`mcp.run()`** = Starts the server listening on stdin/stdout

The server is essentially a collection of functions that Gemini can call, with FastMCP handling all the communication details!

