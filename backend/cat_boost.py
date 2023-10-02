import pandas as pd
import catboost as ctb
from sklearn.metrics import mean_absolute_error
from tqdm import tqdm
from datetime import datetime, timedelta

class CatBoost():

    param_grid = [
        {
            'depth': depth,
            'learning_rate': lr,
            'subsample': subsample,
            'colsample_bylevel': colsample_bylevel,
            'loss_function': 'MAE',
            'eval_metric': 'MAE',
            'verbose': False
        }
        for depth in range(2, 11, 2)
        for lr in [i / 10 for i in range(1, 4)]
        for subsample in [i / 10 for i in range(5, 11)]
        for colsample_bylevel in [i / 10 for i in range(5, 11)]
    ]

    def __init__(self, history_data: pd.DataFrame =False, model_file="", format = ""):
        if model_file:
            self.model = ctb.CatBoostRegressor().load_model(fname = model_file, format=format)
        if history_data:
            self.train_data, self.val_data = self.preprocess(history_data)
            self.model, self.params, self.mae = self.train_best_model(self.train_data, self.val_data)



    def preprocess(self, history_data):
        train_val_data = pd.DataFrame([])
        for i in range(24, 169):
            train_val_data['load_kw_lag' + str(i)] = history_data['load_kw'].shift(i)
        train_val_data['load_kw'] = history_data['load_kw']

        train_val_data = train_val_data.dropna(axis=0)
        n = len(train_val_data)
        return train_val_data[:int(n*0.9)], train_val_data[int(n*0.9):]
    
    def predict(self, history_data, cat_pred = None):
        if cat_pred == None:
            cat_pred = []
        X_pred = pd.DataFrame([])
        for i in range(145): #shift(0) == lag24, shift(1) == lag25, ... , shift(144) == lag168
            #shift load 
            X_pred = pd.concat([X_pred, history_data['load_kw'].shift(i).rename('load_kw_lag' + str(i+24))], axis=1)
        
        #X_pred['load_kw'] = history_data['load_kw']
        X_pred = X_pred.dropna(axis=0)
        X_pred.index = X_pred.index + pd.Timedelta(hours=24) #shift index time
        
        
        for i in range(len(X_pred)):
            #time = time_now + timedelta(hours=i) #increment 'time'
            X = X_pred.iloc[i,:] #1 hour of predictors
            cat_pred.append(float(self.model.predict(X)))
            
        if len(cat_pred) <=24:
            new_df = pd.DataFrame({'load_kw':cat_pred}, index=pd.date_range(history_data.index[-1] + pd.Timedelta(hours=1), periods=len(cat_pred), freq='H'))
            history_data = pd.concat([history_data, new_df])
            return self.predict(history_data[24:], cat_pred)
        else:
            return cat_pred

    def train_best_model(self, train_data, val_data):
        best_model = None
        best_params = None
        best_mae = float('inf')

        X_train = train_data.loc[:, ~train_data.columns.isin(['load_kw'])]
        y_train = train_data['load_kw']
        X_val = val_data.loc[:, ~val_data.columns.isin(['load_kw'])]
        y_val = val_data['load_kw']

        train_pool = ctb.Pool(data=X_train, label=y_train)
        val_pool = ctb.Pool(data=X_val, label=y_val)

        print('training model: CatBoost')

        for params in tqdm(self.param_grid):
            model = ctb.CatBoostRegressor(**params)
            model.fit(train_pool, eval_set=val_pool, early_stopping_rounds=10)
            val_preds = model.predict(val_pool)
            mae = mean_absolute_error(y_val, val_preds)

            if mae < best_mae:
                best_model = model
                best_params = params
                best_mae = mae

        return best_model, best_params, best_mae
