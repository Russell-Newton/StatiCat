import json
from typing import Union, List, Optional

import discord
import discord.ext.commands as commands


_global_data: Optional[dict] = None


def reload_global_data():
    global _global_data
    with open("global_data.json", 'r') as file:
        _global_data = json.load(file)


def save_global_data():
    with open("global_data.json", 'w') as file:
        json.dump(_global_data, file)


def get_global_data() -> dict:
    global _global_data
    if _global_data is None:
        reload_global_data()

    return _global_data


def get_prefixes(bot: commands.Bot, message: discord.Message) -> Union[str, List[str]]:
    prefixes = get_global_data()["prefixes"]
    return prefixes


def get_owner_data() -> dict:
    with open("owner_data.json", 'r') as file:
        return json.load(file)


def get_color_palette() -> List[discord.Color]:
    hexes = get_global_data()["color palette"]
    return [discord.Color(int(hex_val, 0)) for hex_val in hexes]
