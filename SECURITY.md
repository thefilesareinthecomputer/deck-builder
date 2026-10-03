# Security policy

## Supported versions

Fixes go into the latest release. Older releases don't get patches.

## What counts

Anything that breaks the confinement described in the README's Principles: a deck, workbook or imported `.pptx` that makes the engine read or write outside its own folders, or an MCP tool call that reaches outside the workspace. A known vulnerability in a locked dependency counts too.

## Reporting a vulnerability

Don't open a public issue. Report it privately on GitHub instead: on the repo's **Security** tab, choose **Report a vulnerability**, or go straight to https://github.com/thefilesareinthecomputer/deck-builder/security/advisories/new. Include what you found, how to reproduce it, the output of `deck-builder --version`, and what an attacker could do with it.

## What to expect

The maintainer replies in the private advisory, works out the fix there, and publishes the advisory with the release that fixes it.
