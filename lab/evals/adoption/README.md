# adoption evals

Synthetic smoke tests for `scripts/adopt-existing-repo.py`.

These tests build temporary Git repositories, run the adoption phases, and assert that:

- original tracked bytes are still present by content hash;
- root project files are moved under `lab/code/imported/<slug>/`;
- template governance passes after scaffold/normalize;
- the original project test command can still run from the imported root.
