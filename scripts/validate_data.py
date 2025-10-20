"""
Data Validation Script

Validates that generated data files:
1. Exist and are readable
2. Have the correct schema
3. Contain data (not empty)
4. Have valid data types

Used by GitHub Actions to ensure data quality before committing.
"""

import sys
from pathlib import Path

import pandas as pd

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from utils.schema import SCHEMAS, validate, coerce_types, normalize_columns

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"

# Files to validate
FILES_TO_VALIDATE = {
    "fuelmix.parquet": "fuelmix",
    "price_map.parquet": "price_map",
    "generation.parquet": "generation",
    "queue.parquet": "queue",
}


def validate_file(filepath: Path, dataset: str) -> bool:
    """
    Validate a single data file.
    
    Args:
        filepath: Path to the parquet file
        dataset: Dataset name for schema validation
        
    Returns:
        True if valid, False otherwise
    """
    print(f"\nValidating {filepath.name}...")
    
    # Check file exists
    if not filepath.exists():
        print(f"  ✗ File not found: {filepath}")
        return False
    
    try:
        # Read parquet
        df = pd.read_parquet(filepath)
        print(f"  ✓ File readable: {len(df)} rows, {len(df.columns)} columns")
        
        # Normalize and coerce
        df = normalize_columns(df, dataset)
        df = coerce_types(df, dataset)
        
        # Validate schema
        missing, extra = validate(df, dataset)
        
        if missing:
            print(f"  ✗ Missing required columns: {missing}")
            return False
        
        print(f"  ✓ Schema valid")
        
        if extra:
            print(f"  ℹ Extra columns (ok): {extra}")
        
        # Check for empty files (allow generation and queue to be empty stubs)
        if len(df) == 0:
            if dataset in ["generation", "queue"]:
                print(f"  ℹ File is empty (stub - ok)")
            else:
                print(f"  ✗ File is empty")
                return False
        else:
            print(f"  ✓ Contains {len(df)} records")
        
        # Check for null values in required columns
        required_cols = set(SCHEMAS[dataset].keys())
        for col in required_cols:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    print(f"  ⚠ Column '{col}' has {null_count} null values")
        
        print(f"  ✓ {filepath.name} validation passed")
        return True
        
    except Exception as e:
        print(f"  ✗ Validation error: {str(e)}")
        return False


def main():
    """Validate all data files."""
    print("="*60)
    print("Data Validation")
    print("="*60)
    
    all_valid = True
    
    for filename, dataset in FILES_TO_VALIDATE.items():
        filepath = DATA_DIR / filename
        if not validate_file(filepath, dataset):
            all_valid = False
    
    print("\n" + "="*60)
    if all_valid:
        print("✓ All data files validated successfully")
        print("="*60)
        sys.exit(0)
    else:
        print("✗ Some data files failed validation")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
