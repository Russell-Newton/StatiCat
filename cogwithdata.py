import json
import inspect

import discord.ext.commands as commands


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
        self.data_file_location = self.directory + f"\\{data_file_name}.json"
        self.data: dict = self._get_data()

    def _get_data(self) -> dict:
        """
        Save the contents of the json file to self.data.
        """
        try:
            with open(self.data_file_location, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            with open(self.data_file_location, 'w') as file:
                # print("Making {}".format(self.data_file_location))
                file.write("{}")
            return self._get_data()

    def update_data_file(self) -> None:
        """
        Save the contents of self.data to the json file.
        """
        with open(self.data_file_location, 'w') as file:
            json.dump(self.data, file)
