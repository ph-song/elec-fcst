import pandas as pd
from sklearn.metrics import mean_absolute_error

# Load the data
df_true = pd.read_csv("./data/cleaned_actual.csv")

# Rename columns as per your existing script
df_true = df_true.rename(columns={"Time": 'time', 
                                  "Load (kW)": "load_kw", 
                                  "Pressure_kpa": "pres_kpa_true",
                                  'Cloud Cover (%)': 'cld_pct_true',
                                  'Humidity (%)': 'hmd_pct_true',
                                  'Temperature (C)': 'temp_c_true',
                                  'Wind Direction (deg)': 'wd_deg_true',
                                  'Wind Speed (kmh)': 'ws_kmh_true'})

# Convert 'time' column to datetime format
df_true['time'] = pd.to_datetime(df_true['time'])

# Extract 7 am values for each day
df_7am_values = df_true[df_true['time'].dt.hour == 7]

# Use the 7 am values to make predictions for the entire day
df_7am_predictions = df_7am_values.set_index('time').resample('D').first().reindex(df_true['time'], method='ffill')

# Calculate the Mean Absolute Error (MAE) between the predictions and the actual values
naive_7am_mae = mean_absolute_error(df_true['load_kw'], df_7am_predictions['load_kw'])
naive_7am_mae

# Calculate the drift (mean change from 7 am of one day to 7 am of the next day)
drift = df_7am_values['load_kw'].diff().mean()

# Create predictions using the Random Walk with Drift model
df_7am_values['rw_drift_predictions'] = df_7am_values['load_kw'].shift(1) + drift
df_rw_drift_predictions = df_7am_values.set_index('time').resample('D').first().reindex(df_true['time'], method='ffill')

# Handle NaN values in the predictions
df_rw_drift_predictions['rw_drift_predictions'].fillna(method='bfill', inplace=True)

# Recalculate the Mean Absolute Error (MAE) for the Random Walk with Drift model
rw_drift_mae = mean_absolute_error(df_true['load_kw'], df_rw_drift_predictions['rw_drift_predictions'])
rw_drift_mae