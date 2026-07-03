import discord
from discord.ext import commands
import requests
import config 
import os
import difflib

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

def reproducir_siguiente(ctx, error=None):
    if error:
        print(f"Error en la reproducción: {error}")
        
    guild_id = ctx.guild.id
    if guild_id in colas_musica and len(colas_musica[guild_id]) > 0:
        siguiente_cancion = colas_musica[guild_id].pop(0)
        
        vc = ctx.voice_client
        if vc and vc.is_connected():
            vc.play(discord.FFmpegPCMAudio(siguiente_cancion, executable=r"C:\ffmpeg\bin\ffmpeg.exe"), 
                after=lambda e: reproducir_siguiente(ctx, e))

@bot.command()
async def play(ctx, *, argumentos: str = None):
    if not argumentos or argumentos.count("/") != 2:
        await ctx.send("Por favor usa el formato: `banda / album / cancion`")
        return

    partes = [p.strip() for p in argumentos.split("/")]
    banda_input, album_input, cancion_input = partes
    musica_path = "musica" 
    
    bandas_encontradas = difflib.get_close_matches(banda_input, os.listdir(musica_path), n=1, cutoff=0.6)
    if not bandas_encontradas: 
        return await ctx.send("No encontré esa banda.")
    
    ruta_banda = os.path.join(musica_path, bandas_encontradas[0])
    albunes_encontrados = difflib.get_close_matches(album_input, os.listdir(ruta_banda), n=1, cutoff=0.6)
    if not albunes_encontrados: 
        return await ctx.send("No encontré ese álbum.")
    
    ruta_album = os.path.join(ruta_banda, albunes_encontrados[0])
    archivos_album = [f for f in os.listdir(ruta_album) if f.lower().endswith(('.mp3', '.flac'))]
    archivos_album.sort()
    
    cancion_encontrada = difflib.get_close_matches(cancion_input, archivos_album, n=1, cutoff=0.6)
    if not cancion_encontrada:
        return await ctx.send("No encontré esa canción en el álbum.")

    nombre_cancion_actual = cancion_encontrada[0]
    ruta_archivo = os.path.join(ruta_album, nombre_cancion_actual)

    if not ctx.author.voice:
        return await ctx.send("¡Necesitas estar en un canal de voz!")
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        voice_client = await channel.connect()
    else:
        voice_client = ctx.voice_client
        await voice_client.move_to(channel)

    guild_id = ctx.guild.id
    if guild_id not in colas_musica:
        colas_musica[guild_id] = []
    else:
        colas_musica[guild_id].clear() 

    indice_cancion = archivos_album.index(nombre_cancion_actual)
    canciones_restantes = archivos_album[indice_cancion + 1:]
    
    for cancion in canciones_restantes:
        ruta_completa_cancion = os.path.join(ruta_album, cancion)
        colas_musica[guild_id].append(ruta_completa_cancion)
    
    audio_source = discord.FFmpegPCMAudio(ruta_archivo, executable=r"C:\ffmpeg\bin\ffmpeg.exe")
    if voice_client.is_playing():
        voice_client.stop()
        
    voice_client.play(audio_source, after=lambda e: reproducir_siguiente(ctx, e))
    mensaje = f"🎶 Reproduciendo: **{nombre_cancion_actual}**"
    if len(canciones_restantes) > 0:
         mensaje += f"\n*Se añadieron {len(canciones_restantes)} pistas restantes del álbum a la cola.*"
         
    await ctx.send(mensaje)

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