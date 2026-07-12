import random
import discord
from   discord.ext import commands
import requests
import config 
import os
import difflib
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

colas_musica = {}
historial_musica = {} 
cancion_actual = {}   

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
    
def reproducir_siguiente(ctx, error):
    if error:
        print(f"Error en el callback de reproducción: {error}")
    
    guild_id = ctx.guild.id
    
    terminada = cancion_actual.get(guild_id)
    if terminada:
        if guild_id not in historial_musica:
            historial_musica[guild_id] = []
        historial_musica[guild_id].append(terminada)
        cancion_actual[guild_id] = None 

    if guild_id in colas_musica and len(colas_musica[guild_id]) > 0:
        siguiente_cancion = colas_musica[guild_id].pop(0)
        coro = ejecutar_reproduccion(ctx.voice_client, siguiente_cancion, ctx)
        asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
    
    elif guild_id in radio_activada and len(radio_activada[guild_id]) > 0:
        siguiente_cancion = random.choice(radio_activada[guild_id])
        coro = ejecutar_reproduccion(ctx.voice_client, siguiente_cancion, ctx)
        asyncio.run_coroutine_threadsafe(coro, ctx.bot.loop)
        
    else:
       print(f"Cola y radio terminadas en el servidor {guild_id}.")


async def ejecutar_reproduccion(vc, ruta, ctx):
    guild_id = ctx.guild.id
    cancion_actual[guild_id] = ruta 
    
    audio_source = discord.FFmpegPCMAudio(
        ruta, 
        executable=r"C:\ffmpeg\bin\ffmpeg.exe", 
        options="-vn")
    
    vc.play(audio_source, after=lambda e: reproducir_siguiente(ctx, e))
    await ctx.send(f"🎶 Reproduciendo: **{os.path.basename(ruta)}**")
    
@bot.command()
async def play(ctx, *, busqueda: str):
    if not ctx.author.voice:
        return await ctx.send("❌ ¡Necesitas estar en un canal de voz!")
    if "/" not in busqueda:
        return await ctx.send("⚠️ Formato incorrecto. Por favor usa: `!play Nombre de la Banda / Nombre del Álbum`")
    
    banda_busqueda, album_busqueda = [parte.strip() for parte in busqueda.split("/", 1)]
    musica_path = "musica"
    bandas_disponibles = [b for b in os.listdir(musica_path) if os.path.isdir(os.path.join(musica_path, b))]
    match_banda = difflib.get_close_matches(banda_busqueda, bandas_disponibles, n=1, cutoff=0.5)
    
    if not match_banda:
        return await ctx.send(f"🔍 No encontré ninguna banda similar a **{banda_busqueda}**.")   
    banda_encontrada = match_banda[0]
    ruta_banda = os.path.join(musica_path, banda_encontrada)
    
    albumes_disponibles = [a for a in os.listdir(ruta_banda) if os.path.isdir(os.path.join(ruta_banda, a))]
    match_album = difflib.get_close_matches(album_busqueda, albumes_disponibles, n=1, cutoff=0.5)
    if not match_album:
        return await ctx.send(f"🔍 No encontré el álbum **{album_busqueda}** dentro de la banda **{banda_encontrada}**.")   
    album_encontrado = match_album[0]
    ruta_album = os.path.join(ruta_banda, album_encontrado)
    

    archivos_album = [os.path.join(ruta_album, f) for f in os.listdir(ruta_album) 
                      if f.lower().endswith(('.mp3', '.flac'))]
    archivos_album.sort() 
    if not archivos_album:
        return await ctx.send(f"⚠️ El álbum **{album_encontrado}** está vacío o no contiene archivos válidos.")

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client or await channel.connect()
    if ctx.voice_client and ctx.voice_client.channel != channel:
        await voice_client.move_to(channel)

    guild_id = ctx.guild.id
    colas_musica[guild_id] = archivos_album
    embed = discord.Embed(
        title=f"💿 {banda_encontrada} - {album_encontrado}",
        description=f"Se han añadido **{len(archivos_album)}** canciones a la cola.",
        color=discord.Color.blue())

    lista_texto = "\n".join([f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(archivos_album[:35])])
    if len(archivos_album) > 35:
        lista_texto += "\n... y más."
    embed.add_field(name="Pistas:", value=lista_texto, inline=False)
    
    await ctx.send(embed=embed)

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    else:
        siguiente_cancion = colas_musica[guild_id].pop(0)
        await ejecutar_reproduccion(voice_client, siguiente_cancion, ctx)

