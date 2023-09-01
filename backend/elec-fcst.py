from flask import Flask, jsonify, send_file, request, Response
from werkzeug.utils import secure_filename
import pandas as pd
from flask_mysqldb import MySQL
#from flask_sqlalchemy import SQLAlchemy

from zipfile import ZipFile
import zipfile
from sqlalchemy import text

app = Flask(__name__)


app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'elec-fcst'
mysql = MySQL(app)

@app.route('/', methods = ['GET'])
def predict():
    '''
    get history data, prediction data or performance
    '''
    

    cursor = mysql.connection.cursor()
    query = 'SELECT time, load_kw_true FROM data WHERE time >= CURDATE() - INTERVAL 7 DAY ORDER BY time DESC;'
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
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