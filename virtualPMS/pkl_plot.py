# -*- coding:utf-8 -*-
'''
:Created: 2025-06-19 10:44:35
:Project: virtual PMS for microgrids
:Version: 1.0
:Author: Mathieu Lafitte
:Description: This script uses matplotlib to show some plots saved with the '.pkl' extension.
:How to use:
Method 1 (for ad hoc use) :
python pickle_plot.py "pklfilepath"
example : python pickle_plot.py "output//result.pkl"

Method 2 (for regular use, windows environment) :
In this method you will create an executable file and define it as default app to open '.pkl' files.
- "pip install pyinstaller"
- "pyinstaller --onefile pkl_plot.py". This step might take a few minutes.
      NB: if you don't want to display the python terminal (which closes automatically when you close the plot page), run "pyinstaller --onefile --noconsole pkl_plot.py" instead
- find pkl_plot.exe under "pkl_plot_build/dist/": copy it wherever you want, preferably in a folder that won't change
- set pkl_plot.exe as the default app for '.pkl' extension : 
      --> right click on a .pkl file
              --> open with
                      --> choose another app
                              --> enter the path of pkl_plot.exe
'''
#---------------------
# %%
import sys
import pickle
import matplotlib.pyplot as plt

if len(sys.argv) != 2:
    print("Usage: python affiche_figure.py <figure_file.pkl>")
    sys.exit(1)

fichier_pkl = sys.argv[1]

try:
    with open(fichier_pkl, 'rb') as f:
        fig = pickle.load(f)
    plt.show()
except Exception as e:
    print(f"Erreur lors du chargement de {fichier_pkl} : {e}")
    sys.exit(1)
