import os
import subprocess
import traceback
import warnings
from typing import List

import discord
import discord.ext.commands as commands
import imageio
from skimage import img_as_ubyte
from skimage.transform import resize
import cv2

from bot import StatiCat
from .first_order_model.demo import load_checkpoints, make_animation


class DeepFake(commands.Cog):
    """Based on https://github.com/AliaksandrSiarohin/first-order-model"""

    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.directory = "deepfake/"
        self.bm_input_image = self.directory + 'bm_image.png'
        self.bm_template = self.directory + 'bakamitai_template.mp4'
        self.bm_output = self.directory + 'bm_output.mp4'

        self.df_template = self.directory + 'df_template.mp4'
        self.df_input_image = self.directory + 'df_image.png'
        self.df_output = self.directory + 'df_output.mp4'

        self.df_config = self.directory + 'first_order_model/config/vox-adv-256.yaml'
        self.df_checkpoint = self.directory + 'vox-adv-cpk.pth.tar'
        self.generated_slow = self.directory + 'generated_slow.mp4'
        self.generated_fast = self.directory + 'generated_fast.mp4'

        self.is_already_running = False

    @commands.command(name="bakamitai", aliases=["deepfakebm", "dfbm"])
    async def baka_mitai(self, ctx: commands.Context):
        """
        You must attach your input image in the command message! The image will automatically be reshaped to 256x256.
        For best results, do this yourself.
        """

        await self.generate_deepfake(ctx, self.bm_input_image, self.bm_template, self.bm_output)

    @commands.command(name="bakamitailatest", aliases=["bmlatest"])
    async def get_bm_latest(self, ctx: commands.Context):
        if os.path.exists(self.bm_output):
            await ctx.send("Viola!", file=discord.File(self.bm_output))
        else:
            await ctx.send(
                f"There is no valid history for the Baka Mitai deep fakes. Create a new one with `{ctx.prefix}bakamitai`!")

    @commands.group(name="deepfake")
    async def general_deepfake(self, ctx: commands.Context):
        """Some commands for more general deepfake videos"""
        pass

    @general_deepfake.command(name="setvid")
    async def set_deepfake_video(self, ctx: commands.Context):
        """You must attach your input video in the command message! The video will automatically be reshaped to 256x256.
        For best results, do this yourself."""
        attachments: List[discord.Attachment] = ctx.message.attachments
        if len(attachments) > 0:
            try:
                await attachments[0].save(self.df_template)
                await ctx.send("Template video set!")
            except discord.HTTPException as error:
                await ctx.send("Unable to use attached content.")
                traceback.print_exception(type(error), error, error.__traceback__)
                return
        else:
            await ctx.send("You must make the input video an attachment.")
            return

    @general_deepfake.command(name="gen")
    async def generate_general_deepfake(self, ctx: commands.Context):
        """
        You must attach your input image in the command message! The image will automatically be reshaped to 256x256.
        For best results, do this yourself.
        """

        if not os.path.exists(self.df_template):
            await ctx.send("You must set the template video first!")

        await self.generate_deepfake(ctx, self.df_input_image, self.df_template, self.df_output)

    async def generate_deepfake(self, ctx: commands.Context, input_image: str, input_video: str, output_video: str):
        if self.is_already_running:
            await ctx.send("This is a very complex operation, and I'm already in the process of making one. Please try again later. :)")
            return
        self.is_already_running = True

        attachments: List[discord.Attachment] = ctx.message.attachments
        if len(attachments) > 0:
            try:
                await attachments[0].save(input_image)
            except discord.HTTPException as error:
                await ctx.send("Unable to use attached content.")
                traceback.print_exception(type(error), error, error.__traceback__)
                return
        else:
            await ctx.send("You must make the input image an attachment.")
            return

        await ctx.send("Beginning process. Please be patient, this is very hard for me :)")

        warnings.filterwarnings("ignore")

        cv2_input = cv2.VideoCapture(input_video)
        original_fps = cv2_input.get(cv2.CAP_PROP_FPS)
        cv2_input.release()

        source_image = imageio.imread(input_image)
        driving_video = imageio.mimread(input_video)

        # Resize image and video to 256x256
        source_image = resize(source_image, (256, 256))[..., :3]
        driving_video = [resize(frame, (256, 256))[..., :3] for frame in driving_video]

        await ctx.send("Note: The image is automatically scales to 256x256. For best results, do this yourself.")

        generator, kp_detector = await load_checkpoints(config_path=self.df_config,
                                                        checkpoint_path=self.df_checkpoint)

        await ctx.send("Rendering...")
        predictions = await make_animation(source_image, driving_video, generator, kp_detector, relative=True)

        if os.path.exists(input_image):
            os.remove(input_image)

        # Save resulting video
        imageio.mimsave(self.generated_slow, [img_as_ubyte(frame) for frame in predictions])

        cv2_input = cv2.VideoCapture(self.generated_slow)
        slow_fps = cv2_input.get(cv2.CAP_PROP_FPS)
        cv2_input.release()

        await ctx.send("Rendered! Adding some final touches...")
        # Speed up
        multipler = slow_fps / original_fps
        speed_up = subprocess.Popen(f"ffmpeg -i {self.generated_slow} -filter:v \"setpts={multipler:.5f}*PTS\" {self.generated_fast}")
        speed_up.wait()

        # Add audio
        if os.path.exists(output_video):
            os.remove(output_video)
        add_audio = subprocess.Popen(
            f"ffmpeg -i {self.generated_fast} -i {input_video} -c copy -map 0:v:0 -map 1:a:0 -shortest {output_video}")
        add_audio.wait()

        if os.path.exists(self.generated_slow):
            os.remove(self.generated_slow)
        if os.path.exists(self.generated_fast):
            os.remove(self.generated_fast)

        if os.path.exists(output_video):
            await ctx.send("Viola!", file=discord.File(output_video))
        else:
            await ctx.send("Looks like I had some trouble making the video... Hopefully that will be fixed soon :(")

        self.is_already_running = False
