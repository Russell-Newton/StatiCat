import math
import os
from datetime import datetime
from sys import stdout

import aiohttp
import cv2
import discord
import discord.ext.commands as commands
import dlib
import numpy as np
from PIL import Image
from imutils import face_utils

from bot import StatiCat


class Fry(commands.Cog):
    """Fries an image. Thanks /u/DeepFryBot for being open source!"""

    def __init__(self, bot: StatiCat):
        self.bot = bot

        self.directory = 'fry/'
        self.b = self.directory + 'b.png'
        self.laughing_emoji = self.directory + 'laughing_emoji.png'
        self.flare = self.directory + 'flare.png'
        self.haarcascade_eye = self.directory + 'haarcascade_eye_tree_eyeglasses.xml'

        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(self.directory + 'shape_predictor_68_face_landmarks.dat')

    @commands.command()
    async def fryimg(self, ctx, do_buldge: bool = False):
        """Fries an embedded image

        Will not include a buldge by default"""
        image = Image
        if len(ctx.message.attachments) == 0:
            await ctx.send("You have to attach an image.")
        try:
            for attachment in ctx.message.attachments:
                temp_loc = self.directory + str(datetime.now().microsecond)
                url = attachment.url
                client = aiohttp.ClientSession()
                async with client.get(url) as r:
                    imageData = await r.content.read()
                await client.close()
                with open(temp_loc, 'wb') as f:
                    f.write(imageData)
                    image = Image.open(temp_loc).convert('RGB')
                fry = await self.fry(image, do_buldge)
                fry.save(temp_loc + ".png")

                await ctx.send(file=discord.File(temp_loc + ".png"))
                os.remove(temp_loc)
                os.remove(temp_loc + ".png")

        except IndexError:
            await ctx.send("There is no attached image.")

    async def fry(self, img, do_buldge):
        eyecoords = await self.find_eyes(img)
        img = await self.add_flares(img, eyecoords)
        coords = await self.find_chars(img)
        img = await self.add_b_emojis(img, coords)
        img = await self.add_laughing_emojis(img, 5)

        if (do_buldge):
            # bulge at random coordinates
            [w, h] = [img.width - 1, img.height - 1]
            w *= np.random.random(1)
            h *= np.random.random(1)
            r = int(((img.width + img.height) / 10) * (np.random.random(1)[0] + 1))
            img = await self.bulge(img, np.array([int(w), int(h)]), r, 3, 5, 1.8)

        # some finishing touches
        stdout.flush()
        img = await self.add_noise(img, 0.2)
        img = await self.change_contrast(img, 200)

        return img

    async def find_chars(self, img):
        gray = np.array(img.convert("L"))
        ret, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        image_final = cv2.bitwise_and(gray, gray, mask=mask)
        ret, new_img = cv2.threshold(image_final, 180, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        dilated = cv2.dilate(new_img, kernel, iterations=1)
        # Image.fromarray(dilated).save('out.png') # for debugging
        contours = []
        hierarchy = None
        cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE, contours, hierarchy)

        coords = []
        for contour in contours:
            # get rectangle bounding contour
            [x, y, w, h] = cv2.boundingRect(contour)
            # ignore large chars (probably not chars)
            if w > 70 and h > 70:
                continue
            coords.append((x, y, w, h))
        return coords

    async def add_b_emojis(self, img, coords):
        # create a temporary copy if img
        tmp = img.copy()

        # print("Adding B emojis...")
        b = Image.open(self.b)
        for coord in coords:
            if np.random.random(1)[0] < 0.1:
                # print("\tB added to ({0}, {1})".format(coord[0], coord[1]))
                resized = b.copy()
                resized.thumbnail((coord[2], coord[3]), Image.ANTIALIAS)
                tmp.paste(resized, (int(coord[0]), int(coord[1])), resized)

        return tmp

    async def add_laughing_emojis(self, img, max):
        # create a temporary copy if img
        tmp = img.copy()

        emoji = Image.open(self.laughing_emoji)
        for i in range(int(np.random.random(1)[0] * max)):
            # add laughing emoji to random coordinates
            coord = np.random.random(2) * np.array([img.width, img.height])

            resized = emoji.copy()
            size = int((img.width / 10) * (np.random.random(1)[0] + 1))
            resized.thumbnail((size, size), Image.ANTIALIAS)
            tmp.paste(resized, (int(coord[0]), int(coord[1])), resized)

        return tmp

    async def find_eyes(self, img):
        coords = []
        eye_cascade = cv2.CascadeClassifier(self.haarcascade_eye)
        gray = np.array(img.convert("L"))

        rects = self.detector(gray, 1)
        # detect faces in the grayscale image
        rects = self.detector(gray, 1)

        # loop over the face detections
        for (i, rect) in enumerate(rects):
            # determine the facial landmarks for the face region, then
            # convert the landmark (x, y)-coordinates to a NumPy array
            shape = self.predictor(gray, rect)
            shape = face_utils.shape_to_np(shape)

            coords.append(self.average_point(shape[36:42]))
            coords.append(self.average_point(shape[42:48]))

        '''
        eyes = eye_cascade.detectMultiScale(gray, 1.1, 3)
        for (ex, ey, ew, eh) in eyes:
            # print("\tFound eye at ({0}, {1})".format(x+ex+ew/2, y+ey+eh/2))
            coords.append((ex+ew/2, ey+eh/2))
        if len(coords) == 0:
            # print("\tNo eyes found.")
            pass
        '''
        return coords

    async def add_flares(self, img, coords):
        # create a temporary copy if img
        tmp = img.copy()

        # add flares to temporary copy
        # print("Adding lens flares...")
        flare = Image.open(self.flare)
        for coord in coords:
            # print("\tFlare added to ({0}, {1})".format(coord[0], coord[1]))
            tmp.paste(flare, (int(coord[0] - flare.size[0] / 2), int(coord[1] - flare.size[1] / 2)), flare)

        return tmp

    # Creates a fisheye distortion on img at f[x,y], with radius r, flatness a, height h, and index of refraction ior
    async def bulge(self, img, f, r, a, h, ior):
        # load image to numpy array
        width = img.width
        height = img.height
        img_data = np.array(img)

        # ignore too large images
        if width * height > 3000 * 3000:
            return img

        # determine range of pixels to be checked (square enclosing bulge), max exclusive
        x_min = int(f[0] - r)
        if x_min < 0:
            x_min = 0
        x_max = int(f[0] + r)
        if x_max > width:
            x_max = width
        y_min = int(f[1] - r)
        if y_min < 0:
            y_min = 0
        y_max = int(f[1] + r)
        if y_max > height:
            y_max = height

        # make sure that bounds are int and not np array
        if isinstance(x_min, type(np.array([]))):
            x_min = x_min[0]
        if isinstance(x_max, type(np.array([]))):
            x_max = x_max[0]
        if isinstance(y_min, type(np.array([]))):
            y_min = y_min[0]
        if isinstance(y_max, type(np.array([]))):
            y_max = y_max[0]

        # array for holding bulged image
        bulged = np.copy(img_data)
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                ray = np.array([x, y])

                # find the magnitude of displacement in the xy plane between the ray and focus
                s = await self.length(ray - f)

                # if the ray is in the centre of the bulge or beyond the radius it doesn't need to be modified
                if 0 < s < r:
                    # slope of the bulge relative to xy plane at (x, y) of the ray
                    m = -s / (a * math.sqrt(r ** 2 - s ** 2))

                    # find the angle between the ray and the normal of the bulge
                    theta = np.pi / 2 + np.arctan(1 / m)

                    # find the magnitude of the angle between xy plane and refracted ray using snell's law
                    # s >= 0 -> m <= 0 -> arctan(-1/m) > 0, but ray is below xy plane so we want a negative angle
                    # arctan(-1/m) is therefore negated
                    phi = np.abs(np.arctan(1 / m) - np.arcsin(np.sin(theta) / ior))

                    # find length the ray travels in xy plane before hitting z=0
                    k = (h + (math.sqrt(r ** 2 - s ** 2) / a)) / np.sin(phi)

                    # find intersection point
                    intersect = ray + (await self.normalise(f - ray)) * k

                    # assign pixel with ray's coordinates the colour of pixel at intersection
                    if 0 < intersect[0] < width - 1 and 0 < intersect[1] < height - 1:
                        bulged[y][x] = img_data[int(intersect[1])][int(intersect[0])]
                    else:
                        bulged[y][x] = [0, 0, 0]
                else:
                    bulged[y][x] = img_data[y][x]
        img = Image.fromarray(bulged)
        return img

    # return the length of vector v
    async def length(self, v):
        return np.sqrt(np.sum(np.square(v)))

    # returns the unit vector in the direction of v
    async def normalise(self, v):
        return v / (await self.length(v))

    async def add_noise(self, img, factor):
        def noise(c):
            return c * (1 + np.random.random(1)[0] * factor - factor / 2)

        return img.point(noise)

    async def change_contrast(self, img, level):
        factor = (259 * (level + 255)) / (255 * (259 - level))

        def contrast(c):
            return 128 + factor * (c - 128)

        return img.point(contrast)

    @staticmethod
    def average_point(points):
        x_avg = 0
        y_avg = 0
        for x, y in points:
            x_avg += x
            y_avg += y
        x_avg /= len(points)
        y_avg /= len(points)
        return x_avg, y_avg
