# 📋 Claude CLI Commands Guide - V_Track Project

**Comprehensive reference for all custom slash commands available in your project**

---

## 🎯 Quick Comparison: All Commands

| Command | Purpose | Scope | Output | Use When |
|---------|---------|-------|--------|----------|
| **`/list-features`** | Auto-discover & catalog all features | Project-wide | JSON + Markdown catalog | Need feature inventory |
| **`/feature-files`** | Find files related to specific feature | Feature-specific | File tree + impact analysis | Need file locations for a feature |
| **`/prepare-context`** | Generate optimized context files | Feature-specific | Markdown context file | Setting up new chat session |
| **`/assessment`** | Evaluate product readiness | Project-wide | Comprehensive score & roadmap | Checking launch readiness |
| **`/cleanup-organize`** | Organize files into _misc/ structure | Directory-specific | Organized file tree | Cleaning up project |
| **`/explain-log`** | Debug and explain log output | Specific input | Analysis & explanation | Understanding error logs |
| **`/git`** | Auto git commit and push | Repository-wide | Git operations | Quick commits |

---

## 📊 Feature Discovery & Navigation Commands

### 1. **`/list-features`** - Project Feature Catalog
**Purpose**: Automatically discover and catalog all features in the V_Track project

**What it does**:
- Scans entire codebase structure
- Identifies routes, components, and modules
- Analyzes database models and API endpoints
- Creates structured feature inventory

**Output**:
- 📁 **`.claude/cache/features-catalog.json`** - Structured JSON with all 18 features
- 📄 **`docs/project-completion/FEATURES_CATALOG.md`** - Readable markdown index
- 💾 **Cache for fast reuse** - Rebuilds cache automatically

**Key Information Provided**:
```json
{
  "features": {
    "feature_name": {
      "name": "Display Name",
      "category": "Category",
      "confidence": "high/medium/low",
      "keywords": ["keyword1", "keyword2"],
      "files": ["file1.py", "file2.js"],
      "routes": ["/api/endpoint"],
      "description": "What it does"
    }
  }
}
```

**Use Cases**:
- ✅ Get complete overview of project capabilities
- ✅ Understand project architecture
- ✅ Find features by category
- ✅ Feed data to other commands

**Example**:
```bash
/list-features
```

**Output Size**: ~20KB JSON + 10KB Markdown catalog

---

### 2. **`/feature-files [FEATURE_NAME]`** - Find Feature Files
**Purpose**: Discover all files related to a specific feature/functionality

**What it does**:
- Searches for feature by name or keyword
- Finds all related files (frontend, backend, config)
- Analyzes file dependencies and relationships
- Assesses impact of changes

**Output**:
- 📋 **Categorized file tree** - Organized by role (core, supporting, UI, test, config)
- 📊 **Impact analysis** - Risk levels: High/Medium/Low
- 📈 **Dependency graph** - Shows how files connect
- 📝 **Modification guide** - What needs testing

**File Categories Identified**:
1. **Core Files** (High Impact) - Main feature logic
2. **Supporting Files** (Medium Impact) - Helpers & utilities
3. **UI Files** (Medium Impact) - Components & styles
4. **Test Files** (Low Impact) - Tests and mocks
5. **Config Files** (Variable Impact) - Routes, API endpoints

**Use Cases**:
- ✅ Before refactoring a feature
- ✅ Understanding feature scope
- ✅ Impact analysis before changes
- ✅ Finding dependent files
- ✅ Code review preparation

**Example**:
```bash
/feature-files authentication
/feature-files video processing
/feature-files license management
```

**Output Size**: ~15-30KB markdown report + cached JSON data

---

## 📝 Context Preparation & Development

### 3. **`/prepare-context [FEATURE_NAME] [--scope TYPE]`** - Generate Context Files
**Purpose**: Create optimized context files for Claude chat sessions

**What it does**:
- Intelligently collects files related to feature
- Optimizes file content (removes noise, compresses code)
- Generates chat-ready markdown context
- Maintains cache for fast reuse

**Smart Features**:
- 🧠 **Auto cache checking** - Reuses if source files unchanged
- 🔄 **Auto feature catalog** - Runs /list-features if needed
- 📏 **Size optimization** - Keeps to 150KB (50K tokens)
- 🎯 **Smart content extraction** - Preserves important code

**Output**:
- 📄 **`.md` file in `/docs/`** - Date-stamped context file
- 💾 **Cache entry** - Reusable for 3 days
- 📑 **Index update** - Listed in context-index.md

**File Naming Pattern**:
```
2025-01-15-context-user-authentication-full.md
2025-01-15-context-payment-core.md
2025-01-15-context-dashboard-frontend.md
```

**Scope Options**:
- `full` - All related files (default)
- `core` - Core implementation only
- `frontend` - UI files only
- `backend` - API/server files only
- `config` - Configuration files only

