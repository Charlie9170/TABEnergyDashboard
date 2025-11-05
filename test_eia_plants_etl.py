"""
Unit tests for EIA Plants ETL Script

Tests data validation, transformation logic, and error handling.
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Import the ETL functions
import sys
sys.path.append(str(Path(__file__).parent.parent))

from etl.eia_plants_etl import (
    get_api_key,
    validate_input_schema,
    validate_output_schema,
    validate_coordinates,
    normalize_fuel_types,
    transform_to_canonical_schema,
    get_fuel_mapping,
    get_texas_locations,
    geocode_plant_locations,
    atomic_write_parquet,
    ETLValidationError,
    EIAAPIError,
    TEXAS_BOUNDS,
    REQUIRED_INPUT_COLUMNS,
    REQUIRED_OUTPUT_COLUMNS
)


class TestAPIKeyRetrieval:
    """Test API key retrieval functionality."""
    
    def test_get_api_key_from_environment(self):
        """Test getting API key from environment variable."""
        with patch.dict('os.environ', {'EIA_API_KEY': 'test_key'}):
            assert get_api_key() == 'test_key'
    
    def test_get_api_key_missing_raises_error(self):
        """Test that missing API key raises ETLValidationError."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('streamlit.secrets.get', side_effect=ImportError()):
                with pytest.raises(ETLValidationError, match="EIA_API_KEY not found"):
                    get_api_key()


class TestSchemaValidation:
    """Test schema validation functions."""
    
    def test_validate_input_schema_success(self):
        """Test successful input schema validation."""
        df = pd.DataFrame({
            'plantName': ['Plant A', 'Plant B'],
            'technology': ['Solar Photovoltaic', 'Natural Gas Combined Cycle'],
            'nameplate-capacity-mw': [100.0, 500.0],
            'extra_col': ['value1', 'value2']
        })
        
        # Should not raise exception
        validate_input_schema(df)
    
    def test_validate_input_schema_missing_columns(self):
        """Test input schema validation with missing required columns."""
        df = pd.DataFrame({
            'plantName': ['Plant A'],
            'technology': ['Solar Photovoltaic']
            # Missing 'nameplate-capacity-mw'
        })
        
        with pytest.raises(ETLValidationError, match="Missing required columns"):
            validate_input_schema(df)
    
    def test_validate_input_schema_invalid_numeric(self):
        """Test input schema validation with non-numeric capacity."""
        df = pd.DataFrame({
            'plantName': ['Plant A'],
            'technology': ['Solar Photovoltaic'],
            'nameplate-capacity-mw': ['not_numeric']
        })
        
        with pytest.raises(ETLValidationError, match="must be numeric"):
            validate_input_schema(df)
    
    def test_validate_output_schema_success(self):
        """Test successful output schema validation."""
        df = pd.DataFrame({
            'plant_name': ['Plant A'],
            'lat': [30.0],
            'lon': [-97.0],
            'capacity_mw': [100.0],
            'fuel': ['SOLAR'],
            'last_updated': ['2025-01-01T00:00:00Z']
        })
        
        # Should not raise exception
        validate_output_schema(df)
    
    def test_validate_output_schema_negative_capacity(self):
        """Test output schema validation with negative capacity."""
        df = pd.DataFrame({
            'plant_name': ['Plant A'],
            'lat': [30.0],
            'lon': [-97.0],
            'capacity_mw': [-100.0],  # Negative capacity
            'fuel': ['SOLAR'],
            'last_updated': ['2025-01-01T00:00:00Z']
        })
        
        with pytest.raises(ETLValidationError, match="must be positive"):
            validate_output_schema(df)


class TestCoordinateValidation:
    """Test coordinate validation functions."""
    
    def test_validate_coordinates_within_texas(self):
        """Test coordinate validation with valid Texas coordinates."""
        df = pd.DataFrame({
            'lat': [30.0, 32.0],
            'lon': [-97.0, -96.0]
        })
        
        # Should not raise exception
        validate_coordinates(df)
    
    def test_validate_coordinates_outside_texas(self):
        """Test coordinate validation with coordinates outside Texas."""
        df = pd.DataFrame({
            'lat': [40.0, 30.0],  # 40.0 is outside Texas
            'lon': [-97.0, -96.0]
        })
        
        with pytest.raises(ETLValidationError, match="outside Texas bounds"):
            validate_coordinates(df)


