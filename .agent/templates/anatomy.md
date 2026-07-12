---
related_files:
  - ../ANATOMY.md
  - src/example/foo.py
maintenance: |
  Structural changes update this file in the same PR.
  Citations must remain repo-relative and line-addressed.
---

# <directory> ANATOMY

## What this is
One paragraph.

## Components
| File | Role |
| --- | --- |
| `foo.py` | Owns X. Entry: `foo.py:42-90`. |

## Connections
Inbound:
- `api.py` calls `foo.build()` at `api.py:55`.

Outbound:
- `foo.py` writes through `storage.py:30-80`.

## Composition
Parent:
Children:

## State
| Path | Written by | Meaning |
| --- | --- | --- |

## Notes
Only gotchas that prevent wrong edits.
