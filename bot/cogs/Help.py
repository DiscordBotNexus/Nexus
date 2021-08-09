from typing import Optional, Union, Mapping, List
from discord.errors import Forbidden, HTTPException

from discord.ext.commands.core import Group, bot_has_permissions
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.helpers import paginatorinput
from discord.ext.commands.help import HelpCommand, _HelpCommandImpl
from discord import Embed
from discord.abc import Messageable

from utils.subclasses.bot import Nexus


PER_PAGE = 10


class NexusHelp(HelpCommand):
    def get_command_signature(self, c: Command):
        return f"{self.context.clean_prefix}{c.qualified_name} {c.signature}"

    async def _send(
        self,
        items: Union[list, Embed, paginatorinput],
        *,
        destination: Optional[Messageable] = None,
    ) -> None:
        destination = destination or self.get_destination()

        await self.context.paginate(items, destination=destination)

    def _show(self, item: Optional[Union[Cog, Command, Group, _HelpCommandImpl]]):
        if isinstance(item, (Command, Group, _HelpCommandImpl)):
            item = item.cog

        if not list(item.walk_commands()):
            return False

        if (
            self.context.author.id == self.context.bot.owner_id
            or self.context.author.id in self.context.bot.owner_ids
        ):
            return True

        return not item.hidden

    async def send_bot_help(
        self, mapping: Mapping[Optional[Cog], List[Command]]
    ) -> None:
        await self._send(await self._get_bot_help(mapping))

    async def _get_bot_help(
        self, mapping: Mapping[Optional[Cog], List[Command]]
    ) -> paginatorinput:
        cogs: List[Cog] = [cog for cog in mapping.keys() if cog and self._show(cog)]

        _embed = Embed(colour=self.context.bot.config.data.colours.neutral).set_image(
            url="attachment://Banner.png"
        )

        _ = "\n".join(f"{cog.qualified_name}: {cog.doc}" for cog in cogs)
        _embed.description = f"```yaml\n{_.strip()}```"
        return paginatorinput(
            embed=_embed, file=self.context.bot.config.data.assets.banner
        )

    async def send_cog_help(self, cog: Cog) -> None:
        await self._send(await self._get_cog_help(cog))

    async def _get_cog_help(self, cog: Cog) -> Union[List[Embed], Embed]:
        if not self._show(cog):
            return await self.send_error_message(self.command_not_found(self.context.message.content.removeprefix(f"{self.context.prefix}help ")))
        
        commands: List[Command] = await self.filter_commands(cog.get_commands())
        grouped: List[List[Command]] = [
            commands[i:PER_PAGE] for i in range(0, len(commands), PER_PAGE)
        ]

        embeds = []

        for _ in grouped:
            desc = "\n".join(f"{c.qualified_name}: {c.brief}" for c in _)
            embeds.append(
                Embed(
                    colour=self.context.bot.config.data.colours.neutral,
                    description=desc,
                )
            )

        if len(embeds) == 1:
            return embeds[0]
        return embeds

    async def _basic_command_help(self, command: Union[Command, Group]):
        desc = [
            "```",
            self.get_command_signature(command),
            f"```",
            command.help or "No help provided!",
        ]

        embed = Embed(
            description="\n".join(desc),
            colour=self.context.bot.config.data.colours.neutral,
        )

        if command.cog_name:
            embed.add_field(name="Category", value=f"```\n{command.cog_name}```")

        embed.add_field(
            name="Runnable by you, here?",
            value=f"```\n{'Yes' if command in await self.filter_commands([command]) else 'No'}```",
        )

        if getattr(command, "examples", None):
            examples = "\n".join(f"{self.context.clean_prefix}{command.qualified_name} {example}" for example in command.examples)
            embed.add_field(name="Examples", value=f"```\n{examples}```", inline=False)
            
        return embed

    async def send_command_help(self, command: Command) -> None:
        if not self._show(command):
            return await self.send_error_message(self.command_not_found(self.context.message.content.removeprefix(f"{self.context.prefix}help ")))
        await self._send(await self._get_command_help(command))

    async def _get_command_help(self, command: Command) -> Union[List[Embed], Embed]:
        return await self._basic_command_help(command)

    async def send_group_help(self, group: Group):
        if not self._show(group):
            return await self.send_error_message(self.command_not_found(self.context.message.content.removeprefix(f"{self.context.prefix}help ")))
        await self._send(await self._get_group_help(group))
        
    async def _get_group_help(self, group: Group):
        embed = await self._basic_command_help(group)
        
        embed.description += "\n```yaml" + "\n".join(f"{c.qualified_name}: {c.short_doc}" for c in await self.filter_commands(group.commands)) + "```"
        
        return embed
    
    async def send_error_message(self, error):
        await self._send(Embed(title="Error!", description=f"```\n{error}```", colour=self.context.bot.config.data.colours.bad))


class Help(Cog):
    """
    The help category
    """

    def __init__(self, bot: Nexus):
        self.bot = bot
        self._old_help_command = self.bot.help_command

        _help_command = NexusHelp()
        _help_command.add_check(bot_has_permissions(embed_links=True))

        self.bot.help_command = _help_command
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._old_help_command


def setup(bot: Nexus):
    bot.add_cog(Help(bot))