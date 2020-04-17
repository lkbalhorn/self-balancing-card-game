import sys
from cx_Freeze import setup, Executable

# Demo Here: https://www.youtube.com/watch?v=GSoOwSqTSrs
# cd C:\Users\Luke\Documents\_Home\Games\SBCCG\code
# Run in Anaconda Prompt: python cs_freeze_script.py build
# For small updates, files on the same level as the lib folder must be replaced, others do not.




# Dependencies are automatically detected, but it might need fine tuning.
# build_exe_options = {"packages": ["pygame"]}
build_exe_options = {"packages": ["pygame", "asyncio", "aiohttp", "idna.idnadata", "screeninfo"],
                     "excludes": ["tkinter", "numpy" "scipy", "pandas", "IPython", "h5py",
                                  "ipykernel", "ipyparallel", "matplotlib", "sqlite3"]}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = "Win32GUI"
# if sys.platform == "win32":
    # base = "Win32GUI"

setup(name = "RazorsEdge",
        version = "0.2",
        description = "Razor's Edge",
        options = {"build_exe": build_exe_options},
        executables = [Executable("RazorsEdge.py", base=base), Executable("server.py", base=base)])