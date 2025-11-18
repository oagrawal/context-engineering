# Context Engineering Tool MCP Server

A Python MCP server that implements Git-like context management for LLM agents using a local `./context/` folder structure.

## 🚀 Quick Start

**New to MCP servers?** Start here:
1. **[QUICK_START.md](QUICK_START.md)** - Simple explanation and examples
2. **[SETUP_GEMINI_CLI.md](SETUP_GEMINI_CLI.md)** - Step-by-step setup guide
3. **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - Detailed explanation with diagrams
4. **[CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md)** - Understanding the code

## Features

- **Context Commits**: Save current state as timestamped commits in branch-specific directories
- **Branch Management**: Create and manage branches with parent-child relationships
- **Branch Merging**: Combine branch histories with synthesis
- **Context Retrieval**: Query and retrieve relevant context from commit history
- **Resource Exposure**: Access main context and branch data as MCP resources

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Test the server (optional):
```bash
python test_example.py
```

## Configuration

### For Gemini CLI

**📖 See [SETUP_GEMINI_CLI.md](SETUP_GEMINI_CLI.md) for detailed step-by-step instructions.**

Add to your `settings.json`:

```json
{
  "mcpServers": {
    "context-engineering-tool": {
      "command": "python",
      "args": ["/absolute/path/to/GCC/server.py"]
    }
  }
}
```

**⚠️ Important:** Use an absolute path, not a relative path!

### For Director CLI

Add to your MCP server configuration:

```json
{
  "name": "context-engineering-tool",
  "command": "python",
  "args": ["/absolute/path/to/GCC/server.py"]
}
```

## Usage

The server provides four main tools that Gemini CLI can use:

1. **context_commit**: Save a commit to a branch
   - Example: "Save this to context: I'm working on feature X"
   
2. **context_branch**: Create a new branch
   - Example: "Create a branch called 'feature-auth'"
   
3. **context_merge**: Merge one branch into another
   - Example: "Merge feature-auth into main"
   
4. **context_retrieve**: Retrieve context from a branch's commit history
   - Example: "What context do we have about authentication?"

**💡 Tip:** Just ask Gemini naturally - it will automatically use the right tools!

## Directory Structure

```
./context/
  main.md                    # Global project roadmap
  branches/
    {branch_name}/
      commits/
        {timestamp}.md      # Individual commits
      metadata.json         # Branch metadata
```

## Resources

- `context://main.md` - Access the main context file
- `context://branches/{branch_name}` - Access branch metadata and recent commits

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Beginner-friendly introduction
- **[SETUP_GEMINI_CLI.md](SETUP_GEMINI_CLI.md)** - Detailed setup instructions
- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - How MCP servers work
- **[CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md)** - Code explanation

## Testing

Run the test script to verify everything works:

```bash
python test_example.py
```

This will create test branches, commits, and merges to demonstrate functionality.
