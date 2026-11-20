import os
import json
import pytest
import pandas as pd

from pipeline.transform import clean_weather_data

@pytest.fixture
def sample_raw_json(tmp_path):
    """Creates a temporary mock raw JSON file for testing."""
    mock_data = [
        {
            "city": "Bengaluru",
            "current": {
                "time": "2026-11-20T10:00",
                "temperature_2m": 25.5,
                "relative_humidity_2m": 60,
                "precipitation": 0.0
            }
        },
        {
            "city": "London",
            "current": {
                "time": "2026-11-20T10:00",
                "temperature_2m": 8.2,
                "relative_humidity_2m": 85,
                "precipitation": 1.4
            }
        }
    ]
    file_path = tmp_path / "mock_raw.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(mock_data, f)
    return str(file_path)

@pytest.fixture
def sample_corrupt_json(tmp_path):
    """Creates mock data with missing values, corrupt dates, and bad types."""
    mock_corrupt = [
        {
            "city": "Tokyo",
            "current": {
                "time": "NOT_A_DATE",  # Corrupt date
                "temperature_2m": 15.0,
                "relative_humidity_2m": 50,
                "precipitation": 0.0
            }
        },
        {
            "city": "Sydney",
            "current": {
                "time": "2026-11-20T12:00",
                "temperature_2m": None,  # Null temperature
                "relative_humidity_2m": "75",  # String that should convert to int
                "precipitation": None   # Null precipitation
            }
        }
    ]
    file_path = tmp_path / "mock_corrupt.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(mock_corrupt, f)
    return str(file_path)

def test_transform_normal_data(sample_raw_json, tmp_path):
    output_csv = str(tmp_path / "clean_output.csv")
    df = clean_weather_data(raw_filepath=sample_raw_json, output_csv_path=output_csv)

    assert df is not None
    assert len(df) == 2
    assert list(df.columns) == ["city", "date", "temperature", "humidity", "precipitation"]
    assert df.loc[df["city"] == "Bengaluru", "temperature"].values[0] == 25.5
    assert df.loc[df["city"] == "London", "humidity"].values[0] == 85
    assert os.path.exists(output_csv)

def test_transform_corrupt_and_null_handling(sample_corrupt_json, tmp_path):
    output_csv = str(tmp_path / "clean_corrupt.csv")
    df = clean_weather_data(raw_filepath=sample_corrupt_json, output_csv_path=output_csv)

    assert df is not None
    # Row with "NOT_A_DATE" must have been dropped
    assert "Tokyo" not in df["city"].values
    # Row with Sydney must be kept with nulls filled
    sydney_row = df[df["city"] == "Sydney"]
    assert len(sydney_row) == 1
    assert sydney_row["temperature"].values[0] == 0.0
    assert sydney_row["precipitation"].values[0] == 0.0
    assert sydney_row["humidity"].values[0] == 75

def test_transform_empty_file(tmp_path):
    empty_file = str(tmp_path / "empty.json")
    with open(empty_file, "w") as f:
        json.dump([], f)
        
    output_csv = str(tmp_path / "empty.csv")
    df = clean_weather_data(raw_filepath=empty_file, output_csv_path=output_csv)
    assert df is None

def test_transform_missing_file():
    df = clean_weather_data(raw_filepath="non_existent_file.json")
    assert df is None
