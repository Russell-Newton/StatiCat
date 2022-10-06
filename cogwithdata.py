import json
import inspect
from typing import Optional

import nextcord.ext.commands as commands

from autosavedict import AutoSavingDict


class CogWithData(commands.Cog):
    """
    A Cog that has data management with json files.
    """

    def __init__(self, data_file_name: Optional[str] = None):
        """
        :param data_file_name: the optional name to give to the datafile
        """
        if data_file_name is None:
           data_file_name = f"{self.__class__.__name__.lower()}_data"
        py_file_location = inspect.getfile(self.__class__)
        self.directory, _ = py_file_location.rsplit("\\", 1)
        data_file_location = self.directory + f"\\{data_file_name}.json"
        self.data: dict = AutoSavingDict(data_file_location)

    def get_path(self, relative_path) -> str:
        return f"{self.directory}\\{relative_path}"
