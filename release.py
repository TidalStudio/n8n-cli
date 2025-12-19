#!/usr/bin/env python3
"""Release script for n8n-cli.

Usage:
    python release.py patch    # 0.3.0 -> 0.3.1
    python release.py minor    # 0.3.0 -> 0.4.0
    python release.py major    # 0.3.0 -> 1.0.0
    python release.py 0.5.0    # Set specific version
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    pyproject = Path("pyproject.toml").read_text()
    match = re.search(r'version = "([^"]+)"', pyproject)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def bump_version(current: str, bump_type: str) -> str:
    """Calculate new version based on bump type."""
    # If bump_type looks like a version number, use it directly
    if re.match(r"^\d+\.\d+\.\d+$", bump_type):
        return bump_type

    parts = list(map(int, current.split(".")))
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")

    major, minor, patch = parts

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump type: {bump_type}. Use patch, minor, major, or X.Y.Z")

    return f"{major}.{minor}.{patch}"


def update_version_in_file(filepath: Path, old_version: str, new_version: str) -> None:
    """Update version string in a file."""
    content = filepath.read_text()
    updated = content.replace(f'version = "{old_version}"', f'version = "{new_version}"')
    updated = updated.replace(f'__version__ = "{old_version}"', f'__version__ = "{new_version}"')
    filepath.write_text(updated)


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"  $ {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    bump_type = sys.argv[1]

    # Get versions
    current_version = get_current_version()
    new_version = bump_version(current_version, bump_type)

    print("\n🚀 Releasing n8n-cli")
    print(f"   {current_version} -> {new_version}\n")

    # Confirm
    response = input("Continue? [y/N] ").strip().lower()
    if response != "y":
        print("Aborted.")
        sys.exit(0)

    # Step 1: Update version numbers
    print("\n📝 Updating version numbers...")
    update_version_in_file(Path("pyproject.toml"), current_version, new_version)
    update_version_in_file(Path("src/n8n_cli/__init__.py"), current_version, new_version)

    # Step 2: Clean old builds
    print("\n🧹 Cleaning old builds...")
    for folder in ["dist", "build", "src/n8n_cli.egg-info"]:
        path = Path(folder)
        if path.exists():
            shutil.rmtree(path)
            print(f"   Removed {folder}")

    # Step 3: Build
    print("\n📦 Building package...")
    run("python -m build")

    # Step 4: Upload to PyPI
    print("\n☁️  Uploading to PyPI...")
    run("python -m twine upload dist/*")

    # Step 5: Git commit and push
    print("\n📤 Committing and pushing to git...")
    run("git add -A")
    run(f'git commit -m "Release v{new_version}"')
    run(f"git tag v{new_version}")
    run("git push")
    run("git push --tags")

    print(f"\n✅ Released v{new_version} successfully!")
    print(f"   PyPI: https://pypi.org/project/n8n-cli/{new_version}/")
    print(f"   GitHub: https://github.com/TidalStudio/n8n-cli/releases/tag/v{new_version}")


if __name__ == "__main__":
    main()
