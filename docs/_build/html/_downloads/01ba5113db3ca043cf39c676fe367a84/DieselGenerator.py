# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:40:42
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Diesel Generator model : parameters definition, runnning routine (including fuel consumption law), cost function
'''
#---------------------
#%%
import os
import numpy as np
import pandas as pd

class DieselGenerator:
    FuelConsoFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "DataBase","DieselGeneratorFuelConsumption.csv")
    
    def __init__(self, paramIn):
        """typical parameters of a DG :
            0 <= Pmin < Pnom <= Pmax < 2500kW --> for an inverter, Pmin can be close to 0.3*Pnom but for a classical DG it might not go any further down than 0.8 or 0.9 * Pnom.
            50 < TankCapacity < 5000L a powerful DG needs a lot of fuel to run --> 2 < TankCapacity / Pnom < 5
            0 <= f_r_min < FuelRate <= 1
            0.2 < A < 0.3L/kWh
            0.01 < B / Pnom < 0.5L/h
            NB1 : the fuel rate is updated the following way : DG_1.FuelRate -= f_cons * dt / DG_1.TankCapacity
            NB2 : if Pmin!=0, at low power deficit some 'noise' can appear on power and FuelRate curves

        Args:
            paramIn (dict): contains the following parameters
                Pmax (float): maximum power = the maximum power that can be reached by the generator before losses, in kW
                Pnom (float): nominal power = the perfect power for the DG, in kW
                Pmin (float): minimum power = the power minimum that can be reached by the DG before losses, in kW
                TankCapacity (float): volume of the reservoir in L
                FuelRate (float): amount of fuel in the reservoir (0 to 1). This variable will be updated everytime the DG is used
                f_r_min (float): minimum of fuel amount before damaging the DG (0 to 1)
                lifetime (float): life expectancy of the DG in kWh for a rated use
                ReplacementCost (float): replacement cost or price in euro
                MaintenanceCost (float): maintenance cost in euro/kWh
                FuelPrice (float): fuel price in euro/L
                MinimumRuntime (float, optional): minimum runtime before it stops in hours
                cur_runtime (float, optional): current runtime (zero if off) in hours
                A (int, optional): conversion rate in L/kWh (use find_DG_coeffs to determine it). Defaults to 0.
                B (int, optional): no-load consumption in L/h (use find_DG_coeffs to determine it). Defaults to 0.
        """
        self.Pmax = paramIn['Pmax']
        self.Pnom = paramIn['Pnom']
        self.Pmin = paramIn['Pmin']
        self.TankCapacity = paramIn['TankCapacity']
        self.FuelRate = paramIn['FuelRate'] if 'FuelRate' in paramIn.keys() else 1
        self.f_r_min = paramIn['f_r_min'] if 'f_r_min' in paramIn.keys() else 0
        self.lifetime = paramIn['lifetime']
        self.ReplacementCost = paramIn['ReplacementCost']
        self.MaintenanceCost = paramIn['MaintenanceCost']
        self.FuelPrice = paramIn['FuelPrice']
        self.MinimumRuntime = paramIn['MinimumRuntime'] if 'MinimumRuntime' in paramIn.keys() else 0
        self.cur_runtime = paramIn['cur_runtime'] if 'cur_runtime' in paramIn.keys() else 0
        self.A = paramIn['A'] if 'A' in paramIn.keys() else 0
        self.B = paramIn['B'] if 'B' in paramIn.keys() else 0
        # Fuel_consumed = (A * supplied_power + B) * dt, see above for typical values of A and B
        assert(0 < self.TankCapacity)
        assert(0 <= self.Pmin <= self.Pnom <= self.Pmax)
        assert(0 <= self.f_r_min <= self.FuelRate <= 1)
        assert(0 <= self.MinimumRuntime)

    def find_DG_coeffs(self, conso_data = FuelConsoFile, perc_load: list = [0.25,0.5,0.75,1.0]) -> bool:
        """Linear regression to find coefficients of the Fuel Consumption law F_C = A * power + B (in L/h)

        Args:
            conso_data (str, optional): path of the tabular of fuel consumption reference
            perc_load (list, optional): list of the %s of nominal power applied for measures ([0.25,0.5,0.75,1.0] for the tabular from https://www.generatorsource.com/Diesel_Fuel_Consumption.aspx?).
                                        Defaults to [0.25,0.5,0.75,1.0].

        Returns:
            Bool: coeffs A and B of the DG are automatically updated, success if Result == True.
        """
        # data for linear regression to obtain the law fuel_consumption = f(power_needed)
        dg_data = pd.read_csv(conso_data) # collected from https://www.generatorsource.com/Diesel_Fuel_Consumption.aspx?
        # sample of the file :
        # Generator Size (kW)	1/4 Load (gal/hr)	1/2 Load (gal/hr)	3/4 Load (gal/hr)	Full Load (gal/hr)
        # 20	                0.6	                0.9	                1.3             	1.6

        P_ref = dg_data['Generator Size (kW)'].to_numpy()    # reference nominal power array (kW)
        conso_gal = dg_data.iloc[:,1:].to_numpy()            # reference fuel consumption array (gallon/hour)
        gallon = 3.7854
        conso_lit = conso_gal * gallon                       # convert gallon/hour in L/hour

        # print("fuel consumption reference (L/h) :\n", conso_lit)
        assert(self.Pnom >= 0)
        assert(len(conso_lit[0,:]) == len(perc_load))
        assert(len(P_ref) == len(conso_lit[:,0]))
        if P_ref[0] != 0: # adding a line for an hypothetical DG with Pnom = 0, for linear regression
            P_ref = np.concatenate(([0],P_ref))
            conso_lit = np.concatenate(([[0] * len(conso_lit[0,:])],conso_lit))

        idx = len(P_ref) - 1
        for i in range(len(P_ref) - 1):
            if P_ref[i] <= self.Pnom < P_ref[i + 1]:
                idx = i
                break
        idx = 0 if self.Pnom < P_ref[0] else idx
        # print('idx', idx, 'pnom', self.Pnom, 'pref', P_ref[0])

        if idx == len(P_ref) - 1 and abs(P_ref[-1]- P_ref[-2]) < abs(self.Pnom - P_ref[-1]):                 # huge DG
            print(f"engine too big (Pnom = {self.Pnom} >> Pmax_model = {P_ref[-1]}) The linear approx to find consumption coeffs might be badly handled,\n"
            "you must fill A and B by yourself. Typical values are A = 0.24 and B = 0.08 * Pnom.")
            return False
        elif idx == len(P_ref) - 1 and abs(self.Pnom - P_ref[-1]) <= abs(P_ref[-1]- P_ref[-2]):              # big DG
            conso_approx = conso_lit[-2,:] + (conso_lit[-1,:] - conso_lit[-2,:]) / (P_ref[-1] - P_ref[-2]) * (self.Pnom - P_ref[-2])
        elif idx ==0:                                                                           # little DG
            conso_approx = conso_lit[0,:] + (conso_lit[1,:] - conso_lit[0,:]) / (P_ref[1] - P_ref[0]) * (self.Pnom - P_ref[0])
        else :                                                                                               # normal DG
            conso_approx = conso_lit[idx,:] + (conso_lit[idx + 1,:] - conso_lit[idx,:]) / (P_ref[idx + 1] - P_ref[idx]) * (self.Pnom - P_ref[idx])
        
        self.A, self.B = np.polyfit(np.array(perc_load) * self.Pnom, conso_approx,1)
        return True
    
    def run_DG(self, power: float, dt: float, active: bool = True) -> tuple[float, float]:
        """run the DG or buy electricity to the grid according to the power needed but DOES NOT update the fuel amount in the reservoir. It has to be done afterwards.

        Args:
            power (float): the power that has to be produced
            dt (float): duration of the time step, in hours
            active (bool): if True, the DG is being used normally
                            if False, the DG is NOT being used.

        Returns:
            float: the fuel consumption at the given time step in L/h
            float: the remaining power. if negative : lack of power that has to be bought
                                        if positive : surplus of power that can be used to charge the battery stock
        """
        assert(0 <= self.f_r_min <= self.FuelRate <= 1)
        assert(0 <= self.A and 0 <= self.B)

        if not active:
            return 0,0
        
        fuel_available = (self.FuelRate - self.f_r_min) * self.TankCapacity
        P_allowed = max(self.Pmin,min(power, (fuel_available / dt - self.B) / self.A, self.Pmax))
        # print('P_allowed',round(P_allowed,3),'FuelRate', round(self.FuelRate,3), 'power', power, 'comp', fuel_available / dt - self.B)
        
        if P_allowed == power or P_allowed == self.Pmin:                                       # power demand is low
            if fuel_available / dt < self.A * max(power, self.Pmin) + self.B:                  # ... but still not enough fuel
                P_diesel_i = 0
                f_consumption = 0
                # print('diesel_use_case', 1, 'p_a', (fuel_available / dt - self.B) / self.A, 'power', power)
            else:                                                                              # ... and there is enough fuel remaining
                P_diesel_i = max(power, self.Pmin)
                f_consumption = self.A * P_diesel_i + self.B
                # print('diesel_use_case', 2, 'p_a', (fuel_available / dt - self.B) / self.A, 'power', power)
        elif P_allowed == (fuel_available / dt - self.B) / self.A:                             # fuel rate is low, DG won't start
            P_diesel_i = 0
            f_consumption = 0
            # print('diesel_use_case', 3, 'p_a', (fuel_available / dt - self.B) / self.A, 'power', power)
        else:                                                                                  # Pmax DG is restricting (P_allowed = self.Pmax)
            if self.Pmin <= P_allowed < self.Pmax:                                             # almost nominal functioning
                P_diesel_i = P_allowed
                # print('diesel_use_case', 4, 'p_a', (fuel_available / dt - self.B) / self.A, 'power', power)
            else:                                                                              # nominal functioning
                P_diesel_i = self.Pnom
                # print('diesel_use_case', 5, 'p_a', (fuel_available / dt - self.B) / self.A, 'power', power)
            f_consumption = self.A * P_diesel_i + self.B
        return f_consumption, P_diesel_i

    def use_cost(self, f_cons, power: float, P_DG: float, active: bool=True) -> float: # running the DG
        """calculates the cost of running the Diesel Generator at a given power. NB : it is not an economical cost, it is used for decision making in the costs dispatching strategy.

        Args:
            f_cons (float): fuel consumption of the DG in L/h (=dFuel_amount/dt). This value can be obtained with run_DG.
            power (float): the power that has to be produced.
            P_DG (float): the power that can be generated by the DG for the next time step in kW. This value can be obtained with run_DG.
            active (bool): if True, the DG is being used normally
                            if False, the DG is NOT being used.

        Returns:
            float: cost of running the DG in euro/kWh.
        """
        if not active:
            return np.inf
        
        fuel_available = (self.FuelRate - self.f_r_min) * self.TankCapacity
        if fuel_available == 0 or f_cons == 0 or P_DG < power:
            return 10e10
        elif 0 < self.cur_runtime < self.MinimumRuntime: # under a specific period MinimumRuntime, it is not interesting to run the DG : this line ensures the DG to run more by lowering its (virtual) running cost
            return 0
        else:
            return f_cons * self.FuelPrice / P_DG + self.ReplacementCost / self.lifetime + self.MaintenanceCost

# test section
# -----------------------------------------------------------------
if __name__=='__main__':
    print("\n --- testing the diesel generator model ---\n")

    paramIn_DG1 = {"Pmax":400,
                   "Pnom":380,
                   "Pmin":370,
                   "TankCapacity":2000,
                   "FuelRate":1,
                   "f_r_min":0.1,
                   "lifetime":200000,
                   "ReplacementCost":10000,
                   "MaintenanceCost":0.08,
                   "FuelPrice":1.5}
    
    ### find_DG_coeffs() testing
    DG_test_1 = DieselGenerator(paramIn_DG1)
    DG_test_1.find_DG_coeffs()
    P_DG_testlist = [5,20,30,40,60,75,100,125,135,150,175,200,230,250,300,350,400,500,600,750,1000,1250,1500,1750,2000,2250,2500]
    # P_DG_testlist = [5,25]
    for p in P_DG_testlist:
        DG_test_1.Pnom = p
        DG_test_1.Pmin = 0.9*p
        DG_test_1.Pmax = 1.1*p
        res = DG_test_1.find_DG_coeffs()
        print('A =', round(DG_test_1.A,4), 'B =', round(DG_test_1.B,3), 'Pnom =', DG_test_1.Pnom, 'B/Pnom ratio =', round(DG_test_1.B/DG_test_1.Pnom,3))
        assert(0.01 <= DG_test_1.B / DG_test_1.Pnom <= 0.5) # as long as I know, this should be verified for a wide range of diesel generators but maybe you have a weird DG that doesn't verify this equation.

    ### Usual functioning
    DG_test_2 = DieselGenerator(paramIn_DG1)
    DG_test_2.find_DG_coeffs()

    dt = 1 # test duration in hours
    print("dt =",dt,"hours\n")

    print("\nP_demand < Pmin ==> P_DG = Pmin")
    P_demand = DG_test_2.Pmin - 10
    fuel_conso, P_DG = DG_test_2.run_DG(P_demand, dt, True)
    DG_test_2.FuelRate -= fuel_conso * dt / DG_test_2.TankCapacity
    D5_test = DG_test_2.use_cost(fuel_conso, P_demand, P_DG)
    print('f_cons =', fuel_conso, 'f_rem =', DG_test_2.FuelRate)
    print('P_demand =', P_demand, 'P_DG =', P_DG, 'price =', D5_test)

    print("\nPmin < P_demand < Pmax ==> P_DG = P_demand")
    P_demand = (DG_test_2.Pmin + DG_test_2.Pmax) / 2
    fuel_conso, P_DG = DG_test_2.run_DG(P_demand, dt, True)
    DG_test_2.FuelRate -= fuel_conso * dt / DG_test_2.TankCapacity
    D5_test = DG_test_2.use_cost(fuel_conso, P_demand, P_DG)
    print('f_cons =', fuel_conso, 'f_rem =', DG_test_2.FuelRate)
    print('P_demand =', P_demand, 'P_DG =', P_DG, 'price =', D5_test)

    print("\nPmax < P_demand ==> P_DG = Pmax")
    P_demand = DG_test_2.Pmax + 10
    fuel_conso, P_DG = DG_test_2.run_DG(P_demand, dt, True)
    DG_test_2.FuelRate -= fuel_conso * dt / DG_test_2.TankCapacity
    D5_test = DG_test_2.use_cost(fuel_conso, P_demand, P_DG)
    print('f_cons =', fuel_conso, 'f_rem =', DG_test_2.FuelRate)
    print('P_demand =', P_demand, 'P_DG =', P_DG, 'price =', D5_test)

    ### No fuel remaining
    paramIn_DG1['FuelRate'] = paramIn_DG1['f_r_min']
    DG_test_3 = DieselGenerator(paramIn_DG1)
    DG_test_3.find_DG_coeffs()

    print("\nno fuel remaining")
    P_demand = DG_test_3.Pnom
    fuel_conso, P_DG = DG_test_3.run_DG(P_demand, dt, True) # P_demand kW for 1h
    D5_test = DG_test_2.use_cost(fuel_conso, P_demand, P_DG)
    print('f_cons =', fuel_conso, 'f_rem =', DG_test_3.FuelRate - fuel_conso * dt / DG_test_3.TankCapacity)
    print('P_demand =', P_demand, 'P_DG =', P_DG, 'price =', D5_test)
# %%