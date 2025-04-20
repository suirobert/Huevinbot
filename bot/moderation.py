import discord
from discord.ext import commands
import asyncio

def setup_moderation_commands(bot):
    # Verificar permisos de moderador para todos los comandos
    async def check_mod_perms(ctx):
        if not ctx.author.guild_permissions.manage_roles or not ctx.author.guild_permissions.kick_members:
            await ctx.send("No tienes permisos para usar este comando. Necesitas permisos de moderación. 🔒")
            return False
        return True

    @bot.command()
    async def ban(ctx, member: discord.Member, *, reason: str = "No se especificó razón"):
        """Banea a un usuario del servidor."""
        if not await check_mod_perms(ctx):
            return
        
        try:
            await member.ban(reason=reason)
            await ctx.send(f"✅ {member.mention} ha sido baneado. Razón: {reason}")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para banear a este usuario. 😢")
        except discord.HTTPException:
            await ctx.send("Error al banear al usuario. Intenta de nuevo. 😢")

    @bot.command()
    async def unban(ctx, user_id: int, *, reason: str = "No se especificó razón"):
        """Desbanea a un usuario del servidor usando su ID."""
        if not await check_mod_perms(ctx):
            return
        
        try:
            user = await bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"✅ El usuario con ID {user_id} ha sido desbaneado. Razón: {reason}")
        except discord.NotFound:
            await ctx.send("No encontré a un usuario baneado con ese ID. 🔍")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para desbanear a este usuario. 😢")
        except discord.HTTPException:
            await ctx.send("Error al desbanear al usuario. Intenta de nuevo. 😢")

    @bot.command()
    async def kick(ctx, member: discord.Member, *, reason: str = "No se especificó razón"):
        """Expulsa a un usuario del servidor."""
        if not await check_mod_perms(ctx):
            return
        
        try:
            await member.kick(reason=reason)
            await ctx.send(f"✅ {member.mention} ha sido expulsado. Razón: {reason}")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para expulsar a este usuario. 😢")
        except discord.HTTPException:
            await ctx.send("Error al expulsar al usuario. Intenta de nuevo. 😢")

    @bot.command()
    async def mute(ctx, member: discord.Member, duration: int, *, reason: str = "No se especificó razón"):
        """Silencia a un usuario por un tiempo específico (en minutos)."""
        if not await check_mod_perms(ctx):
            return
        
        # Buscar o crear un rol de "Muted"
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            try:
                mute_role = await ctx.guild.create_role(name="Muted", reason="Rol creado para silenciar usuarios")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            except discord.Forbidden:
                return await ctx.send("No tengo permisos para crear un rol de Muted. 😢")

        try:
            await member.add_roles(mute_role, reason=reason)
            await ctx.send(f"✅ {member.mention} ha sido silenciado por {duration} minutos. Razón: {reason}")
            
            # Esperar la duración especificada y luego quitar el rol
            await asyncio.sleep(duration * 60)
            await member.remove_roles(mute_role, reason="Tiempo de silencio terminado")
            await ctx.send(f"✅ {member.mention} ha sido des-silenciado después de {duration} minutos.")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para silenciar a este usuario. 😢")
        except discord.HTTPException:
            await ctx.send("Error al silenciar al usuario. Intenta de nuevo. 😢")

    @bot.command()
    async def clear(ctx, amount: int):
        """Borra una cantidad específica de mensajes en el canal."""
        if not await check_mod_perms(ctx):
            return
        
        if amount < 1 or amount > 100:
            return await ctx.send("Por favor, especifica una cantidad entre 1 y 100 mensajes. 📉")
        
        try:
            await ctx.channel.purge(limit=amount + 1)  # +1 para incluir el mensaje del comando
            await ctx.send(f"✅ Se han borrado {amount} mensajes.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("No tengo permisos para borrar mensajes en este canal. 😢")
        except discord.HTTPException:
            await ctx.send("Error al borrar los mensajes. Intenta de nuevo. 😢")

    @bot.command()
    async def role(ctx, member: discord.Member, role: discord.Role):
        """Asigna un rol a un usuario."""
        if not await check_mod_perms(ctx):
            return
        
        try:
            await member.add_roles(role)
            await ctx.send(f"✅ Se ha asignado el rol {role.name} a {member.mention}.")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para asignar este rol. 😢")
        except discord.HTTPException:
            await ctx.send("Error al asignar el rol. Intenta de nuevo. 😢")
