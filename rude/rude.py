import logging
import os
import re
import traceback
from random import choice, random
from typing import Union
import subprocess

import nextcord
import nextcord.ext.commands as commands
from nextcord import slash_command, message_command
import pyttsx3

from bot import StatiCat
from checks import check_permissions, check_in_guild
from cogwithdata import CogWithData


class Rude(CogWithData):
    def __init__(self, bot: StatiCat):
        super().__init__()
        self.bot = bot
        self.beta_male_video = self.get_path("beta_male.mov")
        self.beta_male_audio = self.get_path("beta_male_audio.mov")
        self.counter_ratio_chance = 0.05

    async def _add_target(self, attack: str, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        if target.id is self.bot.user.id:
            await ctx.send(f"I can't {attack} myself.")
            return
        if ctx.guild.id not in self.data[attack]:
            self.data[attack][ctx.guild.id] = []
        self.data[attack][ctx.guild.id].append(target.id)

        await ctx.send(f"{target.mention} <3")

    async def _remove_target(self, attack: str, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        if ctx.guild.id not in self.data[attack]:
            return
        if target.id in self.data[attack][ctx.guild.id]:
            self.data[attack][ctx.guild.id].remove(target.id)
            await ctx.send(f"You're off the hook for now, {target.mention}.")
            return
        await ctx.send(f"Consider yourself lucky, {target.mention}.")

    async def _clear_guild(self, attack: str, ctx: commands.Context):
        self.data[attack][ctx.guild.id] = []
        await ctx.send("I'll stop now.")

    @check_in_guild()
    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(name="mimic", pass_context=True)
    async def _mimic(self, ctx):
        """Manage the mimicking status"""
        if "mimic" not in self.data:
            self.data["mimic"] = {}
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @check_in_guild()
    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(pass_context=True)
    async def silence(self, ctx):
        """Manage the silencing status"""
        if "silence" not in self.data:
            self.data["silence"] = {}
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @check_in_guild()
    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(name="mock", pass_context=True)
    async def _mock(self, ctx):
        """Manage the mocking status"""
        if "mock" not in self.data:
            self.data["mock"] = {}
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @_mimic.command(name="add", pass_context=True)
    async def mimic_add(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Add someone to the list of targets"""
        await self._add_target("mimic", ctx, target)

    @_mimic.command(name="remove", pass_context=True)
    async def mimic_remove(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Remove someone from the list of targets"""
        await self._remove_target("mimic", ctx, target)

    @_mimic.command(name="clear", pass_context=True)
    async def mimic_clear(self, ctx: commands.Context):
        """Clear the list of targets"""
        await self._clear_guild("mimic", ctx)
        
    @_mock.command(name="add", pass_context=True)
    async def mock_add(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Add someone to the list of targets"""
        await self._add_target("mock", ctx, target)

    @_mock.command(name="remove", pass_context=True)
    async def mock_remove(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Remove someone from the list of targets"""
        await self._remove_target("mock", ctx, target)

    @_mock.command(name="clear", pass_context=True)
    async def mock_clear(self, ctx: commands.Context):
        """Clear the list of targets"""
        await self._clear_guild("mock", ctx)

    @silence.command(name="add", pass_context=True)
    async def silence_add(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Add someone to the list of targets"""
        await self._add_target("silence", ctx, target)

    @silence.command(name="remove", pass_context=True)
    async def silence_remove(self, ctx: commands.Context, target: Union[nextcord.Member, nextcord.User]):
        """Remove someone from the list of targets"""
        await self._remove_target("silence", ctx, target)

    @silence.command(name="clear", pass_context=True)
    async def silence_clear(self, ctx: commands.Context):
        """Clear the list of targets"""
        await self._clear_guild("silence", ctx)

    def get_silence_message(self, input_message) -> str:
        choices = [
            "Bro shut up.",
            "Who said you could speak?",
            "You're on thin ice, bud.",
            "What's so hard to understand about \"shut up\"?",
            lambda: "{0.mention}, get your boy. {1.mention}'s all up in my face, bro".format(
                self.get_random_guild_member(input_message),
                input_message.author) if input_message.guilds is not None else "You're all up in my face, bro."
        ]
        chosen = choice(choices)
        if callable(chosen):
            return chosen()
        return chosen

    @staticmethod
    def get_random_guild_member(input_message) -> nextcord.Member:
        guild: nextcord.Guild = input_message.guilds
        chosen: nextcord.Member = choice(guild.members)
        while chosen.id is input_message.author.id:
            chosen = choice(guild.members)
        return choice(guild.members)

    @staticmethod
    def spongebobify(message: nextcord.Message):
        out = ""
        choices = [lambda x: x.lower(),
                   lambda x: x.upper()]
        for i, char in enumerate(message.content):
            out += choice(choices)(char)
        return out

    def check_ratio(self, message: nextcord.Message):
        pattern = re.compile(r'\b(?:ratio|ratiod|ratioed)\b', re.IGNORECASE)
        return pattern.search(message.content) is not None


    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.id != self.bot.user.id:
            try:
                if message.guild is not None:
                    if message.guild.id in self.data["silence"]:
                        if message.author.id in self.data["silence"][message.guild.id]:
                            try:
                                await message.delete()
                            except nextcord.Forbidden:
                                await message.channel.send(self.get_silence_message(message))
                            return
                    if message.guild.id in self.data["mimic"]:
                        if message.author.id in self.data["mimic"][message.guild.id]:
                            await message.channel.send(self.spongebobify(message))
                            return
                    if message.guild.id in self.data["mock"]:
                        if message.author.id in self.data["mock"][message.guild.id]:
                            await message.channel.send("https://tenor.com/view/i-show-speed-dick-sucker-cock-gif-24582039")
                            return
                if self.check_ratio(message):
                    if random() < self.counter_ratio_chance:
                        sent_message = await message.reply("\@here let's ratio this bozo")
                        await sent_message.add_reaction("⬆")
                    else:
                        await message.add_reaction("⬆")
            except Exception as error:
                traceback.print_exception(type(error), error, error.__traceback__)
                logging.error("Error in rude.", exc_info=(type(error), error, error.__traceback__))

    @commands.Cog.listener()
    async def on_typing(self, channel: nextcord.TextChannel, user: Union[nextcord.User, nextcord.Member], when):
        if not hasattr(channel, "guild"):
            return
        if user.id is not self.bot.user.id:
            try:
                if channel.guild.id in self.data["silence"]:
                    if user.id in self.data["silence"][channel.guild.id]:
                        await channel.send("Stop typing, {0.mention}".format(user))
            except Exception as error:
                traceback.print_exception(type(error), error, error.__traceback__)
                logging.error("Error in rude.", exc_info=(type(error), error, error.__traceback__))

    @slash_command(name="betamale")
    async def beta_male_shadow(self, interaction: nextcord.Interaction, name: str):
        """
        Shadow the Hedgehog thinks someone's a beta male.
        :param name: who should Shadow call out?
        """
        await interaction.response.send_message("Working on it...")
        try:
            tts = pyttsx3.init(debug=True)
            temp_tts_path = self.get_path(f"tts.mp3")
            tts.setProperty("rate", tts.getProperty("rate") - 30)
            tts.save_to_file(name, temp_tts_path)
            tts.runAndWait()
            temp_audio_path = self.get_path(f"audio.mp3")
            print(temp_tts_path, temp_audio_path)
            command = f"ffmpeg -y -i \"{self.beta_male_audio}\" -i \"{temp_tts_path}\" -filter_complex \"[0:0][1:0] concat=n=2:v=0:a=1 [out]\" -map \"[out]\" \"{temp_audio_path}\""
            print(command)
            subprocess.run(command)
            name = "".join(c for c in name if c.isalnum() or c in (" ", ".", "_")).rstrip()[:50]
            temp_video_path = self.get_path(f"{name}_is_a_beta.mp4")
            command = f"ffmpeg -y -i \"{self.beta_male_video}\" -i \"{temp_audio_path}\" -filter_complex amix -c:v copy -c:a aac \"{temp_video_path}\""
            print(command)
            subprocess.run(command)
            # response: InteractionResponse = interaction.response
            await interaction.edit_original_message(content=None, file=nextcord.File(temp_video_path))

            os.remove(temp_tts_path)
            os.remove(temp_audio_path)
            os.remove(temp_video_path)
        except Exception as error:
            await interaction.edit_original_message(content="Yeah that didn't work. Sorry bud")
            logging.error("Error creating betamale video: ", exc_info=(type(error), error, error.__traceback__))

    @message_command(name="Yeah that's a miss")
    async def react_miss(self, interaction: nextcord.Interaction, message: nextcord.Message):
        await interaction.response.send_message("I agree that *was* a miss", ephemeral=True)
        await message.reply("https://media.discordapp.net/attachments/702212719402811422/916187308565336124/thats_a_miss.gif")

    @message_command(name="Yeah that's a hit")
    async def react_hit(self, interaction: nextcord.Interaction, message: nextcord.Message):
        await interaction.response.send_message("I agree that *was* a hit", ephemeral=True)
        await message.reply("https://cdn.discordapp.com/attachments/702212719402811422/916187308770852874/thats_a_hit.gif")
