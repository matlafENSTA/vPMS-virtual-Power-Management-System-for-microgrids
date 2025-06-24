# vPMS - virtual Power Management Systems
This set of python scripts aims to simulate the behavior of different dispatching strategies of Power Management System (PMS).
A PMS is a device that tells where energy comes from and where it goes at any time in a microgrid.
The implemented PMSs include the modelling of the following devices:
- __Grid connexion__ (with prices)
- __Energy Production & Consumption__ (time series)
- __Batteries__ (you can define more than one storage device)
- __Diesel Generator__ (DG)
---
3 dispatching strategies are implemented herein:
- __Load Following__ (LFE): Use the renewable source to supply the load, otherwise buy to the grid, otherwise discharge batteries, otherwise run the DG.
- __Cycle Charging__ (CCE): the difference between Load Following and Cycle Charging is thin. CC only runs the DG at its nominal power, and uses the remaining production to charge batteries, while LF runs the DG in order to match the load demand.
- __Strategy based on costs__ (CostStrat): a modular strategy based on cost comparison for decision making (for now, only economical cost is implemented within. The strategy is a deterministic aproach made to lower NPC at every time step)

## Content
```
virtualPMS_WD/
├── main.py
├── mainHardCode.py
├── input/
|   └── inpParam.xlsx
├── output/
├── virtualPMS/
|   ├── DataBase/
|   |   ├── DieselGeneratorFuelConsumption.csv
|   |   ├── GridPrices.csv
|   |   └── GridSchedule.csv
|   ├── __init__.py
|   ├── Battery.py
|   ├── BatteryStock.py
|   ├── DieselGenerator.py
|   ├── DispatchingStrats.py
|   ├── Grid.py
|   ├── pkl_plot.py
|   ├── TimeSeriesAnalysis.py
|   └── inpReader.py
├── README.md
├── setup.py
└── requirements.txt
```

### Working Directory

- [__main.py__](main.py): reads [__inpParam.xlsx__](input/inpParam.xlsx), define microgrid components and calls the selected dispatching strategy
- [__create_input.py__](create_input.py): helps creating an input to the good format, using known datasets or generating synthetic timeseries.
- [__03_clear_output.bat__](03_clear_output.bat): delete all files under ```output/``` by double-clicking (for windows users)
- [__setup.py__](setup.py): for downloading with ```pip install git+``` command
- [__requirements.txt__](requirements.txt): dependencies used by the script (for creating the virtual environment)

