from flask import Flask, jsonify, send_file, request, Response
from werkzeug.utils import secure_filename
import pandas as pd
from zipfile import ZipFile
from pymongo import MongoClient
import pymongo
from pprint import pprint

app = Flask(__name__)

client = MongoClient()
client = pymongo.MongoClient("mongodb://localhost:27017/")

db = client["elec-fcst"]
data = db["data"] 

@app.route('/', methods = ['GET'])
def predict():
    '''
    get history data, prediction data or performance
    '''
    result_7days = data.find(filter={},
                             projection={'_id': 0},
                             sort=list({'timestamp': -1}.items()),
                             limit=7)
    result = []
    for res in result_7days:
        result.append(res)
    
    response = jsonify({'data': result}) 
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/upload', methods = ['POST'])
def upload():
    '''
    data preprocessing, data formatting, upload data to database 
    question: is it zip file or csv file
    '''
    #unzip file 
    file = request.files['zip_file']  
    dfs = extract(file) 
    df, df_true, df_pred = process_data(dfs) 


    
    #update database
    return str(df) + str(df_true) + str(df_pred)

    
    
    #upload to database

    #fetch data (2 years)

    #predict result ()
  
    #evaluate 

    #send predicted data to database


    #trigger retrainning LSTM, 

    #1. build XGBoost 2. integrate model and FLask

    return "hello"

def extract(file):
    '''
    take in file opject
    return list of dataframes
    '''
    zip_file = ZipFile(file.stream._file)
    dfs = [] #set of data frames in zipped file
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
    #are columns name gonna be consistent?
    df, df_true, df_pred = [], [], [] 
    
    for i in range(len(dfs)):
        dfs[i]['time']= pd.to_datetime(dfs[i]['time']) #format date datatype

        #format column name
        if dfs[i].shape[1]==6:
            dfs[i] = dfs[i].rename(columns={"Time": 'time', "Load (kW)": "load_kw_pred", 
                                    "Pressure_kpa": "pres_kpa_pred", 'Cloud Cover (%)': 'cld_pct_pred',
                                    'Humidity (%)': 'hmd_pct_pred', 'Temperature (C)': 'temp_c_pred',
                                    'Wind Direction (deg)': 'wd_deg_pred', 'Wind Speed (kmh)':'ws_kmh_true'})
            df_pred = dfs[i]

        elif dfs[i].shape[1]==8:
            dfs[i] = dfs[i].rename(columns={"Time": 'time', "Load (kW)": "load_kw_true", 
                                    "Pressure_kpa": "pres_kpa_true",'Cloud Cover (%)': 'cld_pct_true',
                                    'Humidity (%)': 'hmd_pct_true','Temperature (C)': 'temp_c_true',
                                    'Wind Direction (deg)': 'wd_deg_true','Wind Speed (kmh)':'ws_kmh_true'})
            df_true = dfs[i]

        elif dfs[i].shape[1] ==13:
            df = dfs[i]

    return df, df_true, df_pred

def insert_db():
    '''
    df= dfs[i]
    query = 'INSERT INTO data '
    for key in df.columns:
        query = query + key + ' '

        #cur = mysql.connection.cursor()
        #cur.execute()
        #mysql.connection.commit()

        #cur = mysql.connection.cursor()
        #cur.execute()
        #mysql.connection.commit()
    '''

def predict():
    '''
    forecast electricity load
    '''
    pass

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