import discord
from discord.ext import commands
import requests
import config 
import os
import difflib
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command()
async def unir(ctx):
    if ctx.author.voice:
        canal = ctx.author.voice.channel
        await canal.connect()
        await ctx.send(f"me uni a{canal.name}")
    else:
        await ctx.send("no estas en un canal de voz")

@bot.command()
async def salir(ctx):
    if ctx.author.voice: 
        await ctx.voice_client.disconnect()
        await ctx.send("chao")
    else:
        await ctx.send("No estoy en ningún canal de voz")

colas_musica = {}


def reproducir_siguiente(ctx, error):
    # Obtener el cliente de voz
    vc = ctx.voice_client
    if not vc:
        return

    guild_id = ctx.guild.id
    
    # Verificar si hay canciones en la cola
    if guild_id in colas_musica and len(colas_musica[guild_id]) > 0:
        siguiente_cancion = colas_musica[guild_id].pop(0)
        
        coro = ejecutar_reproduccion(vc, siguiente_cancion, ctx)
        asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
    else:
        if guild_id in colas_musica:
            del colas_musica[guild_id]

async def ejecutar_reproduccion(vc, ruta, ctx):

    await asyncio.sleep(0.5)
    
    if not vc.is_playing():
        audio_source = discord.FFmpegPCMAudio(ruta, executable=r"C:\ffmpeg\bin\ffmpeg.exe")
        vc.play(audio_source, after=lambda e: reproducir_siguiente(ctx, e))
        await ctx.send(f"🎶 Reproduciendo: **{os.path.basename(ruta)}**")
        
@bot.command()
async def play(ctx, *, album_busqueda: str):
    musica_path = "musica"
    album_encontrado = None
    ruta_album = None
    
    for banda in os.listdir(musica_path):
        ruta_banda = os.path.join(musica_path, banda)
        if os.path.isdir(ruta_banda):
            match = difflib.get_close_matches(album_busqueda, os.listdir(ruta_banda), n=1, cutoff=0.5)
            if match:
                album_encontrado = match[0]
                ruta_album = os.path.join(ruta_banda, album_encontrado)
                break
    
    if not ruta_album:
        return await ctx.send("No encontré ningún álbum con ese nombre.")                     
    archivos_album = [os.path.join(ruta_album, f) for f in os.listdir(ruta_album) 
                      if f.lower().endswith(('.mp3', '.flac'))]
    archivos_album.sort() 
    
    if not archivos_album:
        return await ctx.send("El álbum está vacío.")

    embed = discord.Embed(
        title=f"💿 Álbum: {album_encontrado}",
        description=f"Se han añadido **{len(archivos_album)}** canciones a la cola:",
        color=discord.Color.blue())

    lista_texto = "\n".join([f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(archivos_album[:15])])
    if len(archivos_album) > 15:
        lista_texto += "\n... y más."
    embed.add_field(name="Pistas:", value=lista_texto, inline=False)
    await ctx.send(embed=embed)
    if not ctx.author.voice:
        return await ctx.send("¡Necesitas estar en un canal de voz!")
    
    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client or await channel.connect()
    if ctx.voice_client and ctx.voice_client.channel != channel:
        await voice_client.move_to(channel)

    guild_id = ctx.guild.id
    colas_musica[guild_id] = archivos_album[1:] 
    
    audio_source = discord.FFmpegPCMAudio(archivos_album[0], executable=r"C:\ffmpeg\bin\ffmpeg.exe")
    if voice_client.is_playing(): voice_client.stop()
    voice_client.play(audio_source, after=lambda e: reproducir_siguiente(ctx, e))
    await ctx.send(f"🎶 Reproduciendo álbum: **{album_encontrado}**\n💿 Total de pistas: {len(archivos_album)}")

@bot.command()
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ **Reproducción pausada.**")
    elif voice_client and voice_client.is_paused():
        await ctx.send("⚠️ **La música ya está pausada.**")
    else:
        await ctx.send("❌ **No hay nada reproduciéndose actualmente.**")

@bot.command()
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ **Reproducción reanudada.**")
    else:
        await ctx.send("❌ **No hay nada pausado.**")

@bot.command()
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop() 
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("No hay nada sonando para saltar.")

@bot.command()
async def bandas(ctx):
    ruta = r'D:\bot musics\musica' 
    carpetas = [d for d in os.listdir(ruta) if os.path.isdir(os.path.join(ruta, d))]
    if carpetas:
        await ctx.send(f"las bandas que hay son{carpetas}")
        
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    
bot.run(config.TOKEN)