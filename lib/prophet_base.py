#!/usr/bin/env python

import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
import json
import logging
import sys
import os

class ProphetAlgorithm:
    """
    Base class for Prophet algorithm implementation in Splunk MLTK
    """
    
    def __init__(self):
        self.model = None
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Setup logging for the Prophet algorithm"""
        logger = logging.getLogger('prophet_algorithm')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def prepare_data(self, df, ds_field, y_field, cap_field=None, floor_field=None):
        """
        Prepare data for Prophet model
        
        Args:
            df (pd.DataFrame): Input dataframe
            ds_field (str): Date field name
            y_field (str): Target variable field name
            cap_field (str): Capacity field name for logistic growth
            floor_field (str): Floor field name for logistic growth
            
        Returns:
            pd.DataFrame: Prepared dataframe with 'ds' and 'y' columns
        """
        try:
            # Create Prophet dataframe format
            prophet_df = pd.DataFrame()
            
            # Convert date field
            if ds_field in df.columns:
                prophet_df['ds'] = pd.to_datetime(df[ds_field])
            else:
                raise ValueError(f"Date field '{ds_field}' not found in data")
            
            # Convert target field
            if y_field in df.columns:
                prophet_df['y'] = pd.to_numeric(df[y_field], errors='coerce')
            else:
                raise ValueError(f"Target field '{y_field}' not found in data")
            
            # Add capacity and floor for logistic growth
            if cap_field and cap_field in df.columns:
                prophet_df['cap'] = pd.to_numeric(df[cap_field], errors='coerce')
            
            if floor_field and floor_field in df.columns:
                prophet_df['floor'] = pd.to_numeric(df[floor_field], errors='coerce')
            
            # Remove rows with NaN values
            prophet_df = prophet_df.dropna()
            
            # Sort by date
            prophet_df = prophet_df.sort_values('ds').reset_index(drop=True)
            
            self.logger.info(f"Prepared data: {len(prophet_df)} rows")
            return prophet_df
            
        except Exception as e:
            self.logger.error(f"Error preparing data: {str(e)}")
            raise
    
    def create_model(self, growth='linear', seasonality_mode='additive',
                    yearly_seasonality='auto', weekly_seasonality='auto',
                    daily_seasonality='auto', holidays=None, 
                    changepoint_prior_scale=0.05, seasonality_prior_scale=10.0,
                    uncertainty_samples=1000, interval_width=0.8):
        """
        Create and configure Prophet model
        
        Args:
            growth (str): 'linear' or 'logistic'
            seasonality_mode (str): 'additive' or 'multiplicative'
            yearly_seasonality (bool/str): Enable yearly seasonality
            weekly_seasonality (bool/str): Enable weekly seasonality
            daily_seasonality (bool/str): Enable daily seasonality
            holidays (pd.DataFrame): Holiday dataframe
            changepoint_prior_scale (float): Changepoint flexibility
            seasonality_prior_scale (float): Seasonality flexibility
            uncertainty_samples (int): Number of samples for uncertainty
            interval_width (float): Confidence interval width
            
        Returns:
            Prophet: Configured Prophet model
        """
        try:
            # Create Prophet model
            self.model = Prophet(
                growth=growth,
                seasonality_mode=seasonality_mode,
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                daily_seasonality=daily_seasonality,
                holidays=holidays,
                changepoint_prior_scale=changepoint_prior_scale,
                seasonality_prior_scale=seasonality_prior_scale,
                uncertainty_samples=uncertainty_samples,
                interval_width=interval_width
            )
            
            self.logger.info("Prophet model created successfully")
            return self.model
            
        except Exception as e:
            self.logger.error(f"Error creating model: {str(e)}")
            raise
    
    def add_regressors(self, regressors):
        """
        Add external regressors to the model
        
        Args:
            regressors (list): List of regressor field names
        """
        if self.model is None:
            raise ValueError("Model not initialized. Call create_model() first.")
        
        for regressor in regressors:
            self.model.add_regressor(regressor)
            self.logger.info(f"Added regressor: {regressor}")
    
    def add_seasonalities(self, seasonalities):
        """
        Add custom seasonalities to the model
        
        Args:
            seasonalities (list): List of seasonality configurations
                Each item should be a dict with 'name', 'period', 'fourier_order'
        """
        if self.model is None:
            raise ValueError("Model not initialized. Call create_model() first.")
        
        for seasonality in seasonalities:
            self.model.add_seasonality(
                name=seasonality.get('name'),
                period=seasonality.get('period'),
                fourier_order=seasonality.get('fourier_order', 10)
            )
            self.logger.info(f"Added seasonality: {seasonality.get('name')}")
    
    def fit_model(self, df):
        """
        Fit the Prophet model to data
        
        Args:
            df (pd.DataFrame): Training data in Prophet format
            
        Returns:
            Prophet: Fitted model
        """
        try:
            if self.model is None:
                raise ValueError("Model not initialized. Call create_model() first.")
            
            self.model.fit(df)
            self.logger.info("Model fitted successfully")
            return self.model
            
        except Exception as e:
            self.logger.error(f"Error fitting model: {str(e)}")
            raise
    
    def make_forecast(self, periods, freq='D', include_history=True):
        """
        Generate forecasts
        
        Args:
            periods (int): Number of periods to forecast
            freq (str): Frequency of predictions ('D', 'H', 'M', etc.)
            include_history (bool): Include historical data in output
            
        Returns:
            pd.DataFrame: Forecast dataframe
        """
        try:
            if self.model is None:
                raise ValueError("Model not fitted. Call fit_model() first.")
            
            # Create future dataframe
            future = self.model.make_future_dataframe(
                periods=periods, 
                freq=freq, 
                include_history=include_history
            )
            
            # Generate predictions
            forecast = self.model.predict(future)
            
            self.logger.info(f"Generated forecast for {periods} periods")
            return forecast
            
        except Exception as e:
            self.logger.error(f"Error making forecast: {str(e)}")
            raise
    
    def cross_validate(self, df, initial='730 days', period='180 days', 
                      horizon='365 days', parallel=None):
        """
        Perform cross-validation
        
        Args:
            df (pd.DataFrame): Historical data
            initial (str): Length of initial training period
            period (str): Spacing between cutoff dates
            horizon (str): Length of forecast horizon
            parallel (str): Parallelization method
            
        Returns:
            pd.DataFrame: Cross-validation results
        """
        try:
            from prophet.diagnostics import cross_validation
            
            cv_results = cross_validation(
                self.model, 
                initial=initial,
                period=period,
                horizon=horizon,
                parallel=parallel
            )
            
            self.logger.info("Cross-validation completed")
            return cv_results
            
        except Exception as e:
            self.logger.error(f"Error in cross-validation: {str(e)}")
            raise
    
    def calculate_metrics(self, cv_results):
        """
        Calculate performance metrics
        
        Args:
            cv_results (pd.DataFrame): Cross-validation results
            
        Returns:
            pd.DataFrame: Performance metrics
        """
        try:
            from prophet.diagnostics import performance_metrics
            
            metrics = performance_metrics(cv_results)
            self.logger.info("Performance metrics calculated")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {str(e)}")
            raise
    
    def save_model(self, filepath):
        """
        Save the fitted model
        
        Args:
            filepath (str): Path to save the model
        """
        try:
            import pickle
            
            if self.model is None:
                raise ValueError("No model to save")
            
            with open(filepath, 'wb') as f:
                pickle.dump(self.model, f)
            
            self.logger.info(f"Model saved to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            raise
    
    def load_model(self, filepath):
        """
        Load a saved model
        
        Args:
            filepath (str): Path to the saved model
        """
        try:
            import pickle
            
            with open(filepath, 'rb') as f:
                self.model = pickle.load(f)
            
            self.logger.info(f"Model loaded from {filepath}")
            return self.model
            
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            raise
