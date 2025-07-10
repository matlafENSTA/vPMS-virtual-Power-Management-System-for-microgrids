# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:43:32
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: A few functions made for reading the input tables (inpParam.xlsx) and check their format.
'''
#---------------------
#%%
import pandas as pd

def openxlsx(ExcelPath: 'str')-> tuple[pd.DataFrame]:
    """reads the input excel file and returns one dataframe per sheet. Also delete unused columns.
    
    Args:
        ExcelPath (str): path of the input excel file (usually input//inpParam.xlsx)
    
    Returns:
        tuple[pd.DataFrame]: input parameters (components, timeseries, output settings...) as DataFrames
    """
    sheets_dict = pd.read_excel(ExcelPath, sheet_name=None)

    # ColsToDrop = ["type", "notes", "..."]
    mainSheetRaw = sheets_dict.get("main")
    mainSheet = mainSheetRaw.drop(["type", "notes"], axis=1).set_index("parameter")

    TimeSeriesSheetRaw = sheets_dict.get("Green&LoadTimeSeries")
    TimeSeriesSheet = TimeSeriesSheetRaw.drop("notes", axis=1).drop(0,axis=0).reset_index(drop=True)

    GridPricesSheetRaw = sheets_dict.get("GridPrices")
    GridPricesSheet = GridPricesSheetRaw.drop("Consumption Mode", axis=1).set_index("Id")
    GridScheduleSheetRaw = sheets_dict.get("GridSchedule")
    GridScheduleSheet = GridScheduleSheetRaw.set_index("Hour | Month")

    BattSheetRaw = sheets_dict.get("Batteries")
    BattSheet = BattSheetRaw.drop(["unit","etc"], axis=1, errors="ignore").iloc[:10].set_index("parameter")

    DieselSheetRaw = sheets_dict.get("DieselGenerator")
    DieselSheet = DieselSheetRaw.drop(["unit","notes"], axis=1).set_index("parameter")

    outFSheetRaw = sheets_dict.get("outputFormat")
    outFSheet = outFSheetRaw.drop("notes", axis=1).set_index("dataset")

    return mainSheet, TimeSeriesSheet, GridPricesSheet, GridScheduleSheet, BattSheet, DieselSheet, outFSheet

def VerifmainSheet(mainSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "main"
    
    Args:
        mainSheet (pd.DataFrame): content of the "main" sheet as a pd.DataFrame. "parameter" column is the index 
    
    Returns:
        pd.DataFrame: only necessary values of mainSheet
    """
    mainSheetNew = pd.DataFrame.copy(mainSheet)
    mainSheetNew = mainSheetNew["value"]
    return mainSheetNew

def VerifTimeSeriesSheet(TimeSeriesSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "Green&LoadTimeSeries"
    
    Args:
        TimeSeriesSheet (pd.DataFrame): content of the "Green&LoadTimeSeries" sheet as a pd.DataFrame. no index set (default)
    
    Returns:
        pd.DataFrame: TimeSeriesSheet, with each column converted to the good format
    """
    TimeSeriesSheetNew = pd.DataFrame.copy(TimeSeriesSheet)
    TimeSeriesSheetNew["Time"] = pd.to_datetime(TimeSeriesSheetNew["Time"])
    TimeSeriesSheetNew["Load"] = pd.to_numeric(TimeSeriesSheetNew["Load"], errors="coerce")
    TimeSeriesSheetNew["Green Prod"] = pd.to_numeric(TimeSeriesSheetNew["Green Prod"], errors="coerce")
    return TimeSeriesSheetNew

def VerifGridPricesSheet(GridPricesSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "GridPrices"
    
    Args:
        GridPricesSheet (pd.DataFrame): content of the "GridPrices" sheet as a pd.DataFrame. "Id" column is the index 
    
    Returns:
        pd.DataFrame: GridPricesSheet, error if wrong format
    """
    assert(GridPricesSheet["Buying price (euros/kWh)"][1] <= GridPricesSheet["Buying price (euros/kWh)"][2] <= GridPricesSheet["Buying price (euros/kWh)"][3])
    GridPricesSheetNew = pd.DataFrame.copy(GridPricesSheet)
    return GridPricesSheetNew

def VerifGridScheduleSheet(GridScheduleSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "GridSchedule"
    
    Args:
        GridScheduleSheet (pd.DataFrame): content of the "GridSchedule" sheet as a pd.DataFrame. "Hour | Month" column is the index 
    
    Returns:
        pd.DataFrame: 
    """
    GridScheduleSheetNew = pd.DataFrame.copy(GridScheduleSheet)
    return GridScheduleSheetNew

def VerifBattSheet(BattSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "Batteries", and ignore wrong batteries in order to run a simulation anyway.
    
    Args:
        BattSheet (pd.DataFrame): content of the "Batteries" sheet as a pd.DataFrame. "parameter" column is the index
    
    Returns:
        pd.DataFrame: BattSheet with modified index names, and equal or less columns according to wether the data was ok or not"""
    BattSheetNew = pd.DataFrame.copy(BattSheet)
    for Batt in BattSheet.keys():
        # print(Batt,type(Batt))
        if not pd.notna(BattSheet[Batt]["capacity"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : capacity !!!")
        elif not pd.notna(BattSheet[Batt]["SOCmin"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : SOCmin !!!")
        elif not pd.notna(BattSheet[Batt]["SOCinit"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : SOCinit !!!")
        elif not pd.notna(BattSheet[Batt]["SOCmax"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : SOCmax !!!")
        elif not pd.notna(BattSheet[Batt]["eta"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : eta !!!")
        elif not pd.notna(BattSheet[Batt]["MaximumChargePower"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : MaximumChargePower !!!")
        elif not pd.notna(BattSheet[Batt]["MaximumDischargePower"]):
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because of a missing value : MaximumDischargePower !!!")
        elif not BattSheet[Batt]["SOCmin"] <= BattSheet[Batt]["SOCinit"] <= BattSheet[Batt]["SOCmax"]:
            BattSheetNew.drop(Batt, axis=1, inplace=True)
            print(f"!!! The battery named {Batt} was dropped because it didn't verify the following statement : SOCmin <= SOCinit <= SOCmax")
    BattSheetNew.rename({"SOCinit":"SOC",
                         "MaximumChargePower":"Pmax_ch",
                         "MaximumDischargePower":"Pmax_disch"}, inplace=True)
    return BattSheetNew

def VerifDieselSheet(DieselSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "DieselGenerator"
    
    Args:
        DieselSheet (pd.DataFrame): content of the "" sheet as a pd.DataFrame. "" column is the index
    
    Returns:
        pd.DataFrame: DieselSheet "value" columns with modified index names
    """
    DieselSheetNew = pd.DataFrame.copy(DieselSheet["value"])
    assert(pd.notna(DieselSheetNew["MaximumPower"]))
    assert(pd.notna(DieselSheetNew["NominalPower"]))
    assert(pd.notna(DieselSheetNew["MinimumPower"]))
    assert(pd.notna(DieselSheetNew["TankCapacity"]))
    assert(pd.notna(DieselSheetNew["FuelRate"]))
    assert(pd.notna(DieselSheetNew["MinimumFuelRate"]))
    assert(pd.notna(DieselSheetNew["FuelPrice"]))
    assert(pd.notna(DieselSheetNew["lifetime"]))
    assert(pd.notna(DieselSheetNew["ReplacementCost"]))
    assert(pd.notna(DieselSheetNew["MaintenanceCost"]))

    assert(DieselSheetNew["MinimumPower"] <= DieselSheetNew["NominalPower"] <= DieselSheetNew["MaximumPower"])
    assert(DieselSheetNew["MinimumFuelRate"] <= DieselSheetNew["FuelRate"])
    DieselSheetNew.rename({"MaximumPower":"Pmax",
                        "NominalPower":"Pnom",
                        "MinimumPower":"Pmin",
                        "MinimumFuelRate":"f_r_min",
                        "MinimumRuntime (optional)":"MinimumRuntime",
                        "A (optional)":"A","B (optional)":"B"}, inplace=True)
    return DieselSheetNew

def VerifoutFSheet(outFSheet: pd.DataFrame)-> pd.DataFrame:
    """Verify the validity of the excel sheet "outputFormat"
    
    Args:
        outFSheet (pd.DataFrame): content of the "" sheet as a pd.DataFrame. "" column is the index 
    
    Returns:
        pd.DataFrame: only necessary values of outFSheet (nan index lines dropped)
    """
    outFSheetNew = pd.DataFrame.copy(outFSheet)
    for row in outFSheet.index:
        if not pd.notna(row):
            outFSheetNew.drop(row, axis=0, inplace=True) # delete note lines
    for i in range(outFSheetNew.shape[0]):
        for j in range(outFSheetNew.shape[1]):
            if pd.notna(outFSheetNew.iloc[i,j]):
                assert(outFSheetNew.iloc[i,j] in ["YES","NO"])
            try:
                outFSheetNew.iloc[i,j] = True if outFSheetNew.iloc[i,j]=="YES" else False
            except:
                print(f"wrong value for line {i} col {j} in outputFormat")
    return outFSheetNew
# %%
