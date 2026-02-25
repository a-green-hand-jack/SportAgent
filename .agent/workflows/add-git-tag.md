---
description: Quickly create an annotated Git tag to mark a milestone, documenting what was achieved and what's planned next.
---

# Add Git Tag Workflow

Use this workflow whenever the user wants to mark a milestone in the current Git repository with a tag. The agent must **ask the user for all required information** before executing any commands.

## Step 1 — Gather Information (Ask the user)

Ask the user the following three questions **in a single message** (do NOT run any commands yet):

1. **Tag version**: What should the tag name be? (e.g. `v0.1.3`)
2. **Achievements**: What was accomplished in this phase? (provide a short bullet-point list of features/fixes completed)
3. **Next plans**: What is planned for the next phase? (provide a short bullet-point list of upcoming goals)

Wait for the user's answers before proceeding.

## Step 2 — Confirm the tag message (Show a preview)

After collecting the user's answers, **compose and display** the full annotated tag message for the user to review. The format should be:

```
Tag: <version>
Date: <current date, YYYY-MM-DD>

## ✅ This Phase — What Was Achieved
- <bullet 1>
- <bullet 2>
...

## 🚀 Next Phase — What's Planned
- <bullet 1>
- <bullet 2>
...
```

Ask the user: **"Does this look good? Should I go ahead and create the tag?"**

Wait for confirmation before proceeding.

## Step 3 — Verify the repository state

// turbo
Run the following command to check the current Git status and confirm we are on the right branch:

```bash
git -C /Users/jieke/Projects/SportAgent log --oneline -5 && git -C /Users/jieke/Projects/SportAgent status --short && git -C /Users/jieke/Projects/SportAgent tag --sort=-version:refname | head -5
```

This gives the last 5 commits, any uncommitted changes, and the 5 most recent existing tags.

## Step 4 — Create the annotated tag

// turbo
Run the following command to create the annotated tag. Use the exact version and message composed in Step 2:

```bash
git -C /Users/jieke/Projects/SportAgent tag -a "<version>" -m "<full_tag_message>"
```

Where:

- `<version>` is the tag name from the user (e.g. `v0.1.3`)
- `<full_tag_message>` is the full formatted message from Step 2

## Step 5 — Push the tag to remote (ask first)

Ask the user: **"Would you like to push the tag `<version>` to the remote repository (origin)?"**

If yes:
// turbo

```bash
git -C /Users/jieke/Projects/SportAgent push origin "<version>"
```

If no, inform the user that the tag was created locally and can be pushed later with:

```bash
git push origin <version>
```

## Step 6 — Confirm success

Report the outcome to the user:

- Show the tag that was created: `git -C /Users/jieke/Projects/SportAgent tag -n1 <version>`
- Confirm whether it was pushed to remote
- Remind the user they can view all tags with `git tag -n1 --sort=-version:refname`
