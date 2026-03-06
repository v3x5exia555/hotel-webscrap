---
description: How to push code changes to the repository using feature branches
---

# Git Push Workflow

**NEVER push directly to `main`.** Always create a feature branch first.

## Steps

1. Create a new feature branch from main:

```bash
git checkout -b feature/<short-descriptive-name>
```

Use prefixes like `feature/`, `fix/`, `chore/` depending on the change type.

2. Stage and commit your changes:

```bash
git add -A
git commit -m "<type>: <short description>"
```

3. Push the feature branch to origin:

```bash
git push origin feature/<short-descriptive-name>
```

4. Inform the user that the branch has been pushed and they can merge it to `main` when ready.

## Branch Naming Convention

| Prefix     | Use for                                     |
| ---------- | ------------------------------------------- |
| `feature/` | New features or enhancements                |
| `fix/`     | Bug fixes                                   |
| `chore/`   | Config changes, dependency updates, cleanup |
| `hotfix/`  | Urgent production fixes                     |

## Examples

```bash
# New scraper feature
git checkout -b feature/add-airbnb-retry

# Bug fix
git checkout -b fix/timeout-config

# Config/chore
git checkout -b chore/update-requirements
```

## Important

- Always branch from an up-to-date `main`:
  ```bash
  git checkout main
  git pull origin main
  git checkout -b feature/<name>
  ```
- Keep commits focused — one logical change per commit.
- Never force push to `main`.
