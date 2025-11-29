# Context Management System - Test Suite

This document provides comprehensive tests for the context management CLI tool.

## Setup

Before running tests, ensure the tool is installed:
```bash
pip install -e .
```

## Test Environment Setup

```bash
# Create a test directory
mkdir -p test-context
cd test-context

# Initialize git repo (optional, for git commit tests)
git init

# Or use existing repo
```

---

## Test Categories

### 1. Branch Operations

#### Test 1.1: Create Empty Branch
```bash
context branch test-main --empty
context info --level project
# Expected: Shows "test-main" branch, current branch is "test-main"
```

#### Test 1.2: Create Branch from Existing
```bash
context branch feature-auth --from test-main
context info --level project
# Expected: Shows both branches, current is "feature-auth"
```

#### Test 1.3: Duplicate Branch Name (Should Fail)
```bash
context branch test-main --empty
# Expected: Error "Branch 'test-main' already exists"
```

#### Test 1.4: Invalid Branch Name (Should Fail)
```bash
context branch "invalid/name" --empty
# Expected: Error "Invalid branch name"
```

#### Test 1.5: Create Branch Without Current Branch (Should Fail)
```bash
rm .context/.current_branch
context branch new-branch
# Expected: Error "No current branch. Use --empty..."
```

#### Test 1.6: Branch from Non-existent Branch (Should Fail)
```bash
context branch new-branch --from nonexistent
# Expected: Error "Source branch 'nonexistent' does not exist"
```

---

### 2. Log Operations

#### Test 2.1: Add Single Log Entry
```bash
context branch test-logs --empty
context log "First reasoning step"
cat .context/branches/test-logs/log.yaml
# Expected: YAML file contains one log entry with timestamp
```

#### Test 2.2: Add Multiple Log Entries
```bash
context log "Second reasoning step"
context log "Third reasoning step"
context info --level session --branch test-logs
# Expected: Shows 3 log entries
```

#### Test 2.3: Add Log Without Branch (Should Fail)
```bash
rm .context/.current_branch
context log "Test"
# Expected: Error "No current branch"
```

---

### 3. Commit Operations

#### Test 3.1: Commit with Message Only
```bash
context branch test-commit --empty
context commit --message "Initial commit"
context info --level branch --branch test-commit
# Expected: Shows 1 commit with the message
```

#### Test 3.2: Commit Without Message (Uses Default)
```bash
context commit
context info --level branch --branch test-commit
# Expected: Shows 2 commits, second has "Progress update"
```

#### Test 3.3: Commit with Logs (All Logs Included)
```bash
context branch test-commit-logs --empty
context log "Step 1: Analyzed requirements"
context log "Step 2: Designed solution"
context commit --message "Implemented feature"
cat .context/branches/test-commit-logs/commits.yaml
# Expected: Commit includes both log entries in "Reasoning steps"
cat .context/branches/test-commit-logs/log.yaml
# Expected: Log file is empty (logs cleared after commit)
```

#### Test 3.4: Commit with Specific Log Range (Last N)
```bash
context branch test-range --empty
context log "Log 1"
context log "Log 2"
context log "Log 3"
context log "Log 4"
context log "Log 5"
context commit --message "Commit with last 3 logs" --from-log 3
cat .context/branches/test-range/commits.yaml
# Expected: Commit includes only last 3 logs (Log 3, 4, 5)
cat .context/branches/test-range/log.yaml
# Expected: Log file contains only first 2 logs (Log 1, 2)
```

#### Test 3.5: Commit with Log Range (Start:End)
```bash
context branch test-range2 --empty
context log "Log 0"
context log "Log 1"
context log "Log 2"
context log "Log 3"
context commit --message "Commit with range" --from-log "1:3"
cat .context/branches/test-range2/commits.yaml
# Expected: Commit includes logs 1 and 2 (indices 1:3)
cat .context/branches/test-range2/log.yaml
# Expected: Log file contains Log 0 and Log 3
```

#### Test 3.6: Commit with Invalid Log Range (Should Fail)
```bash
context branch test-invalid --empty
context log "Test"
context commit --from-log "abc"
# Expected: Error "Invalid log range format"
```

#### Test 3.7: Commit with Out of Bounds Range (Should Fail)
```bash
context branch test-bounds --empty
context log "Test"
context commit --from-log "0:100"
# Expected: Error or warning about out of bounds
```

#### Test 3.8: Commit Accumulates Previous Progress
```bash
context branch test-progress --empty
context commit --message "First commit"
context commit --message "Second commit"
context commit --message "Third commit"
cat .context/branches/test-progress/commits.yaml
# Expected: Third commit's previous_progress includes first and second commits
```

#### Test 3.9: Commit Without Branch (Should Fail)
```bash
rm .context/.current_branch
context commit
# Expected: Error "No current branch"
```

---

### 4. Merge Operations

