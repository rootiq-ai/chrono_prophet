#!/usr/bin/env python

import sys
import os
import pandas as pd
import json
from datetime import datetime
import traceback

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from prophet_base import ProphetAlgorithm
from utils import parse_boolean, parse_holidays

@Configuration()
class ProphetForecastCommand(StreamingCommand):
    """
    Custom Splunk command to implement Facebook Prophet for time series forecasting
    
    Usage:
    | prophet_forecast ds_field=<date_field> y_field=<target_field> periods=<forecast_periods> 
                     freq=<frequency> growth=<linear|logistic> seasonality_mode=<additive|multiplicative>
                     yearly_seasonality=<auto|true|false> weekly_seasonality=<auto|true|false>
                     daily_seasonality=<auto|true|false> holidays=<holiday_field>
                     cap=<capacity_field> floor=<floor_field> uncertainty_samples=<int>
                     confidence_interval=<float> include_history=<true|false>
                     changepoint_prior_scale=<float> seasonality_prior_scale=<float>
                     regressors=<field1,field2,...> seasonalities=<json_config>
    """
    
    # Required parameters
    ds_field = Option(
        doc='''**Syntax:** **ds_field=***<fieldname>*
        **Description:** Name of the field containing dates (required)''',
        require=True, validate=validators.Fieldname())
    
    y_field = Option(
        doc='''**Syntax:** **y_field=***<fieldname>*
        **Description:** Name of the field containing target values (required)''',
        require=True, validate=validators.Fieldname())
    
    periods = Option(
        doc='''**Syntax:** **periods=***<integer>*
        **Description:** Number of future periods to forecast (default: 30)''',
        require=False, validate=validators.Integer(minimum=1), default=30)
    
    # Optional parameters
    freq = Option(
        doc='''**Syntax:** **freq=***<frequency>*
        **Description:** Frequency of predictions: D, H, M, Y, etc. (default: D)''',
        require=False, default='D')
    
    growth = Option(
        doc='''**Syntax:** **growth=***<linear|logistic>*
        **Description:** Growth model type (default: linear)''',
        require=False, validate=validators.Set('linear', 'logistic'), default='linear')
    
    seasonality_mode = Option(
        doc='''**Syntax:** **seasonality_mode=***<additive|multiplicative>*
        **Description:** Seasonality mode (default: additive)''',
        require=False, validate=validators.Set('additive', 'multiplicative'), default='additive')
    
    yearly_seasonality = Option(
        doc='''**Syntax:** **yearly_seasonality=***<auto|true|false>*
        **Description:** Enable yearly seasonality (default: auto)''',
        require=False, default='auto')
    
    weekly_seasonality = Option(
        doc='''**Syntax:** **weekly_seasonality=***<auto|true|false>*
        **Description:** Enable weekly seasonality (default: auto)''',
        require=False, default='auto')
    
    daily_seasonality = Option(
        doc='''**Syntax:** **daily_seasonality=***<auto|true|false>*
        **Description:** Enable daily seasonality (default: auto)''',
        require=False, default='auto')
    
    holidays = Option(
        doc='''**Syntax:** **holidays=***<fieldname>*
        **Description:** Field containing holiday names''',
        require=False, validate=validators.Fieldname())
    
    cap = Option(
        doc='''**Syntax:** **cap=***<fieldname>*
        **Description:** Field containing capacity values for logistic growth''',
        require=False, validate=validators.Fieldname())
    
    floor = Option(
        doc='''**Syntax:** **floor=***<fieldname>*
        **Description:** Field containing floor values for logistic growth''',
        require=False, validate=validators.Fieldname())
    
    uncertainty_samples = Option(
        doc='''**Syntax:** **uncertainty_samples=***<integer>*
        **Description:** Number of samples for uncertainty intervals (default: 1000)''',
        require=False, validate=validators.Integer(minimum=0), default=1000)
    
    confidence_interval = Option(
        doc='''**Syntax:** **confidence_interval=***<float>*
        **Description:** Width of confidence intervals (default: 0.8)''',
        require=False, validate=validators.Float(minimum=0.0, maximum=1.0), default=0.8)
    
    include_history = Option(
        doc='''**Syntax:** **include_history=***<true|false>*
        **Description:** Include historical data in output (default: true)''',
        require=False, default='true')
    
    changepoint_prior_scale = Option(
        doc='''**Syntax:** **changepoint_prior_scale=***<float>*
        **Description:** Changepoint flexibility (default: 0.05)''',
        require=False, validate=validators.Float(minimum=0.0), default=0.05)
    
    seasonality_prior_scale = Option(
        doc='''**Syntax:** **seasonality_prior_scale=***<float>*
        **Description:** Seasonality flexibility (default: 10.0)''',
        require=False, validate=validators.Float(minimum=0.0), default=10.0)
    
    regressors = Option(
        doc='''**Syntax:** **regressors=***<field1,field2,...>*
        **Description:** Comma-separated list of regressor fields''',
        require=False)
    
    seasonalities = Option(
        doc='''**Syntax:** **seasonalities=***<json_config>*
        **Description:** JSON configuration for custom seasonalities''',
        require=False)
    
    def stream(self, records):
        """
        Main streaming function that processes records
        """
        try:
            # Convert records to DataFrame
            df = pd.DataFrame(records)
            
            if df.empty:
                self.logger.error("No data received")
                return
            
            # Initialize Prophet algorithm
            prophet_algo = ProphetAlgorithm()
            
            # Parse boolean parameters
            yearly_seas = parse_boolean(self.yearly_seasonality)
            weekly_seas = parse_boolean(self.weekly_seasonality)
            daily_seas = parse_boolean(self.daily_seasonality)
            include_hist = parse_boolean(self.include_history)
            
            # Prepare data
            prophet_data = prophet_algo.prepare_data(
                df, self.ds_field, self.y_field, self.cap, self.floor
            )
            
            # Parse holidays if provided
            holidays_df = None
            if self.holidays and self.holidays in df.columns:
                holidays_df = parse_holidays(df, self.ds_field, self.holidays)
            
            # Create model
            model = prophet_algo.create_model(
                growth=self.growth,
                seasonality_mode=self.seasonality_mode,
                yearly_seasonality=yearly_seas,
                weekly_seasonality=weekly_seas,
                daily_seasonality=daily_seas,
                holidays=holidays_df,
                changepoint_prior_scale=self.changepoint_prior_scale,
                seasonality_prior_scale=self.seasonality_prior_scale,
                uncertainty_samples=self.uncertainty_samples,
                interval_width=self.confidence_interval
            )
            
            # Add regressors if specified
            if self.regressors:
                regressor_fields = [field.strip() for field in self.regressors.split(',')]
                prophet_algo.add_regressors(regressor_fields)
                
                # Add regressor data to prophet_data
                for regressor in regressor_fields:
                    if regressor in df.columns:
                        prophet_data[regressor] = pd.to_numeric(df[regressor], errors='coerce')
            
            # Add custom seasonalities if specified
            if self.seasonalities:
                try:
                    seasonalities_config = json.loads(self.seasonalities)
                    prophet_algo.add_seasonalities(seasonalities_config)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid seasonalities JSON: {str(e)}")
            
            # Fit model
            prophet_algo.fit_model(prophet_data)
            
            # Generate forecast
            forecast = prophet_algo.make_forecast(
                periods=self.periods,
                freq=self.freq,
                include_history=include_hist
            )
            
            # Prepare output records
            output_records = []
            for index, row in forecast.iterrows():
                record = {
                    'ds': row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
                    'yhat': row['yhat'],
                    'yhat_lower': row['yhat_lower'],
                    'yhat_upper': row['yhat_upper'],
                    'trend': row['trend'],
                    'forecast_type': 'historical' if index < len(prophet_data) else 'forecast'
                }
                
                # Add seasonal components
                if 'yearly' in forecast.columns:
                    record['yearly'] = row['yearly']
                if 'weekly' in forecast.columns:
                    record['weekly'] = row['weekly']
                if 'daily' in forecast.columns:
                    record['daily'] = row['daily']
                
                # Add actual values if available and in history
                if include_hist and index < len(prophet_data):
                    record['y'] = prophet_data.iloc[index]['y']
                
                output_records.append(record)
            
            # Yield results
            for record in output_records:
                yield record
                
        except Exception as e:
            self.logger.error(f"Error in prophet_forecast: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Yield error record
            yield {
                'error': str(e),
                'traceback': traceback.format_exc()
            }

if __name__ == '__main__':
    dispatch(ProphetForecastCommand, sys.argv, sys.stdin, sys.stdout, __name__)