class TestFuelTypeNormalization:
    """Test fuel type normalization functionality."""
    
    def test_get_fuel_mapping_comprehensive(self):
        """Test that fuel mapping includes expected categories."""
        mapping = get_fuel_mapping()
        
        # Test key fuel types are mapped correctly
        assert mapping['Solar Photovoltaic'] == 'SOLAR'
        assert mapping['Natural Gas Combined Cycle'] == 'GAS'
        assert mapping['Onshore Wind Turbine'] == 'WIND'
        assert mapping['Coal'] == 'COAL'
        assert mapping['Nuclear'] == 'NUCLEAR'
        assert mapping['Batteries'] == 'STORAGE'
    
    def test_normalize_fuel_types_known_mapping(self):
        """Test fuel type normalization with known EIA technology types."""
        df = pd.DataFrame({
            'technology': [
                'Solar Photovoltaic',
                'Natural Gas Combined Cycle', 
                'Onshore Wind Turbine',
                'Unknown Technology'
            ]
        })
        
        result = normalize_fuel_types(df)
        
        expected_fuels = ['SOLAR', 'GAS', 'WIND', 'OTHER']
        assert result['fuel'].tolist() == expected_fuels
    
    def test_normalize_fuel_types_unknown_defaults_to_other(self):
        """Test that unknown fuel types default to OTHER."""
        df = pd.DataFrame({
            'technology': ['Unknown Tech Type', 'Another Unknown']
        })
        
        result = normalize_fuel_types(df)
        assert (result['fuel'] == 'OTHER').all()


class TestGeocoding:
    """Test geocoding functionality."""
    
    def test_get_texas_locations_comprehensive(self):
        """Test that Texas locations include major cities."""
        locations = get_texas_locations()
        
        # Should have substantial number of locations
        assert len(locations) >= 40
        
        # Check for major cities
        location_names = [loc[2] for loc in locations]
        major_cities = ['Houston', 'Dallas', 'San Antonio', 'Austin']
        
        for city in major_cities:
            assert city in location_names
    
    def test_geocode_plant_locations_deterministic(self):
        """Test that geocoding produces deterministic results."""
        df = pd.DataFrame({
            'plantName': ['Test Plant A', 'Test Plant B']
        })
        
        result1 = geocode_plant_locations(df)
        result2 = geocode_plant_locations(df)
        
        # Results should be identical (deterministic)
        pd.testing.assert_frame_equal(result1, result2)
    
    def test_geocode_plant_locations_within_texas(self):
        """Test that all geocoded locations are within Texas bounds."""
        df = pd.DataFrame({
            'plantName': ['Plant A', 'Plant B', 'Plant C']
        })
        
        result = geocode_plant_locations(df)
        
        # All coordinates should be within Texas bounds
        assert (result['lat'] >= TEXAS_BOUNDS['lat_min']).all()
        assert (result['lat'] <= TEXAS_BOUNDS['lat_max']).all()
        assert (result['lon'] >= TEXAS_BOUNDS['lon_min']).all()
        assert (result['lon'] <= TEXAS_BOUNDS['lon_max']).all()


class TestTransformation:
    """Test data transformation functionality."""
    
    def test_transform_to_canonical_schema_aggregation(self):
        """Test that transformation properly aggregates by plant and fuel."""
        df = pd.DataFrame({
            'plantName': ['Plant A', 'Plant A', 'Plant B'],
            'lat': [30.0, 30.0, 32.0],
            'lon': [-97.0, -97.0, -96.0],
            'fuel': ['GAS', 'GAS', 'SOLAR'],
            'nameplate-capacity-mw': [100.0, 200.0, 50.0],
            'base_location': ['Austin', 'Austin', 'Dallas']
        })
        
        result = transform_to_canonical_schema(df)
        
        # Should aggregate Plant A's two GAS units
        assert len(result) == 2
        
        # Find Plant A row
        plant_a_row = result[result['plant_name'] == 'Plant A']
        assert len(plant_a_row) == 1
        assert plant_a_row['capacity_mw'].iloc[0] == 300.0  # 100 + 200
    
    def test_transform_to_canonical_schema_columns(self):
        """Test that transformation produces correct output columns."""
        df = pd.DataFrame({
            'plantName': ['Plant A'],
            'lat': [30.0],
            'lon': [-97.0],
            'fuel': ['GAS'],
            'nameplate-capacity-mw': [100.0],
            'base_location': ['Austin']
        })
        
        result = transform_to_canonical_schema(df)
        
        # Check all required columns are present
        for col in REQUIRED_OUTPUT_COLUMNS:
            assert col in result.columns
        
        # Check data types
        assert pd.api.types.is_numeric_dtype(result['capacity_mw'])
        assert pd.api.types.is_numeric_dtype(result['lat'])
        assert pd.api.types.is_numeric_dtype(result['lon'])
    
    def test_transform_to_canonical_schema_sorting(self):
        """Test that transformation sorts by capacity (largest first)."""
        df = pd.DataFrame({
            'plantName': ['Small Plant', 'Large Plant'],
            'lat': [30.0, 32.0],
            'lon': [-97.0, -96.0],
            'fuel': ['SOLAR', 'GAS'],
            'nameplate-capacity-mw': [10.0, 1000.0],
            'base_location': ['Austin', 'Dallas']
        })
        
        result = transform_to_canonical_schema(df)
        
        # Should be sorted by capacity (largest first)
        assert result['capacity_mw'].iloc[0] == 1000.0
        assert result['capacity_mw'].iloc[1] == 10.0