radio_activada = {}

@bot.command()
async def radio(ctx, *, banda_busqueda: str):
    if not ctx.author.voice:
        return await ctx.send("❌ ¡Necesitas estar en un canal de voz!")

    musica_path = "musica"
    bandas_disponibles = [b for b in os.listdir(musica_path) if os.path.isdir(os.path.join(musica_path, b))]
    match_banda = difflib.get_close_matches(banda_busqueda, bandas_disponibles, n=1, cutoff=0.5)

    if not match_banda:
        return await ctx.send(f"🔍 No encontré ninguna banda similar a **{banda_busqueda}**.")   
    
    banda_encontrada = match_banda[0]
    ruta_banda = os.path.join(musica_path, banda_encontrada)

    todas_las_canciones = []
    for raiz, directorios, archivos in os.walk(ruta_banda):
        for archivo in archivos:
            if archivo.lower().endswith(('.mp3', '.flac')):
                todas_las_canciones.append(os.path.join(raiz, archivo))
    
    if not todas_las_canciones:
        return await ctx.send(f"⚠️ No hay canciones válidas en la carpeta de la banda **{banda_encontrada}**.")

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client or await channel.connect()
    if ctx.voice_client and ctx.voice_client.channel != channel:
        await voice_client.move_to(channel)

    guild_id = ctx.guild.id
    radio_activada[guild_id] = todas_las_canciones
    colas_musica[guild_id] = [] 

    embed = discord.Embed(
        title=f"📻 Modo Radio Activado: {banda_encontrada}",
        description=f"Reproduciendo de forma aleatoria e indefinida entre **{len(todas_las_canciones)}** pistas.\n*(Se ha reemplazado la cola actual)*",
        color=discord.Color.green())
    await ctx.send(embed=embed)

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop() 
    else:
        cancion_random = random.choice(todas_las_canciones)
        await ejecutar_reproduccion(voice_client, cancion_random, ctx)
        
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
    vc = ctx.voice_client
    
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("No hay nada reproduciéndose para saltar.")

@bot.command()
async def bandas(ctx):
    ruta = r'D:\bot musics\musica' 
    carpetas = [d for d in os.listdir(ruta) if os.path.isdir(os.path.join(ruta, d))]
    if carpetas:
        await ctx.send(f"las bandas que hay son{carpetas}")

@bot.command(aliases=['back', 'anterior'])
async def volver(ctx):
    guild_id = ctx.guild.id
    voice_client = ctx.voice_client
    
    if not voice_client:
        return await ctx.send("❌ No estoy conectado a ningún canal de voz.")
        
    if guild_id not in historial_musica or len(historial_musica[guild_id]) == 0:
        return await ctx.send("⚠️ No hay canciones anteriores en el historial.")

    cancion_anterior = historial_musica[guild_id].pop()
    actual = cancion_actual.get(guild_id)
    cancion_actual[guild_id] = None 
    
    if guild_id not in colas_musica:
        colas_musica[guild_id] = []
    if actual:
        colas_musica[guild_id].insert(0, actual) 
    colas_musica[guild_id].insert(0, cancion_anterior) 
    
    await ctx.send("⏪ **Regresando a la canción anterior...**")
    
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop() 
    else:
        siguiente = colas_musica[guild_id].pop(0)
        await ejecutar_reproduccion(voice_client, siguiente, ctx)
        
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    
bot.run(config.TOKEN)