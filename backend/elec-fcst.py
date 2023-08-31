from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
app = Flask(__name__)

@app.route('/', methods = ['GET'])
def predict():
    '''
    get history data, prediction data or performance
    '''
    return ''

@app.route('/upload', methods = ['POST'])
def upload():
    '''
    data preprocessing, data formatting, upload data to database 
    question: is it zip file or csv file
    '''
    #if file is zipped, unzip
    df = pd.read_csv(request.files.get('file'))
    print(df)
    #handle date format 

    #handle missing data e.g. missing time

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