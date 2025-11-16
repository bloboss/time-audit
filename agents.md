# Development Workflow

This document outlines the correct workflow to run before making a commit to ensure code quality and consistency.

## Pre-Commit Checklist

Run all of the following commands in order to ensure your changes meet the project's quality standards:

### 1. Code Formatting with Black

Black automatically formats Python code to ensure consistent style across the codebase.

```bash
black src/ tests/
```

**Expected outcome:** All files formatted successfully.

### 2. Linting with Ruff

Ruff checks for code quality issues, unused imports, and style violations.

```bash
ruff check src/ tests/
```

**Expected outcome:** "All checks passed!" If there are fixable errors, run:

```bash
ruff check --fix src/ tests/
```

For more aggressive fixes (including import sorting):

```bash
ruff check --fix --unsafe-fixes src/ tests/
```

### 3. Type Checking with MyPy

MyPy performs static type checking to catch type-related errors.

```bash
mypy src/time_audit
```

**Expected outcome:** "Success: no issues found in XX source files"

**Note:** The project uses strict mypy settings. Type ignore comments are allowed for:
- Platform-specific imports (win32api, AppKit, dbus, etc.)
- Optional dependencies (openpyxl, plyer, etc.)
- Third-party libraries without type stubs

### 4. Run Tests

Run the full test suite to ensure no functionality is broken.

```bash
pytest tests/ -v
```

**Expected outcome:** All tests passing (currently 228 tests)

For faster feedback during development, run tests without coverage:

```bash
pytest tests/
```

### 5. Check Test Coverage (Optional)

To see which lines are covered by tests:

```bash
pytest tests/ --cov=time_audit --cov-report=term-missing
```

## Complete Pre-Commit Workflow

Run all checks in one go:

```bash
# Format code
black src/ tests/

# Lint code
ruff check --fix src/ tests/

# Type check
mypy src/time_audit

# Run tests
pytest tests/ -v
```

## CI/CD Pipeline

The GitHub Actions CI/CD pipeline runs these same checks across multiple Python versions (3.9, 3.10, 3.11, 3.12) and operating systems (Linux, macOS, Windows).

### What CI/CD Checks

1. **Code Quality Job:**
   - Black formatting check
   - Ruff linting
   - MyPy type checking

2. **Test Job (per OS/Python version):**
   - Install dependencies (including platform-specific ones)
   - Run pytest with coverage
   - Run daemon tests separately

3. **Build Job:**
   - Build Python package
   - Validate with twine

## Common Issues and Solutions

### Black Reports Unformatted Files

**Solution:** Run `black src/ tests/` to auto-format.

### Ruff Reports Unused Imports

**Solution:** Run `ruff check --fix src/ tests/` to auto-remove.

### MyPy Reports Type Errors

**Solutions:**
- Add type annotations to function signatures
- Use type guards for Optional types
- Add `# type: ignore[error-code]` comments for legitimate cases

### Tests Failing

**Solutions:**
- Read the test output carefully
- Run specific test file: `pytest tests/test_specific.py -v`
- Use `-vv` for more verbose output
- Use `--tb=short` for shorter tracebacks

## Platform-Specific Notes

### Windows
- Install pywin32 for daemon tests: `pip install pywin32`
- Some daemon tests may be skipped on Windows

### macOS
- Install platform dependencies: `pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz`
- Socket paths use temp directories to avoid permission issues

### Linux
- Install dbus-python for certain automation features
- Systemd integration requires appropriate permissions

## Development Dependencies

All development dependencies are specified in `pyproject.toml`:

```bash
pip install -e ".[dev]"
```

This installs:
- pytest & pytest-cov (testing)
- black (formatting)
- ruff (linting)
- mypy (type checking)
- types-* (type stubs for external libraries)

## Making a Commit

Once all checks pass:

```bash
git add .
git commit -m "type: description of changes"

# Push to your branch
git push -u origin your-branch-name
```

**Commit message format:**
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting/linting changes
- `refactor:` for code refactoring
- `test:` for test additions/modifications
- `chore:` for build/tooling changes