**Use Cases**:
- ✅ Starting new coding session on a feature
- ✅ Sharing feature context with teammates
- ✅ Reducing token usage (pre-formatted context)
- ✅ Archiving feature documentation

**Example**:
```bash
/prepare-context authentication
/prepare-context payment --scope core
/prepare-context dashboard --frontend
```

**Output Size**: 80-150KB markdown file (~50K tokens)

**Token Estimation**:
- 1 token ≈ 3 characters
- Target: 150KB ≈ 50K tokens (safe)
- Warning: 200KB ≈ 65K tokens
- Maximum: 250KB ≈ 80K tokens

---

## 📈 Project Assessment & Quality

### 4. **`/assessment`** - Product Readiness Assessment
**Purpose**: Comprehensive evaluation of V_Track's launch readiness across 8 dimensions

**Assessment Framework** (Weighted):
1. **Technical Architecture** (15%) - Design, database, scalability
2. **Feature Completeness** (20%) - Core features, integration, workflows
3. **Security & Compliance** (18%) - Auth, encryption, privacy, GDPR
4. **Testing & QA** (12%) - Coverage, bugs, quality metrics
5. **User Experience** (10%) - UI design, usability, onboarding
6. **Deployment & Operations** (10%) - Automation, monitoring, backups
7. **Business Readiness** (8%) - Licensing, payments, market positioning
8. **Documentation & Support** (7%) - User docs, technical docs, support

**Scoring System** (1-10):
- **1-2** ❌ Critical Issues
- **3-4** ⚠️ Significant Concerns
- **5-6** ⚖️ Acceptable (minimum standards)
- **7-8** ✅ Good (minor improvements)
- **9-10** 🌟 Excellent (exceeds standards)

**Output Includes**:
- 📊 **Weighted dimension scores** - Each of 8 areas rated
- 📈 **Trend analysis** - Changes since last assessment
- 🎯 **Executive summary** - Key strengths & critical gaps
- 📋 **Action plan** - Immediate/short-term/medium-term/long-term
- ⚠️ **Risk assessment** - Launch & business risks
- 🎯 **Success metrics** - Post-launch KPIs

**Launch Readiness Classifications**:
- **8.5-10.0** - LAUNCH READY (exceeds standards)
- **7.0-8.4** - LAUNCH READY (meets standards, minor improvements)
- **5.5-6.9** - PARTIALLY READY (significant improvements needed)
- **4.0-5.4** - NOT READY (major issues must be resolved)
- **1.0-3.9** - NOT READY (critical foundational issues)

**Use Cases**:
- ✅ Pre-launch readiness check
- ✅ Milestone assessments
- ✅ Tracking improvement over time
- ✅ Identifying critical gaps
- ✅ Resource allocation planning
- ✅ Stakeholder reporting

**Output Size**: 50-80KB comprehensive report

---

## 🧹 Maintenance & Organization

### 5. **`/cleanup-organize [DIRECTORY]`** - File Organization
**Purpose**: Comprehensive cleanup and organization using _misc/ folder system

**What it does**:
- Creates standardized _misc/ folder structure
- Classifies files into categories
- Safely moves non-essential files
- Generates organization report

**Folder Structure Created**:
```
_misc/
├── backup/     - Old versions, replaced code
├── demo/       - Demo files, prototypes, examples
├── fix/        - Temporary patches, hotfixes
├── test/       - Experimental, old test files
├── docs/       - Notes, specs, drafts
└── assets/     - Unused images, media files
```

**File Categories Handled**:
- Unused code and dead imports
- Demo and prototype files
- Temporary workarounds
- Old/experimental tests
- Draft documentation
- Unused media assets

**Use Cases**:
- ✅ Cleaning up project after development
- ✅ Organizing accumulated experimental code
- ✅ Preparing codebase for delivery
- ✅ Archiving old code versions

**Example**:
```bash
/cleanup-organize backend
/cleanup-organize frontend
```

---

## 🔍 Debugging & Support

### 6. **`/explain-log`** - Log Analysis & Debugging
**Purpose**: Analyze and explain log output (automatically available when you need it)

**What it does**:
- Parses error/debug logs
- Identifies root causes
- Suggests fixes
- Explains what went wrong

**Use Cases**:
- ✅ Understanding error messages
- ✅ Debugging test failures
- ✅ Analyzing crash logs
- ✅ Trace execution flow

---

## 🔧 Git Operations

### 7. **`/git`** - Auto Git Commit & Push
**Purpose**: Simple automated git commit and push

**What it does**:
- Detects file changes
- Creates automatic commit message with timestamp
- Stages and commits changes
- Pushes to remote

**Output**:
```
Auto commit 14:30:45
✓ Done
```

**Use Cases**:
- ✅ Quick commits without manual messages
- ✅ Automated backup to remote

---

## 🎯 Command Usage Patterns

