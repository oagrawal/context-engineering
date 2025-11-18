# How It Works: Simple Explanation

## The Big Picture

```
┌─────────────┐         JSON Messages          ┌──────────────┐
│  Gemini CLI │  <──────────────────────────>  │  Our Server  │
│   (Client)  │         over STDIO             │   (server.py)│
└─────────────┘                                └──────────────┘
      │                                                │
      │  "Save this context"                          │
      │──────────────────────────────────────────────>│
      │                                               │
      │                                               │  Creates files:
      │                                               │  - ./context/branches/main/commits/...
      │                                               │  - ./context/branches/main/metadata.json
      │                                               │
      │  "Context saved successfully"                │
      │<──────────────────────────────────────────────│
```

## Step-by-Step: What Happens When You Ask Gemini to Save Context

### 1. You Type a Message
```
You: "Save this to context: I'm working on a login feature"
```

### 2. Gemini CLI Processes Your Request
Gemini CLI thinks: "The user wants to save context. I see there's a tool called `context_commit` available. Let me use it."

### 3. Gemini CLI Sends a JSON Message to Our Server
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "context_commit",
    "arguments": {
      "branch": "main",
      "message": "Working on login feature",
      "content": "I'm working on a login feature"
    }
  }
}
```

### 4. Our Server Receives and Processes
```python
# This function gets called automatically by FastMCP
@mcp.tool()
async def context_commit(branch: str, message: str, content: str):
    # 1. Validate the branch name
    if not validate_branch_name(branch):
        return {"error": "Invalid branch name"}
    
    # 2. Create the commit file
    commit_id = "20250101_120000_123456"
    commit_file = Path("./context/branches/main/commits/20250101_120000_123456.md")
    
    # 3. Write the content
    commit_file.write_text(f"# Commit: {message}\n\n{content}")
    
    # 4. Update metadata
    metadata["commits"].append({
        "id": commit_id,
        "message": message,
        "timestamp": "..."
    })
    
    # 5. Return success
    return {"success": True, "commit_id": commit_id}
```

### 5. Server Sends Response Back
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "commit_id": "20250101_120000_123456",
    "branch": "main",
    "message": "Working on login feature"
  }
}
```

### 6. Gemini CLI Shows You the Result
```
Gemini: "I've saved that context to the main branch. The commit ID is 20250101_120000_123456."
```

## Understanding the Code Structure

### The Decorator Pattern

```python
@mcp.tool()  # ← This tells FastMCP: "This function is a tool the AI can use"
async def context_commit(...):
    # Function implementation
```

**What `@mcp.tool()` does:**
- Registers the function as an available tool
- Extracts the function signature (parameters, types, docstring)
- Makes it discoverable by Gemini CLI
- Handles JSON serialization/deserialization automatically

### Why Async?

```python
# ❌ BAD: Blocking (freezes the server)
def read_file(path):
    return path.read_text()  # Blocks until file is read

# ✅ GOOD: Non-blocking (server can handle other requests)
async def read_file(path):
    return await asyncio.to_thread(path.read_text)  # Doesn't block
```

**Why it matters:** The server can handle multiple requests without freezing.

### The STDIO Communication

```python
# When you run: python server.py
# FastMCP automatically:
# 1. Reads from stdin (standard input)
# 2. Parses JSON messages
# 3. Calls the appropriate tool function
# 4. Writes JSON response to stdout (standard output)

if __name__ == "__main__":
    mcp.run()  # ← This starts listening on stdin/stdout
```

**Why no `print()`?** Because `print()` writes to stdout, which would break the JSON protocol. FastMCP handles all output.

## File Structure Explained

```
./context/
├── main.md                          # Global roadmap (readable as resource)
└── branches/
    ├── main/                        # Main branch
    │   ├── commits/
    │   │   ├── 20250101_120000_123456.md  # Individual commit
    │   │   └── 20250101_130000_789012.md
    │   └── metadata.json            # Branch info, commit list
    └── feature-login/               # Another branch
        ├── commits/
        │   └── 20250101_140000_345678.md
        └── metadata.json
```

### Example Commit File (`20250101_120000_123456.md`)

```markdown
# Commit: Working on login feature

**Timestamp**: 2025-01-01T12:00:00.123456
**Branch**: main

---

I'm working on a login feature
```

### Example Metadata File (`metadata.json`)

```json
{
  "name": "main",
  "created_at": "2025-01-01T10:00:00",
  "parent": null,
  "commits": [
    {
      "id": "20250101_120000_123456",
      "message": "Working on login feature",
      "timestamp": "2025-01-01T12:00:00.123456",
      "file": "branches/main/commits/20250101_120000_123456.md"
    }
  ],
  "last_commit": {
    "id": "20250101_120000_123456",
    "message": "Working on login feature",
    "timestamp": "2025-01-01T12:00:00.123456"
  },
  "updated_at": "2025-01-01T12:00:00.123456"
}
```

## Resources vs Tools

### Tools (Actions)
Tools are **functions** the AI can **call** to **do something**:

```python
@mcp.tool()
async def context_commit(...):
    # This DOES something (saves a commit)
    return result
```

**Usage:** "Save this context" → Gemini calls `context_commit`

### Resources (Data)
Resources are **data** the AI can **read** directly:

```python
@mcp.resource("context://main.md")
async def get_main_context() -> str:
    # This RETURNS data (the file content)
    return file_content
```

**Usage:** "What's in the main context?" → Gemini reads `context://main.md` directly

## Testing Without Gemini CLI

You can test the tools directly using the test script:

```bash
python test_example.py
```

This will:
1. Create a test branch
2. Make some commits
3. Retrieve context
4. Merge branches
5. Show you the results

Check `./context/branches/` to see the files created!

## Common Questions

### Q: Why does the server "hang" when I run it directly?
**A:** That's normal! It's waiting for JSON messages on stdin. Gemini CLI will send those messages.

### Q: How does Gemini know what tools are available?
**A:** When Gemini CLI starts, it calls a special MCP method `tools/list` which returns all available tools. FastMCP handles this automatically.

### Q: Can I use this with other AI assistants?
**A:** Yes! Any MCP-compatible client can use this server. The protocol is standardized.

### Q: What if I want to add more tools?
**A:** Just add more `@mcp.tool()` decorated functions! FastMCP will automatically expose them.

