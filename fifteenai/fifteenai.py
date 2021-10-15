import os
from datetime import datetime

import discord
import discord.ext.commands as commands
from cogwithdata import CogWithData
from bot import StatiCat, Embedinator
import logging

import aiohttp


class FifteenAI(CogWithData):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        super().__init__("fifteenai")

        self.headers = {
            'authority': 'api.15.ai',
            'access-control-allow-origin': '*',
            'accept': 'application/json, text/plain, */*',
            'dnt': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://15.ai',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://15.ai/',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8'
        }
        self.api_url = "https://api.15.ai/app/getAudioFile"
        self._retry_attempts = 6
        self.embedinator = Embedinator(**{"title": "Voicegen Character List"})
        self.embedinator.max_size = 1024
        self.characters_map = {key.lower(): key for key in self.data["characters"]}

    @commands.group(pass_context=True)
    async def voicegen(self, ctx: commands.Context):
        """
        Various commands to make use of 15.ai to generate custom voice lines for various characters.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @voicegen.command(name="list")
    async def list_characters(self, ctx: commands.Context):
        self.embedinator.clear()
        for character, game in self.data["characters"].items():
            self.embedinator.add_line(f"{character} *({game})*")
            # await ctx.send(f"{character} ({game})")
        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar_url):
            await ctx.send(embed=embed)

    @voicegen.command(name="say")
    async def create_voice_line(self, ctx: commands.Context, character: str, *, voice_line):
        """
        Makes use of FifteenAI's API! https://15.ai

        Create the voice line! The character must be from the valid list of characters. This list can be found with the
        `voicegen list` command. If a character's name has spaces, it must be put in parentheses.
        If you find that a word isn't being pronounced correctly, you can use 2-letter ARPAbet
        (https://en.wikipedia.org/wiki/ARPABET) inside of curly braces { }. The stress for vowel sounds should be
        indicated with a number ({AA1 R P AH0 B EH2 T}).
        """
        if len(voice_line) > 200:
            await ctx.send(f"Voice line exceeds 200 character limit! ({len(voice_line)})")
            return

        await ctx.send("This may take a while...")
        character = character.lower()
        if character not in self.characters_map:
            await ctx.send(
                f"Invalid character! Please use `{ctx.prefix}voicegen list` to find a list of valid character voices.")
            return

        # data = f'{"{"}"text":"{voice_line}","character":"{character}","emotion":"Contextual","use_diagonal":"true"{"}"}'
        data = {
            "text": voice_line,
            "character": self.characters_map[character],
            "emotion": "Contextual",
            "use_diagonal": "true"
        }
        await self._get_voice_line(ctx, data)

    async def _get_voice_line(self, ctx: commands.Context, data):
        filepath = f'{datetime.now().strftime("%m%d%Y%H%M%S")}.wav'

        logging.info(f"Attempting to POST {data} to api.15.ai...")
        try:
            errors = []
            # async with aiohttp.ClientSession(headers=self.headers) as session:
            for i in range(self._retry_attempts):
                async with aiohttp.request('post', self.api_url, data=data) as response:
                    if response.status != 200:
                        logging.error(
                            f"Error POSTing to api.15.ai (Attempt {i + 1}/{self._retry_attempts}, status code {response.status})...")
                        errors.append(response.status)
                        # logging.warning(response.content)
                    else:
                        with open(filepath, 'wb') as file:
                            file.write(await response.content.read())
                            await ctx.send(f"Got it! {ctx.author.mention}", file=discord.File(filepath))

                        os.remove(filepath)
                        return

            await ctx.send(
                f"Something went wrong with my attempt to POST to api.15.ai. Check logs. Attempted {i} times, got {errors} status codes")
            return
        except Exception as error:
            await ctx.send("Something went wrong! Check logs.")
            logging.error("Someone tried to use a command that they didn't have permission for.",
                          exc_info=(type(error), error, error.__traceback__))
