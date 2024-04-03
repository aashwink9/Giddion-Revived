import discord
import yt_dlp as youtube_dl
import asyncio
from discord.ext import commands
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import json
import os


class BotMusic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

        self.is_playing = {}
        self.is_paused = {}
        self.music_queue = {}
        self.queue_index = {}
        self.is_in_vc = {}

        self.YTDL_OPTIONS = {
            "format": "bestaudio",
            "noplaylist": "True",
        }

        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            id = int(guild.id)
            self.music_queue[id] = []
            self.queue_index[id] = 0
            self.is_in_vc[id] = None
            self.is_paused[id] = False
            self.is_playing[id] = False

    async def join_vc(self, ctx, channel):
        id = int(ctx.guild.id)
        if not self.is_in_vc[id] or self.is_in_vc[id].is_connected():
            self.is_in_vc[id] = await channel.connect()

            if not self.is_in_vc[id]:
                await ctx.send("Could not connect to vc!")
                return
        else:
            await self.is_in_vc[id].move_to(channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        id = int(member.guild.id)
        if member.id != self.bot.user.id and before.channel is not None and after.channel != before.channel:
            remaining_members = before.channel.members
            if len(remaining_members) == 1 and remaining_members[0].id == self.bot.user.id \
                    and self.is_in_vc[id].is_connected():
                self.is_playing[id] = self.is_paused[id] = False
                self.music_queue[id] = []
                self.queue_index[id] = 0
                await self.is_in_vc[id].disconnect()

    @commands.command(
        name="join",
        aliases=["j"]
    )
    async def join(self, ctx):
        if ctx.author.voice:
            user_channel = ctx.author.voice.channel
            await self.join_vc(ctx, user_channel)
        else:
            await ctx.send("Please join a voice channel first!")

    @commands.command(
        name="leave",
        aliases=["l"]
    )
    async def leave(self, ctx):
        id = int(ctx.guild.id)
        self.is_playing[id] = self.is_paused[id] = False
        self.music_queue[id] = []
        self.queue_index = 0
        if self.is_in_vc[id]:
            await ctx.send("Disconnected to the voice channel! Buh Byeee!")
            await self.is_in_vc[id].disconnect()

    @commands.command(
        name="play",
        aliases=["p"]
    )
    async def play(self, ctx, *args):
        search = " ".join(args)
        id = int(ctx.guild.id)
        try:
            user_channel = ctx.author.voice.channel
        except:
            await ctx.send("Please connect to a voice channel first!")
            return

        if not args:
            if len(self.music_queue[id] == 0):
                await ctx.send("There are no songs in the queue!")
                return
            elif not self.is_playing[id]:
                if not self.music_queue[id] or not self.is_in_vc[id]:
                    await self.play_music(ctx)
                else:
                    self.is_paused[id] = False
                    self.is_playing[id] = True
                    self.is_in_vc[id].resume()
            else:
                return
        else:
            search_results = self.search_video(search)
            song = self.extract_yt(search_results[0])

            if type(song) == type(True):
                await ctx.send("Could not find the song, please try a different search query!")
            else:
                self.music_queue[id].append([song, user_channel])

                if not self.is_playing[id]:
                    await self.play_music(ctx)
                else:
                    ctx.send("Added to queue!")

    def search_video(self, search):
        query = parse.urlencode({'search_query': search})
        html_content = request.urlopen('http://www.youtube.com/results?' + query)
        search_results = re.findall('/watch\\?v=(.{11})', html_content.read().decode())
        for i in range(len(search_results)):
            search_results[i] = "https://www.youtube.com/watch?v=" + search_results[i]

        return search_results[:10]

    def extract_yt(self, url):
        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            try:
                info = ytdl.extract_info(url, download=False)
            except:
                return False

        if 'entries' in info:
            return {
                'link': 'https://www.youtube.com/watch?v=' + url,
                'source': info['entries'][0]['url'],
                'title': info['entries'][0]['title']
            }
        else:
            return {
                'link': 'https://www.youtube.com/watch?v=' + url,
                'source': info['url'],
                'title': info['title'],
            }

    def playing_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        author = ctx.author

        embed = discord.Embed(
            title="Now Playing",
            description=f'[{title}]({link})',
            color=0x4794ff
        )

        embed.set_footer(text=f"Song requested by: {str(author)}")

        return embed

    async def play_music(self, ctx):
        id = int(ctx.guild.id)
        if self.queue_index[id] < len(self.music_queue[id]):
            self.is_playing[id] = True
            self.is_paused[id] = False

            await self.join_vc(ctx, self.music_queue[id][self.queue_index[id]][1])

            song = self.music_queue[id][self.queue_index[id]][0]
            message = self.playing_embed(ctx, song)
            await ctx.send(embed=message)

            self.is_in_vc[id].play(
                discord.FFmpegPCMAudio(song['source']),
                after=lambda e: self.play_next(ctx)
            )

        else:
            ctx.send("No songs in the queue!")
            self.queue_index[id] += 1
            self.is_playing[id] = False

    def play_next(self, ctx):
        id = int(ctx.guild.id)
        if not self.is_playing[id]:
            return

        if self.queue_index[id] + 1 < len(self.music_queue[id]):
            self.is_playing[id] = True
            self.queue_index[id] += 1

            song = self.music_queue[id][self.queue_index[id][0]]

            message = self.playing_embed(ctx, song)
            cor = ctx.send(embed=message)
            do_coroutine = run_coroutine_threadsafe(cor, self.bot.loop)
            try:
                do_coroutine.result()
            except:
                pass

            self.is_in_vc[id].play_music(
                discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS),
                after=lambda e: self.play_next(ctx)
            )

        else:
            self.queue_index[id] += 1
            self.is_playing[id] = False

