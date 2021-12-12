import json
import inspect

import nextcord.ext.commands as commands

from autosavedict import AutoSavingDict


class CogWithData(commands.Cog):
    """
    A Cog that has data management with json files.
    """

    def __init__(self, data_file_name: str = "data"):
        """
        :param data_file_name: the optional name to give to the datafile
        """
        py_file_location = inspect.getfile(self.__class__)
        self.directory, _ = py_file_location.rsplit("\\", 1)
        data_file_location = self.directory + f"\\{data_file_name}.json"
        self.data: dict = AutoSavingDict(data_file_location)

    def get_path(self, relative_path) -> str:
        return f"{self.directory}\\{relative_path}"
