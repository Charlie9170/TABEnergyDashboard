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
        """Test that EIA-860 coordinate joins are stable."""
        df = pd.DataFrame({
            'plantName': ['W A Parish', 'W A Parish'],
            'plant_code': ['3470', '3470'],
        })
        
        result1 = geocode_plant_locations(df)
        result2 = geocode_plant_locations(df)
        
        pd.testing.assert_frame_equal(result1, result2)
    
    def test_geocode_plant_locations_within_texas(self):
        """Test that joined EIA-860 coordinates are within Texas bounds."""
        df = pd.DataFrame({
            'plantName': ['W A Parish'],
            'plant_code': ['3470'],
        })
        
        result = geocode_plant_locations(df)
        
        assert (result['lat'] >= TEXAS_BOUNDS['lat_min']).all()
        assert (result['lat'] <= TEXAS_BOUNDS['lat_max']).all()
        assert (result['lon'] >= TEXAS_BOUNDS['lon_min']).all()
        assert (result['lon'] <= TEXAS_BOUNDS['lon_max']).all()
        assert abs(result['lat'].iloc[0] - 29.4828) < 0.01


@pytest.fixture
def sample_generation_data():
    """Measured facility-fuel rows for transform tests."""
    return pd.DataFrame({
        'plantCode': ['100', '101', '102', '200', '3470', '6145', '54979'],
        'actual_generation_mw': [50.0, 5.0, 800.0, 25.0, 1800.0, 2100.0, 150.0],
    })


class TestTransformation:
    """Test data transformation functionality."""
    
    def test_transform_to_canonical_schema_aggregation(self, sample_generation_data):
        """Test that transformation properly aggregates by plant and fuel."""
        df = pd.DataFrame({
            'plantName': ['Plant A', 'Plant A', 'Plant B'],
            'lat': [30.0, 30.0, 32.0],
            'lon': [-97.0, -97.0, -96.0],
            'fuel': ['GAS', 'GAS', 'SOLAR'],
            'nameplate-capacity-mw': [100.0, 200.0, 50.0],
            'plant_code': ['100', '100', '200'],
        })
        
        result = transform_to_canonical_schema(df, sample_generation_data)
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
            'plant_code': ['100'],
        })
        
        gen = pd.DataFrame({'plantCode': ['100'], 'actual_generation_mw': [70.0]})
        result = transform_to_canonical_schema(df, gen)
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
            'plant_code': ['101', '102'],
        })
        
        gen = pd.DataFrame({
            'plantCode': ['101', '102'],
            'actual_generation_mw': [5.0, 800.0],
        })
        result = transform_to_canonical_schema(df, gen)
        
        # Should be sorted by actual generation (largest first)
        assert result['actual_generation_mw'].iloc[0] > result['actual_generation_mw'].iloc[1]

    def test_transform_requires_measured_generation(self):
        """Transform must fail rather than fabricate generation."""
        df = pd.DataFrame({
            'plantName': ['Plant A'],
            'lat': [30.0],
            'lon': [-97.0],
            'fuel': ['GAS'],
            'nameplate-capacity-mw': [100.0],
            'plant_code': ['999'],
        })
        with pytest.raises(ETLValidationError, match="Measured generation data required"):
            transform_to_canonical_schema(df, None)


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
            'plantName': ['W A Parish', 'Comanche Peak', 'Sweetwater Wind'],
            'technology': [
                'Natural Gas Combined Cycle',
                'Conventional Nuclear',
                'Onshore Wind Turbine',
            ],
            'nameplate-capacity-mw': [500.0, 2430.0, 200.0],
            'plant_code': ['3470', '6145', '54979'],
        })
        
        # Run through the pipeline
        geo_df = geocode_plant_locations(raw_data)
        fuel_df = normalize_fuel_types(geo_df)
        gen = pd.DataFrame({
            'plantCode': ['3470', '6145', '54979'],
            'actual_generation_mw': [1800.0, 2100.0, 150.0],
        })
        final_df = transform_to_canonical_schema(fuel_df, gen)
        
        assert len(final_df) == 3
        assert set(final_df['fuel']) == {'GAS', 'NUCLEAR', 'WIND'}
        
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
            'nameplate-capacity-mw': [100.0, None],
            'plant_code': ['100', '101'],
        })
        
        gen = pd.DataFrame({'plantCode': ['100'], 'actual_generation_mw': [70.0]})
        result = transform_to_canonical_schema(df, gen)
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