#### Test 4.1: Merge Single Branch
```bash
context branch merge-base --empty
context commit --message "Base commit"

context branch feature-a --from merge-base
context commit --message "Feature A work"

context branch merge-target --from merge-base
context merge feature-a
context info --level branch --branch merge-target
# Expected: Shows commits from both branches, including merge commit
```

#### Test 4.2: Merge Multiple Branches
```bash
context branch multi-base --empty
context commit --message "Base"

context branch feat1 --from multi-base
context commit --message "Feature 1"

context branch feat2 --from multi-base
context commit --message "Feature 2"

context branch merge-all --from multi-base
context merge feat1 feat2
context info --level branch --branch merge-all
# Expected: Shows commits from all branches
```

#### Test 4.3: Merge with Logs (Logs Tagged with Source)
```bash
context branch merge-logs-base --empty
context log "Base log"

context branch merge-logs-feat --from merge-logs-base
context log "Feature log"
context commit --message "Feature commit"

context branch merge-logs-target --from merge-logs-base
context merge merge-logs-feat
cat .context/branches/merge-logs-target/log.yaml
# Expected: Logs from merged branch have source_branch tag
```

#### Test 4.4: Merge Non-existent Branch (Should Fail)
```bash
context branch test-merge --empty
context merge nonexistent
# Expected: Error "Branch 'nonexistent' does not exist"
```

#### Test 4.5: Merge Branch into Itself (Should Fail)
```bash
context branch self-merge --empty
context merge self-merge
# Expected: Error "Cannot merge branch into itself"
```

#### Test 4.6: Merge Without Current Branch (Should Fail)
```bash
rm .context/.current_branch
context merge some-branch
# Expected: Error "No current branch"
```

#### Test 4.7: Merge Preserves Common History
```bash
context branch common-base --empty
context commit --message "Common commit 1"
context commit --message "Common commit 2"

context branch branch-a --from common-base
context commit --message "Unique to A"

context branch branch-b --from common-base
context commit --message "Unique to B"

context branch merge-test --from common-base
context merge branch-a branch-b
cat .context/branches/merge-test/commits.yaml
# Expected: Only unique commits merged, not common ones
```

---

### 5. Info Operations

#### Test 5.1: Project Level Info (Text Format)
```bash
context info --level project
# Expected: Shows main.md content, list of branches, current branch
```

#### Test 5.2: Project Level Info (Markdown Format)
```bash
context info --level project --format markdown
# Expected: Same as above but formatted as markdown
```

#### Test 5.3: Project Level Info (YAML Format)
```bash
context info --level project --format yaml
# Expected: Structured YAML output
```

#### Test 5.4: Branch Level Info (Current Branch)
```bash
context branch test-info --empty
context commit --message "Test commit"
context info --level branch
# Expected: Shows branch info for current branch
```

#### Test 5.5: Branch Level Info (Specific Branch)
```bash
context info --level branch --branch test-info
# Expected: Shows branch info for test-info
```

#### Test 5.6: Branch Level Info (Non-existent Branch - Should Fail)
```bash
context info --level branch --branch fake-branch
# Expected: Error "Branch 'fake-branch' does not exist"
```

#### Test 5.7: Session Level Info (With Logs)
```bash
context branch test-session --empty
context log "Log entry 1"
context log "Log entry 2"
context info --level session --branch test-session
# Expected: Shows all log entries
```

#### Test 5.8: Session Level Info (No Logs)
```bash
context branch test-empty-session --empty
context info --level session --branch test-empty-session
# Expected: Shows "Log entries: 0"
```

#### Test 5.9: Info Without Branch (Uses Current)
```bash
context branch test-current --empty
context info --level branch
# Expected: Shows info for test-current (current branch)
```

---

### 6. Error Handling & Edge Cases

#### Test 6.1: Invalid Command
```bash
context invalid-command
# Expected: Error showing available commands
```

#### Test 6.2: Missing Required Arguments
```bash
context branch
# Expected: Error about missing branch name
```

#### Test 6.3: Verbose Mode
```bash
context branch test-verbose --empty -v
context log "Test" -v
context commit --message "Test" -v
# Expected: Additional verbose output
```

#### Test 6.4: Empty Branch Operations
```bash
context branch empty-test --empty
context info --level branch --branch empty-test
# Expected: Handles gracefully, shows 0 commits
```

#### Test 6.5: Branch with No Commits
```bash
context branch no-commits --empty
context info --level branch --branch no-commits
# Expected: Shows branch exists but no commits
```

#### Test 6.6: Commit on Branch with No Previous Commits
```bash
context branch first-commit --empty
context commit --message "First"
cat .context/branches/first-commit/commits.yaml
# Expected: Branch purpose uses default, previous_progress is "Initial state"
```

---

### 7. Integration Tests

