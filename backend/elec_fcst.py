from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from zipfile import ZipFile
from werkzeug.utils import secure_filename
import json
from datetime import datetime, timedelta
import math 

from pymongo import MongoClient
import pymongo
from pprint import pprint

import pandas as pd

import light_gbm
import xg_boost
import cat_boost
import xgboost as xgb
import lightgbm as lgb
import catboost as ctb

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
    models = ['lgb', 'xgb', 'cat', 'n48', 'n168']

    #get 7 days of data 
    projection = {'_id': 0, 'time':1}
    for model in models:
        projection[model+'_load1'] =  '$' + model+ '.load1'
        projection[model+'_load2'] =  '$' + model+ '.load2'
        projection[model+'_error1'] = '$' + model+ '.error1'
        projection[model+'_error2'] = '$' + model+ '.error2'

    #latest 168 hours of prediction data
    pred_7d = pred_data.find(filter={}, sort=list({'time': -1}.items()), limit=168, projection= projection)
    pred_result = [doc for doc in pred_7d]
    pred_res = pd.DataFrame(pred_result)

    # mean of load1 & load2 and error1 & error2
    for col in pred_res:
        if col == 'time':
            continue 
        model = col.split('_')[0] if '_' in col else col
        pred_res[model + '_load'] = pred_res[[model+'_load1', model+'_load2']].mean(axis=1, skipna=True)
        
        if model+'_error1' in pred_res.columns and model+'_error2' in pred_res.columns:
            pred_res[model + '_error'] = pred_res[[model+'_error1', model+'_error2']].mean(axis=1) 

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


    #if time_now.weekday() == 0: #retrain model if day of date is Monday
    #    retrain(time_now)

    prediction(time_now)
    return 'data uploaded successfully', 200

def get_error(model: str, reference_time, hours=168):
    '''
    get past hours time MAE from reference_time of model
    '''

    #projection
    projection = {'_id': 0, 'time':1}
    projection[model+'_error1'] = '$' + model+ '.error1'
    projection[model+'_error2'] = '$' + model+ '.error2'

    #filter
    end_date = reference_time
    start_date = reference_time - timedelta(hours=hours)
    filter={'time': {'$gte': start_date, '$lt': end_date}}

    #prediction data
    error_7d = pred_data.find(filter=filter, sort=list({'time': -1}.items()), projection= projection)
    error_res = pd.DataFrame([doc for doc in error_7d])
    if model+'_error1' in error_res.columns and model+'_error2' in error_res.columns:
        error = error_res[[model+'_error1', model+'_error2']].mean(skipna=True, axis=1).mean(axis = 0) #error
    return error

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

        elif dfs[i].shape[1]==8: #actual data has 8 columns
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
    #load model
    model_lgb = lgb.Booster(model_file='lgb_model.txt')
    model_xgb = xgb.Booster(model_file="xbg_model.json")
    model_cat = ctb.CatBoostRegressor().load_model("cat_model.json", format='json')

    load_pred_df = [] #store records of prediction
    for i in range(len(data_1w)):
        time = time_now + timedelta(hours=i) #increment 'time'

        X = data_1w.iloc[i,:] #1 hour of predictors
        lgb_pred = float(model_lgb.predict(X)[0])  #predict with LightGBM
        xgb_pred = float(model_xgb.predict(xgb.DMatrix(X.to_frame().T))[0]) #predict with XGBoost
        cat_pred = model_cat.predict(X)
        n48_pred = naive_model(time, lag=48) #predict with seasoal naive (48 hours)
        n168_pred = naive_model(time, lag=168) #predict with seasoal naive (168 hours)

        if i < 24: #first 24 hours dd
            load_pred_df.append({'time':time, 'lgb.load1':lgb_pred, 'xgb.load1':xgb_pred, 'cat.load1':cat_pred, 'n48.load1': n48_pred, 'n168.load1': n168_pred})
        else: #last 24 hours
            load_pred_df.append({'time':time, 'lgb.load2':lgb_pred, 'xgb.load2':xgb_pred, 'cat.load2':cat_pred, 'n48.load2': n48_pred, 'n168.load2': n168_pred})
    insert_data(load_pred_df, pred_data) #update database

    return True

def naive_model(time_now, lag):
    result = get_history(time_now - timedelta(hours=lag), actual_data, excl_ref=False)
    if not (result.empty):
        result = result.to_dict('records') # 48hours naive
        result = result[0]['load_kw']
    else:
        result = None
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
    history_data = pd.DataFrame(history_data)
    if not (history_data.empty):
        history_data = history_data.set_index('time', drop=True) 
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
                                            'cat_load1': '$cat.load1', 'cat_load2': '$cat.load2',
                                            'n48_load1': '$n48.load1', 'n48_load2': '$n48.load2',
                                            'n168_load1': '$n168.load1', 'n168_load2': '$n168.load2'})
    pred_result = [doc for doc in pred_ytd]
    pred_res =pd.DataFrame(pred_result)
    if not(pred_ytd.alive): #prediction made yesterday
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

    model_cat = cat_boost.CatBoost(data_3y)
    model_cat.model.save_model('cat_model.json', format="json")

    model_lgb = light_gbm.LightGBM(data_3y) #train LigthGBM
    model_lgb.model.save_model('lgb_model.txt') #save model

    model_xbg = xg_boost.XGBoost(data_3y) #train XGBoost
    model_xbg.model.save_model("xbg_model.json") #save model

if __name__ == '__main__':
   app.run("0.0.0.0", 888)