
import discord
from discord.ext import commands
import os
from groq import Groq

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
# intents.members = True  # Commented out - requires privileged intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Check if message mentions the bot or is a DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # Remove bot mention from message
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if content:
            await handle_ai_conversation(message, content)
    
    # Simple message responses for non-AI conversations
    elif message.content.lower() == "hello":
        await message.channel.send(f"Hello {message.author.mention}!")
    elif message.content.lower() == "how are you":
        await message.channel.send("I'm doing great! Thanks for asking!")
    
    # Process commands
    await bot.process_commands(message)

async def handle_ai_conversation(message, user_input):
    """Handle AI conversation using Groq"""
    try:
        # Show typing indicator
        async with message.channel.typing():
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are Chatty, a helpful Discord bot assistant in the {message.guild.name if message.guild else 'DM'} server. Be friendly, concise, and helpful. Keep responses under 2000 characters to fit Discord's message limit."
                    },
                    {
                        "role": "user", 
                        "content": user_input
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Split long responses if needed (Discord has 2000 char limit)
            if len(ai_response) > 2000:
                chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(ai_response)
                
    except Exception as e:
        print(f"Groq API Error: {e}")
        await message.channel.send("Sorry, I'm having trouble thinking right now. Please try again later!")

# Moderation Commands
@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason=None):
    """Kick a member from the server"""
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} has been kicked. Reason: {reason}')

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason=None):
    """Ban a member from the server"""
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} has been banned. Reason: {reason}')

@bot.command(name='unban')
@commands.has_permissions(ban_members=True)
async def unban_member(ctx, *, member):
    """Unban a member from the server"""
    banned_users = [entry async for entry in ctx.guild.bans()]
    member_name, member_discriminator = member.split('#')
    
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f'Unbanned {user.mention}')
            return
    
    await ctx.send(f'Member {member} not found in ban list.')

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute_member(ctx, member: discord.Member, *, reason=None):
    """Mute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f'{member.mention} has been muted. Reason: {reason}')

@bot.command(name='unmute')
@commands.has_permissions(manage_roles=True)
async def unmute_member(ctx, member: discord.Member):
    """Unmute a member"""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f'{member.mention} has been unmuted.')
    else:
        await ctx.send(f'{member.mention} is not muted.')

# Message Management
@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    """Clear messages in the channel"""
    if amount > 100:
        amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'Deleted {len(deleted) - 1} messages.', delete_after=5)

@bot.command(name='slowmode')
@commands.has_permissions(manage_channels=True)
async def set_slowmode(ctx, seconds: int):
    """Set slowmode for the channel"""
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("Slowmode disabled.")
    else:
        await ctx.send(f"Slowmode set to {seconds} seconds.")

# Channel Management
@bot.command(name='lock')
@commands.has_permissions(manage_channels=True)
async def lock_channel(ctx):
    """Lock the current channel"""
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔒 Channel locked.")

@bot.command(name='unlock')
@commands.has_permissions(manage_channels=True)
async def unlock_channel(ctx):
    """Unlock the current channel"""
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔓 Channel unlocked.")

# Utility Commands
@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command(name='userinfo')
async def user_info(ctx, member: discord.Member = None):
    """Get information about a user"""
    if member is None:
        member = ctx.author
    
    embed = discord.Embed(title=f"User Info - {member}", color=member.color)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Roles", value=len(member.roles), inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='serverinfo')
async def server_info(ctx):
    """Get server information"""
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.blue())
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await ctx.send(embed=embed)

# Welcome/Goodbye Messages
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='general')
    if channel:
        embed = discord.Embed(title="Welcome!", description=f"Welcome to {member.guild.name}, {member.mention}!", color=discord.Color.green())
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.channels, name='general')
    if channel:
        embed = discord.Embed(title="Goodbye!", description=f"{member.name} has left the server.", color=discord.Color.red())
        await channel.send(embed=embed)

# Role Management
@bot.command(name='addrole')
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, member: discord.Member, *, role_name):
    """Add a role to a member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        await ctx.send(f"Added {role.name} to {member.mention}")
    else:
        await ctx.send(f"Role {role_name} not found.")

@bot.command(name='removerole')
@commands.has_permissions(manage_roles=True)
async def remove_role(ctx, member: discord.Member, *, role_name):
    """Remove a role from a member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {member.mention}")
    else:
        await ctx.send(f"Role {role_name} not found or member doesn't have this role.")

# AI Commands
@bot.command(name='ask')
async def ask_ai(ctx, *, question):
    """Ask the AI a question"""
    try:
        async with ctx.typing():
            response = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful AI assistant. Provide accurate, helpful responses. Keep responses concise and under 2000 characters."
                    },
                    {
                        "role": "user", 
                        "content": question
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            embed = discord.Embed(
                title="🤖 AI Response",
                description=answer,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Asked by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
    except Exception as e:
        print(f"Groq API Error: {e}")
        await ctx.send("❌ Sorry, I couldn't process your question right now.")

@bot.command(name='explain')
async def explain_concept(ctx, *, concept):
    """Get an explanation of a concept"""
    try:
        async with ctx.typing():
            response = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an educational assistant. Explain concepts clearly and simply, as if teaching someone new to the topic. Use examples when helpful."
                    },
                    {
                        "role": "user", 
                        "content": f"Please explain: {concept}"
                    }
                ],
                max_tokens=600,
                temperature=0.5
            )
            
            explanation = response.choices[0].message.content
            
            embed = discord.Embed(
                title=f"📚 Explanation: {concept}",
                description=explanation,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
    except Exception as e:
        print(f"Groq API Error: {e}")
        await ctx.send("❌ Sorry, I couldn't explain that right now.")

@bot.command(name='summarize')
async def summarize_text(ctx, *, text):
    """Summarize a long text"""
    try:
        async with ctx.typing():
            response = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a text summarization assistant. Create concise, accurate summaries that capture the main points."
                    },
                    {
                        "role": "user", 
                        "content": f"Please summarize this text: {text}"
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            embed = discord.Embed(
                title="📝 Summary",
                description=summary,
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Summarized for {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
    except Exception as e:
        print(f"Groq API Error: {e}")
        await ctx.send("❌ Sorry, I couldn't summarize that right now.")

# Fun Commands
@bot.command(name='say')
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    """Make the bot say something"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name='embed')
@commands.has_permissions(manage_messages=True)
async def create_embed(ctx, title, *, description):
    """Create an embed message"""
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument.")
    else:
        await ctx.send("❌ An error occurred while processing the command.")

# Get tokens from environment variables
discord_token = os.getenv('DISCORD_TOKEN')
groq_api_key = os.getenv('GROQ_API_KEY')

if not discord_token:
    print("❌ Please set the DISCORD_TOKEN environment variable!")
    print("You can do this in the Secrets tab of your Repl.")
elif not groq_api_key:
    print("❌ Please set the GROQ_API_KEY environment variable!")
    print("You can do this in the Secrets tab of your Repl.")
    print("Get your API key from: https://console.groq.com/keys")
else:
    print("🤖 Starting Chatty - Your AI-powered Discord bot!")
    bot.run(discord_token)