#### Test 7.1: Complete Workflow
```bash
# Initialize
context branch main --empty
context log "Project started"
context commit --message "Initial setup"

# Create feature branch
context branch feature-auth --from main
context log "Analyzed auth requirements"
context log "Designed OAuth flow"
context commit --message "Auth design"

# Work on main
context branch main  # Need to manually set or create new branch
# Actually, create a new branch to switch:
context branch main-continue --from main
context log "Fixed bug in main"
context commit --message "Bug fix"

# Merge feature
context branch main-final --from main-continue
context merge feature-auth
context info --level project
# Expected: Shows merged state
```

#### Test 7.2: Multiple Branches and Merges
```bash
context branch integration-base --empty
context commit --message "Base"

context branch feat1 --from integration-base
context log "Feat1 step 1"
context log "Feat1 step 2"
context commit --message "Feat1 done"

context branch feat2 --from integration-base
context log "Feat2 step 1"
context commit --message "Feat2 done"

context branch feat3 --from integration-base
context log "Feat3 step 1"
context commit --message "Feat3 done"

context branch integration-merge --from integration-base
context merge feat1 feat2 feat3
context info --level branch --branch integration-merge
# Expected: All features merged correctly
```

#### Test 7.3: Log Clearing After Commit
```bash
context branch log-clear-test --empty
context log "Log 1"
context log "Log 2"
context log "Log 3"
cat .context/branches/log-clear-test/log.yaml
# Expected: 3 logs

context commit --message "Commit 1"
cat .context/branches/log-clear-test/log.yaml
# Expected: Empty (all logs cleared)

context log "Log 4"
context log "Log 5"
context commit --message "Commit 2" --from-log 1
cat .context/branches/log-clear-test/log.yaml
# Expected: Only Log 4 (Log 5 was cleared)
```

#### Test 7.4: Git Integration (If in Git Repo)
```bash
git init  # If not already initialized
context branch git-test --empty
context commit --message "Test commit"
git log --oneline | head -1
# Expected: Git commit created with context commit message
```

---

### 8. Data Integrity Tests

#### Test 8.1: YAML File Validity
```bash
context branch yaml-test --empty
context log "Test"
context commit --message "Test"
python3 -c "import yaml; yaml.safe_load(open('.context/branches/yaml-test/commits.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('.context/branches/yaml-test/log.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('.context/branches/yaml-test/metadata.yaml'))"
# Expected: All YAML files are valid
```

#### Test 8.2: Branch Structure
```bash
context branch structure-test --empty
ls -la .context/branches/structure-test/
# Expected: commits.yaml, log.yaml, metadata.yaml all exist
```

#### Test 8.3: Current Branch Pointer
```bash
context branch pointer-test --empty
cat .context/.current_branch
# Expected: Contains "pointer-test"
```

---

### 9. Performance & Scale Tests

#### Test 9.1: Many Logs
```bash
context branch many-logs --empty
for i in {1..100}; do
    context log "Log entry $i"
done
context commit --message "Commit with 100 logs"
# Expected: Handles large number of logs
```

#### Test 9.2: Many Commits
```bash
context branch many-commits --empty
for i in {1..50}; do
    context commit --message "Commit $i"
done
context info --level branch --branch many-commits
# Expected: Shows all 50 commits
```

#### Test 9.3: Many Branches
```bash
for i in {1..20}; do
    context branch "branch-$i" --empty
done
context info --level project
# Expected: Lists all 20 branches
```

---

## Test Execution Script

You can create a test runner script:

```bash
#!/bin/bash
# test-runner.sh

set -e  # Exit on error

echo "Running Context Management System Tests..."

# Setup
TEST_DIR="test-context-$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
git init > /dev/null 2>&1 || true

# Run tests (add your test commands here)
echo "Test 1.1: Create empty branch"
context branch test-main --empty
context info --level project | grep -q "test-main" && echo "✓ Pass" || echo "✗ Fail"

# Cleanup
cd ..
rm -rf "$TEST_DIR"

echo "Tests complete!"
```

---

## Expected Behaviors Summary

### Logs
- Logs are cleared after commit (unless `--from-log` specifies a subset)
- All logs included by default in commit if no `--from-log` specified
- Logs can be selected by range or count
- Logs are tagged with source branch when merged

### Commits
- Commits accumulate previous progress
- Branch purpose comes from first commit
- Commit contribution includes logs if available
- Commits have unique IDs (timestamps)

### Branches
- Branches are independent contexts
- Can copy from existing branches
- Can create empty branches
- Current branch tracked in `.current_branch`

### Merges
- Only unique commits are merged (common history preserved)
- Logs are tagged with source branch
- Merge commits are created
- Metadata is merged (current takes precedence)

### Info
- Project level: Shows all branches and main.md
- Branch level: Shows commits and metadata
- Session level: Shows log entries
- Multiple output formats supported

---

## Notes

- All tests assume you're in a directory with git initialized (for git commit tests)
- Some tests require manual branch switching (create new branch to "switch")
- Tests can be run individually or as a suite
- Clean up test branches between test runs if needed

