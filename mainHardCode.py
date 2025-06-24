# -*- coding:utf-8 -*-
'''
:Created: 2025-06-03 16:09:30
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Virtual PMS for microgrids. Define herein the load and production power time series, components of the microgrids + results type. Once the input data is read, the dispatching is performed.
'''
#---------------------
# %% Required dependencies and imports
import os
cWD = os.path.dirname(os.path.realpath(__file__))

from virtualPMS import DispatchingStrats as DS
from virtualPMS import TimeSeriesAnalysis as TSA
from virtualPMS import Battery, BatteryStock, DieselGenerator, Grid

import pandas as pd

# --------------------------------------------------------------------------------------------
# Strategy
# --------------------------------------------------------------------------------------------
# choose between the following strategies, then precise specific parameters if needed
# Load Following : 'LFE' | Cycle Charging : 'CCE' | CostStrat : 'CostStrat'
strat = 'coststrat'                                                                   # change value
# NB : CostStrat includes other parameters to define within the main script CostStrat.py

strat = strat.lower()
assert(strat in ['lfe', 'cce', 'coststrat'])

# --------------------------------------------------------------------------------------------
# INPUT time series (load demand, production and time arrays)
# --------------------------------------------------------------------------------------------
input_filename = "sinus_2025-01-01_2025-01-15.csv"
input_timeseries = os.path.join(cWD,"input",input_filename)
df_inp = pd.read_csv(input_timeseries)
date_format = df_inp["Time"][0]
df_inp = df_inp.drop(0, axis=0).reset_index(drop=True)
df_inp["Load"] = pd.to_numeric(df_inp["Load"])
df_inp["Green Prod"] = pd.to_numeric(df_inp["Green Prod"])
GridState = pd.to_numeric(df_inp["Grid State"])
df_inp["Time"] = pd.to_datetime(df_inp["Time"].to_numpy(), format=date_format)
dt = (df_inp["Time"][1] - df_inp["Time"][0]).total_seconds() / 3600 # duration of a time step in hours ; every time step must have the same lenght
num_steps = min(len(df_inp["Time"]),len(df_inp["Load"]),len(df_inp["Green Prod"]))

# --------------------------------------------------------------------------------------------
# electrical devices
# --------------------------------------------------------------------------------------------
ActiveDevices = {"Grid": False, "Batteries": False, "DieselGenerator": True}

# --- grid ---
if not ActiveDevices["Grid"]:
    GridState = [0] * len(df_inp)
GridPricesSheet = pd.read_csv(Grid.GridPricesRef)
GridScheduleSheet = pd.read_csv(Grid.GridScheduleRef)
grid_1 = Grid(GridState, GridPricesSheet, GridScheduleSheet)

# --- batteries ---
paramIn_Batt = {"capacity":1000,
                "SOC":0.5,
                "SOCmin":0.1,
                "SOCmax":0.9,
                "eta":0.8,
                "Pmax_ch":100,
                "Pmax_disch":100,
                "lifetime":500000,
                "ReplacementCost":10000,
                "MaintenanceCost":0.03}
# batteries         
battery_1 = Battery(paramIn_Batt)
battery_2 = Battery(paramIn_Batt)
battery_3 = Battery(paramIn_Batt)

BattStock = BatteryStock([battery_1, battery_2, battery_3])

if not ActiveDevices["Batteries"]:
    for batt in BattStock.battery_stock:
        batt.SOCmin, batt.SOC, batt.SOCmax = 0,0,0

# --- diesel generator ---
paramIn_DG = {"Pmax":300,
              "Pnom":250,
              "Pmin":100,
              "TankCapacity":2000,
              "FuelRate":1.0,
              "f_r_min":0.1,
              "lifetime":200000,
              "ReplacementCost":10000,
              "MaintenanceCost":0.08,
              "FuelPrice":1.5,
              "MinimumRuntime":20}
DG_1 = DieselGenerator(paramIn_DG)
DG_1.find_DG_coeffs()

if not ActiveDevices["DieselGenerator"]:
    DG_1.FuelRate, DG_1.f_r_min = 0,0
    DG_1.Pmax, DG_1.Pnom, DG_1.Pmin = 0,0,0
    DG_1.A, DG_1.B = 0,0

# --------------------------------------------------------------------------------------------
# Results parameters
# --------------------------------------------------------------------------------------------
# main_var : most important results calculated herein
# all_var  : every output variables, including debug variables
# SOCs     : SOCs of all batteries
# if True, the set of variable will be saved under the specified format
output_command = {"dataset": ["main_var","all_var","SOCs","costs","energy"],
                  ".csv"   : [False,     True,     False, True,   True],
                  ".png"   : [True,      False,    False, True,   None],
                  ".pkl"   : [True,      False,    False, False,  None],
                  "plot"   : [False,     False,    False, False,  None]}
