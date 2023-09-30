import pandas as pd
from sklearn.metrics import mean_absolute_error

class NaivePredictor:

    def _init_(self, dataframe_path):
        self.df = pd.read_csv(dataframe_path)
        self.preprocess_data()
        self.naive_mae_168 = self.calculate_naive_mae(lag=168)
        self.naive_mae_48 = self.calculate_naive_mae(lag=48)
        self.naive_mae_8760 = self.calculate_naive_mae(lag=8760)
        self.naive_7am_mae = self.calculate_7am_naive_mae()
        self.rw_drift_mae = self.calculate_rw_drift_mae()
    
    def preprocess_data(self):
        self.df = self.df.rename(columns={
            "Time": 'time', 
            "Load (kW)": "load_kw", 
            "Pressure_kpa": "pres_kpa_true",
            'Cloud Cover (%)': 'cld_pct_true',
            'Humidity (%)': 'hmd_pct_true',
            'Temperature (C)': 'temp_c_true',
            'Wind Direction (deg)': 'wd_deg_true',
            'Wind Speed (kmh)': 'ws_kmh_true'
        })
        self.df['time'] = pd.to_datetime(self.df['time'])
    
    def calculate_naive_mae(self, lag):
        df_lag = self.df.copy()
        df_lag[f'load_kw_lag{lag}'] = df_lag['load_kw'].shift(lag)
        mark_90_percent = int(len(df_lag) * 0.9)
        actual_vals = df_lag['load_kw'].dropna().values
        naive_preds = df_lag[f'load_kw_lag{lag}'].dropna().values
        return mean_absolute_error(actual_vals[mark_90_percent:], naive_preds[mark_90_percent-lag:])
    
    def calculate_7am_naive_mae(self):
        df_7am_values = self.df[self.df['time'].dt.hour == 7]
        df_7am_predictions = df_7am_values.set_index('time').resample('D').first().reindex(self.df['time'], method='ffill')
        return mean_absolute_error(self.df['load_kw'], df_7am_predictions['load_kw'])
    
    def calculate_rw_drift_mae(self):
        df_7am_values = self.df[self.df['time'].dt.hour == 7]
        drift = df_7am_values['load_kw'].diff().mean()
        df_7am_values['rw_drift_predictions'] = df_7am_values['load_kw'].shift(1) + drift
        df_rw_drift_predictions = df_7am_values.set_index('time').resample('D').first().reindex(self.df['time'], method='ffill')
        df_rw_drift_predictions['rw_drift_predictions'].fillna(method='bfill', inplace=True)
        return mean_absolute_error(self.df['load_kw'], df_rw_drift_predictions['rw_drift_predictions'])


# Usage:
predictor = NaivePredictor("./data/cleaned_actual.csv")
print("168-hour Naive Prediction MAE:", predictor.naive_mae_168)
print("48-hour Naive Prediction MAE:", predictor.naive_mae_48)
print("8760-hour (1-year) Naive Prediction MAE:", predictor.naive_mae_8760)
print("7am Naive Prediction MAE:", predictor.naive_7am_mae)
print("Random Walk with Drift Prediction MAE:", predictor.rw_drift_mae)