---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
  source: https://github.com/vercel-labs/web-interface-guidelines (command.md, commit 4ecfb9f del 2026-10-05)
  downloaded: "2026-11-26"
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Read `guidelines.md`, in this skill's folder
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in `guidelines.md`
4. Output findings in the terse `file:line` format

## Guidelines

The rules and the output format are in `guidelines.md`, a fixed copy reviewed on 2026-11-26. Never fetch them from the network. Updating the copy means downloading it apart, reviewing it and replacing the file in both skill folders.

The "Content & Copy" and "Typography" rules apply only where they don't contradict the project's language and style. In Spanish and Catalan: sentence case, not Title Case (only the first word is capitalised), and angle quotes «», not curly quotes.

## Usage

When a user provides a file or pattern argument:
1. Read `guidelines.md`
2. Read the specified files
3. Apply all rules from `guidelines.md`
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.
