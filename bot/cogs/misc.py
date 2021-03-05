import asyncio
import random
import discord
from typing import Union

from akinator.async_aki import Akinator
from discord.ext.commands import BucketType, Context
from discord import Color, Embed, Message, Member
from discord.ext import commands

HTTP_ERROR_VALID_RANGES = (
    (100, 102),
    (200, 208),
    (300, 308),
    (400, 452),
    (499, 512),
    (599, 600),
)

AKINATOR_VALID_RESPONSES = (
    "yes",
    "y",
    "0",
    "no",
    "n",
    "1",
    "i",
    "idk",
    "i dont know",
    "i don't know",
    "2",
    "probably",
    "p",
    "3",
    "probably not",
    "pn",
    "4",
    "stop",
)


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="httpcat", aliases=["hcat"])
    async def httpcat(self, ctx, code: Union[int, str] = None):
        """Get a HTTP Cat for a HTTP error code"""

        title = None

        in_valid_range = any((code in range(*i) for i in HTTP_ERROR_VALID_RANGES))

        if code is None:
            code = 400
            title = "Ask with a code"

        elif isinstance(code, str):
            code = 422
            title = "Invalid number code"

        elif not in_valid_range:
            code = 404
            title = "Can't find that code..."

        url = f"https://http.cat/{code}"
        if not title:
            title = str(code)

        embed = Embed(title=title, color=Color(random.randint(0, 0xFFFFFF)))
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="akinator", aliases=["aki"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def aki(self, ctx: commands.Context):
        """Play with aki"""

        index = 1
        """Play akinator!
        **Always respond within 30 seconds**
        Valid question responses:
        - **Yes**: y, yes, 0
        - **No**: no, n, 1
        - **I don't know**: i, idk, i dont know, i don't know, 2
        - **Probably**: probably, p, 3
        - **Probably Not**: probably not, pn, 4
        - **Stop**: stop
        """
        await ctx.trigger_typing()
        akinator = Akinator()
        question = await akinator.start_game(child_mode=True)

        def check(message: Message):
            return (
                message.channel == ctx.channel
                and message.author == ctx.author
                and message.content.lower() in AKINATOR_VALID_RESPONSES
            )

        while akinator.progression <= 80:
            await ctx.trigger_typing()

            embed = Embed(
                title=f"{ctx.author.display_name}, Question {index}",
                color=Color.gold(),
                timestamp=ctx.message.created_at,
            )
            embed.add_field(
                name=f"**{question}**",
                value="[yes (**y**) / no (**n**) / idk (**i**) / probably (**p**) / probably not (**pn**)]\
                    \n[back (**b**)]\
                    \n[stop (**stop**)]",
            )
            await ctx.send(embed=embed)
            try:
                answer_message = await self.bot.wait_for(
                    "message", check=check, timeout=30
                )
            except asyncio.TimeoutError:
                await ctx.send(f"{ctx.author.mention} You didn't respond in time!")
                return
            if answer_message.content.lower() == "stop":
                await ctx.send("Akinator stopped!")
                return
            question = await akinator.answer(answer_message.content)

            index += 1

        await akinator.win()

        embed = Embed(
            title=akinator.first_guess["name"], color=Color(random.randint(0, 0xFFFFFF))
        )

        embed.set_image(url=akinator.first_guess["absolute_picture_path"])
        embed.add_field(name="From", value=akinator.first_guess["description"])
        embed.set_footer(text="Was I Correct? | y/yes/n/no")

        await ctx.send(embed=embed)

        def confirmation_check(message: Message):
            return message.channel == ctx.channel and message.author == ctx.author

        try:
            confirmation_message = await self.bot.wait_for(
                "message", check=confirmation_check, timeout=10
            )
            response = confirmation_message.content.lower()

            if response in ("yes", "y"):
                await ctx.send("I Guessed correct, Once Again")
            elif response in ("no", "n"):
                await ctx.send("I have been defeated. You Win.")
            else:
                await ctx.send(
                    "I don't know what that means but I'll take it as a win "
                )

        except TimeoutError:
            await ctx.send("I don't know what that means but I'll take it as a win ")

    @commands.command()
    async def emojify(self, ctx: Context, *, word: str):
        num2words = {
            0: "zero",
            1: "one",
            2: "two",
            3: "three",
            4: "four",
            5: "five",
            6: "six",
            7: "seven",
            8: "eight",
            9: "nine",
        }
        word = word.lower()

        if not word:
            return

        emojified = ""
        for letter in word:
            if letter == " ":
                emojified += "    "
            elif letter.isalpha():
                emoji = f":regional_indicator_{letter}: "
                emojified += emoji
            elif letter.isdigit():
                letter = int(letter)
                emoji = num2words[letter]
                emojified += f":{emoji}: "
            else:
                emojified += letter

        await ctx.send(emojified)


def setup(bot):
    bot.add_cog(Misc(bot))