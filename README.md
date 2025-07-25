# Prophet Algorithm for Splunk MLTK

A comprehensive implementation of Facebook's Prophet time series forecasting algorithm for Splunk Machine Learning Toolkit (MLTK).

## Overview

Prophet is a powerful time series forecasting tool developed by Facebook that is designed to handle:
- Strong seasonal effects with multiple seasons
- Holiday effects
- Missing data and outliers
- Non-linear trends with automatic changepoint detection
- External regressors
- Uncertainty intervals

## Features

- **Time Series Forecasting**: Generate accurate forecasts with trend and seasonality
- **Holiday Effects**: Model the impact of holidays on your time series
- **Custom Seasonality**: Add custom seasonal patterns beyond yearly/weekly/daily
- **External Regressors**: Include external variables that influence your target
- **Uncertainty Intervals**: Get confidence bounds around your predictions
- **Cross-Validation**: Validate model performance with time series cross-validation
- **Flexible Growth Models**: Support for linear and logistic growth patterns

## Installation

### Prerequisites

1. Splunk Enterprise 8.0+ or Splunk Cloud
2. Splunk Machine Learning Toolkit (MLTK) 5.3+
3. Python 3.7+

### Step 1: Install Dependencies

```bash
# Install Prophet and dependencies
pip install prophet pandas numpy scikit-learn matplotlib plotly

# Or use requirements.txt
pip install -r requirements.txt
```

### Step 2: Deploy the App

1. Copy the `prophet_algorithm` directory to `$SPLUNK_HOME/etc/apps/`
2. Restart Splunk
3. Verify installation:
   ```spl
   | makeresults | prophet_forecast ds_field=_time y_field=count periods=30
   ```

### Step 3: Verify Installation

Run this test query to ensure Prophet is working:

```spl
| makeresults count=100
| eval _time=relative_time(now(), "-".tostring(100-_serial_number)."d")
| eval date=strftime(_time, "%Y-%m-%d")
| eval value=100+_serial_number*0.1+10*sin(2*3.14159*_serial_number/30)
| prophet_forecast ds_field=date y_field=value periods=30
```

## Usage

### Basic Forecasting

```spl
| inputlookup your_data.csv
| prophet_forecast ds_field=date y_field=sales periods=30
```

### Advanced Usage with All Parameters

```spl
| inputlookup sales_data.csv
| prophet_forecast ds_field=date y_field=sales periods=90
    freq=D
    growth=linear
    seasonality_mode=additive
    yearly_seasonality=true
    weekly_seasonality=true
    daily_seasonality=false
    holidays=holiday_name
    cap=capacity_limit
    floor=minimum_value
    regressors="temperature,marketing_spend,competitor_price"
    changepoint_prior_scale=0.05
    seasonality_prior_scale=10.0
    uncertainty_samples=1000
    confidence_interval=0.8
    include_history=true
```

## Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `ds_field` | Date/time field name | `ds_field=date` |
| `y_field` | Target variable field name | `y_field=sales` |

### Optional Parameters

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `periods` | Number of future periods to forecast | 30 | Any positive integer |
| `freq` | Frequency of predictions | D | D, H, M, Y, etc. |
| `growth` | Growth model type | linear | linear, logistic |
| `seasonality_mode` | How seasonalities are combined | additive | additive, multiplicative |
| `yearly_seasonality` | Enable yearly seasonality | auto | auto, true, false |
| `weekly_seasonality` | Enable weekly seasonality | auto | auto, true, false |
| `daily_seasonality` | Enable daily seasonality | auto | auto, true, false |
| `holidays` | Field containing holiday names | None | Field name |
| `cap` | Capacity field for logistic growth | None | Field name |
| `floor` | Floor field for logistic growth | None | Field name |
| `regressors` | External regressor fields | None | Comma-separated list |
| `changepoint_prior_scale` | Changepoint flexibility | 0.05 | 0.001 to 0.5 |
| `seasonality_prior_scale` | Seasonality flexibility | 10.0 | 0.01 to 100 |
| `uncertainty_samples` | Samples for uncertainty intervals | 1000 | 0 to 5000 |
| `confidence_interval` | Width of confidence intervals | 0.8 | 0.1 to 0.99 |
| `include_history` | Include historical data in output | true | true, false |

## Examples

### Example 1: Basic Sales Forecasting

```spl
// Load sales data
| inputlookup daily_sales.csv

// Generate 30-day forecast
| prophet_forecast ds_field=date y_field=sales periods=30
    yearly_seasonality=true weekly_seasonality=true

// Format results
| eval forecast_date=strftime(strptime(ds, "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d")
| table forecast_date yhat yhat_lower yhat_upper trend yearly weekly
```

