# Repository guidance

Read `README.md` before changing the project. Prefer readable, auditable code over
clever abstractions. Never add device credentials, private keys, Wi-Fi data,
books, firmware images, backups, generated installers, or runtime evidence.

Every mutation of a mounted reader must be preceded by device detection and a
verified backup. Device-specific boot behavior belongs in an adapter; portable
backup, staging, profiles, and evidence behavior belongs in the core package.

Before committing:

1. Run `python3 -m unittest discover -s tests -v`.
2. Run `python3 -m compileall -q src tests`.
3. Run a secret scan over the exact staged tree.
4. Inspect `git diff --cached --name-only` before every push.
