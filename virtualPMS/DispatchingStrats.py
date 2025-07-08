# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:41:51
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Dispatching strategies implemented : Load Following (LFE), Cycle Charging (CCE) and a modular strategy based on cost comparison (CostStrat).
'''
#---------------------
#%%
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) # add the entire module to python path

from virtualPMS import Battery, BatteryStock, DieselGenerator, Grid
import pandas as pd
import numpy as np

def LFE_CCE(strat: str, dfIN: pd.DataFrame, ActiveDevices: dict, grid_1: Grid, BattStock: BatteryStock, DG_1: DieselGenerator, dt: float, SOClim: float = 0.7, forecast: bool=False, forecast_period: float = 24) -> tuple[dict,dict]:
    """Load Following and Cycle Charging dispatching routine.
    
    Args:
        strat (str): "lfe" for Load Following strategy, "cce" for Cycle Charging strategy
        dfIN (pd.DataFrame): input dataframe. Content : "Time": list or np.array of datetime.datetime objects
                                                        "Load": list or np.array of floats (>=0)
                                                        "Green Prod": list or np.array of floats (>=0)
        ActiveDevices (dict): {"Grid": True/False, "Batteries": True/False, "DieselGenerator": True/False} : enter True for using the device, False to disable it.
        grid_1 (Grid): the grid used during simulation
        BattStock (BatteryStock): the battery stock used during simulation
        DG_1 (DieselGenerator): the diesel generator used during simulation
        dt (float): duration of the time step, in hours
        SOClim (float, optional): under this SOC, batteries will be charged by the grid (when the grid is reliable). 
                                   NB : if you don't want to charge the batteries with the grid power at all, enter SOClim = 0. Defaults to 0.7.
        forecast (bool, optional): If True, future data will be used to dispatch power.
                                   If False, only current and past data will be used. Defaults to False.
        forecast_period (float, optional): will only be used when forecast == True. based on the duration of battery charging and forecast abilities, 
                                           it represents the future period of time the function is allowed to look at in order to anticipate dispatching, IN HOURS. 
                                           Defaults to 24.
    
    Returns:
        dict, dict: Power and others time series.
            main:
                TimeArray [datetime]: dfIN["Time"]
                P_L [kWh]: dfIN["Load"]
                P_L_modif [kWh]: load power effectively supplied (clipped) (>=0)
                P_green [kWh]: dfIN["Green Prod"] (>=0)
                P_grid [kWh]: grid power output
                P_bat [kWh]: battery stock power output
                P_diesel [kWh]: diesel generator power output (>=0)
                SOC [%]: State Of Charge of the battery stock (0<=SOC<=1)
                F_C [L]: fuel remaining in the tank (>=0)
            others:
                P_net [kWh]: P_green - P_L
                P_net_modif [kWh]: P_green - P_L_modif
                P_diff [kWh]: Excess (>0) and Deficit (<0) power. = P_green + P_grid + P_bat + P_diesel - P_L
                P_resistor [kWh]: Excess of power that couldn't be used, neither sold : it goes to a resistor (>0)
            debug:
                indic [int]: indicates which branch of if-else was chosen at every time step
                RuntimeDG [int]: indicates how many time steps the diesel generator was running
            allSOCs [dict]: time series of the SOC of every battery of the tank
    """
    TimeArray = pd.to_datetime(dfIN["Time"])
    P_L = dfIN["Load"]
    P_green = dfIN["Green Prod"]

    assert(len(TimeArray) == len(P_L) == len(P_green))
    
    # time series
    # --------------------------------------------------------------------------------------------
    P_net = P_green - P_L  # Production - Load power (kW).

    P_L_modif = []      # [kW] clipped electrical load
    P_grid = []         # [kW] Grid OUTPUT power (<0 when selling and >0 when buying)
    P_bat = []          # [kW] Battery OUTPUT power (<0 when charging and >0 when discharging).
    SOC = []            # [%]  State-of-charge of the whole stock of batteries (0 to 1).
    P_diesel = []       # [kW] Power supplied by the Diesel Generator (>=0).
    F_C = []            # [L]  Fuel remaining in the tank (L)
    
    # debug & details
    # --------------------------------------------------------------------------------------------
    indic = [] # indicates in which if/else branch each time step is
    allSOCs = {} # saves the timeserie of every SOC of every battery
    for k in range(len(BattStock.battery_stock)):
        allSOCs['bat_'+str(k)] = []
    # BattStocks_debug = []

    RuntimeDG = []

    # SIMULATION
    # --------------------------------------------------------------------------------------------
    for i in range(len(TimeArray)):
        for j,bat_name in enumerate(allSOCs.keys()):
            allSOCs[bat_name].append(BattStock.battery_stock[j].SOC)
        F_C.append(DG_1.FuelRate)
        SOC.append(BattStock.get_SOC())
        RuntimeDG.append(DG_1.cur_runtime)

        if P_net[i] >= 0:                                                                                              # green power excess
            P_L_modif.append(P_L[i])
            P_diesel.append(0)
            DG_1.cur_runtime = 0
            if BattStock.get_SOC() < BattStock.get_SOC('max'):                          # battery charging
                Pbat_ch_i = BattStock.battery_stock_charge(P_net[i],dt)
                P_grid.append(0)
                P_bat.append(- Pbat_ch_i)
                # P_resistor.append(P_net[i] - Pbat_ch_i) # renewable prod clipping
                indic.append(1)
            elif grid_1.state[i]:                                                                                      # selling to the grid
                P_grid.append(- P_net[i])
                P_bat.append(0)
                # P_resistor.append(0)
                indic.append(2)
            else :                                                                                                     # battery full and grid unavailable : resistor
                P_grid.append(0)
                P_bat.append(0)
                # P_resistor.append(P_net[i]) # renewable prod clipping
                indic.append(3)
        else :                                                                                                         # green power deficit
            # print('belif   max',get_Pmax(BattStock,dt,'dis'),'pnet',abs(P_net[i]),'P_bat',get_Pbat(BattStock,abs(P_net[i]),dt))
            if grid_1.state[i] and not 0 < DG_1.cur_runtime < DG_1.MinimumRuntime:                                        # purchasing from the grid
                P_L_modif.append(P_L[i])
                P_diesel.append(0)
                DG_1.cur_runtime = 0
                # P_resistor.append(0)
                grid_state_long = np.concatenate((grid_1.state,grid_1.state[:int(forecast_period/dt)]))
                if forecast and (BattStock.get_SOC() < SOClim or 0 in grid_state_long[i:i+int(forecast_period/dt)]): # battery charging using grid
                    Pmax_bat = BattStock.get_Pmax(dt, 'ch')
                    Pbat_ch_i = BattStock.battery_stock_charge(Pmax_bat, dt)
                    P_grid.append(Pbat_ch_i - P_net[i])
                    P_bat.append(- Pbat_ch_i)
                    indic.append(4)
                else :                                                                                                 # grid supplies load
                    P_grid.append(abs(P_net[i]))
                    P_bat.append(0)
                    indic.append(5)
            elif abs(P_net[i]) <= BattStock.get_Pmax(dt, 'dis') and not 0 < DG_1.cur_runtime < DG_1.MinimumRuntime: # battery discharging
                # battery power sufficient
                # print('bchar   max',get_Pmax(BattStock,dt,'dis'),'pnet',abs(P_net[i]),'P_bat',get_Pbat(BattStock,abs(P_net[i]),dt))
                Pbat_dis_i = BattStock.battery_stock_discharge(abs(P_net[i]), dt)
                # print('achar   max',get_Pmax(BattStock,dt,'dis'),'P_bat_real',Pbat_dis_i,'P_bat_sim',get_Pbat(BattStock,abs(P_net[i]),dt))
                # if Pbat_dis_i < abs(P_net[i]):
                #     BattStocks_debug.append([[copy.deepcopy(b) for b in BattStock], P_net[i], dt])
                #     print('idx',i,'time', time[i],'p_disch', Pbat_dis_i, 'soc', get_SOC(BattStock,'soc'))
                # assert(Pbat_dis_i == abs(P_net[i]))
                P_L_modif.append(P_L[i] if grid_1.state[i] == 1 else P_green[i] + Pbat_dis_i)
                P_grid.append(- P_net[i] - Pbat_dis_i if grid_1.state[i] == 1 else 0)
                P_bat.append(Pbat_dis_i)
                P_diesel.append(0)
                DG_1.cur_runtime = 0
                # P_resistor.append(0)
                indic.append(6)
            else :                                                                                                     # running DG
                P_grid.append(0)
                P_DG_asked = DG_1.Pnom if strat.lower()=='cce' else abs(P_net[i])
                F_Cons, Pdiesel_i = DG_1.run_DG(P_DG_asked, dt, ActiveDevices["DieselGenerator"])
                P_diesel.append(Pdiesel_i)
                DG_1.cur_runtime += dt
                DG_1.FuelRate -= F_Cons * dt / DG_1.TankCapacity
                if Pdiesel_i < abs(P_net[i]):                                                                        # DG power unsufficient
                    Pbat_dis_i = BattStock.battery_stock_discharge(abs(P_net[i]) - Pdiesel_i, dt)
                    P_bat.append(Pbat_dis_i)
                    P_L_modif.append(P_green[i] + Pdiesel_i + Pbat_dis_i) # load clipping
                    # P_resistor.append(0)
                    indic.append(7)
                else :                                                                                                 # DG power sufficient
                    P_L_modif.append(P_L[i])
                    Pbat_ch_i = BattStock.battery_stock_charge(Pdiesel_i + P_net[i], dt)
                    # print('p_dg',Pdiesel_i,'soc',get_SOC(BattStock))
                    P_bat.append(- Pbat_ch_i)
                    indic.append(8)
                    # P_resistor.append(P_green[-1] + P_bat[-1] + P_diesel[-1] - P_L_modif[-1]) # DG output clipping
                # print(round(F_Cons * dt / DG_1.TankCapacity,3), round(DG_1.FuelRate,3))
    
    # OUTPUT
    # --------------------------------------------------------------------------------------------
    P_L_modif = np.array(P_L_modif)
    P_bat = np.array(P_bat)
    P_grid = np.array(P_grid)
    P_diesel = np.array(P_diesel)
    F_C = np.array(F_C)
    SOC = np.array(SOC)
    P_net_modif = P_green - P_L_modif
    P_diff = P_green + P_grid + P_bat + P_diesel - P_L
    P_resistor = np.array([max(0,pow) for pow in P_diff])

    RuntimeDG = np.array(RuntimeDG)

    DictOut_TS = {"TimeArray":TimeArray, "P_L":P_L, "P_L_modif":P_L_modif, "P_green":P_green, "P_net":P_net, "P_net_modif":P_net_modif, 
                  "P_diff":P_diff, "P_resistor":P_resistor, "indic":indic} # only time series
    if ActiveDevices["Grid"]:
        DictOut_TS["P_grid"] = P_grid
    else:
        assert(len(P_grid[abs(P_grid) > 10**(-14)]) == 0)
    if ActiveDevices["Batteries"]:
        DictOut_TS["P_bat"] = P_bat
        DictOut_TS["SOC"] = SOC
    else:
        assert(len(P_bat[abs(P_bat) > 10**(-14)]) == 0)
        assert(len(SOC[abs(SOC) > 10**(-14)]) == 0)
    if ActiveDevices["DieselGenerator"]:
        DictOut_TS["P_diesel"] = P_diesel
        DictOut_TS["F_C"] = F_C
        DictOut_TS["RuntimeDG"] = RuntimeDG
    else:
        assert(len(P_diesel[abs(P_diesel) > 10**(-14)]) == 0)
        assert(len(F_C[abs(F_C) > 10**(-14)]) == 0)
    dfOut_TS = pd.DataFrame(DictOut_TS)
    return dfOut_TS, allSOCs

def CostStrat(dfIN: pd.DataFrame, ActiveDevices: dict, grid_1: Grid, BattStock: BatteryStock, DG_1: DieselGenerator, dt: float, ChargeUsingGridCost: float=0, forecast: bool=False, forecast_period: float = 24) -> tuple[dict,dict]:
    """Strategy based on costs dispatching routine.
    
    Args:
        dfIN (pd.DataFrame): input dataframe. Content : "Time": list or np.array of datetime.datetime objects
                                                        "Load": list or np.array of floats (>=0)
                                                        "Green Prod": list or np.array of floats (>=0)
        ActiveDevices (dict): {"Grid": True/False, "Batteries": True/False, "DieselGenerator": True/False} : enter True for using the device, False to disable it.
        grid_1 (Grid): the grid used during simulation
        BattStock (BatteryStock): the battery stock used during simulation
        DG_1 (DieselGenerator): the diesel generator used during simulation
        dt (float): duration of the time step, in hours
        ChargeUsingGridCost (float, optional): if the cost of 1kWh purchased from the grid is less than this, it will be used to charge batteries. Defaults to 0.
        forecast (bool, optional): If True, future data will be used to dispatch power.
                                   If False, only current and past data will be used. Defaults to False.
        forecast_period (float, optional): will only be used when forecast == True. based on the duration of battery charging and forecast abilities, 
                                           it represents the future period of time the function is allowed to look at in order to anticipate dispatching, IN HOURS. 
                                           Defaults to 24.
    
    Returns:
        dict, dict: Power and others time series.
            main:
                TimeArray [datetime]: dfIN["Time"]
                P_L [kWh]: dfIN["Load"]
                P_L_modif [kWh]: load power effectively supplied (clipped) (>=0)
                P_green [kWh]: dfIN["Green Prod"] (>=0)
                P_grid [kWh]: grid power output
                P_bat [kWh]: battery stock power output
                P_diesel [kWh]: diesel generator power output (>=0)
                SOC [%]: State Of Charge of the battery stock (0<=SOC<=1)
                F_C [L]: fuel remaining in the tank (>=0)
            others:
                P_net [kWh]: P_green - P_L
                P_net_modif [kWh]: P_green - P_L_modif
                P_diff [kWh]: Excess (>0) and Deficit (<0) power. = P_green + P_grid + P_bat + P_diesel - P_L
                P_resistor [kWh]: Excess of power that couldn't be used, neither sold : it goes to a resistor (>0)
            debug:
                indic [int]: indicates which branch of if-else was chosen at every time step
                RuntimeDG [int]: indicates how many time steps the diesel generator was running
            allSOCs [dict]: time series of the SOC of every battery of the tank 
    """
    TimeArray = dfIN["Time"]
    P_L = dfIN["Load"]
    P_green = dfIN["Green Prod"]

    assert(len(TimeArray) == len(P_L) == len(P_green))

    # time series
    # --------------------------------------------------------------------------------------------
    P_net = P_green - P_L  # Production - Load power (kW).

    P_L_modif = []      # [kW] clipped electrical load
    P_grid = []         # [kW] Grid OUTPUT power (<0 when selling and >0 when buying)
    P_bat = []          # [kW] Battery OUTPUT power (<0 when charging and >0 when discharging).
    SOC = []            # [%]  State-of-charge of the whole stock of batteries (0 to 1).
    P_diesel = []       # [kW] Power supplied by the Diesel Generator (>=0).
    F_C = []            # [L]  Fuel remaining in the tank (L)
    
    # debug & details
    # --------------------------------------------------------------------------------------------
    indic = [] # indicates in which if/else branch each time step is
    allSOCs = {} # saves the timeserie of every SOC of every battery
    for k in range(len(BattStock.battery_stock)):
        allSOCs['bat_'+str(k)] = []
    RuntimeDG = []
    GridSaleCost_list = []
    BatteryChargeCost_list = []
    GridPurchaseCost_list = []
    BatteryDischargeCost_list = []
    DGUseCost_list = []

    # SIMULATION
    # --------------------------------------------------------------------------------------------
    # to understand 'Yes' and 'No' comments, refer to the practical diagram
    for i in range(len(TimeArray)):
        for j,bat_name in enumerate(allSOCs.keys()):
            allSOCs[bat_name].append(BattStock.battery_stock[j].SOC)
        F_C.append(DG_1.FuelRate)
        SOC.append(BattStock.get_SOC())
        RuntimeDG.append(DG_1.cur_runtime)

        GridSaleCost = grid_1.sale_cost(TimeArray, i)
        BatteryChargeCost = BattStock.charge_cost(grid_1, i, dt, ActiveDevices["Batteries"], forecast, forecast_period)
        GridSaleCost_list.append(GridSaleCost)
        BatteryChargeCost_list.append(BatteryChargeCost)

        if P_net[i] == 0:                                                                                              # P_green = P_load
            P_L_modif.append(P_L[i])
            P_grid.append(0)
            P_bat.append(0)
            P_diesel.append(0)
            DG_1.cur_runtime = 0
            indic.append(1)
            GridPurchaseCost_list.append(np.inf)
            BatteryDischargeCost_list.append(np.inf)
            DGUseCost_list.append(np.inf)
        elif P_net[i] > 0:                                                                                             # green power excess
            P_L_modif.append(P_L[i])
            P_diesel.append(0)
            DG_1.cur_runtime = 0
            if BatteryChargeCost < GridSaleCost:                                                                       # selling to the grid
                P_grid.append(- P_net[i])
                P_bat.append(0)
                indic.append(2)
            else :                                                                                                     # battery charging
                Pbat_ch_i = BattStock.battery_stock_charge(P_net[i], dt)
                P_grid.append(Pbat_ch_i - P_net[i] if grid_1.state[i] == 1 else 0)
                P_bat.append(- Pbat_ch_i)
                indic.append(3)
            GridPurchaseCost_list.append(np.inf)
            BatteryDischargeCost_list.append(np.inf)
            DGUseCost_list.append(np.inf)
        else:                                                                                                          # green power deficit
            f_cons, Pdiesel_i = DG_1.run_DG(abs(P_net[i]), dt, ActiveDevices["DieselGenerator"]) # simulation to see if running the DG is worth the effort (time series are not updated here)
            GridPurchaseCost = grid_1.purchase_cost(TimeArray, i)
            BatteryDischargeCost = BattStock.discharge_cost(grid_1, abs(P_net[i]), dt, ActiveDevices["Batteries"])
            DGUseCost = DG_1.use_cost(f_cons, abs(P_net[i]), Pdiesel_i, ActiveDevices["DieselGenerator"])
            GridPurchaseCost_list.append(GridPurchaseCost)
            BatteryDischargeCost_list.append(BatteryDischargeCost)
            DGUseCost_list.append(DGUseCost)
            # print(grid_state[i],'GridSaleCost', round(GridSaleCost,3), 'BatteryChargeCost', round(BatteryChargeCost,3), 'GridPurchaseCost', round(GridPurchaseCost,3), 'BatteryDischargeCost', round(BatteryDischargeCost,3), 'DGUseCost', round(DGUseCost,3))
            if GridPurchaseCost < BatteryDischargeCost and GridPurchaseCost < DGUseCost:                                                                                    # purchasing from the grid
                P_L_modif.append(P_L[i])
                P_diesel.append(0)
                DG_1.cur_runtime = 0
                if GridPurchaseCost < ChargeUsingGridCost:                                                             # battery charging with the grid
                    Pmax_bat = BattStock.get_Pmax(dt, 'ch')
                    Pbat_ch_i = BattStock.battery_stock_charge(Pmax_bat, dt)
                    P_grid.append(abs(P_net[i]) + Pbat_ch_i)
                    P_bat.append(- Pbat_ch_i)
                    indic.append(4)
                else:                                                                                                  # grid supplying only the load
                    P_grid.append(abs(P_net[i]))
                    P_bat.append(0)
                    indic.append(5)
            else :                                                                                                     # grid too expensive or disconnected
                if BatteryDischargeCost < DGUseCost:                                                                   # battery discharging
                    Pbat_dis_i = BattStock.battery_stock_discharge(abs(P_net[i]), dt)
                    P_L_modif.append(P_L[i] if grid_1.state[i] == 1 else P_green[i] + Pbat_dis_i)
                    P_grid.append(abs(P_net[i]) - Pbat_dis_i if grid_1.state[i] == 1 else 0)
                    P_bat.append(Pbat_dis_i)
                    P_diesel.append(0)
                    DG_1.cur_runtime = 0
                    indic.append(6)
                else :                                                                                                 # running DG
                    P_diesel.append(Pdiesel_i) # the DG is really running
                    DG_1.cur_runtime += dt
                    DG_1.FuelRate -= f_cons * dt / DG_1.TankCapacity
                    if abs(P_net[i]) < Pdiesel_i:                                                                      # DG power sufficient
                        P_L_modif.append(P_L[i])
                        if BatteryChargeCost < GridSaleCost:                                                           # selling DG excess to the grid
                            P_grid.append(abs(P_net[i]) - Pdiesel_i)
                            P_bat.append(0)
                            indic.append(7)
                        else :                                                                                         # battery charging with DG excess
                            Pbat_ch_i = BattStock.battery_stock_charge(Pdiesel_i - abs(P_net[i]), dt)
                            P_grid.append(abs(P_net[i]) + Pbat_ch_i - Pdiesel_i if grid_1.state[i] == 1 else 0)
                            P_bat.append(- Pbat_ch_i)
                            indic.append(8)
                    else :                                                                                             # DG power unsufficient
                        if GridPurchaseCost < BatteryDischargeCost:                                                    # purchasing from the grid
                            P_L_modif.append(P_L[i])
                            P_grid.append(abs(P_net[i]) - Pdiesel_i)
                            P_bat.append(0)
                            indic.append(9)
                        else :                                                                                         # battery discharging
                            Pbat_dis_i = BattStock.battery_stock_discharge(abs(P_net[i]) - Pdiesel_i, dt)
                            P_L_modif.append(P_L[i] if grid_1.state[i] == 1 else P_green[i] + Pdiesel_i + Pbat_dis_i) # load clipping
                            P_grid.append(- P_net[i] - Pdiesel_i - Pbat_dis_i if grid_1.state[i] == 1 else 0)
                            P_bat.append(Pbat_dis_i)
                            indic.append(10)

    # OUTPUT
    # --------------------------------------------------------------------------------------------
    P_L_modif = np.array(P_L_modif)
    P_bat = np.array(P_bat)
    P_grid = np.array(P_grid)
    P_diesel = np.array(P_diesel)
    F_C = np.array(F_C)
    SOC = np.array(SOC)
    P_net_modif = P_green - P_L_modif
    P_diff = P_green + P_grid + P_bat + P_diesel - P_L
    P_resistor = np.array([max(0,pow) for pow in P_diff])

    RuntimeDG = np.array(RuntimeDG)

    DictOut_TS = {"TimeArray":TimeArray, "P_L":P_L, "P_L_modif":P_L_modif, "P_green":P_green, "P_net":P_net, "P_net_modif":P_net_modif, 
                  "P_diff":P_diff, "P_resistor":P_resistor, "indic":indic} # only time series
    if ActiveDevices["Grid"]:
        DictOut_TS["P_grid"] = P_grid
        DictOut_TS["GridPurchaseCost"] = GridPurchaseCost_list
        DictOut_TS["GridSaleCost"] = GridSaleCost_list
    else:
        assert(len(P_grid[abs(P_grid) > 10**(-14)]) == 0)
    if ActiveDevices["DieselGenerator"]:
        DictOut_TS["P_diesel"] = P_diesel
        DictOut_TS["F_C"] = F_C
        DictOut_TS["DGUseCost"] = DGUseCost_list
        DictOut_TS["RuntimeDG"] = RuntimeDG
    else:
        assert(len(P_diesel[abs(P_diesel) > 10**(-14)]) == 0)
        assert(len(F_C[abs(F_C) > 10**(-14)]) == 0)
    if ActiveDevices["Batteries"]:
        DictOut_TS["P_bat"] = P_bat
        DictOut_TS["SOC"] = SOC
        DictOut_TS["BatteryDischargeCost"] = BatteryDischargeCost_list
        DictOut_TS["BatteryChargeCost"] = BatteryChargeCost_list
    else:
        assert(len(P_bat[abs(P_bat) > 10**(-14)]) == 0)
        assert(len(SOC[abs(SOC) > 10**(-14)]) == 0)
    dfOut_TS = pd.DataFrame(DictOut_TS)
    return dfOut_TS, allSOCs

# test section
# -----------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime, timedelta
    import virtualPMS.TimeSeriesAnalysis as TSA

    # time series
    # ----------------------------------------------
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
    GridStateNormal = np.array([1] * (num_steps - num_steps//2) + [0] * (num_steps//2), dtype=np.int64)  # grid reliable or not at t
    df_TS = pd.DataFrame({"Time":TimeArray,"Load":P_L,"Green Prod": P_green, "Grid State": GridStateNormal}).set_index("Time")

    # all components allowed
    # ----------------------------------------------
    PlotNormal = True
    # --- components definition ---
    ActiveDevicesNormal = {"Grid": True, "Batteries": True, "DieselGenerator": True}

    # grid
    GridNormal = Grid(GridStateNormal, pd.read_csv(Grid.GridPricesRef), pd.read_csv(Grid.GridScheduleRef)) 

    # batteries
    paramIn_batt = {'capacity':800,
                    'SOC':0.2, 
                    'SOCmin':0.1,
                    'SOCmax':0.9,
                    'eta':0.8,
                    'Pmax_ch':200,
                    'Pmax_disch':150,
                    'lifetime':1000,
                    'ReplacementCost':10000,
                    'MaintenanceCost':0.03}
    
    battery_1 = Battery(paramIn_batt)
    battery_2 = Battery(paramIn_batt)
    battery_3 = Battery(paramIn_batt)

    BattStockNormal = BatteryStock([
                                battery_1,
                                battery_2,
                                battery_3
                              ])
    
    # diesel generator
    paramInDGNormal = {"Pmax":400,
                   "Pnom":380,
                   "Pmin":370,
                   "TankCapacity":2000,
                   "FuelRate":1,
                   "f_r_min":0.1,
                   "lifetime":200000,
                   "ReplacementCost":10000,
                   "MaintenanceCost":0.08,
                   "FuelPrice":1.5}
    
    DGNormal = DieselGenerator(paramInDGNormal)
    DGNormal.find_DG_coeffs()

    # --- simulations ---
    dfResNormalCostStrat, allSOCsCostStrat = CostStrat(df_TS, ActiveDevicesNormal, GridNormal, BattStockNormal, DGNormal, dt, 0.1, True, 48)
    dfResNormalLFE, allSOCsLFE = LFE_CCE("lfe", df_TS, ActiveDevicesNormal, GridNormal, BattStockNormal, DGNormal, dt, 0.5, True, 48)
    dfResNormalCCE, allSOCsCCE = LFE_CCE("cce", df_TS, ActiveDevicesNormal, GridNormal, BattStockNormal, DGNormal, dt, 0.5, True, 48)

    TSA.plot_compact(dfResNormalCostStrat, "test_output", False, False, False, True)
    TSA.plot_compact(dfResNormalLFE, "test_output", False, False, False, True)
    TSA.plot_compact(dfResNormalCCE, "test_output", False, False, False, True)

    # only PV and Load
    # ----------------------------------------------
    PlotEmpty = False

    # --- components definition ---
    ActiveDevicesEmpty = {"Grid": False, "Batteries": False, "DieselGenerator": False}

    # grid
    GridState = np.array([0] * num_steps)
    GridEmpty = Grid(GridState, pd.read_csv(Grid.GridPricesRef), pd.read_csv(Grid.GridScheduleRef))

    # batteries
    BattStockEmpty = BatteryStock([Battery({
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
                                            })])
    
    # diesel generator
    paramInDGEmpty = {"Pmax":1,
                "Pnom":1,
                "Pmin":0,
                "TankCapacity":1,
                "FuelRate":0,
                "f_r_min":0,
                "lifetime":0,
                "ReplacementCost":0,
                "MaintenanceCost":0,
                "FuelPrice":0,
                "MinimumRuntime":0}
    
    DGEmpty = DieselGenerator(paramInDGEmpty)
    DGEmpty.find_DG_coeffs()

    # --- simulations ---
    dfResEmptyCostStrat, allSOCs = CostStrat(df_TS, ActiveDevicesEmpty, GridEmpty, BattStockEmpty, DGEmpty, dt, 0.1, True, 48)
    dfResEmptyLFE, allSOCs = LFE_CCE("lfe", df_TS, ActiveDevicesEmpty, GridEmpty, BattStockEmpty, DGEmpty, dt, 0.5, True, 48)
    dfResEmptyCCE, allSOCs = LFE_CCE("cce", df_TS, ActiveDevicesEmpty, GridEmpty, BattStockEmpty, DGEmpty, dt, 0.5, True, 48)

    TSA.plot_compact(dfResEmptyCostStrat, "test_output", False, False, False, True)
    TSA.plot_compact(dfResEmptyLFE, "test_output", False, False, False, True)
    TSA.plot_compact(dfResEmptyCCE, "test_output", False, False, False, True)
# %%
