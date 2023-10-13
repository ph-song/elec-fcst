from elec_fcst import process_data, prediction
from model import lg_boost
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

import pytest

def test_predict():
   #load data
    X = pd.read_csv('test_data/predict.csv')
    X['time'] = pd.to_datetime(X['time'])
    X = X.set_index('time') #load testing data 

    model_lgb = lg_boost.LightGBM(model_file="model/lgb_model.txt") #import model
    prediction = model_lgb.predict(X)
    assert len(prediction) == 48



          



