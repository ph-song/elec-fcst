from elec_fcst import process_data, prediction
from model import lg_boost

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

import pytest

'''
from pymongo import MongoClient
import pymongo

client = MongoClient()
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["elec-fcst"]
pred_data = db["predict"]  #forecast data collection
actual_data = db["actual"] #actual data collection
'''

def test_process_data():
    df_true = pd.read_csv('./test_data/actual.csv')   
    df_pred = pd.read_csv('./test_data/forecast.csv')
    df_true, df_pred = process_data([df_true, df_pred])

    exp_true_col_name = ["time", "load_kw","pressure_kpa",'cloud_cover_pct','humidity_pct',
                         'temperature_c','wind_direction_deg','wind_speed_kmh']
    assert all(col_name in exp_true_col_name for col_name in df_true.columns)
    assert is_datetime64_any_dtype(df_true['time'])

    exp_pred_col_name = ["time","pressure_kpa",'cloud_cover_pct','temperature_c',
                         'wind_direction_deg','wind_speed_kmh']
    assert all(col_name in exp_pred_col_name for col_name in df_pred.columns)
    assert is_datetime64_any_dtype(df_pred['time'])



          



