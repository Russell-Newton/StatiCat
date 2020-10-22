import json
from typing import Union, List

import discord
import discord.ext.commands as commands


def get_global_data() -> dict:
    with open("global_data.json", 'r') as file:
        return json.load(file)


def get_prefixes(bot: commands.Bot, message: discord.Message) -> Union[str, List[str]]:
    prefixes = get_global_data()["prefixes"]
    return prefixes


def get_owner_data() -> dict:
    with open("owner_data.json", 'r') as file:
        return json.load(file)


def get_color_palette() -> List[discord.Color]:
    hexes = get_global_data()["color palette"]
    return [discord.Color(int(hex_val, 0)) for hex_val in hexes]
