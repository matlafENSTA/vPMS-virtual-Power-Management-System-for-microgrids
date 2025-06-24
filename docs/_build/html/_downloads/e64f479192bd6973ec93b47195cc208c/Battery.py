# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:39:23
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Single battery definition. Includes charge and discharge routines, and test section.
'''
#---------------------
#%%

class Battery:
    def __init__(self,paramIn):
        """battery definition. NB : the energy efficiency eta is only takin into account during the discharge process.

        Args:
            paramIn (dict): contains the following parameters
                capacity (float): storage capacity (kWh)
                SOC (float): (initial) state of charge (0 to 1)
                SOCmin (float): minimum state of charge (0 to 1)
                SOCmax (float): maximum state of charge (0 to 1)
                eta (float): energy efficiency (0 to 1)
                Pmax_ch (float): maximum power allowed during charge (kW)
                Pmax_disch (float): maximum power allowed during discharge (kW)
                lifetime (float): life expectancy of the battery (kWh) (= lifetime in number of cycles * capacity * (SOCmax - SOCmin))
                ReplacementCost (float): replacement cost or price (euros)
                MaintenanceCost (float): maintenance cost (euros/kWh)
            """
        self.capacity = paramIn['capacity']
        self.SOC = paramIn['SOC']
        self.SOCmin = paramIn['SOCmin']
        self.SOCmax = paramIn['SOCmax']
        self.eta = paramIn['eta']
        self.Pmax_ch = paramIn['Pmax_ch']
        self.Pmax_disch = paramIn['Pmax_disch']
        self.lifetime = paramIn['lifetime']
        self.ReplacementCost = paramIn['ReplacementCost']
        self.MaintenanceCost = paramIn['MaintenanceCost']

        assert(self.SOCmin <= self.SOC <= self.SOCmax)
        assert(0 <= self.eta <=1)

    def battery_charge(self, power: float, dt: float) -> float:
        """simulates the charge of a battery. SOC is updated within.

        Args:
            power (float): excess power from the microgrid (>0, in kW)
            dt (float): charging time (= 1 time step), in hours

        Returns:
            float: the power actually used to charge the battery, in kW
        """
        assert(power>=0)
        if self.SOC == self.SOCmax: # battery already full
            P_ch = 0
        else :
            e_needed = (self.SOCmax - self.SOC) * self.capacity # energy needed to fully charge the battery
            P_ch = min(power, self.Pmax_ch, e_needed / dt) # charging power
            
            self.SOC += P_ch * dt / self.capacity
            self.SOC = max(min(self.SOC, self.SOCmax),self.SOCmin)
        return P_ch

    def battery_discharge(self,power: float,dt: float) -> float:
        """simulates the discharge of a battery. SOC is updated within

        Args:
            power (float): power deficit needed by the microgrid (>0, in kW)
            dt (float): discharging time (= 1 time step), in hours

        Returns:
            float: power supplied by the battery, in kW
        """
        assert(power>=0)
        if self.SOC==self.SOCmin: # battery won't discharge
            P_disch = 0
        else :
            e_available = (self.SOC - self.SOCmin) * self.capacity * self.eta # energy remaining and usable
            P_disch = min(power, self.Pmax_disch, e_available / dt) # discharging power knowing the constraints
            
            self.SOC -= P_disch * dt / self.capacity / self.eta
            self.SOC = round(min(max(self.SOC, self.SOCmin),self.SOCmax),14)
            # print('P_disch_bat',P_disch)
            # print(' - e_lost =', P_disch * dt * (1 - self.eta), 'Wh (because of the energy efficiency eta)')
        return P_disch

# test section
# -----------------------------------------------------------------
if __name__=="__main__":
    print("\n --- testing the battery model ---\n")

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

    # NB : see grid section for cost function tests
    battery_test = Battery(paramIn_batt)
    initial_SOC = battery_test.SOC
    dt = 1 # test duration in hours
    print("dt =",dt,"hours\n")

    print("energy efficiency test with one charge - discharge cycle for", [name for name in globals() if globals()[name] is battery_test][0])
    print('initial SOC =',round(battery_test.SOC,3))

    print('power supply < Pmax_ch and power demand < Pmax_disch')
    P_charge_demand, P_disch_demand = 0.5 * battery_test.Pmax_ch, 0.5 * battery_test.Pmax_ch * battery_test.eta
    P_charge_real = battery_test.battery_charge(P_charge_demand, dt)
    print('power supply =',P_charge_demand,' battery charging power   =',P_charge_real,' charged SOC    =',round(battery_test.SOC,3))
    P_disch_real = battery_test.battery_discharge(P_disch_demand, dt)
    print('power demand =',P_disch_demand,' battery discharging power =', P_disch_real,' discharged SOC =',round(battery_test.SOC,3), '\n')
    assert(battery_test.SOC == initial_SOC)
    assert(P_charge_real == P_charge_demand and P_disch_real == P_disch_demand)

    print('power supply = 0 and power demand = 0')
    P_charge_demand, P_disch_demand = 0, 0
    battery_test.SOC = initial_SOC
    P_charge_real = battery_test.battery_charge(P_charge_demand, dt)
    print('power supply =',P_charge_demand,' battery charging power   =',P_charge_real,' charged SOC    =',round(battery_test.SOC,3))
    P_disch_real = battery_test.battery_discharge(P_disch_demand, dt)
    print('power demand =',P_disch_demand,' battery discharging power =', P_disch_real,' discharged SOC =',round(battery_test.SOC,3), '\n')
    assert(battery_test.SOC == initial_SOC)
    assert(P_charge_real == P_charge_demand and P_disch_real == P_disch_demand)

    print('power supply > Pmax_ch and power demand > Pmax_disch')
    P_charge_demand, P_disch_demand = 1.5 * battery_test.Pmax_ch, 1.5 * battery_test.Pmax_ch
    battery_test.SOC = initial_SOC
    P_charge_real = battery_test.battery_charge(P_charge_demand, dt)
    print('power supply =',P_charge_demand,' battery charging power   =',P_charge_real,' charged SOC    =',round(battery_test.SOC,3))
    P_disch_real = battery_test.battery_discharge(P_disch_demand, dt)
    print('power demand =',P_disch_demand,' battery discharging power =', P_disch_real,' discharged SOC =',round(battery_test.SOC,3), '\n')
    assert(battery_test.SOC != initial_SOC)
    assert(P_charge_real < P_charge_demand and P_disch_real < P_disch_demand)
# %%
