import untools
from untools.gptools.tools import *

if untools.__version__ == "2.1.0.0":
    raise ValueError("The toolbox requires version untools 2.1.0.1 or higher")
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Asset Package Tools Preview"
        self.alias = "pt"
        # List of tool classes associated with this toolbox
        self.tools = [ChangeGDBSpatialReference]
