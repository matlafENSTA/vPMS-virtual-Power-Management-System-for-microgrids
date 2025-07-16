# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:42:37
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: Grid definition (costs and schedule) + buy and sell functions + test section.
'''
#---------------------
#%%
import os
import numpy as np
import pandas as pd

class Grid:
    GridPricesRef = os.path.join(os.path.dirname(os.path.realpath(__file__)),"DataBase","GridPrices.csv")
    GridScheduleRef = os.path.join(os.path.dirname(os.path.realpath(__file__)),"DataBase","GridSchedule.csv")
    
    def __init__(self, state: pd.DataFrame, prices: pd.DataFrame, schedule: pd.DataFrame):
        """grid definition

        Args:
            state (pd.DataFrame): time serie of the grid state : 0 if cut-off, 1 if normal. has the same lenght as every other time serie. works with type=list too.
            prices (pd.DataFrame): price scale table of the grid (4*3 array)
            schedule (pd.DataFrame): grid schedule table. rows = hours, columns = months and values in {1,2,3} representing the price peridos of the grid in the year
                                     example : schedule[1,2] = 3 means that at midnight ('1') in february ('2'), it is a peak hour for electricity ('3')
        """
        self.state = state
        self.prices = prices
        self.schedule = schedule
    
    def sale_cost(self, time_array: np.array, time_step: int) -> float: # selling to the grid
        """finds the benefit of energy selling in euro/kWh. NB : it is not an economical cost, it is used for decision making in the costs dispatching strategy.

        Args:
            time_array (np.array): measurement time for all results.
            time_step (int): index of the for loop

        Returns:
            float: benefit of energy selling in euro/kWh (0 <= c < +inf)
        """
        if self.state[time_step] == 0: # the grid is cut-off
            return 0
        else :
            price_zone = self.schedule.iloc[time_array[time_step].hour, time_array[time_step].month] # off-peak ? medium power ? peak hour ?
            # print("price_zone", price_zone)
            return self.prices["Selling price (euros/kWh)"][price_zone] # matching price
    
    def purchase_cost(self, time_array: np.array, time_step: int) -> float: # purchasing from the grid
        """finds the cost of purchasing electricity from the grid at the given time. NB : it is not an economical cost, it is used for decision making in the costs dispatching strategy.

        Args:
            time_array (list or np.array): list or np.array representing the measurement time for all results.
            time_step (int): index of the for loop

        Returns:
            float: cost of energy purchasing in euro/kWh (0 <= c <= +inf)
        """
        if self.state[time_step] == 0: # the grid is cut-off
            return np.inf
        else:
            # print('date =', time_array[time_step], 'hour =', time_array[time_step].hour + 1, 'month =', time_array[time_step].month)
            price_zone = self.schedule.iloc[time_array[time_step].hour, time_array[time_step].month] # off-peak ? medium power ? peak hour ?
            # print("price_zone", price_zone)
            return self.prices["Buying price (euros/kWh)"][price_zone] # matching price

# test section
# -----------------------------------------------------------------
if __name__=='__main__':
    from datetime import datetime, timedelta
    import numpy as np
    
    print(" --- testing the grid model ---\n")
    print("NB : run BatteryStock to compare battery and grid costs\n")
    dt = 1 # sampling period in hours
    start_date = datetime(2025, 1, 1)
    num_steps = int(20 / dt) # 20 hours
    time = np.array([start_date + timedelta(hours=i * dt) for i in range(20)])

    GridPrices = pd.read_csv(Grid.GridPricesRef).set_index('Id')
    GridSchedule = pd.read_csv(Grid.GridScheduleRef)
    GridState = np.array([1] * (num_steps - num_steps//2) + [0] * (num_steps//2), dtype=np.int64)  # grid reliable or not at t
    GridTest = Grid(GridState, GridPrices, GridSchedule)

    print("state :\n",GridTest.state)
    print("\nprices :\n",GridTest.prices)
    print("\nschedule :\n",GridTest.schedule)

    print("\ngrid connected")
    D1_test = GridTest.sale_cost(time, 5)
    D3_test = GridTest.purchase_cost(time, 5)
    print('selling price =', D1_test, 'euros/kWh\nbuying price =', D3_test, 'euros/kWh')

    print("\ngrid disconnected")
    D1_test = GridTest.sale_cost(time, 15)
    D3_test = GridTest.purchase_cost(time, 15)
    print('selling price =', D1_test, 'euros/kWh\nbuying price =', D3_test, 'euros/kWh')
# %%
