# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:40:01
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Battery Stock Management. A "BatteryStock" object is a list of "Battery" Objects. Includes charge and discharge routines, cost functions and test section. 
'''
#---------------------
#%%
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) # add the entire module to python path

from virtualPMS.Battery import Battery
from virtualPMS.Grid import Grid

import numpy as np
import copy

class BatteryStock:    
    def __init__(self, battery_stock: list[Battery]):
        """initiate a battery stock. See Battery.py for more info on the modelling of a single battery.

        Args:
            battery_stock (list[Battery]): list of 'Battery' objects previously defined.
        """     
        self.battery_stock = battery_stock

    def battery_stock_charge(self, power: float, dt: float) -> float:
        """charge the batteries from the lower to the upper SOC.

        Args:
            power (float): the power not being used by the load (in most cases = P_green - P_L > 0) in kW
            dt (float): charging time (= 1 time step), in hours

        Returns:
            float: >=0 cumulated power input of the battery stock, in kW.
        """
        assert(power >= 0)
        batt_sorted = sorted(self.battery_stock, key=lambda x: -x.SOC, reverse=True)

        P_remaining = power # power still usable for charging batteries
        for b in batt_sorted:
            # print('charge of   ', [name for name, value in globals().items() if value is battery_stock[t[0]]], '; power still available :', P_remaining, 'W')
            # charge the battery that has the lowest SOC and update the remaining power
            P_remaining -= b.battery_charge(P_remaining, dt)
            if P_remaining == 0:
                break

        return power - P_remaining

    def battery_stock_discharge(self, power: float, dt: float) -> float:
        """discharge the batteries from the upper to the lower SOC.

        Args:
            power (float): the power needed by the load (in most cases = P_L - P_green > 0) in kW
            dt (float): discharging time (= 1 time step), in hours
        Returns:
            float: >=0 the cumulated power output of the battery stock, in kW. 
        """
        assert(power >= 0)
        batt_sorted = sorted(self.battery_stock, key=lambda x: x.SOC, reverse=True)

        P_remaining = power # power still needed by the load
        for b in batt_sorted:
            # discharge the battery that has the highest SOC and update the remaining power
            P_remaining -= b.battery_discharge(P_remaining, dt)
            # print('P_bat =',P_rem_debug - P_remaining, '; power still needed:', P_remaining, 'kW')
            if P_remaining == 0:
                break
        return power - P_remaining

    def sort_batteries(self, criteria: str) -> list: # unused
        """sorts a list of batteries in order to charge or discharge them following the given criteria.

        Args:
            criteria (str): choose among a list of pre-made criterias to sort batteries

        Returns:
            list of battery objects: the batteries sorted with the criteria or battery_stock if the criteria was not understood
        """
        crit_list = ['socmin', 'socmax', 'capacity']
        if criteria.lower() not in crit_list:
            # print('!! criteria not understood !! choose among the following :'+crit_list)
            return self.battery_stock
        else:
            # print('else')
            return self.battery_stock

    def get_SOC(self,which: str = 'soc') -> float:
        """for a given stock of many batteries, calculates the overall SOC by processing a weighted average.

        Args:
            which (str): 'soc' for current/real SOC
                         'min' for minimum SOC
                         'max' for maximum SOC

        Returns:
            float: SOC of the entire battery stock (weighted average).
        """
        which = which.lower()
        assert(which in ['soc','min','max'])

        var_tot = 0
        capa_tot = 0
        for batt in self.battery_stock:
            capa_tot += batt.capacity
            if which == 'soc':             # real/current SOC
                var_tot += batt.SOC * batt.capacity
            elif which == 'min':           # SOCmin
                var_tot += batt.SOCmin * batt.capacity
            elif which == 'max':           # SOCmax
                var_tot += batt.SOCmax * batt.capacity            
        var_tot = var_tot / capa_tot if capa_tot > 0 else 0
        return var_tot

    def get_Pmax(self, dt: float, which: str) -> float:
        """
        Args:
            dt (float): discharging time (= 1 time step), in hours
            which (str): if 'ch', returns the maximum charge power that can store the battery stock during dt
                         if 'dis', returns the maximum discharge power that can supply the battery stock during dt

        Returns:
            float: maximum charge or discharge power for the considered time step.
        """
        which = which.lower()
        assert(which in ['ch','dis'])

        if which == 'ch':
            e_needed = 0
            power_max_inst = 0
            for batt in self.battery_stock:
                e_needed += (batt.SOCmax - batt.SOC) * batt.capacity
                if batt.SOC < batt.SOCmax:
                    power_max_inst += batt.Pmax_ch
            Pmax_ch = min(e_needed / dt, power_max_inst)
            return Pmax_ch
        elif which == 'dis':
            e_available = 0
            power_max_inst = 0
            for batt in self.battery_stock:
                e_available += (batt.SOC - batt.SOCmin) * batt.capacity * batt.eta
                if batt.SOC > batt.SOCmin:
                    power_max_inst += batt.Pmax_disch
            # print("SOClim_pow",e_available / dt, "inst_lim_pow", power_max_inst)
            Pmax_dis = min(e_available / dt, power_max_inst)
            return Pmax_dis
        
    def get_Pbat(self, power: float, dt: float) -> float: # unused
        """simulates the charge (power>0) or discharge (power<0) of the battery stock and returns the remaining power
        NB : SOCs are NOT uploaded within this function.

        Args:
            power (float): power demand in kW : if power > 0, batteries will be charged
                                                if power < 0, batteries will be discharged
            dt (float>0): duration of the time step in hours

        Returns:
            float: P_bat if =0, batteries can be fully charged / can supply the load demand
                                    if >0, batteries cannot use all the power to charge / cannot supply all the load demand
        """
        virtual_stock = BatteryStock([copy.deepcopy(b) for b in self.battery_stock])
        if power > 0:
            P_batt_stock = virtual_stock.battery_stock_charge( power, dt)
        elif power < 0:
            P_batt_stock = virtual_stock.battery_stock_discharge( -power, dt)
        else :
            P_batt_stock = 0
        return P_batt_stock

    def get_var(self, which: str) -> float:
        """get the value of any other battery variable non reachable using get_SOC or get_Pmax.

        Args:
            which (str): 'capacity' for overall capacity
                         'eta' for overall energy efficiency
                         'ReplacementCost' for total replacement cost
                         'MaintenanceCost' for total maintenance cost.

        Returns:
            float: equivalent variable for the battery stock
        """
        which = which.lower()
        assert(which in ['capacity', 'eta', 'replacementcost', 'maintenancecost'])
        
        capa_tot = 0
        var_tot = 0
        for batt in self.battery_stock:
            capa_tot += batt.capacity
            if which == 'capacity':
                var_tot += batt.capacity
            elif which == 'ReplacementCost':
                var_tot += batt.ReplacementCost
            elif which == 'MaintenanceCost':
                var_tot += batt.MaintenanceCost
            elif which == 'eta':
                var_tot += batt.eta * batt.capacity
        return var_tot / capa_tot if which == 'eta' else var_tot

    def charge_cost(self, grid_comp: Grid, time_step: int, dt: float, active: bool=True, forecast: bool=False, charac_period: int=0) -> float: # charging batteries
        """calculates the cost of charging batteries. NB : it is not an economical cost, it is used for decision making in the costs dispatching strategy.

        Args:
            grid_comp ('Grid' object): the grid (if the microgrid is connected to it)
            time_step (int): index of the for loop (used to know if the grid is reliable or not)
            dt (float): duration of the time step, in hours
            active (bool): if True, the DG is being used normally
                            if False, the DG is NOT being used.
            forecast (bool, optional): if True, future data will be used to dispatch power,
                                       if False, only current and past data will be used.
            charac_period (int, optional): (Defaults to 0, use only when forecast == True) based on the duration of battery charging and forecast abilities, 
                            charac_period is the future period of time the function is allowed to look at in order to anticipate dispatching, in hours. 

        Returns:
            float: cost of batteries charging in euro/kWh (0 <= c <= +inf)
        """
        if not active:
            return 0
        
        if not forecast:
            charac_period = 0
        
        current_soc = self.get_SOC()
        socmax = self.get_SOC('max')
        GridState = np.concatenate((grid_comp.state,grid_comp.state[:int(charac_period/dt)]))
        if current_soc == socmax:
            return 0
        else:
            # print(GridState[time_step : time_step + int(charac_period/dt)])
            if 0 in GridState[time_step : time_step + int(charac_period/dt) + 1]: # in the next *charac_period* hours, the grid will be cut-off
                return 10e10 # batteries really should be used
            else:
                return grid_comp.prices.iloc[2,1] # peak-hours price ('2'), buying ('1')

    def discharge_cost(self, grid_comp: Grid, power: float, dt: float, active: bool=False) -> float: # discharging batteries
        """calculates the cost of discharging the battery stock knowing the energy needed (power*dt). NB : it is not an economical cost, it is used for decision making in the costs dispatching strategy.

        Args:
            grid_comp (grid object): the grid (if the microgrid is connected to it).
            power (float): power demand in kW
            dt (float): duration of the time step, in hours
            active (bool): if True, the DG is being used normally
                            if False, the DG is NOT being used.

        Returns:
            float: cost of batteries discharging in euro/kWh
        """
        if not active:
            return np.inf
        
        capa = self.get_var('capacity')
        capa_eta_sum = sum([batt.capacity * batt.eta * (batt.SOCmax - batt.SOCmin) for batt in self.battery_stock])
        
        # lifetime of the battery stock in kWh
        lifetime_avg = sum([batt.capacity * batt.eta * (batt.SOCmax - batt.SOCmin) * batt.lifetime for batt in self.battery_stock])
        
        ReplacementCost = self.get_var('ReplacementCost')
        MaintenanceCost = self.get_var('MaintenanceCost')

        cost = grid_comp.prices.iloc[2,1] / capa_eta_sum * capa + ReplacementCost / lifetime_avg + MaintenanceCost
        # available_power = get_Pbat(battery_stock, power, dt)
        # print('av_pow',available_power,'grid',grid_comp.prices[2,1],'capaetesum',capa_eta_sum,'capa',capa,'repl',ReplacementCost,'lifetime_avg',lifetime_avg,'maint',MaintenanceCost, 'cost', cost)
        if power <= self.get_Pmax(dt, 'dis'):
        # if available_power == power:
            return cost
        else:
            return 10e10 # batteries shouldn't be used but they could

# test section
# -----------------------------------------------------------------
if __name__=="__main__":
    from datetime import datetime, timedelta
    import pandas as pd
    
    print(" --- testing the battery stock model ---\n")

    # Input parameter
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

    dt = 1 # test duration in hours
    print("dt =",dt,"hours\n")

    print("energy efficiency test with one charge - discharge cycle for", [name for name in globals() if globals()[name] is battery_1][0])
    # power > 0
    print('initial SOC     =',round(battery_1.SOC,3))
    P_charge_single_real = battery_1.battery_charge(100, dt)
    print('power supply =',100,' battery charging power     =',P_charge_single_real,' charged SOC     =',round(battery_1.SOC,3))
    P_disch_single_real = battery_1.battery_discharge(80, dt)
    print('power demand =',80,' battery discharging power   =', P_disch_single_real,' discharged SOC  =',round(battery_1.SOC,3), '\n')
    # power = 0
    P_charge_single_real = battery_1.battery_charge(0, dt)
    print('power supply =',0,' battery charging power    =',P_charge_single_real,' charged SOC    =',round(battery_1.SOC,3))
    P_disch_single_real = battery_1.battery_discharge(0, dt)
    print('power demand =',0,' battery discharging power =', P_disch_single_real,' discharged SOC =',round(battery_1.SOC,3), '\n')
 
    bat_list = [
                battery_1,
                battery_2,
                battery_3
                ]

    BattStock = BatteryStock(bat_list)

    print('initial SOCs    =',[round(batt.SOC,3) for batt in BattStock.battery_stock])
    print("stock SOCmax    =",round(BattStock.get_SOC('max')),3)
    print("stock SOCmin    =",round(BattStock.get_SOC('min')),3)
    print("stock capacity  =",round(BattStock.get_var( 'capacity'),3))
    print("Pmax charge     =",round(BattStock.get_Pmax( dt, 'ch'),3))
    print("Pmax discharge  =",round(BattStock.get_Pmax( dt, 'dis'),3))
    print("Pbat charge     =",round(BattStock.get_Pbat(2*BattStock.get_Pmax(dt, 'ch'), dt),3))
    print("Pbat discharge  =",round(BattStock.get_Pbat(-2*BattStock.get_Pmax(dt, 'dis'), dt),3))

    for batt in bat_list:
        batt.SOC = 0.5
    soc_init = BattStock.get_SOC()
    
    # cycles of charge - discharge
    n_cycles = 3
    P_charge_tank = 500
    P_disch_tank = P_charge_tank * BattStock.get_var('eta')

    print("\nenergy efficiency test with", n_cycles, "charge - discharge cycles for", [name for name in globals() if any(globals()[name] is b for b in BattStock.battery_stock)])
    print("\nSOCs uploaded")
    print('initial SOCs       =',[round(batt.SOC,3) for batt in BattStock.battery_stock])
    print('initial stock SOC  =',round(soc_init,3))
    print("stock SOCmax       =",round(BattStock.get_SOC('max'),3))
    print("stock SOCmin       =",round(BattStock.get_SOC('min'),3))
    print("stock capacity     =",round(BattStock.get_var( 'capacity'),3))
    print("Pmax charge        =",round(BattStock.get_Pmax( dt, 'ch'),3))
    print("Pmax discharge     =",round(BattStock.get_Pmax( dt, 'dis'),3))
    print("Pbat charge        =",round(BattStock.get_Pbat( 2*BattStock.get_Pmax(dt, 'ch'), dt),3))
    print("Pbat discharge     =",round(BattStock.get_Pbat( -2*BattStock.get_Pmax(dt, 'dis'), dt),3))

    print("\ncharging power  =", P_charge_tank, "discharging power =", P_disch_tank)
    for i in range(n_cycles):
        print(" ~~~ cycle", i+1)
        P_charge_tank_real = BattStock.battery_stock_charge(P_charge_tank,dt)
        print('battery charging power =',P_charge_tank_real,'charged SOCs =',[round(batt.SOC,3) for batt in BattStock.battery_stock])
        print('stock SOC              =', round(BattStock.get_SOC('soc'),3), '\n')

        P_disch_tank_real = BattStock.battery_stock_discharge(P_disch_tank,dt)
        print('battery discharging power  =', P_disch_tank_real,'discharged SOCs =',[round(batt.SOC,3) for batt in BattStock.battery_stock])
        print('stock SOC                  =', round(BattStock.get_SOC('soc'),3), '\n')
    
    if dt <= 1:
        assert(BattStock.get_SOC() == soc_init)

    print(" --- costs functions tests ---")
    dt = 1 # sampling period in hours
    start_date = datetime(2025, 1, 1)
    num_steps = int(20 / dt) # 20 hours
    time = np.array([start_date + timedelta(hours=i * dt) for i in range(20)])
    
    # grid
    GridState = np.array([1] * (num_steps - num_steps//2) + [0] * (num_steps//2), dtype=np.int64)  # grid reliable or not at t
    GridTest = Grid(GridState,  pd.read_csv(Grid.GridPricesRef), pd.read_csv(Grid.GridScheduleRef))

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

    batt_stock = BatteryStock([
                                battery_1,
                                battery_2,
                                battery_3
                              ])

    print("state :\n",GridTest.state)
    print("\nprices :\n",GridTest.prices)
    print("\nschedule :\n",GridTest.schedule)

    print("\ngrid connected")
    D1_test = GridTest.sale_cost(time, 5)
    D2_test = batt_stock.charge_cost(GridTest, 5, dt, False)
    D3_test = GridTest.purchase_cost(time, 5)
    D4_test = batt_stock.discharge_cost(GridTest, 200, dt) # demand ok
    print('selling price         D1 =', D1_test, 'euros/kWh | buying price             D3 =', D3_test, 'euros/kWh')
    print('battery charging cost D2 =', D2_test, 'euros/kWh | battery discharging cost D4 =', D4_test, 'euros/kWh')

    print("\ngrid disconnected")
    D1_test = GridTest.sale_cost(time, 15)
    D2_test = batt_stock.charge_cost(GridTest, 15, dt, False)
    D3_test = GridTest.purchase_cost(time, 15)
    D4_test = batt_stock.discharge_cost(GridTest, 500, dt) # demand too high
    print('selling price         D1 =', D1_test, 'euros/kWh | buying price             D3 =', D3_test, 'euros/kWh')
    print('battery charging cost D2 =', D2_test, 'euros/kWh | battery discharging cost D4 =', D4_test, 'euros/kWh')
# %%
