#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for Alice Display tests.
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to Python path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def data_dir(project_root):
    """Return the data directory."""
    return project_root / "data"


@pytest.fixture
def scripts_dir():
    """Return the scripts directory."""
    return Path(__file__).parent.parent / "scripts"
