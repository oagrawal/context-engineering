# Step-by-Step: Connecting to Gemini CLI

## Prerequisites

- Python 3.8 or higher installed
- Gemini CLI installed and working
- Basic terminal knowledge

## Step 1: Install Dependencies

Open your terminal and navigate to the project directory:

```bash
cd /Users/omagr/Documents/Personal/Agents/GCC
```

Install the required Python package:

```bash
pip install -r requirements.txt
```

**Verify installation:**
```bash
python -c "import fastmcp; print('FastMCP installed successfully!')"
```

You should see: `FastMCP installed successfully!`

## Step 2: Test the Server (Optional but Recommended)

Run the test script to make sure everything works:

```bash
python test_example.py
```

You should see output like:
```
🧪 Testing Git Context Controller MCP Server
✅ Context structure initialized
📦 Test 1: Creating branch 'test-feature'...
...
✅ All tests completed!
```

Check that files were created:
```bash
ls -la ./context/branches/
```

## Step 3: Find Your Gemini CLI Settings File

The settings file location depends on your operating system:

### macOS
```bash
open ~/Library/Application\ Support/google-gemini-cli/settings.json
```

Or manually navigate to:
```
~/Library/Application Support/google-gemini-cli/settings.json
```

### Linux
```bash
nano ~/.config/google-gemini-cli/settings.json
```

Or manually navigate to:
```
~/.config/google-gemini-cli/settings.json
```

### Windows
Open in Notepad:
```
%APPDATA%\google-gemini-cli\settings.json
```

**If the file doesn't exist**, create it with this basic structure:
```json
{
  "mcpServers": {}
}
```

## Step 4: Add Our Server Configuration

Edit the `settings.json` file. It should look like this:

```json
{
  "mcpServers": {
    "git-context-controller": {
      "command": "python",
      "args": ["/Users/omagr/Documents/Personal/Agents/GCC/server.py"]
    }
  }
}
```

**⚠️ IMPORTANT:** Replace `/Users/omagr/Documents/Personal/Agents/GCC/server.py` with the **actual absolute path** to your `server.py` file.

**To find your absolute path:**
```bash
# On macOS/Linux:
pwd
# Copy the output and add /server.py to the end

# Example output:
# /Users/omagr/Documents/Personal/Agents/GCC
# So the path would be:
# /Users/omagr/Documents/Personal/Agents/GCC/server.py
```

**On Windows:**
```powershell
# In PowerShell:
(Get-Location).Path + "\server.py"
```

## Step 5: Verify the Configuration

Your `settings.json` should look like this (with your actual path):

```json
{
  "mcpServers": {
    "git-context-controller": {
      "command": "python",
      "args": ["/full/path/to/GCC/server.py"]
    }
  }
}
```

**Common mistakes to avoid:**
- ❌ Using relative paths (like `./server.py`)
- ❌ Using `~` or `$HOME` (use full absolute path)
- ❌ Missing quotes around the path
- ❌ Wrong Python command (use `python3` if `python` doesn't work)

## Step 6: Restart Gemini CLI

**Important:** You must restart Gemini CLI for changes to take effect.

1. Close Gemini CLI completely
2. Reopen Gemini CLI
3. Start a new conversation

## Step 7: Test the Connection

In Gemini CLI, try these commands:

### Test 1: Save Context
```
Save this to context: I'm working on a new project called "MyApp"
```

**Expected response:** Gemini should confirm it saved the context.

### Test 2: Create a Branch
```
Create a new branch called "feature-auth" for authentication work
```

**Expected response:** Gemini should confirm the branch was created.

### Test 3: Retrieve Context
```
What context do we have saved?
```

**Expected response:** Gemini should list the commits/context saved.

## Step 8: Verify Files Are Being Created

Check that the server is actually creating files:

```bash
# List branches
ls -la ./context/branches/

# View a commit (replace with actual filename)
cat ./context/branches/main/commits/*.md

# View metadata
cat ./context/branches/main/metadata.json
```

## Troubleshooting

### Problem: "Server not found" or "Connection failed"

**Solution 1: Check the path**
```bash
# Verify the path exists
ls -la /full/path/to/GCC/server.py
```

**Solution 2: Check Python command**
Try changing `"command": "python"` to `"command": "python3"` in settings.json

**Solution 3: Test server manually**
```bash
# This should hang (waiting for input) - that's normal!
python /full/path/to/GCC/server.py
# Press Ctrl+C to stop
```

### Problem: "Permission denied"

**Solution:**
```bash
chmod +x /full/path/to/GCC/server.py
```

### Problem: Tools not appearing in Gemini

**Solution 1:** Restart Gemini CLI completely

**Solution 2:** Check Gemini CLI logs for errors

**Solution 3:** Verify fastmcp is installed:
```bash
pip list | grep fastmcp
```

### Problem: "ModuleNotFoundError: No module named 'fastmcp'"

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

Or if using Python 3 specifically:
```bash
python3 -m pip install -r requirements.txt
```

### Problem: Server starts but tools don't work

**Check the server can read/write:**
```bash
# Test write permissions
touch ./context/test.txt
rm ./context/test.txt
```

## Advanced: Using Python Virtual Environment

If you want to isolate dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Update settings.json to use venv Python
{
  "mcpServers": {
    "git-context-controller": {
      "command": "/full/path/to/GCC/venv/bin/python",
      "args": ["/full/path/to/GCC/server.py"]
    }
  }
}
```

## Next Steps

Once connected, try:
1. Saving different types of context
2. Creating multiple branches
3. Merging branches
4. Retrieving old context
5. Asking Gemini to summarize your work

The AI will automatically use the tools when appropriate!

