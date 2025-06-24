# -*- coding:utf-8 -*-
'''
:Created: 2025-06-03 16:09:30
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Virtual PMS for microgrids. This script reads inpParam.xlsx, where are defined the load and production power time series, components of the microgrids + results type. Once the input data is read, the dispatching is performed herein.
'''
#---------------------
# %% Required dependencies and imports
import os
import sys

from virtualPMS import inpReading as inpR
from virtualPMS import DispatchingStrats as DS
from virtualPMS import TimeSeriesAnalysis as TSA
from virtualPMS import Battery, BatteryStock, DieselGenerator, Grid

import pandas as pd

# --------------------------------------------------------------------------------------------
# Read input//inpParam.xlsx
# --------------------------------------------------------------------------------------------
# --- locate entry file ---
if len(sys.argv)==2:
    inputName = sys.argv[1] # this way you can save your inputs easily without changing their name for execution.
else:
    inputName = 'inpParam.xlsx'
cWD = os.path.dirname(os.path.realpath(__file__))
ExcelPath = os.path.join(cWD,'input',inputName)
print("Reading", ExcelPath)

# --- Download all sheets of the entry file ---
mainSheetRaw,TimeSeriesSheetRaw,GridPricesSheetRaw,GridScheduleSheetRaw,BattSheetRaw,DieselSheetRaw,outFSheetRaw=inpR.openxlsx(ExcelPath)
# Verify and adapt the format
# print(mainSheetRaw.shape,TimeSeriesSheetRaw.shape,GridPricesSheetRaw.shape,GridScheduleSheetRaw.shape,BattSheetRaw.shape,DieselSheetRaw.shape,outFSheetRaw.shape)
mainSheet = inpR.VerifmainSheet(mainSheetRaw)
TimeSeriesSheet = inpR.VerifTimeSeriesSheet(TimeSeriesSheetRaw)
GridPricesSheet = inpR.VerifGridPricesSheet(GridPricesSheetRaw)
GridScheduleSheet = inpR.VerifGridScheduleSheet(GridScheduleSheetRaw)
BattSheet = inpR.VerifBattSheet(BattSheetRaw)
DieselSheet = inpR.VerifDieselSheet(DieselSheetRaw)
outFSheet = inpR.VerifoutFSheet(outFSheetRaw)
# print(mainSheet.shape,TimeSeriesSheet.shape,GridPricesSheet.shape,GridScheduleSheet.shape,BattSheet.shape,DieselSheet.shape,outFSheet.shape)

# --------------------------------------------------------------------------------------------
# %% Strategy
# --------------------------------------------------------------------------------------------
# choose between the following strategies, then precise specific parameters if needed
# Load Following : 'LFE' | Cycle Charging : 'CCE' | CostStrat : 'CostStrat'                                                                   # change value
# NB : CostStrat includes other parameters to define within the main script CostStrat.py
strat = mainSheet["strategy"].lower()
assert(strat in ['lfe', 'cce', 'coststrat'])

# --------------------------------------------------------------------------------------------
# INPUT time series (load demand, production and time arrays)
# --------------------------------------------------------------------------------------------
dt = (TimeSeriesSheet["Time"][1] - TimeSeriesSheet["Time"][0]).total_seconds() / 3600 # duration of a time step in hours ; every time step must have the same lenght
num_steps = min(len(TimeSeriesSheet["Time"]),len(TimeSeriesSheet["Load"]),len(TimeSeriesSheet["Green Prod"]))

# --------------------------------------------------------------------------------------------
# Electrical Components
# --------------------------------------------------------------------------------------------
ActiveDevices = {"Grid": mainSheet["Grid"], 
                 "Batteries": mainSheet["Batteries"],
                 "DieselGenerator": mainSheet["DieselGenerator"]}

# --- grid ---
if ActiveDevices["Grid"]:
    GridState = TimeSeriesSheet["Grid State"].to_numpy()
else: # grid disconnected
    GridState = [0] * len(TimeSeriesSheet)
grid_1 = Grid(GridState, GridPricesSheet, GridScheduleSheet)

# --- batteries ---
BattList = []
if ActiveDevices["Batteries"]:
    for batt in BattSheet.keys():
        BattDict = BattSheet[batt].to_dict()
        BattList.append(Battery(BattDict))
else: # batteries disconnected
    BattList = [Battery({
                        "capacity":1,
                        "SOC":0,
                        "SOCmin":0,
                        "SOCmax":0,
                        "eta":0,
                        "Pmax_ch":0,
                        "Pmax_disch":0,
                        "lifetime":1,
                        "ReplacementCost":0,
                        "MaintenanceCost":0
                        })]
BattStock = BatteryStock(BattList)

# --- diesel generator ---
if ActiveDevices["DieselGenerator"]:
    DieselDict = DieselSheet.to_dict()