class TestFileOperations:
    """Test file I/O operations."""
    
    def test_atomic_write_parquet_success(self):
        """Test successful atomic write to Parquet file."""
        df = pd.DataFrame({
            'plant_name': ['Test Plant'],
            'lat': [30.0],
            'lon': [-97.0],
            'capacity_mw': [100.0],
            'fuel': ['SOLAR'],
            'last_updated': ['2025-01-01T00:00:00Z']
        })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.parquet"
            
            atomic_write_parquet(df, output_path)
            
            # File should exist and be readable
            assert output_path.exists()
            
            # Content should match original
            result = pd.read_parquet(output_path)
            pd.testing.assert_frame_equal(df, result)
    
    def test_atomic_write_parquet_creates_directory(self):
        """Test that atomic write creates necessary directories."""
        df = pd.DataFrame({'col': [1, 2, 3]})
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "test.parquet"
            
            atomic_write_parquet(df, output_path)
            
            # Directory and file should be created
            assert output_path.parent.exists()
            assert output_path.exists()


class TestIntegration:
    """Integration tests for complete ETL pipeline components."""
    
    def test_end_to_end_transformation_pipeline(self):
        """Test complete transformation pipeline with realistic data."""
        # Create sample EIA-style data
        raw_data = pd.DataFrame({
            'plantName': ['Houston Solar Farm', 'Dallas Gas Plant', 'Austin Wind Farm'],
            'technology': ['Solar Photovoltaic', 'Natural Gas Combined Cycle', 'Onshore Wind Turbine'],
            'nameplate-capacity-mw': [100.0, 500.0, 200.0]
        })
        
        # Run through the pipeline
        geo_df = geocode_plant_locations(raw_data)
        fuel_df = normalize_fuel_types(geo_df)
        final_df = transform_to_canonical_schema(fuel_df)
        
        # Validate final result
        assert len(final_df) == 3
        assert set(final_df['fuel']) == {'SOLAR', 'GAS', 'WIND'}
        assert final_df['capacity_mw'].sum() == 800.0
        
        # All coordinates should be in Texas
        validate_coordinates(final_df)
        validate_output_schema(final_df)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrames."""
        df = pd.DataFrame(columns=['plantName', 'technology', 'nameplate-capacity-mw'])
        
        # Should handle empty data gracefully
        geo_df = geocode_plant_locations(df)
        assert len(geo_df) == 0
        
        fuel_df = normalize_fuel_types(df)
        assert len(fuel_df) == 0
    
    def test_invalid_capacity_values(self):
        """Test handling of invalid capacity values."""
        df = pd.DataFrame({
            'plantName': ['Plant A', 'Plant B'],
            'lat': [30.0, 32.0],
            'lon': [-97.0, -96.0],
            'fuel': ['GAS', 'SOLAR'],
            'nameplate-capacity-mw': [100.0, None],  # None value
            'base_location': ['Austin', 'Dallas']
        })
        
        result = transform_to_canonical_schema(df)
        
        # Should drop rows with invalid capacity
        assert len(result) == 1
        assert result['plant_name'].iloc[0] == 'Plant A'


# Pytest configuration
@pytest.fixture
def sample_input_data():
    """Fixture providing sample input data for tests."""
    return pd.DataFrame({
        'plantName': ['Test Plant A', 'Test Plant B'],
        'technology': ['Solar Photovoltaic', 'Natural Gas Combined Cycle'],
        'nameplate-capacity-mw': [100.0, 500.0]
    })


@pytest.fixture
def sample_output_data():
    """Fixture providing sample output data for tests."""
    return pd.DataFrame({
        'plant_name': ['Test Plant A'],
        'lat': [30.0],
        'lon': [-97.0],
        'capacity_mw': [100.0],
        'fuel': ['SOLAR'],
        'last_updated': ['2025-01-01T00:00:00Z']
    })


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])