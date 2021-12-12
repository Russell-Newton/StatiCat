import logging
import os
from random import choice
from typing import Union
import subprocess

import nextcord
import nextcord.ext.commands as commands
import pyttsx3

import interactions
from bot import StatiCat
from checks import check_permissions
from cogwithdata import CogWithData


class Rude(CogWithData):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        super().__init__("targets")
        self.beta_male_video = self.get_path("beta_male.mov")
        self.beta_male_audio = self.get_path("beta_male_audio.mov")

    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(name="mimic", pass_context=True)
    async def _mimic(self, ctx):
        """Manage the mimicking status"""
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(pass_context=True)
    async def silence(self, ctx):
        """Manage the silencing status"""
        if ctx.invoked_subcommand is None:
            await ctx.send("You have to invoke a subcommand.")

    @_mimic.command(name="add", pass_context=True)
    async def mimic_add(self, ctx, target: Union[nextcord.Member, nextcord.User]):
        """Add someone to the list of targets"""
        if target.id is self.bot.user.id:
            await ctx.send("I can't mimic myself.")
            return
        self.data["mimic"].append(target.id)
        self.update_data_file()

        await ctx.send("{0.mention} <3".format(target))

    @_mimic.command(name="remove", pass_context=True)
    async def mimic_remove(self, ctx, target: Union[nextcord.Member, nextcord.User]):
        """Remove someone from the list of targets"""
        self.data["mimic"].remove(target.id)
        self.update_data_file()

        await ctx.send("You're off the hook for now, {0.mention}.".format(target))

    @_mimic.command(name="clear", pass_context=True)
    async def mimic_clear(self, ctx):
        """Clear the list of targets"""
        self.data["mimic"] = []
        self.update_data_file()

        await ctx.send("I'll stop now.")

    @silence.command(name="add", pass_context=True)
    async def silence_add(self, ctx, target: Union[nextcord.Member, nextcord.User]):
        """Add someone to the list of targets"""
        if target.id is self.bot.user.id:
            await ctx.send("I can't silence myself.")
            return
        self.data["silence"].append(target.id)
        self.update_data_file()

        await ctx.send("{0.mention} <3".format(target))

    # @silence.command(name="server", pass_context=True)
    # async def silence_all_server(self, ctx: commands.Context):
    #     """Silence an entire server"""
    #     guild: nextcord.Guild = ctx.guild
    #     members: List[nextcord.Member] = guild.members
    #     logging.info(guild._members)
    #     for member in members:
    #         logging.info(member.id)
    #         if not member.bot:
    #             self.data["silence"].append(member.id)
    #     self.update_data_file()
    #
    #     await ctx.send("You will regret this...")

    @silence.command(name="remove", pass_context=True)
    async def silence_remove(self, ctx, target: Union[nextcord.Member, nextcord.User]):
        """Remove someone from the list of targets"""
        self.data["silence"].remove(target.id)
        self.update_data_file()

        await ctx.send("You're off the hook for now, {0.mention}.".format(target))

    @silence.command(name="clear", pass_context=True)
    async def silence_clear(self, ctx):
        """Clear the list of targets"""
        self.data["silence"] = []
        self.update_data_file()

        await ctx.send("I'll stop now.")

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

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.id is not self.bot.user.id:
            try:
                if message.author.id in self.data["mimic"]:
                    await message.channel.send(self.spongebobify(message))
                if message.author.id in self.data["silence"]:
                    try:
                        await message.delete()
                    except nextcord.Forbidden:
                        await message.channel.send(self.get_silence_message(message))
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_typing(self, channel: nextcord.abc.Messageable, user: Union[nextcord.User, nextcord.Member], when):
        if user.id is not self.bot.user.id:
            try:
                if user.id in self.data["silence"]:
                    await channel.send("Stop typing, {0.mention}".format(user))
            except Exception:
                pass

    @interactions.slash_command(name="betamale")
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

    @interactions.message_command(name="Yeah that's a miss")
    async def react_miss(self, interaction: nextcord.Interaction, message: nextcord.Message):
        await interaction.response.send_message("I agree that *was* a miss", ephemeral=True)
        await message.reply("https://media.discordapp.net/attachments/702212719402811422/916187308565336124/thats_a_miss.gif")

    @interactions.message_command(name="Yeah that's a hit")
    async def react_hit(self, interaction: nextcord.Interaction, message: nextcord.Message):
        await interaction.response.send_message("I agree that *was* a hit", ephemeral=True)
        await message.reply("https://cdn.discordapp.com/attachments/702212719402811422/916187308770852874/thats_a_hit.gif")
