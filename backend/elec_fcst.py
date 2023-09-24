from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from zipfile import ZipFile
from werkzeug.utils import secure_filename
import json

from datetime import datetime, timedelta

from pymongo import MongoClient
import pymongo
from pprint import pprint

import pandas as pd
import numpy as np

import light_gbm
import xg_boost
import xgboost as xgb
import lightgbm as lgb


app = Flask(__name__)
CORS(app)

client = MongoClient()
client = pymongo.MongoClient("mongodb://localhost:27017/")

db = client["elec-fcst"]
pred_data = db["predict"]  #forecast data collection
actual_data = db["actual"] #actual data collection

@app.route('/', methods = ['GET'])
def get_data():
    '''
    get history data, prediction data or performance
    '''
    #get 7 days of data 

    #prediction data
    pred_7d = pred_data.find(filter={}, sort=list({'time': -1}.items()), limit=168,
                             projection= {'_id': 0, 'time':1,
                                          'lgb_load1': '$lgb.load1', 'lgb_load2': '$lgb.load2',
                                          'lgb_error1': '$lgb.error1', 'lgb_error2': '$lgb.error2', 
                                          'xgb_load1': '$xgb.load1', 'xgb_load2': '$xgb.load2',
                                          'xgb_error1': '$xgb.error1', 'xgb_error2': '$xgb.error2'})
    pred_result = [doc for doc in pred_7d]

    pred_res = pd.DataFrame(pred_result)
    pred_res['lgb_load'] = pred_res[['lgb_load1', 'lgb_load2']].mean(axis=1)
    pred_res['xgb_load'] = pred_res[['xgb_load1', 'xgb_load2']].mean(axis=1) 
    pred_res['xgb_error'] = pred_res[['xgb_error1', 'xgb_error2']].mean(axis=1) 
    pred_res['lgb_error'] = pred_res[['lgb_error1', 'lgb_error2']].mean(axis=1)  
    pred_res = pred_res.fillna(0).to_dict('records')

    #actaul data
    actual_7d = actual_data.find(filter={}, sort=list({'time': -1}.items()), limit=168,
                                  projection={'_id':0, 'load_kw':1, 'time':1})
    actual_res = [doc for doc in actual_7d]

    response = jsonify({'actual': actual_res, 'predict':pred_res }) 
    return response


@app.route('/upload', methods = ['POST'])
def upload():
    '''
    data preprocessing, data formatting, upload data to database 
    question: is it zip file or csv file
    '''
    file = request.files['zip_file']  
    dfs = extract(file) #extract data from zipped file
    df_true, df_pred = process_data(dfs) #process dataframes

    time_now = df_true['time'].iloc[-1] + timedelta(hours=1) #time now

    evaluate(df_true, reference_time = time_now)

    if time_now.weekday() == 0: #retrain model if day of date is Monday
        retrain(time_now)

    prediction(time_now)
    return 'data uploaded successfully', 200

def extract(file):
    '''
    take in file object
    unzip file, read csv files, convert to pd.dataframe, store in a list
    return the list
    '''
    zip_file = ZipFile(file.stream._file)
    dfs = [] #to store dataframes

    #extract all csv file in zipped file 
    for text_file in zip_file.infolist():
        if text_file.filename.endswith('.csv') and text_file:
            data = pd.read_csv(zip_file.open(text_file.filename), encoding='unicode_escape')
            if not data.empty:
                dfs.append(data)
    return dfs

def process_data(dfs):
    '''
    format date format & handle missing data
    take in list of dataframes
    return df, df_true, df_pred
    '''
    df_true, df_pred = [], []
    
    for i in range(len(dfs)):
        #change column name to MongoDB field name 
        dfs[i] = dfs[i].rename(columns={"Time": 'time', "Load (kW)": "load_kw", 
                                "Pressure_kpa": "pressure_kpa", 'Cloud Cover (%)': 'cloud_cover_pct',
                                'Humidity (%)': 'humidity_pct', 'Temperature (C)': 'temperature_c',
                                'Wind Direction (deg)': 'wind_direction_deg', 'Wind Speed (kmh)':'wind_speed_kmh'})
        dfs[i]['time']= pd.to_datetime(dfs[i]['time']) #format date datatype
       
        if dfs[i].shape[1]==6: #forecast data has 6 columns
            df_pred = dfs[i] #store data in a variable 
            insert_data(data = df_pred, collection=pred_data)  #insert database

        elif dfs[i].shape[1]==8: #actual data has 6 columns
            df_true = dfs[i] #store data in a variable 
            insert_data(data = df_true, collection=actual_data) #insert database
    
    return df_true, df_pred

