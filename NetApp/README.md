# Python Environment Setup with UV

This guide explains how to install **UV**, set up **Python 3.11**, and manage dependencies for your project.

---

## 1. Install UV

UV is a fast, modern Python package and environment manager.
To install it, run the following command in your terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal or run the command displayed at the end of the installer (usually something like `source ~/.profile` or `source ~/.bashrc`) so the `uv` command becomes available.

You can verify the installation with:

```bash
uv --version
```

---

## 2. Install Python 3.11 through UV

UV can manage multiple Python versions for you.
To install **Python 3.11**, run:

```bash
uv python install 3.11
```

Then confirm the version is available:

```bash
uv python list
```

If you want to make Python 3.11 the default for this project:

```bash
uv python pin 3.11
```

---

## 3. Install Project Dependencies

If your project has a `pyproject.toml` or `requirements.txt`, you can install all dependencies automatically:

```bash
uv pip install -r requirements.txt
```

Or, for projects using `pyproject.toml` (recommended):

```bash
uv pip install .
```

If you need to add a new dependency:

```bash
uv add <package-name>
```

---

## 4. Running Scripts

You have two options when working in your project environment:

### Option A — Activate the Environment

```bash
source .venv/bin/activate
```

Then you can run your scripts normally:

```bash
python script.py
```

### Option B — Use `uv run` (Recommended)

Run scripts directly using UV without manually activating the environment:

```bash
uv run python script.py
```

You can also use it for other Python commands, like:

```bash
uv run pytest
uv run jupyter notebook
```

---

## ✅ Summary

| Step | Description |
|------|--------------|
| 1 | Install UV package manager |
| 2 | Install Python 3.11 |
| 3 | Install your dependencies |
| 4 | Run scripts via `uv run` or activate the environment |

---