### virtualPMS
Homemade python package that simulates the behavior of different PMS strategies. The package includes 3 dispatching strategies, the modelling of electrical devices and some functions to facilitate the use of time series.
Content:
- [__DispatchingStrats.py__](virtualPMS//DispatchingStrats.py): Contains LFE_CCE() and CostStrat(), the functions performing the dispatch of power at any time step. Results are only time series.
- [__Battery.py__](virtualPMS//Battery.py): definition of a single battery, charge and discharge routines
- [__BatteryStock.py__](virtualPMS//BatteryStock.py): definition of a battery stock (= python list of batteries), charge and discharge routines, cost functions
- [__DieselGenerator.py__](virtualPMS//DieselGenerator.py): definition of the diesel generator, help for fuel consumption law parameters, use routine and cost function
- [__Grid.py__](virtualPMS//Grid.py): definition (mainly schedule and prices), cost functions
- [__TimeSeriesAnalysis.py__](virtualPMS//TimeSeriesAnalysis.py): mainly for saving results, but also for comparing time series and calculating simple results (EnergySums() function).
- [__inpReading.py__](virtualPMS//inpReading.py): some functions to read [__inpParam.xlsx__](input/inpParam.xlsx) and verify the consistency of its content.
- [__pkl_plot.py__](virtualPMS//pkl_plot.py): this script doesn't depend on the rest of the package. It is used to open '.pkl' results files.
- [__\_\_init\_\_.py__](virtualPMS//__init__.py): this file is only required by python to use the folder as a package.

NB: every script includes a test section, to check some basic results just run the desired script with python.
### input
[__inpParam.xlsx__](input/inpParam.xlsx): where you define the parameters for every component of the microgrid (Load and Renewable Prod time series, Grid characteristics, Batteries, Diesel Generator), and specify the results you want to generate. Contains time series of load and green power production.
Here is an example of the *"Green&LoadTimeSeries"* sheet :
|  1 | Time                |     Load |   Green Prod |           Grid State |
|----|---------------------|----------|--------------|----------------------|
|  2 |   %Y-%m-%d %H:%M:%S |       kW |           kW |    binary (optional) |
|  3 | 2025-01-01 00:00:00 |      150 |          100 |                  100 |
|  4 | 2025-01-01 00:15:00 |      120 |          110 |                  110 |

### output
Under ```output/```, you'll find all the results you chose to generate. They will be named as follows :
{inputIdd}_{StratIdd}_{DevicesIdd}_F{forecast}_DataSet.{type}
where :
- inputIdd = identifier of the input time series
- StratIdd = 'LF' for *Load Following*, 'CC' for *Cycle Charging* or 'CS' for *CostStrat*
- DevicesIdd = 'GBD' if Grid, Batteries and Diesel Generator are connected, '---' if nothing is connected. (also 'G-D', 'GB-', ...)
- forecast = 'True' or 'False' wether the forecast on grid cut-offs is activated or not
- DataSet = 'MAIN', 'AllVar', 'Costs', 'AllSOCs'
- type = 'csv', 'png' or 'pkl'

NB : the algorithm has a linear computational complexity (O(N)), so it runs fast (for one year of data, hourly, count less than 20seconds to generate every possible result).
## How to use
Quick start of the virtual PMS
- Fill [__inpParam.xlsx__](input/inpParam.xlsx) (see description below)
- Open a terminal in ```virtualPMS_WD/```, and run ```python main.py ``` : the dispatching will be simulated. You can run another input this way : ```python main.py your_input.xlsx``` if the input has the same format than [__inpParam.xlsx__](input/inpParam.xlsx).
- Find your results under ```output/```.

### [__inpParam.xlsx__](input/inpParam.xlsx)
| Sheet                | Description         
|----------------------|---------------------
| main                 | activated devices, strategy, forecast on grid reliability... 
| Green&LoadTimeSeries | Green Power Production and Load (kW) + Grid State (0 if the grid is connected, 1 if not)
| GridPrices           | Buying and Selling prices for Off-Peak Medium and Peak consumption hours.
| GridSchedule         | Consumption schedule described by the grid manager over the year
| Batteries            | Capacities, States of Charge, Charge and Discharge Power, and economical parameters
| DieselGenerator      | Operating Range, Tank capacity, Fuel Consumption Law, and economical parameters
|   outputFormat       | Choose the results you want to generate during the simulation: TRUE for activation, FALSE for deactivation.

## Get Started
This routine was designed under [python 3.12.3](https://www.python.org/downloads/release/python-3123/). Please ensure using a compatible version to run the code.
To get started, you'll need 1.5Go or 500Mo according to wether you use a virtual environment or not.

### Clone the Repository
in the desired folder on your computer, use the command that will copy all the files of this repository under ```virtualPMS_WD/```
``` 
git clone *repo_link*
```
### Install dependencies
We strongly recommand to use a virtual environment to avoid conflicts with other python projects. Follow the next steps to do so :

1 - Create the virtual environment (in the working directory)
```
python -m venv venv
```
2 - Activate it (Windows PowerShell)
```
venv\Scripts\Activate.ps1
```
or (Windows cmd) :
```
venv\Scripts\activate.bat
```
3 - Download dependencies (this might take a few time)
```
pip install -r requirements.txt
```

---
If you are not familiar with virtual environments, you can still import manually the following modules (but it might cause version conflicts on other python projects):
- __os__
- __sys__
- __csv__
- __copy__
- __numpy__
- __pandas__
- __pickle__
- __datetime__
- __matplotlib.pyplot__

### Install only the module at python's root
```
pip install git+*repo_link*
```
Then import dependencies directly in your code as follows:
then import mandatory modules :
```
from virtualPMS-0.1.0 import DispatchingStrats as DS
from virtualPMS-0.1.0 import TimeSeriesAnalysis as TSA
from virtualPMS-0.1.0 import Battery, BatteryStock, DieselGenerator, Grid
```
We really encourage you to use [main.py](main.py) or [mainHardCode.py](mainHardCode.py) as a starting point to get use to the process.

---
You can uninstall the module at any time with the following command :
```
pip uninstall virtualPMS-0.1.0
```
__CAUTION :__ This method does not include the ```DataBase``` folder which is mandatory for modelling the diesel generator.

---
PIMENT Research Laboratory [\[GitHub\]](https://github.com/Laboratoire-Piment) [\[WebPage\]](https://piment.univ-reunion.fr)  
97410 Saint Pierre, La Réunion  
Mathieu LAFITTE [\[GitHub\]](https://github.com/matlafENSTA/Computing-Projects-ML) [\[LinkedIn\]](www.linkedin.com/in/mathieu-lafitte-188679247)  
2025  