else: # DG disconnected
    DieselDict = {
                  "Pmax":1,
                  "Pnom":1,
                  "Pmin":0,
                  "TankCapacity":1,
                  "FuelRate":0,
                  "f_r_min":0,
                  "lifetime":0,
                  "ReplacementCost":0,
                  "MaintenanceCost":0,
                  "FuelPrice":0,
                  "MinimumRuntime":0
                  }
DG_1 = DieselGenerator(DieselDict)
DG_1.find_DG_coeffs()

# --------------------------------------------------------------------------------------------
# Results Parameters
# --------------------------------------------------------------------------------------------

# specific parameters
# ----------------------------------------------
# forecast : [boolean] If True, future data will be used to dispatch power.
#                      If False, only current and past data will be used.
forecast = mainSheet["forecast"]
# ForecastPeriod : [int] will only be used when forecast == True. based on the duration of battery charging and forecast abilities, 
# it represents the future period of time the function is allowed to look at in order to anticipate dispatching, IN HOURS.
try:
    ForecastPeriod = mainSheet["forecast_charac_period"]
except: # default to 3 days
    ForecastPeriod = 24 * 3

#  ONLY FOR CostStrat.py :
# ----------------------------------------------
# ChargeUsingGridCost [float] : if the cost of 1kWh purchased from the grid is less than this, it will be used to charge batteries
try:
    ChargeUsingGridCost = mainSheet["ChargeUsingGridCost"]
except: # default to minimum grid price
    ChargeUsingGridCost = GridPricesSheet["Buying price (euros/kWh)"][1]

#  ONLY FOR LFE_CCE.py :
# ----------------------------------------------
# under this SOC, batteries will be charged by the grid (when the grid is reliable).
# NB : if you don't want to charge the batteries with the grid power at all, just enter SOClim = 0.
try:
    SOClim = mainSheet["SOClim"]
except: # by default, batteries are not charged by the grid
    SOClim = 0

# --------------------------------------------------------------------------------------------
# %% Simulation, time series generation
# --------------------------------------------------------------------------------------------
if strat in ["lfe","cce"]:
    dfRes, allSOCs = DS.LFE_CCE(strat,TimeSeriesSheet, ActiveDevices, grid_1, BattStock, DG_1, dt, SOClim, forecast, ForecastPeriod)
elif strat == "coststrat":
    dfRes, allSOCs = DS.CostStrat(TimeSeriesSheet, ActiveDevices, grid_1, BattStock, DG_1, dt, ChargeUsingGridCost, forecast, ForecastPeriod)
TSA.VerifTimeSeries(dfRes, ActiveDevices, BattStock, DG_1)

# --------------------------------------------------------------------------------------------
# Save files
# --------------------------------------------------------------------------------------------
inputIdd = mainSheet["inputID"]
DevicesIdd = f"{"G"if ActiveDevices['Grid'] else "-"}{"B"if ActiveDevices['Batteries'] else "-"}{"D"if ActiveDevices['DieselGenerator'] else "-"}"
StratIdd = "LF" if strat=="lfe" else "CC" if strat=="cce" else "CS"

# --- main results ---
TSA.plot_compact(dfRes, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_MAIN"),
                   outFSheet[".csv"]["mainVar"],outFSheet[".png"]["mainVar"],outFSheet[".pkl"]["mainVar"],outFSheet["plot"]["mainVar"])

if outFSheet[".csv"]["energy"]:
    energy_file_path = os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_TradedEnergy.csv")
    df_energysums = TSA.EnergySums(dfRes, DG_1)
    df_energysums.to_csv(energy_file_path, index=False)

# --- debug & details ---
TSA.plot_separately(dfRes, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_AllVar"),
                    outFSheet[".csv"]["allVar"],outFSheet[".png"]["allVar"],outFSheet[".pkl"]["allVar"],outFSheet["plot"]["allVar"])

allSOCs["TimeArray"] = dfRes["TimeArray"]
if ActiveDevices["Batteries"]:
    allSOCs["all_bat"] = dfRes["SOC"] # add general SOC to SOCs
TSA.plot_group(allSOCs, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_AllSOCs"), '',
               outFSheet[".csv"]["allSOCs"],outFSheet[".png"]["allSOCs"],outFSheet[".pkl"]["allSOCs"],outFSheet["plot"]["allSOCs"])

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
                False,outFSheet[".png"]["costs"],outFSheet[".pkl"]["costs"],outFSheet["plot"]["costs"])
    TSA.plot_group(d_costs_remain, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_CostsEnergRem"), '',
                False,outFSheet[".png"]["costs"],outFSheet[".pkl"]["costs"],outFSheet["plot"]["costs"])
    TSA.plot_group(d_costs_full, os.path.join(cWD,"output",f"{inputIdd}_{StratIdd}_{DevicesIdd}_F{str(forecast)}_CostsEnergAll"),
                outFSheet['.csv']["costs"])
# %%
