# 🔌 Setup Guide — Making Agents Actually Use paper2tex

> **The skill exists. Now you need to tell your agent about it.**
> Without setup, agents will try to convert your paper themselves (badly).

---

## The Problem

You clone this repo. You tell Claude Code "convert my paper to IEEE format."
Claude Code **ignores** the skill and does it the ChatGPT way — re-typing your
math through its tokenizer, producing `?` symbols everywhere.

Why? Because the agent **doesn't know this skill exists** unless you set it up.

---

## Setup by Agent Platform

### 🟣 Antigravity (AGY)

Antigravity discovers skills from configured skill directories.

**Option A: Symlink into your skills directory (recommended)**
```powershell
# Clone once
git clone https://github.com/redfries/paper2tex.git C:\tools\paper2tex

# Create a symlink so AGY finds it
# (Replace the target path with wherever AGY looks for skills)
New-Item -ItemType Junction -Path "$env:USERPROFILE\.gemini\config\skills\paper2tex" -Target "C:\tools\paper2tex"
```

**Option B: Clone directly into your skills directory**
```powershell
cd $env:USERPROFILE\.gemini\config\skills
git clone https://github.com/redfries/paper2tex.git
```

AGY reads the `SKILL.md` frontmatter automatically. Once it's in the skills directory, saying "convert my paper to LaTeX" will trigger it.

---

### 🟠 Claude Code

Claude Code reads project-level instruction files.

**Option A: Per-project setup (if you're working in a paper directory)**
```powershell
# In your paper's directory (where your .docx lives)
git clone https://github.com/redfries/paper2tex.git

# Create the Claude instruction file
@"
When asked to convert a .docx to LaTeX or format a paper for a conference:
1. Read paper2tex/AGENTS.md for the complete workflow
2. Follow the steps EXACTLY — do not improvise
3. Use the deterministic scripts (extract_math, extract_tables, etc.)
4. NEVER rewrite equations or text yourself — use the registry outputs
"@ | Out-File -Encoding utf8 CLAUDE.md
```

**Option B: Global custom instructions**
Go to Claude Code settings → Custom Instructions → paste:
```
When I ask you to convert a .docx paper to LaTeX or format for a conference,
look for paper2tex/AGENTS.md in the project and follow it step by step.
If paper2tex is not in the project, clone it:
git clone https://github.com/redfries/paper2tex.git
Then read AGENTS.md and follow the pipeline.
```

---

### 🔵 Cursor

Cursor reads `.cursorrules` in the project root.

```powershell
# In your paper's directory
git clone https://github.com/redfries/paper2tex.git

# Create the rules file
@"
When asked to convert a .docx to LaTeX or format a paper for a conference:
1. Read paper2tex/AGENTS.md for the complete workflow
2. Run the scripts in paper2tex/scripts/ — do not do the conversion manually
3. NEVER rewrite the student's text, math, or tables — use registry outputs
4. ALWAYS run paper2tex/scripts/verify.py before delivering results
"@ | Out-File -Encoding utf8 .cursorrules
```

---

### 🟢 OpenCode / Windsurf / Cline / Aider / Other

Most agents support one of these discovery mechanisms:

| Mechanism | File to create in project root |
|-----------|-------------------------------|
| `AGENTS.md` | ✅ Already included in the repo |
| `.cursorrules` | ✅ Instructions above |
| `CLAUDE.md` | ✅ Instructions above |
| `rules.md` or `INSTRUCTIONS.md` | Copy `AGENTS.md` → rename |
| System prompt / custom instructions | Paste the text from Option B above |

**Universal fallback — just tell the agent explicitly:**
```
Read the file paper2tex/AGENTS.md and follow those instructions
to convert my paper.docx to IEEE conference format.
Do NOT try to convert it yourself.
```

---

## The Nuclear Option: Force It

If your agent keeps ignoring the skill and doing its own thing, **be explicit**:

```
IMPORTANT: Do NOT convert my docx to LaTeX yourself.
Use the paper2tex pipeline in this directory.
Run: python paper2tex/scripts/extract.py paper.docx work/
Then read paper2tex/AGENTS.md for the remaining steps.
I repeat: do NOT re-type my equations or text. Use the script outputs.
```

This works because agents prioritize explicit user instructions over their default behavior.

---

## Verify It's Working

After setup, test with a simple prompt:

```
What tools do you have available for converting docx to LaTeX?
```

If the agent mentions `paper2tex`, `SKILL.md`, `extract.py`, or the pipeline — it found the skill ✅

If it says "I can help you convert that" without mentioning any tools — setup failed ❌

---

## Quick Reference: What Goes Where

```
your_paper_folder/
├── paper.docx                    ← Your document
├── figures/                      ← Your figures
├── CLAUDE.md                     ← Tells Claude Code to use paper2tex
├── .cursorrules                  ← Tells Cursor to use paper2tex
└── paper2tex/                    ← The cloned skill repo
    ├── AGENTS.md                 ← Agent reads this
    ├── SKILL.md                  ← Antigravity reads this
    ├── PREREQUISITES.md          ← Student reads this
    ├── README.md                 ← Everyone reads this
    ├── .claude/instructions.md   ← Backup discovery for Claude
    ├── .cursor/rules             ← Backup discovery for Cursor
    └── scripts/                  ← The actual pipeline
```

---

## Still Not Working?

1. **Check the agent can see the files**: Ask "list the files in paper2tex/"
2. **Force-read the instructions**: Say "read paper2tex/AGENTS.md and summarize it"
3. **Be explicit about scripts**: Say "run `python paper2tex/scripts/preflight.py`"
4. **Last resort**: Copy-paste the contents of `AGENTS.md` directly into the chat

The goal is to get the agent to **run the scripts** instead of doing the conversion in its head.
That's the entire point — scripts are deterministic, LLMs are not.
