from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from zipfile import ZipFile
from werkzeug.utils import secure_filename

from datetime import datetime, timedelta

from pymongo import MongoClient
import pymongo
from pprint import pprint

import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

client = MongoClient()
client = pymongo.MongoClient("mongodb://localhost:27017/")

db = client["elec-fcst"]
pred_data = db["predict"]  #forecast data collection
actual_data = db["actual"] #actual data collection

@app.route('/', methods = ['GET'])
def predict():
    '''
    get history data, prediction data or performance
    '''

    #get 7 days of data 
    result_7days = pred_data.find(filter={},
                                  projection={'_id': 0},
                                  sort=list({'time': -1}.items()),
                                  limit=7)
    result = []
    
    for res in result_7days:
        result.append(res)
    response = jsonify({'data': result}) 
    return response


@app.route('/upload', methods = ['POST'])
def upload():
    '''
    data preprocessing, data formatting, upload data to database 
    question: is it zip file or csv file
    '''
    print(request.files)
    file = request.files['zip_file']  
    dfs = extract(file) #extract data from zipped file
    df_true, df_pred = process_data(dfs) #process dataframes
    get_history(reference_time=df_pred['time'][0], hours = 168)

    #predict result ()
  
    #evaluate 

    #send predicted data to database
    return 'test'

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

def insert_data(df, collection):
    '''
    update document if exist
    else insert
    '''
    data = df.to_dict('records')
    for point in data:
        #if manage to find one, update, else insert 
        print(point)
        is_exist = collection.find_one_and_replace(filter = {'time':point["time"]}, 
                          replacement = point) #replace if exist
        if not bool(is_exist):
            collection.insert_one(point) #insert 

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
                                "Pressure_kpa": "pressure_kpa", 'Cloud Cover (%)': 'cloud__cover_pct',
                                'Humidity (%)': 'humidity_pct', 'Temperature (C)': 'temperature_c',
                                'Wind Direction (deg)': 'wind_direction_deg', 'Wind Speed (kmh)':'wind_speed_kmh'})
        dfs[i]['time']= pd.to_datetime(dfs[i]['time']) #format date datatype
       

        if dfs[i].shape[1]==6: #forecast data has 6 columns
            df_pred = dfs[i] #store data in a variable 
            insert_data(df = df_pred, collection=pred_data)  #insert database

        elif dfs[i].shape[1]==8: #actual data has 6 columns
            df_true = dfs[i] #store data in a variable 
            insert_data(df = df_true, collection=actual_data) #insert database
    
    return df_true, df_pred

def predict(time):
    '''
    forecast electricity load
    time: time of first hour of 48 hours prediction
    '''
    
    #get pass 168 hours of the data 


    #make prediction 
    #evaluate 
    #upload predicted and evaluation
    pass

def get_history(reference_time, hours):
    '''
    get history data 
    time: reference time 
    hours: how many hours of history data to get 
    '''
    one_week_ago = reference_time - timedelta(hours=hours)
    print(one_week_ago, reference_time)
    result = client['elec-fcst']['actual'].find(
        filter={'time': {'$gte': one_week_ago, '$lte': reference_time}},
        projection = {'_id': 0},
        sort=list({'time': -1}.items())
        ) #past seven days of data
    
    history_data = []
    for doc in result:
        history_data.append(doc)
    print(len(history_data), 123)
    return history_data


def evaluate():
    '''
    evaluate electricity load
    '''
    pass

def retrain():
    '''
    trigger retrain
    '''
    pass

if __name__ == '__main__':
   app.run("0.0.0.0", 888)