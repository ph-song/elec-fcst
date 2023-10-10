import pandas as pd
from lightgbm import Dataset, train, early_stopping
from sklearn.metrics import mean_absolute_error
import numpy as np
import sklearn
from tqdm import tqdm
import lightgbm as lgb
import pandas as pd
from datetime import datetime, timedelta

class LightGBM():
    param_grid = [
        {'max_depth': depth, 'num_leaves': num_leaves, 'learning_rate': lr, 'subsample': subsample, 
        'colsample_bytree': colsample_bytree, 'objective': 'regression', 'metric': 'mae', 'verbose':-1}
        for depth in range(2, 11, 2)
        for num_leaves in [7, 15, 31]
        for lr in [i / 10 for i in range(1, 4)]
        for subsample in [i / 10 for i in range(5, 11)]
        for colsample_bytree in [i / 10 for i in range(5, 11)]
    ]

    def __init__(self, history_data: pd.DataFrame = False, model_file=""):
        if model_file:
            self.model = lgb.Booster(model_file=model_file)
        else:
            self.train_data, self.val_data = self.preprocess(history_data)
            self.model, self.params, self.mae = self.train_best_model(self.train_data, self.val_data, self.param_grid)

    
    def preprocess(self, history_data, lgb_pred = None):
        if lgb_pred == None:
            lgb_pred = []
            
        train_val_data = pd.DataFrame([])
        for i in range(24, 169, 24):
            key = 'load_kw_lag' + str(i)
            shift_col =  history_data['load_kw'].shift(i).rename(key)
            train_val_data = pd.concat([train_val_data, shift_col], axis=1)
            #train_val_data[key] = history_data['load_kw'].shift(i)

        train_val_data = pd.concat([train_val_data, history_data['load_kw']], axis=1)
        #train_val_data['load_kw'] = history_data['load_kw']

        #train_val_data = train_val_data.drop('time_lag168', axis=1) #drop time_lag168
        #train_val_data.index = history_data.index #retrieve 'time' as index

        train_val_data= train_val_data.dropna(axis=0) #drop rows with NA values (due to shift)


        n = len(train_val_data)
        return train_val_data[:int(n*0.9)], train_val_data[int(n*0.9):]

    def predict(self, history_data, lgb_pred=None):
        #print(history_data.index, 123123)
        if lgb_pred == None:
            lgb_pred = []
        X_pred = pd.DataFrame([])
        for i in range(0, 145, 24): #lag24,lag48, ..., lag168
            #shift load 
            X_pred = pd.concat([X_pred, history_data['load_kw'].shift(i).rename('load_kw_lag' + str(i+24))], axis=1)
    
        #X_pred['load_kw'] = history_data['load_kw']
        X_pred = X_pred.dropna(axis=0)
        X_pred.index = X_pred.index + pd.Timedelta(hours=24) #shift index time
        
        for i in range(len(X_pred)):
            #time = time_now + timedelta(hours=i) #increment 'time'
            X = X_pred.iloc[i,:] #1 hour of predictors
            lgb_pred.append(float(self.model.predict(X)))

        if len(lgb_pred) <=24:
            new_df = pd.DataFrame({'load_kw':lgb_pred}, index=pd.date_range(history_data.index[-1] + pd.Timedelta(hours=1), periods=len(lgb_pred), freq='H'))
            history_data = pd.concat([history_data, new_df])
            return self.predict(history_data[24:], lgb_pred=lgb_pred)
        
        else:
            return lgb_pred
    
    def train_best_model(self, train_data, val_data, param_grid):
        """
        This function trains a LightGBM model using a grid search over the parameter grid 
        and returns the model with the smallest mean absolute error (MAE) on the validation data.
        
        Args:
        train_data (pd.DataFrame): The training data.
        val_data (pd.DataFrame): The validation data.
        param_grid (dict): The grid of parameters to search over.
        
        Returns:
        best_model (lgb.Booster): The model with the smallest MAE on the validation data.
        best_params (dict): The parameters of the best model.
        best_mae (float): The MAE of the best model on the validation data.
        """
        best_model = None
        best_params = None
        best_mae = float('inf')
        
        # Extract features and labelsx
        X_train = train_data.loc[:, ~train_data.columns.isin(['load_kw'])]
        y_train = train_data['load_kw']
        X_val = val_data.loc[:, ~val_data.columns.isin(['load_kw'])]
        y_val = val_data['load_kw']
        #print(X_train.info(), y_train.info())
        
        # Create LightGBM datasets
        dtrain = lgb.Dataset(X_train, label=y_train)
        dval = lgb.Dataset(X_val, label=y_val)
        
        print('training model: Light GBM')

        # Iterate over all combinations of parameters
        for params in tqdm(param_grid):
            model = lgb.train(params, dtrain, num_boost_round=100, 
                            callbacks = [early_stopping(stopping_rounds = 10, verbose=False)],
                            valid_sets=[dval])
            
            # Predict on validation set and calculate MAE
            val_preds = model.predict(X_val)
            mae = mean_absolute_error(y_val, val_preds)
            
            # Update best model if current model has lower MAE
            if mae < best_mae:
                best_model = model
                best_params = params
                best_mae = mae


        return best_model, best_params, best_mae

