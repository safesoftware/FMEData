import shutil
import os

if not os.path.exists('C:/FundraisingWalk'):
    os.makedirs('C:/FundraisingWalk')
shutil.copy2('c:/FMEData2016/Output/Training/FundraisingWalk.kml', 'C:/FundraisingWalk/FundraisingWalk.kml')