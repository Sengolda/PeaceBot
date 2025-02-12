import inspect
import os
import re
import sys
from typing import Optional

import discord
from __main__ import PeaceBot
from discord import Embed, Message, TextChannel
from discord.ext import commands, flags

from bot.utils.embed_flag_input import (
    allowed_mentions_input,
    dict_to_allowed_mentions,
    dict_to_embed,
    embed_input,
    process_message_mentions,
    webhook_input,
)
from bot.utils.mixins.better_cog import BetterCog

flags._converters.CONVERTERS["Message"] = commands.MessageConverter().convert


async def maybe_await(coro):
    if not coro:
        return
    return await coro


class EmbedError(commands.CommandError):
    pass


class Utils(BetterCog):
    @commands.command(name="avatar", aliases=["av"])
    async def show_avatar(
        self, ctx: commands.Context, member: Optional[discord.Member]
    ):
        member = member or ctx.author

        embed = discord.Embed(title="Avatar", colour=discord.Color.blue())
        embed.set_author(name=member, url=member.avatar_url, icon_url=member.avatar_url)
        embed.set_image(url=member.avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.reply(embed=embed)

    @commands.command(aliases=["user", "info"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def whois(self, ctx: commands.Context, user: Optional[discord.Member]):
        user = user or ctx.author

        fmt = "%a, %b %d, %Y, %I:%M %p"
        created_at = user.created_at.strftime(fmt)
        joined_at = user.joined_at.strftime(fmt)

        roles_list = [role.mention for role in user.roles][1:][::-1]
        # Gets the formatted user's permissions in a list
        permissions = [
            (" ".join(permission[0].split("_"))).title()
            for permission in user.guild_permissions
            if permission[1]
        ]

        if user == ctx.guild.owner:
            acknowledgements = "Server Owner"
        elif "Administrator" in permissions:
            acknowledgements = "Administrator"
        elif "Manage Guild" in permissions:
            acknowledgements = "Moderator"
        else:
            acknowledgements = "Member"

        roles = (" ".join(roles_list)) if roles_list else "@everyone"
        permissions = ", ".join(permissions)

        embed = discord.Embed(
            description=user.mention,
            timestamp=ctx.message.created_at,
            colour=discord.Color.blue(),
        )
        embed.set_author(name=user, url=user.avatar_url, icon_url=user.avatar_url)
        embed.add_field(name="**Joined**", value=joined_at, inline=True)
        embed.add_field(name="**Registered**", value=created_at, inline=True)
        embed.add_field(name=f"**Roles**[{len(roles_list)}]", value=roles, inline=False)
        embed.add_field(name="**Permissions**", value=permissions, inline=False)
        embed.add_field(
            name="**Acknowledgements**", value=acknowledgements, inline=False
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"ID: {user.id}")
        await ctx.reply(embed=embed)

    """
    Source of the following code:
    https://github.com/falsedev/tech-struck
    """

    @embed_input(all=True)
    @allowed_mentions_input()
    @webhook_input()
    @flags.add_flag("--channel", "--in", type=TextChannel, default=None)
    @flags.add_flag("--message", "--msg", "-m", default=None)
    @flags.add_flag("--edit", "-e", type=Message, default=None)
    @flags.command(
        brief="Send an embed with any fields, in any channel, with command line like arguments"
    )
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_permissions(manage_webhooks=True, embed_links=True)
    async def embed(self, ctx: commands.Context, **kwargs):
        """
        Send an embed and its fully customizable
        Default mention settings:
            Users:      Enabled
            Roles:      Disabled
            Everyone:   Disabled
        """
        embed = dict_to_embed(kwargs, author=ctx.author)
        allowed_mentions = dict_to_allowed_mentions(kwargs)
        message = process_message_mentions(kwargs.pop("message"))

        if kwargs.pop("webhook"):
            if edit_message := kwargs.pop("edit"):
                edit_message.close()
            username, avatar_url = kwargs.pop("webhook_username"), kwargs.pop(
                "webhook_avatar"
            )
            if kwargs.pop("webhook_auto_author"):
                username, avatar_url = (
                    username or ctx.author.display_name,
                    avatar_url or ctx.author.avatar_url,
                )
            target = kwargs.pop("channel") or ctx.channel
            if name := kwargs.pop("webhook_new_name"):
                wh = await target.create_webhook(name=name)
            elif name := kwargs.pop("webhook_name"):
                try:
                    wh = next(
                        filter(
                            lambda wh: wh.name.casefold() == name.casefold(),
                            await target.webhooks(),
                        )
                    )
                except StopIteration:
                    return await ctx.reply(
                        "No pre existing webhook found with given name"
                    )
            else:
                return await ctx.reply("No valid webhook identifiers provided")
            await wh.send(
                message,
                embed=embed,
                allowed_mentions=allowed_mentions,
                username=username,
                avatar_url=avatar_url,
            )
            if kwargs.pop("webhook_dispose"):
                await wh.delete()
            return await ctx.message.add_reaction("\u2705")

        if edit := await maybe_await(kwargs.pop("edit")):
            if edit.author != ctx.guild.me:
                return await ctx.reply(
                    f"The target message wasn't sent by me! It was sent by {edit.author}"
                )
            await edit.edit(
                content=message, embed=embed, allowed_mentions=allowed_mentions
            )
        else:
            target = kwargs.pop("channel") or ctx
            await target.send(message, embed=embed, allowed_mentions=allowed_mentions)
        await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def rawembed(self, ctx: commands.Context, message: Optional[discord.Message]):
        if not message:
            if not ctx.message.refrence:
                raise EmbedError("Reply to an message with an embed")
            ref = ctx.message.reference
            message = ref.cached_message or await ctx.channel.fetch_message(
                ref.message_id
            )

        if not message.embeds:
            raise EmbedError("Message had no embeds")

        em = message.embeds[0]
        description = "```" + str(em.to_dict()) + "```"
        embed = Embed(description=description)
        await ctx.reply(embed=embed)

    @commands.command(aliases=["github", "code"])
    @commands.cooldown(1, 1, commands.BucketType.channel)
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you can separate it by
        periods or spaces.
        """
        github = '<:white_github:852245817175179284>'
        embed = discord.Embed(title=f'{github} GitHub (Click Here) {github}')
        source_url = 'https://github.com/samrid-pandit/peacebot'
        branch = 'master'
        if command is None:
            embed.url = source_url
            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.send(embed=commands.BadArgument('Could not find command.'))

            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = 'https://github.com/Rapptz/discord.py'
            branch = 'master'

        final_url = (f'{source_url}/blob/{branch}/{location}#L{firstlineno}-L'
                     f'{firstlineno + len(lines) - 1}')
        embed.url = final_url
        await ctx.send(embed=embed)


def teardown(bot: PeaceBot):
    del sys.modules["bot.utils.embed_flag_input"]


def setup(bot: PeaceBot):
    bot.add_cog(Utils(bot))
