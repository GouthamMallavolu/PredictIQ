"""
Schema Validation using Pandera
Validates data schemas for ingestion, training, and serving
"""
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from typing import Optional

# Schema for stock data ingestion
stock_data_schema = DataFrameSchema({
    "symbol": Column(str, checks=Check.str_length(min_value=1, max_value=10)),
    "date": Column(pd.Timestamp, nullable=False),
    "open": Column(float, checks=Check.greater_than(0)),
    "high": Column(float, checks=Check.greater_than(0)),
    "low": Column(float, checks=Check.greater_than(0)),
    "close": Column(float, checks=Check.greater_than(0)),
    "volume": Column(int, checks=Check.greater_than_or_equal_to(0)),
    "adjusted_close": Column(float, checks=Check.greater_than(0), nullable=True, required=False),
}, strict=False)  # Allow extra columns like adjusted_close

# Schema for API request
api_request_schema = DataFrameSchema({
    "user_id": Column(str, checks=Check.str_length(min_value=1)),
    "symbols": Column(list, checks=Check(lambda x: len(x) > 0 and len(x) <= 10)),
    "model": Column(str, checks=Check.isin(["lstm", "randomforest", "movingaverage", "all"]), nullable=True),
}, strict=True)

# Schema for API response
api_response_schema = DataFrameSchema({
    "request_id": Column(str, nullable=False),
    "timestamp": Column(str, nullable=False),
    "status": Column(str, checks=Check.isin(["success", "error"])),
    "results": Column(dict, nullable=True),
    "model_used": Column(str, nullable=True),
    "latency_ms": Column(float, checks=Check.greater_than_or_equal_to(0), nullable=True),
}, strict=False)  # Allow extra columns

# Schema for Kafka reco_request
kafka_reco_request_schema = DataFrameSchema({
    "user_id": Column(str, nullable=False),
    "symbols": Column(list, nullable=False),
    "model": Column(str, nullable=True),
    "timestamp": Column(str, nullable=True),
}, strict=False)

# Schema for Kafka reco_response
kafka_reco_response_schema = DataFrameSchema({
    "request_id": Column(str, nullable=False),
    "response": Column(dict, nullable=True),
    "latency_ms": Column(float, nullable=True),
    "timestamp": Column(str, nullable=False),
    "num_predictions": Column(int, nullable=True),
    "status": Column(str, checks=Check.isin(["success", "error"])),
    "error": Column(str, nullable=True),
    "status_code": Column(int, nullable=True),
}, strict=False)

def validate_stock_data(df: pd.DataFrame) -> tuple[bool, Optional[str]]:
    """
    Validate stock data schema
    
    Returns:
        (is_valid, error_message)
    """
    try:
        stock_data_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaError as e:
        return False, str(e)

def validate_api_request(request: dict) -> tuple[bool, Optional[str]]:
    """
    Validate API request schema
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Convert to DataFrame for validation
        df = pd.DataFrame([request])
        api_request_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def validate_api_response(response: dict) -> tuple[bool, Optional[str]]:
    """
    Validate API response schema
    
    Returns:
        (is_valid, error_message)
    """
    try:
        df = pd.DataFrame([response])
        api_response_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def validate_kafka_reco_request(record: dict) -> tuple[bool, Optional[str]]:
    """
    Validate Kafka reco_request record
    
    Returns:
        (is_valid, error_message)
    """
    try:
        df = pd.DataFrame([record])
        kafka_reco_request_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def validate_kafka_reco_response(record: dict) -> tuple[bool, Optional[str]]:
    """
    Validate Kafka reco_response record
    
    Returns:
        (is_valid, error_message)
    """
    try:
        df = pd.DataFrame([record])
        kafka_reco_response_schema.validate(df, lazy=True)
        return True, None
    except pa.errors.SchemaError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"

if __name__ == "__main__":
    print("Schema Validation Module")
    print("Import this module to use validation functions")

