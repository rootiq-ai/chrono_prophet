#!/usr/bin/env python

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json

def parse_boolean(value):
    """
    Parse boolean values from string input
    
    Args:
        value (str): String value to parse
        
    Returns:
        bool or str: Parsed boolean value or 'auto'
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ['true', '1', 'yes', 'on']:
            return True
        elif value_lower in ['false', '0', 'no', 'off']:
            return False
        elif value_lower == 'auto':
            return 'auto'
    
    return value

def parse_holidays(df, ds_field, holiday_field):
    """
    Parse holidays from input data
    
    Args:
        df (pd.DataFrame): Input dataframe
        ds_field (str): Date field name
        holiday_field (str): Holiday field name
        
    Returns:
        pd.DataFrame: Holidays dataframe in Prophet format
    """
    try:
        holidays_data = df[[ds_field, holiday_field]].dropna()
        
        if holidays_data.empty:
            return None
        
        holidays_df = pd.DataFrame({
            'holiday': holidays_data[holiday_field],
            'ds': pd.to_datetime(holidays_data[ds_field])
        })
        
        # Remove duplicates
        holidays_df = holidays_df.drop_duplicates().reset_index(drop=True)
        
        return holidays_df
        
    except Exception as e:
        logging.error(f"Error parsing holidays: {str(e)}")
        return None

def validate_frequency(freq):
    """
    Validate frequency parameter
    
    Args:
        freq (str): Frequency string
        
    Returns:
        bool: True if valid frequency
    """
    valid_frequencies = [
        'D', 'H', 'T', 'min', 'S', 'L', 'ms', 'U', 'us', 'N', 'ns',
        'B', 'C', 'W', 'M', 'SM', 'BM', 'CBM', 'MS', 'SMS', 'BMS', 'CBMS',
        'Q', 'BQ', 'QS', 'BQS', 'A', 'Y', 'BA', 'BY', 'AS', 'YS', 'BAS', 'BYS'
    ]
    
    # Check base frequency
    base_freq = freq.rstrip('0123456789')
    return base_freq in valid_frequencies

def create_future_dataframe(last_date, periods, freq='D'):
    """
    Create future dates dataframe
    
    Args:
        last_date (datetime): Last date in historical data
        periods (int): Number of future periods
        freq (str): Frequency
        
    Returns:
        pd.DataFrame: Future dates dataframe
    """
    try:
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=periods,
            freq=freq
        )
        
        return pd.DataFrame({'ds': future_dates})
        
    except Exception as e:
        logging.error(f"Error creating future dataframe: {str(e)}")
        return pd.DataFrame()

def calculate_mape(y_true, y_pred):
    """
    Calculate Mean Absolute Percentage Error
    
    Args:
        y_true (array-like): True values
        y_pred (array-like): Predicted values
        
    Returns:
        float: MAPE value
    """
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    
    # Avoid division by zero
    mask = y_true != 0
    if not mask.any():
        return np.inf
    
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def calculate_smape(y_true, y_pred):
    """
    Calculate Symmetric Mean Absolute Percentage Error
    
    Args:
        y_true (array-like): True values
        y_pred (array-like): Predicted values
        
    Returns:
        float: SMAPE value
    """
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    mask = denominator != 0
    
    if not mask.any():
        return 0.0
    
    return np.mean(np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100

def detect_outliers(df, method='iqr', threshold=1.5):
    """
    Detect outliers in time series data
    
    Args:
        df (pd.DataFrame): Input dataframe with 'y' column
        method (str): Outlier detection method ('iqr', 'zscore')
        threshold (float): Threshold for outlier detection
        
    Returns:
        pd.DataFrame: Dataframe with outlier flags
    """
    try:
        df_copy = df.copy()
        
        if method == 'iqr':
            Q1 = df_copy['y'].quantile(0.25)
            Q3 = df_copy['y'].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            df_copy['outlier'] = (df_copy['y'] < lower_bound) | (df_copy['y'] > upper_bound)
            
        elif method == 'zscore':
            mean_y = df_copy['y'].mean()
            std_y = df_copy['y'].std()
            z_scores = np.abs((df_copy['y'] - mean_y) / std_y)
            
            df_copy['outlier'] = z_scores > threshold
            
        return df_copy
        
    except Exception as e:
        logging.error(f"Error detecting outliers: {str(e)}")
        return df

def format_prophet_output(forecast_df, include_components=True):
    """
    Format Prophet forecast output for Splunk
    
    Args:
        forecast_df (pd.DataFrame): Prophet forecast dataframe
        include_components (bool): Include seasonal components
        
    Returns:
        list: List of formatted records
    """
    try:
        records = []
        
        for index, row in forecast_df.iterrows():
            record = {
                'ds': row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
                'yhat': float(row['yhat']),
                'yhat_lower': float(row['yhat_lower']),
                'yhat_upper': float(row['yhat_upper']),
                'trend': float(row['trend'])
            }
            
            if include_components:
                # Add seasonal components if they exist
                for component in ['yearly', 'weekly', 'daily']:
                    if component in forecast_df.columns:
                        record[component] = float(row[component])
                
                # Add holiday effects if they exist
                if 'holidays' in forecast_df.columns:
                    record['holidays'] = float(row['holidays'])
                
                # Add regressor effects
                regressor_cols = [col for col in forecast_df.columns 
                                if col not in ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 
                                             'trend', 'yearly', 'weekly', 'daily', 'holidays']]
                
                for regressor in regressor_cols:
                    if regressor in forecast_df.columns:
                        record[regressor] = float(row[regressor])
            
            records.append(record)
        
        return records
        
    except Exception as e:
        logging.error(f"Error formatting output: {str(e)}")
        return []

def load_default_holidays():
    """
    Load default holidays configuration
    
    Returns:
        dict: Default holidays by country
    """
    default_holidays = {
        'US': [
            {'holiday': 'New Year\'s Day', 'ds': '2024-01-01'},
            {'holiday': 'Independence Day', 'ds': '2024-07-04'},
            {'holiday': 'Thanksgiving', 'ds': '2024-11-28'},
            {'holiday': 'Christmas', 'ds': '2024-12-25'}
        ],
        'UK': [
            {'holiday': 'New Year\'s Day', 'ds': '2024-01-01'},
            {'holiday': 'Christmas Day', 'ds': '2024-12-25'},
            {'holiday': 'Boxing Day', 'ds': '2024-12-26'}
        ]
    }
    
    return default_holidays

def validate_prophet_data(df):
    """
    Validate data for Prophet model
    
    Args:
        df (pd.DataFrame): Input dataframe
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Check required columns
        if 'ds' not in df.columns:
            return False, "Missing 'ds' column"
        
        if 'y' not in df.columns:
            return False, "Missing 'y' column"
        
        # Check data types
        if not pd.api.types.is_datetime64_any_dtype(df['ds']):
            return False, "'ds' column must be datetime type"
        
        if not pd.api.types.is_numeric_dtype(df['y']):
            return False, "'y' column must be numeric type"
        
        # Check for minimum data points
        if len(df) < 2:
            return False, "Need at least 2 data points"
        
        # Check for duplicated dates
        if df['ds'].duplicated().any():
            return False, "Duplicate dates found in 'ds' column"
        
        # Check for missing values
        if df['ds'].isnull().any():
            return False, "Missing values in 'ds' column"
        
        if df['y'].isnull().any():
            return False, "Missing values in 'y' column"
        
        return True, "Data validation passed"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def generate_sample_data(start_date='2020-01-01', periods=365, freq='D', 
                        trend=1.0, seasonality=10.0, noise=5.0):
    """
    Generate sample time series data for testing
    
    Args:
        start_date (str): Start date
        periods (int): Number of periods
        freq (str): Frequency
        trend (float): Trend component
        seasonality (float): Seasonality amplitude
        noise (float): Noise level
        
    Returns:
        pd.DataFrame: Sample data
    """
    try:
        dates = pd.date_range(start=start_date, periods=periods, freq=freq)
        
        # Create trend
        trend_component = np.arange(periods) * trend
        
        # Create seasonality (yearly)
        seasonal_component = seasonality * np.sin(2 * np.pi * np.arange(periods) / 365.25)
        
        # Add noise
        noise_component = np.random.normal(0, noise, periods)
        
        # Combine components
        y = 100 + trend_component + seasonal_component + noise_component
        
        df = pd.DataFrame({
            'ds': dates,
            'y': y
        })
        
        return df
        
    except Exception as e:
        logging.error(f"Error generating sample data: {str(e)}")
        return pd.DataFrame()
