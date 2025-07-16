# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:50:48
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: This library was made for manipulating time series.

    it includes the following operations :

    - plot a dictionnary of array-like elements on the same graph or on different graphs on the same fig (.png) : plot_on_same_graph() and png_graphs()
    - save dictionaries or array-like elements within a tabular (.csv) : save_dict_to_csv()
    - adjust and make constant the sampling period of a time serie : adjust_time_serie()
    - typical behavior of a period : you have 10 years of data and you want to vizualise it on one averaged-year data ? calculate_typical_behavior()
    - comparison of time series : relative_error()
'''
#---------------------
# %%
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) # add the entire module to python path

from virtualPMS import Battery, BatteryStock, DieselGenerator

import pickle
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

def generalized_func(abs_array,ord_array,x): # unused
    '''
    PURPOSE :
        given 2 lists reprenting a function and an abscissa x, evaluate f(x) by joining linearly every point of the function.
    INPUT :
        :abs_array: np.array of shape (1,n). sorted list of abscissas we have values for the function
        :ord_array: np.array of shape (1,n). list of values taken by the function at the abs_array points
        :x: point you want the function to be evaluated
    OUTPUT :
        :f(x): where f is the piecewise linear function represented by abs_array and ord_array'''
    assert(len(abs_array)==len(ord_array))

    if abs_array[-1] < x:
        print("!! the value you are trying to reach is not in the definition domain of the function !! (lower than the first element)")
        return -9999
    elif x < abs_array[0]:
        print("!! the value you are trying to reach is not in the definition domain of the function !! (higher than the last element)")
        return -9999
    else: # linear approximation f(x) = ax+b between abs_array[i] and abs_array[i+1]
        for i in range(len(abs_array)-1):
            if abs_array[i]<=x and x<=abs_array[i+1]:
                index = i
                break
        a = (ord_array[index+1]-ord_array[index])/(abs_array[index+1]-abs_array[index])
        b = ord_array[index]-abs_array[index]*a
        return a*x+b

def adjust_time_serie(time,results,fixed_sampling_period): # unused
    '''
    PURPOSE :
        sort out a time serie by fixing its sampling period.
    INPUT :
        :results: pd.DataFrameionnary of arrays of size (1,n). it represents time series of same sampling rate, constant.
        :fixed_sampling_period: float. if the sampling period of the result is variable, 
                                it will be approached by a fixed sampling period time serie using the linear estimation implemented in generalized_func().
    OUTPUT :
        :formatted_results: time serie representing the same data than the input 'results' but with fixed sampling period
    '''
    # Initialize dictionary to store the formatted results
    formatted_results = {key: [] for key in results.keys()}

    for data in results.keys():
        nb_samples = len(results[data])//fixed_sampling_period
        for i in range(nb_samples):
            formatted_results[data].append(generalized_func(time,results[data],time[0]+i*fixed_sampling_period))
            if formatted_results[data][-1] == -9999:
                print('!! data not found for',data,len(formatted_results[data]),sep=' ')
        
        # in order not to loose the last value of the results, we copy it in the end of the formatted time serie
        if len(data)%fixed_sampling_period != 0:
            formatted_results[data].append(results[data][-1])
        print(data,formatted_results[data][:10])
    return formatted_results

def calculate_typical_behavior(formatted_results,sample_lenght): # unused
    '''
    INPUT :
        :formatted_results: time serie with fixed sampling period.
        :sample_lenght: int. typically 24 if you want hourly value over a representative day, or 365 if you want daily value over a representative year.
                          ! be consistent with the sampling_period !
    OUTPUT :
        :period_results: dictionnary of arrays of size (1,n). Typical behavior of the time serie over the chosen period, for a given sample lenght.
    '''
    # Initialize dictionary to store the averaged results
    period_results = {key: [] for key in formatted_results.keys()}

    # Calculate the average behavior for each hour of the day over the period
    for key in formatted_results.keys():
        # Split the data into two periods
        period_data = formatted_results[key]

        # Group the data by congruency modulo sample_lenght and calculate the mean for each group
        period_avg = np.array([np.mean(period_data[i::sample_lenght]) for i in range(sample_lenght)])

        # Store the result of each variable
        period_results[key] = period_avg

    return period_results

def plot_separately(dfResults : pd.DataFrame, plot_name: str,csv: bool=False,png: bool=False,pkl: bool=False,plot: bool=False):
    """Quickly plot a bunch of time series on one PNG file with an elongated layout.
       Saves the figure into a png file showing all graphs with a long horizontal format.

    Args:
        dfResults (pd.DataFrame): DataFrame containing time series
                                  mandatory: contains 'TimeArray', the time vector.
        plot_name (str): name of the output file (without extension)
        csv (bool, optional): if True, saves the time series under output//*plot_name*.csv. Defaults to False.
        png (bool, optional): if True, saves the figure under output//*plot_name*.png. Defaults to False.
        pkl (bool, optional): if True, saves the figure under output//*plot_name*.pkl. This file can be read by pkl_plot. Defaults to False.
        plot (bool, optional): if True, shows the figure. Defaults to False.
    """
    TS_len = dfResults.shape[0] # lenght of the time series

    nb_fig = dfResults.shape[1]
    nb_cols = max(2, min(3, nb_fig // 4))  # 2 <= nb_cols <= 3
    nb_rows = (nb_fig + nb_cols - 1) // nb_cols  # Compute required rows

    fig, axes = plt.subplots(nb_rows, nb_cols, figsize=(6 * nb_cols, 3 * nb_rows))
    axes = np.array(axes).reshape(-1)  # Flatten for easy indexing

    colors = ['green', 'red', 'blue', 'orange', 'purple', 'grey', 'pink']
    
    for i, (name, data) in enumerate(dfResults.items()):
        if name != "TimeArray":
            ax = axes[i]
            ax.plot(dfResults["TimeArray"], data, label=name, color=colors[i % len(colors)])
            ax.axhline(0, color='black', linewidth=0.2)  # Add y=0 axis
            ax.set_xlim(dfResults["TimeArray"].head(1), dfResults["TimeArray"][TS_len-1])
            ax.set_title(f'{name} over time')
            ax.set_ylabel(name)
            ax.legend()
            ax.grid(True)

            # Format X-axis to avoid overlap
            # ax.xaxis.set_major_locator(mdates.AutoDateLocator())  # Auto-ajuste les ticks
            # ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Formatte les dates
            # plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")  # Rotation pour lisibilite
            ax.tick_params(axis='x', rotation=30)
        
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])     # Hide unused subplots

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.5, wspace=0.3)  # Adjust spacing

    if csv:
        dfResults = pd.DataFrame(dfResults)
        dfResults.to_csv(plot_name + '.csv')
    if png:
        plt.savefig(plot_name + '.png', bbox_inches='tight')  # Save with reduced empty space
    if pkl:
        with open(plot_name + ".pkl", "wb") as f:
            pickle.dump(fig, f)        
    if plot:
        plt.show()

def plot_compact(dfResults : pd.DataFrame, plot_name: str,csv: bool=False,png: bool=False,pkl: bool=False,plot: bool=False):
    """Especially created for showing important time series generated by handmade PMSs LFE_CCE_emergency_system.py, LFE_CCE_self_sufficiency.py and cost_strat.py

    Args:
        dfResults (pd.DataFrame): DataFrame with keys like 'SOC', 'P_L', 'P_green', etc.
                                  mandatory: contains 'TimeArray', the time vector.
        plot_name (str): name of the output file (without extension)
        csv (bool, optional): if True, saves the time series under output//*plot_name*.csv. Defaults to False.
        png (bool, optional): if True, saves the figure under output//*plot_name*.png. Defaults to False.
        pkl (bool, optional): if True, saves the figure under output//*plot_name*.pkl. This file can be read by pkl_plot. Defaults to False.
        plot (bool, optional): if True, shows the figure. Defaults to False.
    """
    plt.close('all') # cleaning of previous plots

    TS_len = len(dfResults["TimeArray"]) # lenght of the time series

    fig, axes = plt.subplots(2, 2, figsize=(20, 6))
    #                               width --^   ^-- height
    axes = axes.flatten()

    # 1. Load and Renewable Energy Production
    if 'P_green' in dfResults.keys():
        axes[0].plot(dfResults["TimeArray"], dfResults['P_green'], label='greenpower', color='green')
    if 'P_L' in dfResults.keys():
        axes[0].plot(dfResults["TimeArray"], dfResults['P_L'], label='input loadpower', color='purple', alpha=0.8)
    if 'P_L_modif' in dfResults.keys():
        axes[0].plot(dfResults["TimeArray"], dfResults['P_L_modif'], label='clipped loadpower', color='red', alpha=0.5)
    axes[0].set_xlim(dfResults["TimeArray"].head(1), dfResults["TimeArray"][TS_len-1])
    axes[0].set_title('Load Demand and Renewable Power')
    axes[0].set_ylabel('power (kW)')
    # axes[0].set_xlabel('time')
    axes[0].legend()
    axes[0].grid(True)
    axes[0].axhline(0, color='black', linewidth=0.5)  # Add y=0 axis
    axes[0].tick_params(axis='x', rotation=15)

    # 3. Controllable Power Supply
    if 'P_grid' in dfResults.keys():
        axes[1].plot(dfResults["TimeArray"], dfResults['P_grid'], label='Grid', color='blue')
    if 'P_bat' in dfResults.keys():
        axes[1].plot(dfResults["TimeArray"], dfResults['P_bat'], label='Battery', color='green', alpha=0.7)
    if 'P_diesel' in dfResults.keys():
        axes[1].plot(dfResults["TimeArray"], dfResults['P_diesel'], label='Diesel', color='red', alpha=0.6)
    axes[1].set_xlim(dfResults["TimeArray"].head(1), dfResults["TimeArray"][TS_len-1])
    axes[1].set_title('Controllable Power Supply')
    # axes[1].set_xlabel('time')
    axes[1].set_ylabel('power (kW)')
    axes[1].legend()
    axes[1].grid(True)
    axes[1].axhline(0, color='black', linewidth=0.5)  # Add y=0 axis
    axes[1].tick_params(axis='x', rotation=15)

    # 2. Power Deltas
    if 'P_net_modif' in dfResults.keys():
        axes[2].plot(dfResults["TimeArray"], dfResults['P_net_modif'], label='P_net_modif = P_green - P_L_modif', color='blue')
    if 'P_resistor' in dfResults.keys():
        axes[2].plot(dfResults["TimeArray"], dfResults['P_resistor'], label='P_resistor', color='orange', alpha=0.7)
    axes[2].set_xlim(dfResults["TimeArray"].head(1), dfResults["TimeArray"][TS_len-1])
    axes[2].set_title('Excess And Deficit Power')
    # axes[2].set_xlabel('time')
    axes[2].set_ylabel('power (kW)')
    axes[2].legend()
    axes[2].grid(True)
    axes[2].axhline(0, color='black', linewidth=0.5)  # Add y=0 axis
    axes[2].tick_params(axis='x', rotation=15)

    # 4. SOC and Fuel Amount
    if 'SOC' in dfResults.keys():
        axes[3].plot(dfResults["TimeArray"], dfResults['SOC'], label='overall SOC', color='green')
    if 'F_C' in dfResults.keys():
        axes[3].plot(dfResults["TimeArray"], dfResults['F_C'], label='fuel tank', color='red')
    axes[3].set_xlim(dfResults["TimeArray"].head(1), dfResults["TimeArray"][TS_len-1])
    axes[3].set_title('State Of Charge (SOC) of batteries (%) and Fuel Rate (%)')
    # axes[3].set_xlabel('time')
    axes[3].set_ylabel('SOC, Fuel Rate')
    axes[3].legend()
    axes[3].grid(True)
    axes[3].axhline(0, color='black', linewidth=0.5)  # Add y=0 axis
    axes[3].tick_params(axis='x', rotation=15)

    # # 5 & 6 : Empty → optionally hide them
    # for ax in axes[4:]:
    #     fig.delaxes(ax)

    plt.tight_layout()

    if csv:
        dfResults = pd.DataFrame(dfResults)
        dfResults.to_csv(plot_name + '.csv')
    if png:
        plt.savefig(plot_name + '.png', bbox_inches='tight')  # Save with reduced empty space
    if pkl:
        with open(plot_name + ".pkl", "wb") as f:
            pickle.dump(fig, f)        
    if plot:
        plt.show()

def plot_group(dfResults : pd.DataFrame, plot_name: str, title: str = '',csv: bool=False,png: bool=False,pkl: bool=False,plot: bool=False):
    """Plot multiple time series on the same graph with a common time axis.

    Args:
        dfResults (pd.DataFrame): DataFrame of time series
                                  mandatory: contains 'TimeArray', the time vector.
        plot_name (str): name of the output file (without extension)
        title (str, optional): title of the graph. Defaults to '' for no title.
        csv (bool, optional): if True, saves the time series under *plot_name*.csv. Defaults to False.
        png (bool, optional): if True, saves the figure under *plot_name*.png. Defaults to False.
        pkl (bool, optional): if True, saves the figure under *plot_name*.pkl. This file can be read by pkl_plot. Defaults to False.
        plot (bool, optional): if True, shows the figure. Defaults to False.
    """
    fig = plt.figure(figsize=(10, 5))  # Set figure size for better visibility
    
    colors = ['black','blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray']

    for i, dataset in enumerate(dfResults.keys()):
        if dataset != "TimeArray":
            plt.plot(dfResults["TimeArray"], dfResults[dataset], label=dataset, color=colors[i % len(colors)], linewidth=1, alpha=1 - 0.5 * i / len(dfResults.keys()))

    plt.axhline(0, color='black', linestyle='--', linewidth=1)  # Add y=0 axis
    plt.xlabel('time')
    plt.tick_params(axis='x', rotation=30)

    if title != '':
        plt.title(title)
    else:
        plt.title(plot_name + ' over time')
    plt.legend()
    plt.grid(True)
    
    if csv:
        dfResults = pd.DataFrame(dfResults)
        dfResults.to_csv(plot_name + '.csv')
    if png:
        plt.savefig(plot_name + '.png', bbox_inches='tight')  # Save with reduced empty space
    if pkl:
        with open(plot_name + ".pkl", "wb") as f:
            pickle.dump(fig, f)        
    if plot:
        plt.show()

def relative_error(TimeArray: np.ndarray, f_values: np.ndarray, g_values: np.ndarray, p: int = 2, method: str = 'reference_f', plot: bool = False, png_name: str = "") -> tuple[float, dict]:
    """Calculates the relative difference between two functions of time f and g, using the Lp norm (p can be defined precisely)

    Args:
        TimeArray (np.ndarray): time list (np.array of datetime objects)
        f_values (np.ndarray): values taken by f at every time step
        g_values (np.ndarray): values taken by g at every time step
        p (int, optional): Lp norm parameter (power): 0 < p <= inf. Defaults to 2.
        method (str, optional): Calculation method of relative difference. Defaults to 'reference_f'.
                                'reference_f': |f-g|p / |f|p (f est la reference)
                                'reference_g': |f-g|p / |g|p (g est la reference)
                                'maximum': |f-g|p / max(|f|p, |g|p)
                                'average': |f-g|p / ((|f|p + |g|p)/2)
        plot (bool, optional): if True, a graph will be shown with both functions and their difference. Defaults to False.
        png_name (str, optional): if not "", graphs will be generated and saved under this name (NB: does not include the .png mention). Defaults to "".

    Returns:
        Tuple[float, dict]: Tuple containing the relative difference obtained with the chosen method plus intermediate results.
    """
    # Verification des dimensions
    if len(TimeArray) != len(f_values) or len(TimeArray) != len(g_values):
        raise ValueError("Les tableaux TimeArray, f_values et g_values doivent avoir la même taille")
    
    # nettoyage des precedents plots
    plt.close('all')

    # Conversion des datetimes en heures depuis le premier point pour l'integration
    if isinstance(TimeArray[0], datetime):
        time_hours = np.array([(t - TimeArray[0]).total_seconds() / 3600 for t in TimeArray])
    else:
        time_hours = TimeArray  # Supposer que c'est deja dans un format numerique
    
    # Calcul de la difference
    diff = np.abs(f_values - g_values)
    
    # Calcul des normes Lp
    if p == float('inf'):
        # Norme L∞ (norme uniforme)
        norm_diff = np.max(diff)
        norm_f = np.max(np.abs(f_values))
        norm_g = np.max(np.abs(g_values))
    else:
        # Pour les autres normes Lp, nous utilisons l'integration numerique (methode des trapezes)
        diff_power_p = diff**p
        f_power_p = np.abs(f_values)**p
        g_power_p = np.abs(g_values)**p
        
        # Integration
        integral_diff = np.trapz(diff_power_p, time_hours)
        integral_f = np.trapz(f_power_p, time_hours)
        integral_g = np.trapz(g_power_p, time_hours)
        
        # Normes Lp
        norm_diff = integral_diff**(1/p)
        norm_f = integral_f**(1/p)
        norm_g = integral_g**(1/p)
    
    # Calcul de l'ecart relatif selon la methode choisie
    if method == 'reference_f':
        if norm_f == 0:
            rel_error = float('inf') if norm_diff > 0 else 0
        else:
            rel_error = norm_diff / norm_f
    elif method == 'reference_g':
        if norm_g == 0:
            rel_error = float('inf') if norm_diff > 0 else 0
        else:
            rel_error = norm_diff / norm_g
    elif method == 'maximum':
        max_norm = max(norm_f, norm_g)
        if max_norm == 0:
            rel_error = float('inf') if norm_diff > 0 else 0
        else:
            rel_error = norm_diff / max_norm
    elif method == 'average':
        avg_norm = (norm_f + norm_g) / 2
        if avg_norm == 0:
            rel_error = float('inf') if norm_diff > 0 else 0
        else:
            rel_error = norm_diff / avg_norm
    else:
        raise ValueError("Methode invalide. Choisissez 'reference_f', 'reference_g', 'maximum' ou 'average'")
    
    # Creation des graphiques
    plt.figure(figsize=(12, 8))
    
    # Sous-graphique pour les fonctions
    plt.subplot(2, 1, 1)
    plt.plot(TimeArray, f_values, 'b-', label='f_HOMER')
    plt.plot(TimeArray, g_values, 'r--', label='g_myPMS', alpha=0.7)
    plt.legend()
    plt.title(f'Comparaison des fonctions')
    plt.grid(True)
    
    # Sous-graphique pour la difference
    plt.subplot(2, 1, 2)
    plt.plot(TimeArray, diff, 'g-', label='|f-g|')
    plt.legend()
    plt.title(f'Difference absolue |f-g|')
    plt.grid(True)
    
    plt.tight_layout()
    if plot:
        plt.show()
    if png_name != "":
        plt.savefig(png_name, bbox_inches='tight')
    
    # Renvoyer l'ecart relatif et les normes intermediaires
    return rel_error, {
        'norm_diff': norm_diff,
        'norm_f': norm_f,
        'norm_g': norm_g,
        'p': p,
        'method': method
    }

def VerifTimeSeries(dfResults: pd.DataFrame, ActiveDevices : dict, BattStock: BatteryStock, DG_1: DieselGenerator):
    """Make sure the results have the good format and that they are technically correct (fuel rate > fuel rate min, P_balance = 0 for energy conservation...) .
    
    Args:
        dfResults (pd.DataFrame) : every time series generated by the chosen dispatching strategy (stands for DataFrame_TimeSeries)
        ActiveDevices (dict): {"Grid": True/False, "Batteries": True/False, "DieselGenerator": True/False} : type True for using the device, False to disable it.
        BattStock (BatteryStock) : the battery stock used during simulation
        DG_1 (DieselGenerator) : the diesel generator used during simulation
    """
    dt = (dfResults["TimeArray"][1] - dfResults["TimeArray"][0]).total_seconds() / 3600 # duration of a time step in hours
    # print(len(dfResults["P_green"]),len(dfResults["P_L"]),len(dfResults["P_resistor"]),len(dfResults["P_L_modif"]))
    # print(len(dfResults["TimeArray"]),len(dfResults["P_diff"]),len(dfResults["P_diesel"]),len(dfResults["P_bat"]),len(dfResults["SOC"]),len(dfResults["F_C"]),len(indic),len(P_net),len(grid_state))
    TA_len = len(dfResults["TimeArray"])
    assert(TA_len==len(dfResults["P_green"])==len(dfResults["P_L_modif"])==len(dfResults["P_resistor"])==len(dfResults["P_diff"]))
     
    P_balance = dfResults["P_green"] - dfResults["P_L_modif"] - dfResults["P_resistor"] # validation of energy conservation
    
    if ActiveDevices["Batteries"]:
        assert(TA_len==len(dfResults["P_bat"]))
        assert(len(dfResults["SOC"][dfResults["SOC"] < BattStock.get_SOC('min') - 10**(-14)]) == 0)
        P_balance += dfResults["P_bat"]
    if ActiveDevices["DieselGenerator"]:
        assert(TA_len==len(dfResults["P_diesel"]))
        assert(len(dfResults["P_diesel"][dfResults["P_diesel"] < -10**(-14)]) == 0)
        assert(len(dfResults["F_C"][dfResults["F_C"] < DG_1.f_r_min - 10**(-14)]) == 0)
        P_balance += dfResults["P_diesel"]
    if ActiveDevices["Grid"]:
        assert(TA_len==len(dfResults["P_grid"]))
        P_balance += dfResults["P_grid"]

    if "GridSaleCost_list" in dfResults.keys() and "BatteryChargeCost_list" in dfResults.keys() and "GridPurchaseCost_list" in dfResults.keys() and "BatteryDischargeCost_list" in dfResults.keys() and "DGUseCost_list" in dfResults.keys():
        assert(TA_len==len(dfResults["GridSaleCost_list"])==len(dfResults["BatteryChargeCost_list"])==len(dfResults["GridPurchaseCost_list"])==len(dfResults["BatteryDischargeCost_list"])==len(dfResults["DGUseCost_list"]))

    assert(len(dfResults["P_L_modif"][dfResults["P_L_modif"] < -10**(-14)]) == 0) # Load is positive
    assert(len(dfResults["P_resistor"][dfResults["P_resistor"] < -10**(-14)]) == 0) # Excess Power is positive

    e_balance = round(np.trapz(np.abs(P_balance), x=None, dx=dt),10)
    print('e_balance    =', e_balance,'\n')
    assert(e_balance <= len(P_balance) * 10**(-14)) # P_balance has to be the zero function so its integral is near the machine approx

def EnergySums(dfResults: pd.DataFrame, DG_1: DieselGenerator) -> pd.DataFrame:
    """Calculates energy variables over the given period by integration of Power time series.
    
    Args:
        dfResults (pd.DataFrame): every time series generated by the chosen dispatching strategy (stands for DataFrame_TimeSeries)
        DG_1 (DieselGenerator): the diesel generator used during simulation
    
    Returns:
        pd.DataFrame: energy and fuel consumption.
    """
    TS_len = len(dfResults["TimeArray"])
    dt = (dfResults["TimeArray"][1] - dfResults["TimeArray"][0]).total_seconds() / 3600 # duration of a time step in hours

    if "P_L" in dfResults.keys():
        e_load = round(np.trapz(dfResults["P_L"], x=None, dx=dt),5)                                              # energy consumed (kWh)
        print('e_load    =', e_load,'kWh')
    else:
        e_load = 'NotFound'
    if "P_green" in dfResults.keys():
        e_green = round(np.trapz(dfResults["P_green"], x=None, dx=dt),5)                                         # renewable energy produced (kWh)
        print('e_green   =', e_green,'kWh')
    else:
        e_green = 'NotFound'
    if "P_grid" in dfResults.keys():
        e_sold = round(np.trapz(np.array([max(0, - pow) for pow in dfResults["P_grid"]]), x=None, dx=dt),5)      # energy sold during the simulation (kWh)
        e_bought = round(np.trapz(np.array([max(0,pow) for pow in dfResults["P_grid"]]), x=None, dx=dt),5)       # energy bought (kWh)
        print('e_sold    =', e_sold, 'kWh')
        print('e_bought  =', e_bought,'kWh')
    else:
        e_sold, e_bought = 'NotFound', 'NotFound'
    if "P_diff" in dfResults.keys():
        e_lack = round(np.trapz(np.array([max(0,-pow) for pow in dfResults["P_diff"]]), x=None, dx=dt),5)        # energy that was needed but couldn't be produced neither bought (kWh)
        print('e_lack    =', e_lack,'kWh')
    else:
        e_lack = 'NotFound'
    if "P_resistor" in dfResults.keys():
        e_unused = round(np.trapz(dfResults["P_resistor"], x=None, dx=dt),5)                                     # energy that couldn't be used neither sold (kWh)
        print('e_unused  =', e_unused,'kWh')
    else:
        e_unused = 'NotFound'
    if "P_bat" in dfResults.keys():
        e_bat = round(np.trapz(np.array([max(0,pow) for pow in dfResults["P_bat"]]), x=None, dx=dt),5)           # energy supplied by batteries (kWh)
        print('e_bat     =', e_bat,'kWh')
    else:
        e_bat = 'NotFound'
    if "P_diesel" in dfResults.keys():
        e_diesel = round(np.trapz(dfResults["P_diesel"], x=None, dx=dt),5)                                       # energy produced by the DG (kWh)
        print('e_diesel  =', e_diesel,'kWh')
    else:
        e_diesel = 'NotFound'
    try:
        fuel_conso = round((dfResults["F_C"][0] - dfResults["F_C"][TS_len-1]) * DG_1.TankCapacity,5)                    # total amount of fuel consumed during the simulation (L)
        print('fuel_cons =', str(fuel_conso),'L')
    except:
        fuel_conso = 'NotFound'
        
    dfEnergy = pd.DataFrame({"var"  :["Load Conso","Renewable Prod","Sales","Purchases","Lack","Unused","Battery Supply","Diesel","Fuel Consumed"],
                             "value":[e_load,      e_green,         e_sold, e_bought,   e_lack,e_unused,e_bat,           e_diesel,fuel_conso],
                             "unit" :["kWh" ,      "kWh",           "kWh",  "kWh",      "kWh", "kWh",   "kWh",           "kWh",   "L"]})
    dfEnergy.set_index("var")
    return dfEnergy

if __name__ == "__main__":
    from datetime import datetime, timedelta
    print("\n --- testing the relative_error() comparison function ---\n")

    # Simuler des donnees avec numpy
    n_points = 100
    TimeArray = np.linspace(0, 10, n_points)  # 10 secondes de donnees
    
    # Exemple avec des fonctions sin et cos
    f_values = np.sin(TimeArray)
    g_values = np.cos(TimeArray)  # Une approximation differente
    
    # Calcul de l'ecart relatif avec differentes methodes et normes
    rel_error_l2_f, details = relative_error(TimeArray, f_values, g_values, p=2, method='reference_f')
    print(f"ecart relatif L² (reference f): {rel_error_l2_f:.6f}")
    
    rel_error_l1_f, _ = relative_error(TimeArray, f_values, g_values, p=1, method='reference_f')
    print(f"ecart relatif L¹ (reference f): {rel_error_l1_f:.6f}")
    
    rel_error_l2_max, _ = relative_error(TimeArray, f_values, g_values, p=2, method='maximum')
    print(f"ecart relatif L² (maximum): {rel_error_l2_max:.6f}")
    
    rel_error_l2_avg, _ = relative_error(TimeArray, f_values, g_values, p=2, method='average')
    print(f"ecart relatif L² (moyenne): {rel_error_l2_avg:.6f}")
    
    # Exemple avec une norme L∞ (norme uniforme)
    rel_error_linf, _ = relative_error(TimeArray, f_values, g_values, p=float('inf'), method='reference_f')
    print(f"ecart relatif L∞ (reference f): {rel_error_linf:.6f}")


    print("\n --- testing VerifTimeSeries() and EnergySums() ---\n")
    ActiveDevices = {"Grid": True, "Batteries": True, "DieselGenerator": True}

    paramIn_batt = {'capacity':800,
              'SOC':0.2, 
              'SOCmin':0.0,
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
     
    bat_list = [
                battery_1,
                battery_2,
                battery_3
                ]
    BattStock = BatteryStock(bat_list)

    paramIn_DG1 = {"Pmax":400,
                   "Pnom":380,
                   "Pmin":370,
                   "TankCapacity":2000,
                   "FuelRate":1,
                   "f_r_min":0.0,
                   "lifetime":200000,
                   "ReplacementCost":10000,
                   "MaintenanceCost":0.08,
                   "FuelPrice":1.5}
    
    DG_test_1 = DieselGenerator(paramIn_DG1)
    DG_test_1.find_DG_coeffs()

    num_steps = 10
    Vnull = np.transpose(np.zeros(num_steps))
    start_date = datetime(2025, 1, 1)
    TimeNull = np.array([start_date + timedelta(hours=i) for i in range(num_steps)])
    dfRes = pd.DataFrame({"TimeArray": TimeNull, "P_L":Vnull, "P_L_modif":Vnull, "P_green":Vnull, "P_net":Vnull, "P_net_modif":Vnull, 
                "P_grid":Vnull, "P_bat":Vnull, "P_diesel":Vnull, "SOC":Vnull, "F_C":Vnull, "P_diff":Vnull, "P_resistor":Vnull, "runtime_DG":Vnull})

    VerifTimeSeries(dfRes, ActiveDevices, BattStock, DG_test_1)
    dfEnergy = EnergySums(dfRes, DG_test_1)
    for sum in dfEnergy["value"]:
        assert(sum == 0)
# %%
