#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="prophet_algorithm",
    version="1.0.0",
    description="Facebook Prophet time series forecasting algorithm for Splunk MLTK",
    long_description="""
    This package provides Facebook Prophet time series forecasting capabilities
    for Splunk Machine Learning Toolkit. Prophet is a forecasting tool developed
    by Facebook that is designed to handle time series data with strong seasonal
    effects and several seasons of historical data.
    
    Features:
    - Time series forecasting with trend and seasonality
    - Holiday effects modeling
    - Custom seasonality support
    - External regressors
    - Uncertainty intervals
    - Cross-validation capabilities
    """,
    author="Splunk MLTK Team",
    author_email="mltk@splunk.com",
    url="https://github.com/splunk/prophet-algorithm",
    packages=find_packages(),
    install_requires=[
        "prophet>=1.1.0",
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "scikit-learn>=1.0.0",
        "matplotlib>=3.3.0",
        "plotly>=5.0.0"
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    keywords="time-series forecasting prophet splunk machine-learning",
    project_urls={
        "Bug Reports": "https://github.com/splunk/prophet-algorithm/issues",
        "Source": "https://github.com/splunk/prophet-algorithm",
        "Documentation": "https://docs.splunk.com/Documentation/MLApp"
    }
)
