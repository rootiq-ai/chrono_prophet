# Prophet Algorithm Troubleshooting Guide

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Command Execution Errors](#command-execution-errors)
3. [Data-Related Problems](#data-related-problems)
4. [Performance Issues](#performance-issues)
5. [Forecast Quality Problems](#forecast-quality-problems)
6. [Integration Issues](#integration-issues)
7. [Debug Techniques](#debug-techniques)

## Installation Issues

### Problem: ModuleNotFoundError: No module named 'prophet'

**Error Message:**
```
ModuleNotFoundError: No module named 'prophet'
```

**Solution:**
```bash
# Install Prophet with all dependencies
pip install prophet

# If using conda
conda install -c conda-forge prophet

# For CentOS/RHEL systems
sudo yum install python3-devel
pip install prophet

# For Ubuntu/Debian systems  
sudo apt-get install python3-dev
pip install prophet
```

**Verification:**
```spl
| makeresults 
| eval test_prophet=1
| prophet_forecast ds_field=_time y_field=test_prophet periods=1
```

### Problem: Prophet installation fails on macOS

**Error Message:**
```
ERROR: Failed building wheel for prophet
```

**Solution:**
```bash
# Install required system dependencies
brew install cmake
brew install boost

# Install Prophet with specific compiler
export CC=clang
export CXX=clang++
pip install prophet

# Alternative: Use conda
conda install -c conda-forge prophet
```

### Problem: Permission denied when installing

**Error Message:**
```
Permission denied: '/opt/splunk/bin/python'
```

**Solution:**
```bash
# Use sudo if installing system-wide
sudo /opt/splunk/bin/python -m pip install prophet

# Or install in user directory
/opt/splunk/bin/python -m pip install --user prophet

# Check Splunk Python path
/opt/splunk/bin/python -c "import sys; print(sys.path)"
```

## Command Execution Errors

### Problem: Command not found

**Error Message:**
```
Unknown command 'prophet_forecast'
```

**Solutions:**

1. **Check app installation:**
   ```bash
   ls $SPLUNK_HOME/etc/apps/prophet_algorithm/
   ```

2. **Verify commands.conf:**
   ```bash
   cat $SPLUNK_HOME/etc/apps/prophet_algorithm/default/commands.conf
   ```

3. **Restart Splunk:**
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

4. **Check app permissions:**
   ```bash
   chmod +x $SPLUNK_HOME/etc/apps/prophet_algorithm/bin/*.py
   ```

### Problem: Python version compatibility

**Error Message:**
```
SyntaxError: invalid syntax (python version issue)
```

**Solution:**
```bash
# Check Python version
python --version
python3 --version

# Ensure Splunk uses Python 3
echo 'python.version = python3' >> $SPLUNK_HOME/etc/system/local/commands.conf

# Restart Splunk
$SPLUNK_HOME/bin/splunk restart
```

### Problem: Import errors in custom commands

**Error Message:**
```
ImportError: cannot import name 'ProphetAlgorithm'
```

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la $SPLUNK_HOME/etc/apps/prophet_algorithm/lib/
   chmod 644 $SPLUNK_HOME/etc/apps/prophet_algorithm/lib/*.py
   ```

2. **Verify __init__.py files exist:**
   ```bash
   touch $SPLUNK_HOME/etc/apps/prophet_algorithm/lib/__init__.py
   touch $SPLUNK_HOME/etc/apps/prophet_algorithm/bin/__init__.py
   ```

3. **Check Python path in commands:**
   ```python
   # Add to top of command files
   import sys
   import os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
   ```

## Data-Related Problems

### Problem: No data received

**Error Message:**
```
No data received
```

**Solutions:**

1. **Check input data format:**
   ```spl
   | inputlookup your_data.csv 
   | head 5
   | table *
   ```

2. **Verify field names:**
   ```spl
   | inputlookup your_data.csv
   | eval has_date_field=if(isnotnull(date), "yes", "no")
   | eval has_value_field=if(isnotnull(sales), "yes", "no")
   | stats count by has_date_field, has_value_field
   ```

3. **Test with simple data:**
   ```spl
   | makeresults count=10
   | eval date=strftime(relative_time(now(), "-".tostring(10-_serial_number)."d"), "%Y-%m-%d")
   | eval sales=100+random()%50
   | prophet_forecast ds_field=date y_field=sales periods=5
   ```

### Problem: Date parsing issues

**Error Message:**
```
Unable to parse date field
```

**Solutions:**

1. **Check date format:**
   ```spl
   | inputlookup your_data.csv
   | eval parsed_date=strptime(date_field, "%Y-%m-%d")
   | where isnull(parsed_date)
   | head 5
   ```

2. **Convert date formats:**
   ```spl
   | inputlookup your_data.csv
   | eval standardized_date=case(
       match(date_field, "^\d{4}-\d{2}-\d{2}$"), date_field,
       match(date_field, "^\d{2}/\d{2}/\d{4}$"), strftime(strptime(date_field, "%m/%d/%Y"), "%Y-%m-%d"),
       1=1, null()
   )
   | where isnotnull(standardized_date)
   | prophet_forecast ds_field=standardized_date y_field=value periods=30
   ```

3. **Handle timezone issues:**
   ```spl
   | eval date_utc=strftime(_time, "%Y-%m-%d %H:%M:%S")
   | prophet_forecast ds_field=date_utc y_field=value periods=30
   ```

### Problem: Missing or null values

**Error Message:**
```
Missing values in target field
```

**Solutions:**

1. **Identify missing data:**
   ```spl
   | inputlookup your_data.csv
   | eval is_null_target=if(isnull(target_field), 1, 0)
   | stats sum(is_null_target) as null_count, count as total_count
   | eval null_percentage=round(null_count/total_count*100, 2)
   ```

2. **Fill missing values:**
   ```spl
   | inputlookup your_data.csv
   | fillnull value=0 target_field    // or use average
   | prophet_forecast ds_field=date y_field=target_field periods=30
   ```

3. **Interpolate missing values:**
   ```spl
   | inputlookup your_data.csv
   | sort date
   | streamstats avg(target_field) as rolling_avg window=3
   | eval target_field=coalesce(target_field, rolling_avg)
   | prophet_forecast ds_field=date y_field=target_field periods=30
   ```

### Problem: Insufficient historical data

**Error Message:**
```
Need at least 2 data points
```

**Solutions:**

1. **Check data volume:**
   ```spl
   | inputlookup your_data.csv
   | stats count as data_points, 
       min(date) as start_date, 
       max(date) as end_date
   | eval date_range_days=round((strptime(end_date,"%Y-%m-%d")-strptime(start_date,"%Y-%m-%d"))/86400,0)
   ```

2. **Expand date range:**
   ```spl
   // If you have sparse data, generate full date range
   | inputlookup your_data.csv
   | eval date_epoch=strptime(date, "%Y-%m-%d")
   | stats min(date_epoch) as min_date, max(date_epoch) as max_date
   | eval date_range=mvrange(min_date, max_date+86400, 86400)
   | mvexpand date_range
   | eval date=strftime(date_range, "%Y-%m-%d")
   | join type=left date [
       | inputlookup your_data.csv
   ]
   | fillnull value=0 target_field
   | prophet_forecast ds_field=date y_field=target_field periods=30
   ```

## Performance Issues

### Problem: Slow execution

**Symptoms:**
- Command takes very long to complete
- Timeouts in search results

**Solutions:**

1. **Reduce data size:**
   ```spl
   | inputlookup large_dataset.csv
   | where date >= relative_time(now(), "-2y@d")  // Last 2 years only
   | prophet_forecast ds_field=date y_field=value periods=30
   ```

2. **Optimize parameters:**
   ```spl
   | prophet_forecast ds_field=date y_field=value periods=30
       uncertainty_samples=100        // Reduce from 1000
       yearly_seasonality=false      // Disable if not needed
       weekly_seasonality=false      // Disable if not needed
   ```

3. **Use sampling:**
   ```spl
   | inputlookup huge_dataset.csv
   | where random() < 0.1           // 10% sample
   | prophet_forecast ds_field=date y_field=value periods=30
   ```

### Problem: Memory errors

**Error Message:**
```
MemoryError: Unable to allocate array
```

**Solutions:**

1. **Increase memory limits:**
   ```ini
   # In local/limits.conf
   [prophet_forecast]
   max_memory_usage_mb = 4096
   ```

2. **Process in chunks:**
   ```spl
   | inputlookup large_data.csv
   | eval chunk=floor(_serial_number/1000)
   | map maxsearches=10 search="
       | search chunk=$chunk$
       | prophet_forecast ds_field=date y_field=value periods=30
       | eval chunk=$chunk$
   "
   ```

3. **Aggregate data:**
   ```spl
   | inputlookup hourly_data.csv
   | bucket _time span=1d
   | stats avg(value) as daily_value by _time
   | eval date=strftime(_time, "%Y-%m-%d")
   | prophet_forecast ds_field=date y_field=daily_value periods=30
   ```

## Forecast Quality Problems

### Problem: Poor forecast accuracy

**Symptoms:**
- Large prediction intervals
- Forecasts don't follow expected patterns
- High error rates

**Diagnostic Steps:**

1. **Check data quality:**
   ```spl
   | inputlookup your_data.csv
   | eval outlier=if(abs(value-avg(value)) > 3*stdev(value), 1, 0)
   | stats sum(outlier) as outlier_count, count as total
   | eval outlier_percentage=round(outlier_count/total*100, 2)
   ```

2. **Analyze seasonality:**
   ```spl
   | inputlookup your_data.csv
   | eval day_of_week=strftime(strptime(date, "%Y-%m-%d"), "%w")
   | eval month=strftime(strptime(date, "%Y-%m-%d"), "%m")
   | stats avg(value) by day_of_week
   | sort day_of_week
   ```

3. **Tune parameters:**
   ```spl
   // More flexible model
   | prophet_forecast ds_field=date y_field=value periods=30
       changepoint_prior_scale=0.1         // Increase from 0.05
       seasonality_prior_scale=15          // Increase from 10
       seasonality_mode=multiplicative     // Try multiplicative
   ```

### Problem: Unrealistic trend extrapolation

**Solutions:**

1. **Use logistic growth:**
   ```spl
   | eval capacity=max_realistic_value
   | prophet_forecast ds_field=date y_field=value periods=30
       growth=logistic cap=capacity
   ```

2. **Adjust changepoint detection:**
   ```spl
   | prophet_forecast ds_field=date y_field=value periods=30
       changepoint_prior_scale=0.01    // More conservative
   ```

3. **Add external regressors:**
   ```spl
   | prophet_forecast ds_field=date y_field=sales periods=30
       regressors="marketing_spend,economic_indicator"
   ```

### Problem: Missing seasonal patterns

**Solutions:**

1. **Enable all seasonalities:**
   ```spl
   | prophet_forecast ds_field=date y_field=value periods=30
       yearly_seasonality=true
       weekly_seasonality=true
       daily_seasonality=true
   ```

2. **Add custom seasonality:**
   ```spl
   | prophet_forecast ds_field=date y_field=value periods=30
       seasonalities='[{"name": "monthly", "period": 30.5, "fourier_order": 8}]'
   ```

3. **Use multiplicative seasonality:**
   ```spl
   | prophet_forecast ds_field=date y_field=value periods=30
       seasonality_mode=multiplicative
   ```

## Integration Issues

### Problem: Results not appearing in dashboard

**Solutions:**

1. **Check search syntax:**
   ```xml
   <!-- In dashboard XML -->
   <search>
     <query>
       | inputlookup data.csv 
       | prophet_forecast ds_field=date y_field=sales periods=30
       | table ds yhat yhat_lower yhat_upper
     </query>
   </search>
   ```

2. **Verify field names:**
   ```spl
   | inputlookup data.csv
   | prophet_forecast ds_field=date y_field=sales periods=30
   | eval forecast_date=strftime(strptime(ds, "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d")
   | table forecast_date yhat yhat_lower yhat_upper
   ```

### Problem: Scheduled search failures

**Solutions:**

1. **Add error handling:**
   ```spl
   | inputlookup data.csv
   | eval row_count=1
   | stats sum(row_count) as total_rows
   | eval search_status=if(total_rows > 0, "success", "no_data")
   | append [
       | inputlookup data.csv
       | prophet_forecast ds_field=date y_field=sales periods=30
       | eval search_status="forecast_complete"
   ]
   | outputlookup forecast_results.csv
   ```

2. **Set appropriate timeouts:**
   ```ini
   # In savedsearches.conf
   [Prophet Daily Forecast]
   search = | inputlookup data.csv | prophet_forecast ...
   dispatch.ttl = 3600
   max_concurrent = 1
   ```

## Debug Techniques

### Enable Detailed Logging

1. **Add debug statements to Python code:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   logger.debug(f"Processing {len(df)} rows of data")
   ```

2. **Check Splunk logs:**
   ```bash
   tail -f $SPLUNK_HOME/var/log/splunk/splunkd.log | grep prophet
   ```

### Test with Minimal Data

```spl
// Minimal test case
| makeresults count=30
| eval date=strftime(relative_time(now(), "-".tostring(30-_serial_number)."d"), "%Y-%m-%d")
| eval value=100+_serial_number+10*sin(_serial_number/5)
| prophet_forecast ds_field=date y_field=value periods=5
```

### Parameter Validation

```spl
// Test parameter combinations
| makeresults 
| eval test_cases=split("linear|logistic", "|")
| mvexpand test_cases
| map search="
    | makeresults count=100
    | eval date=strftime(relative_time(now(), \"-\".tostring(100-_serial_number).\"d\"), \"%Y-%m-%d\")
    | eval value=100+_serial_number
    | prophet_forecast ds_field=date y_field=value periods=10 growth=$test_cases$
    | eval growth_type=\"$test_cases$\"
    | stats avg(yhat) as avg_forecast by growth_type
"
```

### Cross-validation for Debugging

```spl
| inputlookup historical_data.csv
| prophet_fit ds_field=date y_field=sales 
    model_name="debug_model"
    cross_validate=true
    cv_initial="365 days"
    cv_period="90 days" 
    cv_horizon="180 days"
| where component_type="cv_result"
| eval mape=abs(cv_error)/cv_y*100
| stats avg(mape) as avg_mape, max(mape) as max_mape
```

### Performance Profiling

```spl
// Time different parameter settings
| rest /services/search/jobs 
| search label="prophet_*"
| eval duration=tostring(round((dispatch_time-earliest_time)/60,2))."min"
| table label, duration, result_count
```

### Error Recovery Patterns

```spl
// Robust search with fallback
| union 
    [| inputlookup primary_data.csv 
     | prophet_forecast ds_field=date y_field=sales periods=30]
    [| inputlookup backup_data.csv
     | where isnull(primary_data)
     | prophet_forecast ds_field=date y_field=sales periods=30
     | eval source="backup"]
| fillnull value="primary" source
```

This troubleshooting guide should help resolve most common issues encountered when implementing and using the Prophet algorithm in Splunk MLTK. For additional support, check the Splunk community forums or Prophet documentation.
