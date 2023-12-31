from flask import Flask, jsonify, send_file, request, Response, abort
from flask_cors import CORS
from zipfile import ZipFile
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from pymongo import MongoClient
import pymongo
from pprint import pprint

import pandas as pd

import model.lg_boost as lg_boost
#import model.xg_boost as xg_boost
#import model.cat_boost as cat_boost

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
    #models = ['lgb', 'xgb', 'cat', 'n48', 'n168']
    models = ['lgb', 'n48', 'n168']

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
        if model+'_load1' in pred_res.columns and model+'_load2' in pred_res.columns:
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
    handle data uploaded by user
    '''
    file = request.files['zip_file']            # zipped file in request
    dfs = extract(file)                         # extract data from zipped file
    df_true, df_pred = process_data(dfs)        # process dataframes
    time_now = df_true['time'].iloc[-1] + timedelta(hours=1) #time now
    if time_now.weekday() == 0:                 # retrain model if day of date is Monday
        retrain(time_now)
    evaluate(df_true, reference_time = time_now)# evaluate performance of model the day before
    prediction(time_now)                        # make prediction
    
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
    if len(dfs)!=2:
        raise_error('unexpected number of file in zipped folder')
    
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
        
        exp_col_name = ["time", "load_kw","pressure_kpa",'cloud_cover_pct','humidity_pct','temperature_c','wind_direction_deg','wind_speed_kmh']
        if not all(col_name in exp_col_name for col_name in dfs[i].columns):
            raise_error('unexpected column name', 400)

        
        dfs[i] = dfs[i].dropna(how='all') #drop row where all values are NA
        dfs[i]['time']= pd.to_datetime(dfs[i]['time']) #format date datatype

        if len(dfs[i]) != 24:
            raise_error('unexpected number of rows')

        if dfs[i].shape[1]==6: #forecast data has 6 columns
            df_pred = dfs[i] #store data in a variable 
            insert_data(data = df_pred, collection=pred_data)  #insert database

        elif dfs[i].shape[1]==8: #actual data has 8 columns
            df_true = dfs[i] #store data in a variable 
            insert_data(data = df_true, collection=actual_data) #insert database

        else:
            raise_error('unexpected number of columns')
    
    return df_true, df_pred

def insert_data(data, collection):
    '''
    take in pd.DataFrame or dictionary in records format 
    update document if exist else create document
    '''
    if isinstance(data, pd.DataFrame):
        data = data.to_dict('records')
        
    for point in data:
        #point = convert_to_nested(point)
        #if manage to find one, update the document
        is_exist = collection.find_one_and_update(filter = {'time':point["time"]}, 
                          update = {'$set':point}) 
        #replace if existx
        if not bool(is_exist):
            collection.insert_one(point) #insert 

    return True

def convert_to_nested(data):
    transformed_data = {}
    for key, value in data.items():
        if '.' in key:
            main_key, sub_key = key.split('.')
            transformed_data.setdefault(main_key, {})[sub_key] = value
        else:
            transformed_data[key] = value
    return transformed_data

def prediction(time_now):
    '''
    upload forecast electricity load to database
    and return the prediciton result 

    time_now: point where to start making prediction
    time: time of first hour of 48 hours prediction
    '''
    data_1w = get_history(reference_time=time_now, collection=actual_data, weeks = 1).sort_index()
    

    #check missing data 
    data_1w = preprocess_predict(data_1w, time_now)

    #model_cat = cat_boost.CatBoost(model_file="model/cat_model.json", format='json')
    #cat_pred = model_cat.predict(data_1w)

    #model_xgb = xg_boost.XGBoost(model_file="model/xgb_model.json")
    #xgb_pred = model_xgb.predict(data_1w)

    model_lgb = lg_boost.LightGBM(model_file="./model/lgb_model.txt")
    lgb_pred = model_lgb.predict(data_1w)

    #benchmark
    n48_pred, n168_pred = [], []
    for i in range(48):
        time = time_now + timedelta(hours=i) #increment 'time'
        n48_pred.append(season_naive_model(time, lag=48)) #predict with seasoal naive (48 hours)
        n168_pred.append(season_naive_model(time, lag=168)) #predict with seasoal naive (168 hours)

    load_pred_df = []
    #print(time_now,123)
    for i in range(48): #***
        time = time_now + timedelta(hours=i) #increment 'time'
        if i < 24: #first 24 hours 
            load_pred_df.append({'time':time, 'lgb.load1': lgb_pred[i], 'n48.load1': n48_pred[i], 'n168.load1': n168_pred[i]})

            #load_pred_df.append({'time':time, 'lgb.load1':lgb_pred[i], 'xgb.load1':xgb_pred[i], 
            #                     'cat.load1':cat_pred[i], 'n48.load1': n48_pred[i], 'n168.load1': n168_pred[i]})
        else: #last 24 hours
            load_pred_df.append({'time':time, 'lgb.load2': lgb_pred[i], 'n48.load2': n48_pred[i], 'n168.load2': n168_pred[i]})

            #load_pred_df.append({'time':time, 'lgb.load2':lgb_pred[i], 'xgb.load2':xgb_pred[i], 
            #                     'cat.load2':cat_pred[i], 'n48.load2': n48_pred[i], 'n168.load2': n168_pred[i]})
        
    insert_data(load_pred_df, pred_data) #update database

    return load_pred_df #prediction result 
    pass

def preprocess_predict(data_1w, time_now):
    '''
    preprocess prediction data 
    if no missing data, return 
    elif one day of missing consecutive data, fill it with predicted data
    else more than one missing day of data raise error 
    '''
    if len(data_1w)<168:
        datetimes = data_1w.index
        #start_datetime = min(datetimes)
        #end_datetime = max(datetimes) 
        end_datetime = time_now
        start_datetime= end_datetime - timedelta(hours=167)
        expected_datetimes = [start_datetime + timedelta(hours=i) for i in range((end_datetime - start_datetime).days * 24 + 1)]
        missing_date = [dt for dt in expected_datetimes if dt not in datetimes]

        if len(data_1w)<(168-24): #more than 1 missing day of data
            if bool(missing_date):
                raise_error('missing data' + str(missing_date[0]) + 'and' +  str(missing_date[-1])) 
            else: 
                raise_error('missing data')

        else: #fix the gap
            interp_data = get_history(reference_time=missing_date[-1], collection=pred_data, excl_ref=False,
                                      hours=24, projection= {'_id':0, 'time': 1, 'load_kw': '$lgb.load1'}) #*** 
            interp_data.drop(interp_data.index[-1], inplace=True)
            if len(interp_data)<24:
                raise_error('missing data')
            data_1w = pd.concat([data_1w, interp_data]).sort_index()
    
    return data_1w

def season_naive_model(time_now, lag):
    result = get_history(time_now - timedelta(hours=lag), actual_data, excl_ref=False)
    if not (result.empty):
        result = result.to_dict('records') # 48hours naive
        result = result[0]['load_kw']
    else:
        result = None
    return result


def get_history(reference_time, collection, hours=0, days=0, weeks=0, excl_ref=True, projection = {'_id': 0}):
    '''
    return history data of set time range in pd.DataFrame
    reference time: end date is excluded
    hours: how many hours of history data to get 
    excl_ref: exclude reference time data 
    '''
    end_date = reference_time
    start_date = reference_time - timedelta(hours=hours, days=days, weeks=weeks)
    #print(one_week_ago, reference_time)

    oprt = "$lt" if excl_ref else "$lte"
    result = collection.find(
        filter={'time': {'$gte': start_date, oprt : end_date}},
        projection = projection,
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
    #models = ['lgb', 'xgb', 'cat', 'n48', 'n168']
    models = ['lgb', 'n48', 'n168']
    projection = {'_id': 0, 'time':1}
    for model in models:
        projection[model+'_load1'] =  '$' + model+ '.load1'
        projection[model+'_load2'] =  '$' + model+ '.load2'
    filter={'time': {'$gte': ytd_time, '$lt': reference_time}}
    pred_ytd = pred_data.find(filter=filter,projection= projection)
    pred_result = [doc for doc in pred_ytd]
    pred_res =pd.DataFrame(pred_result)

    if not(pred_res.empty): #prediction made yesterday
        error = pd.DataFrame([])
        error['time'] = pred_res['time']
        for col in pred_res:
            if col == 'time': continue #skip 'time' column
            model, num = col.split('_')[0] if '_' in col else col, col[-1] #string before first '_' is model name, last char is prediction order
            error[model + '.error' + num] = (pred_res[col] - df_true['load_kw']).abs() #calculate absolute error
        insert_data(error, pred_data)


def retrain(time_now):
    '''
    trigger retrain
    '''
    #get past 3 years of historical data
    data_3y = get_history(reference_time=time_now, collection=actual_data, weeks=156) 
    print(data_3y.info(), data_3y.columns)

    #model_cat = cat_boost.CatBoost(data_3y)
    #model_cat.model.save_model('./model/cat_model.json', format="json")

    model_lgb = lg_boost.LightGBM(data_3y) #train LigthGBM
    model_lgb.model.save_model('./model/lgb_model.txt') #save model

    #model_xbg = xg_boost.XGBoost(data_3y) #train XGBoost
    #model_xbg.model.save_model("./model/xbg_model.json") #save model

@app.route('/')
def raise_error(error_msg: str, code = 400):
    abort(code, error_msg)


if __name__ == '__main__':
   app.run("0.0.0.0", 888)