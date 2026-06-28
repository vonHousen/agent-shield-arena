# <project-placeholder>

## Project's context

All the necessary context can be found in the [docs](docs/) directory. Among others:

- short project context in [project-brief.md](docs/project-brief.md),
- the design doc with a high-level specification in [design.md](docs/03-design.md).

## Development commands

- This project uses `uv` for package management (prepend all commands with `uv run`, e.g. `uv run pytest` instead of activating the virtual environment)
- This project uses `just` as a command runner. Run `just` to see all available recipes, or `just ci` to run the full CI pipeline locally to confirm your changes are valid.
- Assume commands are always run from the project's root directory, so DO NOT prefix commands with 'cd <project>' as it is redundant.

### Run tests
```bash
uv run pytest
```
Avoid unnecessary piping of `pytest` output to `cat` when running tests.

### Verify changes before pushing
```bash
just ci
```
Runs lint, validation, and tests in sequence — same checks as the GitLab CI pipeline.


## Coding guidelines

### Core principles

- You are an experienced, pragmatic software engineer. You don't over-engineer a solution when a simple one is possible.
- YOU MUST ALWAYS STOP and ask for clarification rather than making assumptions.
- YOU MUST make the SMALLEST reasonable changes to achieve the desired outcome.
- We STRONGLY prefer simple, clean, maintainable solutions over clever or complex ones. Readability and maintainability are PRIMARY CONCERNS, even at the cost of conciseness or performance.
- YOU MUST WORK HARD to reduce code duplication, even if the refactoring takes extra effort.

### General guidelines

- Use modern Python syntax:
  - use f-strings instead of % or .format wherever possible;
  - use type hints wherever possible (PEP 604, e.g. `int | None` instead of `Optional[int]`);
- use docstrings in all public functions and methods - check also if all the arguments are documented;
- keep imports at the beginning of the file - do NOT import inside functions;
- keep 'public()' functions above the '_private()' functions/methods;
- constants should be extracted into separate variables and should not repeat themselves, following the DRY principle;
- when logging exceptions, use .exception() instead of any other level + manual error/traceback formatting;
- avoid defensive programming - if something can go wrong, let's fail fast;
- NEVER use string references as type hints (nor from `from __future__ import annotations` nor `from typing import TYPE_CHECKING; if TYPE_CHECKING: ...` as it may hide circular imports) - use the actual type in type hints instead;
- break long functions into smaller ones, each with a single responsibility;
- avoid nested function definitions — extract inner functions to module-level or class methods; closures are acceptable only when they genuinely need to capture enclosing scope variables;
- avoid using getattr() / setattr() etc. - use direct attribute access instead, as it is safer and easier to maintain;
- do not overuse `type: ignore` — fix the underlying type issue instead. Only use it when the type checker is genuinely wrong and there's no reasonable way to satisfy it; when used, always add a comment explaining why the ignore is necessary;
- when implementing any python script to be used using CLI, use `typer`;

### Commit messages

Format: `action(scope): Description.`

- **action** — one of: `add`, `update`, `fix`, `remove`, `implement`, `enhance`.
- **scope** — the affected component or file in parentheses (e.g. `design`, `.gitignore`, `shared-contract`).
- **description** — sentence-case, ending with a period; brief explanation of what was done
- Optionally, add a more detailed explanation after a blank line (`\n\n`) following the subject line.
- Merge commits use the default `Merge branch '<branch-name>'` format.

### Designing software

- YAGNI. The best code is no code. Don't add features we don't need right now.
- When it doesn't conflict with YAGNI, architect for extensibility and flexibility.

### Code comments

- NEVER add comments explaining that something is "improved", "better", "new", "enhanced", or referencing what it used to be
- NEVER add instructional comments telling developers what to do ("copy this pattern", "use this instead")
- Comments should explain WHAT the code does or WHY it exists, not how it's better than something else
- YOU MUST NEVER remove code comments unless you can PROVE they are actively false. Comments are important documentation and must be preserved.

### Writing tests
- Keep the files & directories structure that resemble tested code. In single file, use classes (aka test suites) to gather all tests that cover single tested function.
- Keep their naming convention: 'test_X_when_Y_expect_Z'. However, when test functions are under class (aka test suite), you can omit repeating X part.
- Use the arrange/act/assert pattern by leaving comments that separate logical parts.
- Any magic numbers that are repeated within the same function should be extracted to local variables as constants at the beginning of the function. This improves readability and maintainability by making the values more semantic and reducing duplication within individual test methods.
- Mock external dependencies, not the code under test.
- Prefer specific assertions over generic ones.
