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
    models = ['lgb', 'xgb', 'n48', 'n168']
    #get 7 days of data 
    projection = {'_id': 0, 'time':1}
    for model in models:
        projection[model+'_load1'] =  '$' + model+ '.load1'
        projection[model+'_load2'] =  '$' + model+ '.load2'
        projection[model+'_error1'] = '$' + model+ '.error1'
        projection[model+'_error2'] = '$' + model+ '.error2'

    #prediction data
    pred_7d = pred_data.find(filter={}, sort=list({'time': -1}.items()), limit=168, projection= projection)
                             #projection= {'_id': 0, 'time':1,
                             #             'lgb_load1': '$lgb.load1', 'lgb_load2': '$lgb.load2',
                             #             'xgb_load1': '$xgb.load1', 'xgb_load2': '$xgb.load2',
                             #             'n48_load1': '$n48.load1', 'n48_load2': '$n48.load2',
                             #             'n168_load1': '$n168.load1', 'n168_load2': '$n168.load2',
                             #             'lgb_error1': '$lgb.error1', 'lgb_error2': '$lgb.error2', 
                             #             'xgb_error1': '$xgb.error1', 'xgb_error2': '$xgb.error2', 
                             #             'n48_error1': '$n48.error1', 'n48_error2': '$n48.error2',
                             #             'n168_error1': '$n168.error1', 'n168_error2': '$n168.error2'})

    pred_result = [doc for doc in pred_7d]

    pred_res = pd.DataFrame(pred_result)
    for col in pred_res:
        if col == 'time':
            continue 
        model = col.split('_')[0] if '_' in col else col
        pred_res[model + '_load'] = pred_res[[model+'_load1', model+'_load2']].mean(axis=1)
        pred_res[model + '_error'] = pred_res[[model+'_error1', model+'_error2']].mean(axis=1) 
        
    #pred_res['lgb_load'] = pred_res[['lgb_load1', 'lgb_load2']].mean(axis=1)
    #pred_res['xgb_load'] = pred_res[['xgb_load1', 'xgb_load2']].mean(axis=1) 
    #pred_res['xgb_error'] = pred_res[['xgb_error1', 'xgb_error2']].mean(axis=1) 
    #pred_res['lgb_error'] = pred_res[['lgb_error1', 'lgb_error2']].mean(axis=1)  
    #pred_res['n48_load'] = pred_res[['n48_load1', 'n48_load2']].mean(axis=1) 
    #pred_res['n48_error'] = pred_res[['n48_error1', 'n48_error2']].mean(axis=1) 
    #pred_res['n168_load'] = pred_res[['n168_load1', 'n168_load2']].mean(axis=1) 
    #pred_res['n168_error'] = pred_res[['n168_error1', 'n168_error2']].mean(axis=1) 

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
        dfs[i].columns = dfs[i].columns.str.replace(' ', '') #remove spaces
        dfs[i].columns = dfs[i].columns.str.lower() #change to lower case

        #change column name to MongoDB field name 
        dfs[i] = dfs[i].rename(columns={"load(kw)": "load_kw", 
                                "pressure_kpa": "pressure_kpa", 'cloudcover(%)': 'cloud_cover_pct',
                                'humidity(%)': 'humidity_pct', 'temperature(c)': 'temperature_c',
                                'winddirection(deg)': 'wind_direction_deg', 'windspeed(kmh)':'wind_speed_kmh'})
        
        dfs[i] = dfs[i].dropna(how='all') #drop row where all values are NA
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
        time = time_now + timedelta(hours=i) #increment 'time'

        X = data_1w.iloc[i,:] #1 hour of predictors
        lgb_pred = float(model_lgb.predict(X)[0])  #predict with LightGBM
        xgb_pred = float(model_xgb.predict(xgb.DMatrix(X.to_frame().T))[0]) #predict with XGBoost
        n48_pred = model_naive(time, lag=48) #predict with seasoal naive (48 hours)
        n168_pred = model_naive(time, lag=168) #predict with seasoal naive (168 hours)

        
        if i < 24: #first 24 hours
            load_pred_df.append({'time':time, 'lgb.load1':lgb_pred, 'xgb.load1':xgb_pred, 'n48.load1': n48_pred, 'n168.load1': n168_pred})
        else: #last 24 hours
            load_pred_df.append({'time':time, 'lgb.load2':lgb_pred, 'xgb.load2':xgb_pred, 'n48.load2': n48_pred, 'n168.load2': n168_pred})
    insert_data(load_pred_df, pred_data) #update database

    return True

def model_naive(time_now, lag):
    print(time_now)
    result = get_history(time_now - timedelta(hours=lag), actual_data, excl_ref=False)
    result = result.to_dict('records') # 48hours naive
    result = result[0]['load_kw']
    return result


def get_history(reference_time, collection, hours=0, days=0, weeks=0, excl_ref=True):
    '''
    return history data of set time range in pd.DataFrame
    reference time: end date is excluded
    hours: how many hours of history data to get 
    excl_ref: exclude reference time data 
    '''
    end_date = reference_time
    start_date = reference_time - timedelta(hours=hours, days=days, weeks=weeks)
    #print(one_week_ago, reference_time)

    if excl_ref:
        result = collection.find(
            filter={'time': {'$gte': start_date, '$lt': end_date}},
            projection = {'_id': 0},
            sort=list({'time': -1}.items())
            ) 
    elif not(excl_ref):
        result = collection.find(
            filter={'time': {'$gte': start_date, '$lte': end_date}},
            projection = {'_id': 0},
            sort=list({'time': -1}.items())
            ) 
    
    history_data = []
    for doc in result:
        history_data.append(doc)
    if bool(history_data):
        history_data = pd.DataFrame(history_data).set_index('time', drop=True) 
    return history_data

def evaluate(df_true, reference_time):
    '''
    evaluate electricity load
    '''
    ytd_time = reference_time - timedelta(days=1) #yesterday timestamp 
    #get yesterday data, flatten it 
    pred_ytd = pred_data.find(filter={'time': {'$gte': ytd_time, '$lt': reference_time}},
                              projection= {'_id': 0, 'time':1,
                                           'lgb_load1': '$lgb.load1', 'lgb_load2': '$lgb.load2', 
                                            'xgb_load1': '$xgb.load1', 'xgb_load2': '$xgb.load2',
                                            'n48_load1': '$n48.load1', 'n48_load2': '$n48.load2',
                                            'n168_load1': '$n168.load1', 'n168_load2': '$n168.load2'})
    pred_res =pd.DataFrame([doc for doc in pred_ytd]) #prediction made yesterday
    #print(pred_res, df_true)

    error = pd.DataFrame([])
    error['time'] = pred_res['time']
    for col in pred_res:
        if col == 'time': #skip 'time' column
            continue
        model, num = col.split('_')[0] if '_' in col else col, col[-1] #string before first '_' is model name, last char is prediction order
        error[model + '.error' + num] = (pred_res[col] - df_true['load_kw']).abs() #calculate absolute error
    insert_data(error, pred_data)


def retrain(time_now):
    '''
    trigger retrain
    '''
    #get past 3 years of historical data
    data_3y = get_history(reference_time=time_now, collection=actual_data, weeks=156)
    print(data_3y.info())

    model_lgb = light_gbm.LightGBM(data_3y) #train LigthGBM
    model_lgb.model.save_model('model_lgb.txt') #save model

    model_xbg = xg_boost.XGBoost(data_3y) #train XGBoost
    model_xbg.model.save_model("model_xbg.json") #save model

    pass

if __name__ == '__main__':
   app.run("0.0.0.0", 888)