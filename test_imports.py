#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_imports():
    """Test all critical imports"""
    errors = []

    print("Testing imports...")

    # Test core modules
    try:
        from core.config import Settings
        print("✓ core.config imported successfully")
    except Exception as e:
        errors.append(f"✗ core.config: {e}")
        print(f"✗ core.config: {e}")

    try:
        from core.database import Base, init_db, get_db
        print("✓ core.database imported successfully")
    except Exception as e:
        errors.append(f"✗ core.database: {e}")
        print(f"✗ core.database: {e}")

    try:
        from core.data_processor import DataProcessor
        print("✓ core.data_processor imported successfully")
    except Exception as e:
        errors.append(f"✗ core.data_processor: {e}")
        print(f"✗ core.data_processor: {e}")

    try:
        from core.trainer import Trainer_Qwen3, TrainingConfig
        print("✓ core.trainer imported successfully")
    except Exception as e:
        errors.append(f"✗ core.trainer: {e}")
        print(f"✗ core.trainer: {e}")

    # Test API modules
    try:
        from api import router
        print("✓ api router imported successfully")
    except Exception as e:
        errors.append(f"✗ api router: {e}")
        print(f"✗ api router: {e}")

    # Test app
    try:
        from app import app
        print("✓ app imported successfully")
    except Exception as e:
        errors.append(f"✗ app: {e}")
        print(f"✗ app: {e}")

    print("\n" + "="*50)
    if errors:
        print(f"FAILED: {len(errors)} errors found")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("SUCCESS: All imports working correctly!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
