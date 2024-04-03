import discord
from discord.ext import commands
from music import BotMusic
from phrases import BotPhrases
import asyncio

bot = commands.Bot(command_prefix="#", intents=discord.Intents.all())

asyncio.run(bot.add_cog(BotMusic(bot)))
asyncio.run(bot.add_cog(BotPhrases(bot)))

with open("token.txt", "r") as tokenfile:
    token = tokenfile.read().strip()
    bot.run(token)
