import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
from tqdm import tqdm

class XGBoost():
    param_grid = [
        {'max_depth': depth, 'eta': eta, 'subsample': subsample, 'colsample_bytree': colsample_bytree,
        'objective': 'reg:absoluteerror', 'eval_metric': 'mae'}
        for depth in range(2, 11, 2)
        for eta in [i / 10 for i in range(1, 4)]
        for subsample in [i / 10 for i in range(5, 11)]
        for colsample_bytree in [i / 10 for i in range(5, 11)]
    ]

    def __init__(self, history_data):
        train_data, val_data =  self.preprocess(history_data)
        self.model, self.params, self.mae = self.train_best_model(train_data, val_data, XGBoost.param_grid)
    
    def preprocess(self, history_data):
        train_val_data = pd.DataFrame([])
        for col in history_data.columns:
            train_val_data[str(col)+'_lag168'] = history_data[str(col)].shift(168) #create lag
        
        train_val_data['load_kw'] = history_data['load_kw'] #retrieve label, 'load_kw'

        train_val_data = train_val_data.drop('time_lag168', axis=1) #drop time_lag168
        train_val_data.index = history_data['time'] #retrieve 'time' as index

        train_val_data= train_val_data.dropna(axis=0) #drop rows with NA values (due to shift)
        
        n = len(train_val_data)
        return train_val_data[:int(n*0.9)], train_val_data[int(n*0.9):]

    def train_best_model(self, train_data, val_data, param_grid):
        """
        This function trains an XGBoost model using a grid search over the parameter grid 
        and returns the model with the smallest mean absolute error (MAE) on the validation data.
        
        Args:
        train_data (pd.DataFrame): The training data.
        val_data (pd.DataFrame): The validation data.
        param_grid (dict): The grid of parameters to search over.
        
        Returns:
        best_model (xgb.Booster): The model with the smallest MAE on the validation data.
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
        print(X_train.info(), y_train.info())
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        
        print('training model: XGBoost')

        # Iterate over all combinations of parameters
        for params in tqdm(param_grid):
            model = xgb.train(params, dtrain, 
                            num_boost_round=100, 
                            evals=[(dtrain, 'train'), (dval, 'val')], 
                            early_stopping_rounds=10, verbose_eval=False)

            # Predict on validation set and calculate MAE
            val_preds = model.predict(dval)
            mae = mean_absolute_error(y_val, val_preds)

            # Update best model if current model has lower MAE
            if mae < best_mae:
                best_model = model
                best_params = params
                best_mae = mae

        return best_model, best_params, best_mae