df_output_command = pd.DataFrame(output_command)
inputIdd = input_filename.split('_')[0]

# specific parameters
# ----------------------------------------------
# forecast : [boolean] If True, future data will be used to dispatch power.
#                      If False, only current and past data will be used.
forecast = True
# ForecastPeriod : [int] will only be used when forecast == True. based on the duration of battery charging and forecast abilities, 
# it represents the future period of time the function is allowed to look at in order to anticipate dispatching, IN HOURS.
ForecastPeriod = 3 * 24

#  ONLY FOR CostStrat.py :
# ----------------------------------------------
# ChargeUsingGridCost [float] : if the cost of 1kWh purchased from the grid is less than this, it will be used to charge batteries
ChargeUsingGridCost = 0.1

#  ONLY FOR LFE_CCE.py :
# ----------------------------------------------
SOClim = 0.7 # under this SOC, batteries will be charged by the grid (when the grid is reliable).
# NB : if you don't want to charge the batteries with the grid power at all, just enter SOClim = 0.

# --------------------------------------------------------------------------------------------
# %% Simulation, time series generation
# --------------------------------------------------------------------------------------------
if strat in ["lfe","cce"]:
    dfRes, allSOCs = DS.LFE_CCE(strat,df_inp, ActiveDevices, grid_1, BattStock, DG_1, dt, SOClim, forecast, ForecastPeriod)
elif strat == "coststrat":
    dfRes, allSOCs = DS.CostStrat(df_inp, ActiveDevices, grid_1, BattStock, DG_1, dt, ChargeUsingGridCost, forecast, ForecastPeriod)
TSA.VerifTimeSeries(dfRes, ActiveDevices, BattStock, DG_1)

# --------------------------------------------------------------------------------------------
# Save files
# --------------------------------------------------------------------------------------------
DevicesIdd = f"{"G"if ActiveDevices['Grid'] else "-"}{"B"if ActiveDevices['Batteries'] else "-"}{"D"if ActiveDevices['DieselGenerator'] else "-"}"
StratIdd = "LF" if strat=="lfe" else "CC" if strat=="cce" else "CS"

# --- main ---
TSA.plot_compact(dfRes, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_MAIN"),
                   df_output_command[".csv"][0],df_output_command[".png"][0],df_output_command[".pkl"][0],df_output_command["plot"][0])

if df_output_command[".csv"][4]:
    energy_file_path = os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_TradedEnergy.csv")
    df_energysums = TSA.EnergySums(dfRes, DG_1)
    df_energysums.to_csv(energy_file_path, index=False)

# --- debug & details ---
TSA.plot_separately(dfRes, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_AllVar"),
                    df_output_command[".csv"][1],df_output_command[".png"][1],df_output_command[".pkl"][1],df_output_command["plot"][1])

allSOCs["TimeArray"] = dfRes["TimeArray"]
if ActiveDevices["Batteries"]:
    allSOCs["all_bat"] = dfRes["SOC"] # add general SOC to SOCs
TSA.plot_group(allSOCs, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_AllSOCs"), '',
               df_output_command[".csv"][2],df_output_command[".png"][2],df_output_command[".pkl"][2],df_output_command["plot"][2])

if strat == "coststrat": # costs results
    d_costs_needed = pd.DataFrame({"TimeArray":dfRes["TimeArray"]})
    d_costs_remain = pd.DataFrame({"TimeArray":dfRes["TimeArray"]})

    if ActiveDevices["Grid"]:
        d_costs_needed["GridState"] = GridState
        d_costs_needed["GridSaleCost"] = dfRes["GridSaleCost"]
        d_costs_remain["GridPurchaseCost"] = dfRes["GridPurchaseCost"]
    if ActiveDevices["Batteries"]:
        d_costs_needed["BatteryChargeCost"] = dfRes["BatteryChargeCost"]
        d_costs_remain["BatteryDischargeCost"] = dfRes["BatteryDischargeCost"]
    if ActiveDevices["DieselGenerator"]:
        d_costs_remain["DGUseCost"] = dfRes["DGUseCost"]

    d_costs_full = pd.concat([d_costs_needed,d_costs_remain.drop("TimeArray", axis = 1)], axis=1)

    TSA.plot_group(d_costs_needed, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_CostsEnergNeeded"), '',
                False,df_output_command[".png"][3],df_output_command[".pkl"][3],df_output_command["plot"][3])
    TSA.plot_group(d_costs_remain, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_CostsEnergRem"), '',
                False,df_output_command[".png"][3],df_output_command[".pkl"][3],df_output_command["plot"][3])
    TSA.plot_group(d_costs_full, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_CostsEnergAll"),
                df_output_command['.csv'][3])
# %%
