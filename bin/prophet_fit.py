#!/usr/bin/env python

import sys
import os
import pandas as pd
import json
import pickle
from datetime import datetime
import traceback

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from prophet_base import ProphetAlgorithm
from utils import parse_boolean, parse_holidays

@Configuration()
class ProphetFitCommand(StreamingCommand):
    """
    Custom Splunk command to train/fit a Prophet model for later use
    
    Usage:
    | prophet_fit ds_field=<date_field> y_field=<target_field> 
                model_name=<model_name> growth=<linear|logistic> 
                seasonality_mode=<additive|multiplicative>
                yearly_seasonality=<auto|true|false> weekly_seasonality=<auto|true|false>
                daily_seasonality=<auto|true|false> holidays=<holiday_field>
                cap=<capacity_field> floor=<floor_field>
                changepoint_prior_scale=<float> seasonality_prior_scale=<float>
                regressors=<field1,field2,...> seasonalities=<json_config>
                save_model=<true|false> model_path=<path>
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
    
    model_name = Option(
        doc='''**Syntax:** **model_name=***<string>*
        **Description:** Name for the trained model (required)''',
        require=True)
    
    # Optional parameters
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
    
    changepoint_prior_scale = Option(
        doc='''**Syntax:** **changepoint_prior_scale=***<float>*
        **Description:** Changepoint flexibility (default: 0.05)''',
        require=False, validate=validators.Float(minimum=0.0), default=0.05)
    
    seasonality_prior_scale = Option(
        doc='''**Syntax:** **seasonality_prior_scale=***<float>*
        **Description:** Seasonality flexibility (default: 10.0)''',
        require=False, validate=validators.Float(minimum=0.0), default=10.0)
    
    uncertainty_samples = Option(
        doc='''**Syntax:** **uncertainty_samples=***<integer>*
        **Description:** Number of samples for uncertainty intervals (default: 1000)''',
        require=False, validate=validators.Integer(minimum=0), default=1000)
    
    confidence_interval = Option(
        doc='''**Syntax:** **confidence_interval=***<float>*
        **Description:** Width of confidence intervals (default: 0.8)''',
        require=False, validate=validators.Float(minimum=0.0, maximum=1.0), default=0.8)
    
    regressors = Option(
        doc='''**Syntax:** **regressors=***<field1,field2,...>*
        **Description:** Comma-separated list of regressor fields''',
        require=False)
    
    seasonalities = Option(
        doc='''**Syntax:** **seasonalities=***<json_config>*
        **Description:** JSON configuration for custom seasonalities''',
        require=False)
    
    save_model = Option(
        doc='''**Syntax:** **save_model=***<true|false>*
        **Description:** Save the trained model to disk (default: true)''',
        require=False, default='true')
    
    model_path = Option(
        doc='''**Syntax:** **model_path=***<path>*
        **Description:** Path to save the model (default: auto-generated)''',
        require=False)
    
    cross_validate = Option(
        doc='''**Syntax:** **cross_validate=***<true|false>*
        **Description:** Perform cross-validation (default: false)''',
        require=False, default='false')
    
    cv_initial = Option(
        doc='''**Syntax:** **cv_initial=***<period>*
        **Description:** Initial training period for CV (default: 730 days)''',
        require=False, default='730 days')
    
    cv_period = Option(
        doc='''**Syntax:** **cv_period=***<period>*
        **Description:** Spacing between cutoffs for CV (default: 180 days)''',
        require=False, default='180 days')
    
    cv_horizon = Option(
        doc='''**Syntax:** **cv_horizon=***<period>*
        **Description:** Forecast horizon for CV (default: 365 days)''',
        require=False, default='365 days')
    
    def stream(self, records):
        """
        Main streaming function that trains the Prophet model
        """
        try:
            # Convert records to DataFrame
            df = pd.DataFrame(records)
            
            if df.empty:
                self.logger.error("No data received")
                yield {'error': 'No data received'}
                return
            
            # Initialize Prophet algorithm
            prophet_algo = ProphetAlgorithm()
            
            # Parse boolean parameters
            yearly_seas = parse_boolean(self.yearly_seasonality)
            weekly_seas = parse_boolean(self.weekly_seasonality)
            daily_seas = parse_boolean(self.daily_seasonality)
            save_model_flag = parse_boolean(self.save_model)
            cv_flag = parse_boolean(self.cross_validate)
            
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
            regressor_fields = []
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
                    prophet_algo.logger.error(f"Invalid seasonalities JSON: {str(e)}")
            
            # Fit model
            fitted_model = prophet_algo.fit_model(prophet_data)
            
            # Perform cross-validation if requested
            cv_results = None
            cv_metrics = None
            if cv_flag:
                try:
                    cv_results = prophet_algo.cross_validate(
                        prophet_data,
                        initial=self.cv_initial,
                        period=self.cv_period,
                        horizon=self.cv_horizon
                    )
                    cv_metrics = prophet_algo.calculate_metrics(cv_results)
                except Exception as e:
                    prophet_algo.logger.warning(f"Cross-validation failed: {str(e)}")
            
            # Save model if requested
            model_save_path = None
            if save_model_flag:
                if self.model_path:
                    model_save_path = self.model_path
                else:
                    # Generate default path
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_save_path = f"/tmp/prophet_model_{self.model_name}_{timestamp}.pkl"
                
                try:
                    prophet_algo.save_model(model_save_path)
                except Exception as e:
                    prophet_algo.logger.error(f"Failed to save model: {str(e)}")
                    model_save_path = None
            
            # Get model components for output
            changepoints = fitted_model.changepoints
            params = fitted_model.params
            
            # Prepare training summary
            training_summary = {
                'model_name': self.model_name,
                'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_points': len(prophet_data),
                'date_range_start': prophet_data['ds'].min().strftime('%Y-%m-%d'),
                'date_range_end': prophet_data['ds'].max().strftime('%Y-%m-%d'),
                'growth_model': self.growth,
                'seasonality_mode': self.seasonality_mode,
                'yearly_seasonality': yearly_seas,
                'weekly_seasonality': weekly_seas,
                'daily_seasonality': daily_seas,
                'num_changepoints': len(changepoints),
                'changepoint_prior_scale': self.changepoint_prior_scale,
                'seasonality_prior_scale': self.seasonality_prior_scale,
                'has_holidays': holidays_df is not None,
                'num_regressors': len(regressor_fields),
                'regressor_names': ','.join(regressor_fields) if regressor_fields else '',
                'model_saved': model_save_path is not None,
                'model_path': model_save_path or '',
                'cross_validated': cv_flag
            }
            
            # Add cross-validation metrics if available
            if cv_metrics is not None:
                training_summary.update({
                    'cv_mse': float(cv_metrics['mse'].mean()),
                    'cv_rmse': float(cv_metrics['rmse'].mean()),
                    'cv_mae': float(cv_metrics['mae'].mean()),
                    'cv_mape': float(cv_metrics['mape'].mean()),
                    'cv_coverage': float(cv_metrics['coverage'].mean())
                })
            
            # Yield training summary
            yield training_summary
            
            # Yield changepoint information
            for i, cp in enumerate(changepoints):
                yield {
                    'model_name': self.model_name,
                    'component_type': 'changepoint',
                    'changepoint_index': i,
                    'changepoint_date': cp.strftime('%Y-%m-%d'),
                    'changepoint_value': float(params.get('delta', [0] * len(changepoints))[i]) if 'delta' in params else 0.0
                }
            
            # Yield seasonality information
            seasonality_info = {
                'model_name': self.model_name,
                'component_type': 'seasonality',
                'yearly_enabled': yearly_seas,
                'weekly_enabled': weekly_seas,
                'daily_enabled': daily_seas
            }
            
            if self.seasonalities:
                seasonality_info['custom_seasonalities'] = self.seasonalities
            
            yield seasonality_info
            
            # If cross-validation was performed, yield detailed results
            if cv_results is not None:
                for index, row in cv_results.head(10).iterrows():  # Limit to first 10 rows
                    yield {
                        'model_name': self.model_name,
                        'component_type': 'cv_result',
                        'cv_cutoff': row['cutoff'].strftime('%Y-%m-%d'),
                        'cv_ds': row['ds'].strftime('%Y-%m-%d'),
                        'cv_yhat': float(row['yhat']),
                        'cv_y': float(row['y']),
                        'cv_error': float(row['y'] - row['yhat'])
                    }
                
        except Exception as e:
            self.logger.error(f"Error in prophet_fit: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Yield error record
            yield {
                'model_name': self.model_name or 'unknown',
                'error': str(e),
                'traceback': traceback.format_exc(),
                'component_type': 'error'
            }

if __name__ == '__main__':
    dispatch(ProphetFitCommand, sys.argv, sys.stdin, sys.stdout, __name__)