### Example 2: Forecasting with Holidays

```spl
// Load data with holiday information
| inputlookup sales_with_holidays.csv

// Forecast with holiday effects
| prophet_forecast ds_field=date y_field=sales periods=60
    holidays=holiday_name
    seasonality_mode=multiplicative
    confidence_interval=0.9
```

### Example 3: Multiple External Regressors

```spl
// Load data with external factors
| inputlookup sales_with_factors.csv

// Forecast with multiple regressors
| prophet_forecast ds_field=date y_field=sales periods=90
    regressors="temperature,marketing_spend,competitor_price,economic_index"
    changepoint_prior_scale=0.1
    include_history=false
```

### Example 4: Logistic Growth with Capacity

```spl
// Load data with capacity constraints
| inputlookup user_adoption.csv

// Forecast with logistic growth
| prophet_forecast ds_field=date y_field=users periods=180
    growth=logistic
    cap=max_capacity
    floor=min_users
    yearly_seasonality=true
```

## Output Fields

| Field | Description |
|-------|-------------|
| `ds` | Date/time of the prediction |
| `yhat` | Predicted value |
| `yhat_lower` | Lower bound of confidence interval |
| `yhat_upper` | Upper bound of confidence interval |
| `trend` | Trend component |
| `yearly` | Yearly seasonal component (if enabled) |
| `weekly` | Weekly seasonal component (if enabled) |
| `daily` | Daily seasonal component (if enabled) |
| `holidays` | Holiday effects (if holidays provided) |
| `forecast_type` | 'historical' or 'forecast' |

## Data Requirements

### Input Data Format

Your data should have:
- **Date column**: Properly formatted dates (YYYY-MM-DD or timestamp)
- **Target column**: Numeric values to forecast
- **No missing dates**: Fill gaps or Prophet will interpolate
- **Sufficient history**: At least 2 data points, preferably 2+ seasons

### Data Quality Tips

1. **Handle missing values**: Fill or interpolate missing values before forecasting
2. **Remove outliers**: Consider outlier detection and treatment
3. **Consistent frequency**: Ensure regular time intervals
4. **Sufficient history**: More historical data generally improves forecasts

## Best Practices

### Model Configuration

1. **Start simple**: Begin with basic parameters, then add complexity
2. **Validate thoroughly**: Use cross-validation for model evaluation
3. **Monitor performance**: Track forecast accuracy over time
4. **Domain knowledge**: Incorporate business understanding into model choices

### Parameter Tuning

1. **Changepoint prior scale**: Lower values = less flexible trend
2. **Seasonality prior scale**: Higher values = more flexible seasonality
3. **Growth model**: Use logistic when you know the saturation point
4. **Seasonality mode**: Multiplicative when seasonal effects grow with trend

### Production Deployment

1. **Regular retraining**: Update models with new data
2. **Performance monitoring**: Track forecast accuracy metrics
3. **Version control**: Maintain model configurations and parameters
4. **Documentation**: Document model assumptions and limitations

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'prophet'"**
   - Install Prophet: `pip install prophet`

2. **"No data received" error**
   - Check input data has required fields
   - Verify field names match parameters

3. **Poor forecast quality**
   - Increase historical data period
   - Adjust changepoint and seasonality parameters
   - Add relevant external regressors

4. **Slow performance**
   - Reduce uncertainty_samples
   - Use fewer periods for forecasting
   - Consider data sampling for large datasets

### Debug Mode

Enable detailed logging by modifying the Python files to set logging level to DEBUG.

## Advanced Features

### Custom Seasonalities

Add custom seasonal patterns using the `seasonalities` parameter:

```spl
| prophet_forecast ds_field=date y_field=sales periods=30
    seasonalities='[{"name": "monthly", "period": 30.5, "fourier_order": 5}]'
```

### Cross-Validation

Evaluate model performance using time series cross-validation (implement separately):

```python
from prophet.diagnostics import cross_validation, performance_metrics

cv_results = cross_validation(model, initial='730 days', period='180 days', horizon='365 days')
metrics = performance_metrics(cv_results)
```

## Support and Resources

- **Splunk MLTK Documentation**: [Splunk ML Toolkit](https://docs.splunk.com/Documentation/MLApp)
- **Prophet Documentation**: [Prophet Documentation](https://facebook.github.io/prophet/)
- **GitHub Issues**: Report bugs and feature requests
- **Splunk Community**: Get help from other users

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## Changelog

### Version 1.0.0
- Initial release
- Basic Prophet forecasting functionality
- Holiday effects support
- External regressors support
- Custom seasonalities support
- Comprehensive documentation and examples
