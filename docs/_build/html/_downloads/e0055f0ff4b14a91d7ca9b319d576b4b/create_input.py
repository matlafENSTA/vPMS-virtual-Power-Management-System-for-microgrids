# -*- coding:utf-8 -*-
'''
:Created: 2025-05-26 15:27:09
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Easily creates an input data file for main.py from known datasets
'''
#---------------------
# %%
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

cWD = os.path.dirname(os.path.realpath(__file__))
# Choose your input data set among the following :
# constant time series : 'constant' | sinus function : 'sinus' | French industrial site : 'indus'
inp_data = 'indus'                                                              # change value

assert(inp_data in ['constant','sinus', 'indus'])

# --------------------------------------------------------------------------------------------
# Constant time series
# --------------------------------------------------------------------------------------------
# constant arrays to check details
if inp_data == 'constant':
    dt = 0.25 # sampling period in hours
    start_date = datetime(2025, 1, 1)                                           # change value
    # lenght of the period you want to study, in days :
    period = 15                                                                 # change value
    num_steps = int((period * 24) / dt)
    TimeArray = np.array([start_date + timedelta(hours=i * dt) for i in range(num_steps)])
    end_date = TimeArray[-1]
    P_green = np.array([100] * num_steps)     # non controlled power supply : solar panels, wind turbines... 
    P_L = np.array([150] * num_steps)         # load demand

# --------------------------------------------------------------------------------------------
# Wavy (sinus) time series
# --------------------------------------------------------------------------------------------
# sinusoidal arrays to check details
if inp_data == 'sinus':
    dt = 0.25 # sampling period in hours
    start_date = datetime(2025, 1, 1)                                           # change value
    # lenght of the period you want to study, in days :
    period = 15                                                                 # change value
    num_steps = int((period * 24) / dt)
    TimeArray = np.array([start_date + timedelta(hours=i * dt) for i in range(num_steps)])
    end_date = TimeArray[-1]
    x_axis = np.array([i / num_steps * 4 * np.pi for i in range(num_steps)])
    P_green = 10 * np.sin(x_axis) + 100     # non controlled power supply : solar panels, wind turbines... 
    P_L = 20 * np.cos(x_axis) + 100         # load demand

# --------------------------------------------------------------------------------------------
# Industrial data
# --------------------------------------------------------------------------------------------
# data comes from french industries forecasting PV and Load : https://zenodo.org/records/5510400#.YUizGls69hE
# !! check input before running, sometimes data is missing and dates not in the good order
elif inp_data == 'indus':
    df = pd.read_csv(os.path.join(cWD,'input','indus_22.csv'), sep=None, engine='python')           # change value
    TimeArray = pd.to_datetime(df['timestamp'].to_numpy())
    TimeArray = TimeArray.tz_localize(None)
    dt = (TimeArray[1] - TimeArray[0]).total_seconds() / 3600 # duration of a time step in hours ; every time step should be the same lenght
    P_L = df['actual_consumption'].to_numpy()
    P_green = df['actual_pv'].to_numpy()

    # you can select the period you want to study giving the date bounds, but make sure that there is no missing data in between !
    start_date = pd.to_datetime('2016-01-01 00:00:00')                           # change value
    end_date = pd.to_datetime('2016-03-01 00:00:00')                             # change value
    start_idx = TimeArray.get_loc(start_date)
    end_idx = TimeArray.get_loc(end_date)
    
    TimeArray = TimeArray[start_idx : end_idx]
    P_L = P_L[start_idx : end_idx]
    P_green = P_green[start_idx : end_idx]

    num_steps = min(len(TimeArray),len(P_L),len(P_green))
    # plt.plot(TimeArray) # to check if some dates are missing
    # plt.show()

# grid reliable (=1) or not (=0) at any given time step
GridState = np.array([1] * (num_steps - num_steps//2) + [0] * (num_steps//2), dtype=np.int64) # change value

assert(len(TimeArray) == len(P_L) == len(P_green) == len(GridState))
print("dt =",dt,"h")
# print(np.shape(TimeArray),TimeArray[:10],"\n",np.shape(P_L),P_L[:10],"\n",np.shape(P_green),P_green[:10])

# prepare the time array
TimeFormat = "%Y-%m-%d %H:%M:%S" # do not change
TimeArray = np.array([date_i.strftime(TimeFormat) for date_i in TimeArray])

# add unit line
TimeArray = np.concatenate(([TimeFormat], TimeArray))
P_L = np.concatenate((["kW"], P_L))
P_green = np.concatenate((["kW"], P_green))
GridState = np.concatenate((["binary (optional)"], GridState))

# csv generation
dict_TS = {"Time":TimeArray,"Load":P_L, "Green Prod":P_green, "Grid State": GridState}
df_TS = pd.DataFrame(dict_TS)
df_TS.set_index("Time")
filepath = os.path.join(cWD,"input",f"{inp_data}_{str(start_date).split(" ")[0]}_{str(end_date).split(" ")[0]}.csv")
df_TS.to_csv(filepath, index=False)
print("file saved at ",filepath)
# %%
