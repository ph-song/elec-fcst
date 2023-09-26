import pandas as pd
import catboost as ctb
from sklearn.metrics import mean_absolute_error
from tqdm import tqdm

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

    def __init__(self, history_data: pd.DataFrame):
        self.train_data, self.val_data = self.preprocess(history_data)
        self.model, self.params, self.mae = self.train_best_model(self.train_data, self.val_data)

    def preprocess(self, history_data):
        train_val_data = pd.DataFrame([])
        for col in history_data.columns:
            if col != 'time':
                train_val_data[str(col)+'_lag168'] = history_data[str(col)].shift(168)
        train_val_data['load_kw'] = history_data['load_kw']

        train_val_data = train_val_data.dropna(axis=0)
        n = len(train_val_data)
        return train_val_data[:int(n*0.9)], train_val_data[int(n*0.9):]

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
