---
name: x-automation
description: Direct execution layer for posting to X (Twitter). Handles browser automation (cli.py), 3-tier retry logic, error handling, post-verification, and dedup enforcement. Use when content is approved for manual or automated publishing.
---

# X Automation — Stage 4

This skill handles the direct execution layer for posting to X (Twitter).

## Core Capabilities
- **Browser Automation (cli.py)**: Direct interface for X.com interactions.
- **3-Tier Retry Logic**: Robust handling of network and platform-level errors.
- **Error Handling**: Comprehensive capturing and reporting of execution failures.
- **Post-Verification**: Confirmation of successful distribution and engagement.
- **Dedup Enforcement**: Prevents duplicate posting of identical content.

## Workflow
1. **Approval**: Triggers only when content is approved for publishing.
2. **Execution**: Hands off to browser automation layer.
3. **Verification**: Verifies post visibility and handles initial engagement monitoring.
