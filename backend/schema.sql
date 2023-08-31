CREATE TABLE data (
    time DATETIME PRIMARY KEY,
    load_kw_true FLOAT,
    pres_kpa_true FLOAT,
    cld_cvr_true FLOAT,
    hmd_true FLOAT,
    temp_true FLOAT,
    wd_deg_true FLOAT,
    ws_kmh_true FLOAT,
    temp_c_pred FLOAT,
    pres_kpa_pred FLOAT,
    cld_pct_pred FLOAT,
    wd_deg_pred FLOAT,
    ws_kmh_pred FLOAT
);

CREATE TABLE lstm (
    time DATETIME,
    load_kw_pred FLOAT,
    FOREIGN KEY (time) REFERENCES data(time)
);

CREATE TABLE tbats (
    time DATETIME,
    load_kw_pred FLOAT,
    FOREIGN KEY (time) REFERENCES data(time)
);

CREATE TABLE prophet (
    time DATETIME,
    load_kw_pred FLOAT,
    FOREIGN KEY (time) REFERENCES data(time)
);
