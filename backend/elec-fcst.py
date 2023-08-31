from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
from flask_mysqldb import MySQL
from zipfile import ZipFile
import zipfile

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
    query = 'SELECT time, load_kw_true FROM data \
        WHERE time >= CURDATE() - INTERVAL 7 DAY \
            ORDER BY time DESC;'
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()

    return jsonify(result)


@app.route('/upload', methods = ['POST'])
def upload():
    '''
    data preprocessing, data formatting, upload data to database 
    question: is it zip file or csv file
    '''
    #if file is zipped, unzip
    file = request.files['zip_file']  
    zip_file = ZipFile(file.stream._file)
    dfs = [] #set of data frames in zipped file
    for text_file in zip_file.infolist():
        if text_file.filename.endswith('.csv'):
            print(text_file)
            dfs.append(pd.read_csv(zip_file.open(text_file.filename)))

    df, df_true, df_pred = [], [], [] 

    print(dfs)
    for i in range(len(dfs)):
        #change column name
        dfs[i] = dfs[i].rename(columns={"Time": 'time', 
                                "Load (kW)": "load_kw_true", 
                                "Pressure_kpa": "pres_kpa_true",
                                'Cloud Cover (%)': 'cld_pct_true',
                                'Humidity (%)': 'hmd_pct_true',
                                'Temperature (C)': 'temp_c_true',
                                'Wind Direction (deg)': 'wd_deg_true',
                                'Wind Speed (kmh)':'ws_kmh_true'})
        print(dfs[i])
        dfs[i]['time']= pd.to_datetime(dfs[i]['time'])

        #dfs[i].to_sql('data', mysql.connection, if_exists='append', index=False)
        
        '''
        if dfs[i].shape[1]==6:
            df_pred = dfs[i]
            #upload to db
        elif dfs[i].shape[1]==8:
            df_true = dfs[i]
            #upload to db
        elif dfs[i].shape[1] ==13:
            df = dfs[i]
            #upload to db
        '''

     #handle date format
        
    #handle missing data
    
    #update database
    #print(df)
    return str(df) + str(df_true) + str(df_pred)

    
    
    #upload to database

    #predict model 

    #evaluate 

    #trigger retrainning 

    return "hello"

def process_data():
    '''
    format date format & handle missing data
    '''
    #are columns name gonna be consistent?
    pass

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