### Pattern 1: Feature Discovery Workflow
```bash
# Step 1: Get feature catalog
/list-features

# Step 2: Find files for specific feature
/feature-files authentication

# Step 3: Create context for coding session
/prepare-context authentication --scope full

# Result: Ready to code with full context
```

### Pattern 2: Pre-Launch Assessment
```bash
# Run comprehensive assessment
/assessment

# Review results and identify gaps
# Create action plan based on recommendations

# Result: Know exactly what needs fixing before launch
```

### Pattern 3: Project Cleanup
```bash
# Organize project files
/cleanup-organize backend

# Create context for clean codebase
/prepare-context video-processing

# Quick commit
/git

# Result: Clean, organized project ready for delivery
```

---

## 📊 Command Capability Matrix

| Capability | /list-features | /feature-files | /prepare-context | /assessment | /cleanup | /explain-log | /git |
|------------|---|---|---|---|---|---|---|
| **Find features** | ✅ | ✅ | - | - | - | - | - |
| **Show file locations** | - | ✅ | ✅ | - | - | - | - |
| **Impact analysis** | - | ✅ | - | - | - | - | - |
| **Generate context** | - | - | ✅ | - | - | - | - |
| **Quality assessment** | - | - | - | ✅ | - | - | - |
| **File organization** | - | - | - | - | ✅ | - | - |
| **Debug/explain** | - | - | - | - | - | ✅ | - |
| **Git automation** | - | - | - | - | - | - | ✅ |

---

## 🚀 Command Performance

| Command | Execution Time | Cache Benefit | Output Size |
|---------|---|---|---|
| `/list-features` | 30-60s (first run) | 2-5s (cached) | 30KB |
| `/feature-files` | 20-40s | 1-2s (cached) | 15-30KB |
| `/prepare-context` | 45-90s (first run) | 2-3s (cached) | 80-150KB |
| `/assessment` | 15-30s | N/A (always fresh) | 50-80KB |
| `/cleanup-organize` | 30-60s | N/A | 10-20KB |
| `/explain-log` | 10-20s | N/A | 5-10KB |
| `/git` | 5-10s | N/A | 1KB |

---

## 💾 Cache Strategy

### What Gets Cached
- ✅ **Features catalog** (`.claude/cache/features-catalog.json`) - Valid 7 days
- ✅ **Feature analysis** (`.claude/cache/feature-data-{feature}.json`) - Valid 7 days
- ✅ **Context files** (`.claude/cache/generated-contexts/`) - Valid 3 days

### What Doesn't Get Cached
- ❌ Assessment results (always fresh)
- ❌ Git operations
- ❌ Log explanations

### Cache Management
- Automatic cleanup of expired cache (>7 days)
- Invalid cache removed (deleted source files)
- Manual refresh: Use `--refresh` flag

---

## 🎓 Best Practices

### ✅ DO:
1. **Run `/list-features` first** - Build feature catalog
2. **Use `/feature-files` before refactoring** - Know dependencies
3. **Generate context with `/prepare-context`** - Optimize token usage
4. **Use assessment for milestones** - Track progress
5. **Leverage caching** - Commands are much faster on repeat runs
6. **Clean up regularly** - Use `/cleanup-organize` to stay organized

### ❌ DON'T:
1. ❌ Skip feature discovery - Might miss dependencies
2. ❌ Make changes without impact analysis
3. ❌ Ignore assessment warnings - Address critical gaps
4. ❌ Commit without context - Always know what you're changing
5. ❌ Leave old experimental code in main directories - Use _misc/

---

## 📞 Command Help & Documentation

For detailed information on any command:
- Check `.claude/commands/{command-name}.md` file
- Look in `.claude/instructions.md` for general guidelines
- Review cache location for previous results

---

## 🔄 Integration Points

**These commands work together**:
- `list-features` → feeds into `feature-files`
- `feature-files` → feeds into `prepare-context`
- `prepare-context` → context for new development
- `assessment` → identifies improvements needed
- `cleanup-organize` → prepares for delivery

---

## 📋 Summary Table: When to Use Each Command

| Situation | Command | Output | Next Step |
|-----------|---------|--------|-----------|
| Don't know project structure | `/list-features` | Feature catalog | Use /feature-files for details |
| Need to modify a feature | `/feature-files` + `/prepare-context` | File map + context | Code with full understanding |
| Starting new chat session | `/prepare-context` | Context file | Paste context into chat |
| Before launch | `/assessment` | Readiness score | Address critical gaps |
| Project cleanup time | `/cleanup-organize` | Organized _misc/ | Commit clean codebase |
| Debugging issue | `/explain-log` | Error analysis | Apply suggested fix |
| Quick save to git | `/git` | Auto commit | Code continues... |

---

**Last Updated**: 2025-01-30
**V_Track Version**: 2.1.0
**Commands Available**: 7 custom + built-in slash commands
