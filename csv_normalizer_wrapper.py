#!/usr/bin/env python3
"""
Wrapper script for csv_normalizer bash utility.
This allows the bash script to be installed via pip in editable mode.
"""
import os
import sys
import subprocess


def get_script_path():
    """Find the prepare.sh script path."""
    # Get the directory where this wrapper is located
    wrapper_dir = os.path.dirname(os.path.abspath(__file__))

    # Try common locations
    candidates = [
        # Editable install: script/ subdirectory
        os.path.join(wrapper_dir, 'script', 'prepare.sh'),
        # Direct install: same directory
        os.path.join(wrapper_dir, 'prepare.sh'),
        # Site-packages with data
        os.path.join(wrapper_dir, '..', 'script', 'prepare.sh'),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def main():
    """Execute the csv_normalizer bash script."""
    script_path = get_script_path()

    if not script_path:
        print("Error: csv_normalizer script not found", file=sys.stderr)
        print("", file=sys.stderr)
        print("This package requires editable installation:", file=sys.stderr)
        print("  pip install -e .", file=sys.stderr)
        print("", file=sys.stderr)
        print("Or use the Makefile installation:", file=sys.stderr)
        print("  make install", file=sys.stderr)
        sys.exit(1)

    # Execute the bash script with all arguments
    try:
        result = subprocess.run(
            ['bash', script_path] + sys.argv[1:],
            check=False
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error executing csv_normalizer: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
