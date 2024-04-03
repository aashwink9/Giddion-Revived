import discord
from discord.ext import commands


class BotPhrases(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if "HI GIDDION" in message.content.upper():
            await message.channel.send(f"Hey {message.author}! nice to meet you, I'm Giddion! :D")