def insert_data(data, collection):
    '''
    take in pd.DataFrame or dictionary in records format 
    update document if exist else create document
    '''
    if isinstance(data, pd.DataFrame):
        data = data.to_dict('records')

    for point in data:
        #if manage to find one, update the document
        is_exist = collection.find_one_and_update(filter = {'time':point["time"]}, 
                          update = {'$set':point}) #replace if exist
        if not bool(is_exist):
            collection.insert_one(point) #insert 

    return True

def prediction(time_now):
    '''
    forecast electricity load

    time_now: point where to start making prediction
    time: time of first hour of 48 hours prediction
    '''
    #get history data, sort, add suffix '_lag168', get first 48 hours 
    data_1w = get_history(reference_time=time_now, collection=actual_data, weeks = 1).sort_index().add_suffix('_lag168').iloc[:48,:]

    #data frame to store predicted load 
    model_lgb = lgb.Booster(model_file='model_lgb.txt')
    model_xgb = xgb.Booster(model_file="model_xbg.json")

    load_pred_df = [] #store records of prediction
    for i in range(len(data_1w)):
        X = data_1w.iloc[i,:] #1 hour of predictors
        lgb_pred = float(model_lgb.predict(X)[0])  #predict with LightGBM
        xgb_pred = float(model_xgb.predict(xgb.DMatrix(X.to_frame().T))[0]) #predict with XGBoost
        time = time_now + timedelta(hours=i) #increment 'time'
        if i < 24: #first 24 hours
            load_pred_df.append({'time':time, 'lgb.load1':lgb_pred, 'xgb.load1':xgb_pred})
        else: #last 24 hours
            load_pred_df.append({'time':time, 'lgb.load2':lgb_pred, 'xgb.load2':xgb_pred})

    insert_data(load_pred_df, pred_data) #update database

    return True

    #loop through time range 


    #make prediction 
    #evaluate 
    #upload predicted and evaluation
    pass

def get_history(reference_time, collection, hours=0, days=0, weeks=0):
    '''
    return history data of set time range in pd.DataFrame
    reference time 
    hours: how many hours of history data to get 
    '''
    one_week_ago = reference_time - timedelta(hours=hours, days=days, weeks=weeks)
    print(one_week_ago, reference_time)
    result = collection.find(
        filter={'time': {'$gte': one_week_ago, '$lt': reference_time}},
        projection = {'_id': 0},
        sort=list({'time': -1}.items())
        ) #past seven days of data
    
    history_data = []
    for doc in result:
        history_data.append(doc)
    return pd.DataFrame(history_data).set_index('time', drop=True)


def evaluate(df_true, reference_time):
    '''
    evaluate electricity load
    '''
    # get yesterday data, flatten it 
    ytd_time = reference_time - timedelta(days=1)
    pred_ytd = pred_data.find(filter={'time': {'$gte': ytd_time, '$lt': reference_time}},
                              projection= {'_id': 0, 'time':1,
                                           'lgb_load1': '$lgb.load1', 'lgb_load2': '$lgb.load2', 
                                            'xgb_load1': '$xgb.load1', 'xgb_load2': '$xgb.load2'})
    pred_res =pd.DataFrame([doc for doc in pred_ytd]) #prediction made yesterday
    print(pred_res, df_true)

    error = pd.DataFrame([])
    error['time'] = pred_res['time']
    for col in pred_res:
        if col == 'time':
            continue
        model, num = col[:3], col[-1] #first three char is model, last char is prediction order
        error[model + '.error' + num] = (pred_res[col] - df_true['load_kw']).abs()
    insert_data(error, pred_data)


def retrain(time_now):
    '''
    trigger retrain
    '''
    data_3y = get_history(reference_time=time_now, collection=actual_data, weeks=156)
    model_lgb = light_gbm.LightGBM(data_3y)
    model_lgb.model.save_model('model_lgb.txt')

    model_xbg = xg_boost.XGBoost(data_3y)
    model_xbg.model.save_model("model_xbg.json")

    pass

if __name__ == '__main__':
   app.run("0.0.0.0", 888)