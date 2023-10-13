from elec_fcst import process_data, prediction


import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

import pytest

def test_process_data1():
    df_true = pd.read_csv('./test_data/actual.csv') # one day of weather and electricity measurement
    df_pred = pd.read_csv('./test_data/forecast.csv') # one day of weather forecast
    df_true, df_pred = process_data([df_true, df_pred])

    exp_true_col_name = ["time", "load_kw","pressure_kpa",'cloud_cover_pct','humidity_pct',
                         'temperature_c','wind_direction_deg','wind_speed_kmh']
    assert all(col_name in exp_true_col_name for col_name in df_true.columns)
    assert is_datetime64_any_dtype(df_true['time'])

    exp_pred_col_name = ["time","pressure_kpa",'cloud_cover_pct','temperature_c',
                         'wind_direction_deg','wind_speed_kmh']
    assert all(col_name in exp_pred_col_name for col_name in df_pred.columns)
    assert is_datetime64_any_dtype(df_pred['time'])


def test_process_data2():
    df_test = pd.read_csv('./test_data/na_col_name.csv') # one day of weather and electricity measurement
    with pytest.raises(Exception) as e:
        response = process_data([df_test, df_test])
    assert str(e.value) == "400 Bad Request: unexpected column name"

def test_process_data3():
    df_test = pd.read_csv('./test_data/na_col_num.csv') # one day of weather and electricity measurement
    with pytest.raises(Exception) as e:
        response = process_data([df_test, df_test])
    assert str(e.value) == "400 Bad Request: unexpected number of columns"

def test_process_data4():
    df_test = pd.read_csv('./test_data/na_row_num.csv') # one day of weather and electricity measurement
    with pytest.raises(Exception) as e:
        response = process_data([df_test, df_test])
    assert str(e.value) == "400 Bad Request: unexpected number of rows"

          



