mport discord
from discord.ext import tasks
from discord import app_commands
from collections import defaultdict
import asyncio
from typing import Literal

# Hardcoded token
TOKEN = ""

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

EMBED_COLOR = 0x2f3136
DENIED_EMOJI = "<:Denied:1394932620952997959>"
ACCEPTED_EMOJI = "<:Accepted:1394932663952871505>"

whitelist = set()
logs_channel = {}
antinuke_settings = defaultdict(set)
vanity_protection = {}
ping_on_join_channels = defaultdict(set)

VALID_ANTINUKE_FEATURES = [
    "ban", "kick", "deleting roles", "adding roles", "deleting channels", "adding channels",
    "pruning members", "adding bots", "giving administrator", "giving dangerous permissions",
    "vanity protection"
]

@tasks.loop(seconds=3)
async def check_vanity():
    for guild_id, protected_vanity in vanity_protection.items():
        guild = client.get_guild(guild_id)
        if guild:
            try:
                current_vanity = (await guild.vanity_invite()).code
                if current_vanity != protected_vanity:
                    await guild.edit(vanity_code=protected_vanity)
                    await log_action(guild, f"Vanity URL reset to `{protected_vanity}` by anti-nuke.")
            except Exception:
                pass

async def log_action(guild, description):
    if guild.id in logs_channel:
        chan = guild.get_channel(logs_channel[guild.id])
        if chan:
            embed = discord.Embed(title="Anti-Nuke Alert", description=description, color=EMBED_COLOR)
            await chan.send(embed=embed)

@tree.command(name="whitelist", description="Manage whitelist users")
@app_commands.describe(action="Add, remove or list users", user="User to add or remove")
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list")
])
async def whitelist_cmd(interaction: discord.Interaction, action: app_commands.Choice[str], user: discord.User = None):
    if interaction.user != interaction.guild.owner:
        await interaction.response.send_message(f"{DENIED_EMOJI} Only the server owner can use this command.", ephemeral=True)
        return

    if action.value == "add":
        if not user:
            await interaction.response.send_message(f"{DENIED_EMOJI} You must specify a user to add.", ephemeral=True)
            return
        whitelist.add(user.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Added {user.mention} to whitelist.", color=EMBED_COLOR))

    elif action.value == "remove":
        if not user:
            await interaction.response.send_message(f"{DENIED_EMOJI} You must specify a user to remove.", ephemeral=True)
            return
        whitelist.discard(user.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Removed {user.mention} from whitelist.", color=EMBED_COLOR))

    else:
        if not whitelist:
            await interaction.response.send_message(f"{DENIED_EMOJI} Whitelist is empty.", ephemeral=True)
            return
        mentions = [f"<@{uid}>" for uid in whitelist]
        embed = discord.Embed(title="Whitelisted Users", description="\n".join(mentions), color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="logs", description="Set or view logs channel")
@app_commands.describe(channel="Channel to set for logs")
async def logs_cmd(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if interaction.user != interaction.guild.owner:
        await interaction.response.send_message(f"{DENIED_EMOJI} Only the server owner can use this command.", ephemeral=True)
        return

    if channel:
        logs_channel[interaction.guild.id] = channel.id
        await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Logs channel set to {channel.mention}.", color=EMBED_COLOR))
    else:
        if interaction.guild.id in logs_channel:
            chan = interaction.guild.get_channel(logs_channel[interaction.guild.id])
            if chan:
                await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Current logs channel is {chan.mention}.", color=EMBED_COLOR))
            else:
                await interaction.response.send_message(f"{DENIED_EMOJI} Logs channel not found.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{DENIED_EMOJI} No logs channel set.", ephemeral=True)

@tree.command(name="antinuke", description="Enable or disable anti-nuke features")
@app_commands.describe(action="Enable or disable a feature", feature="The feature to modify", vanity="Vanity string (required if feature is vanity protection)")
@app_commands.choices(feature=[app_commands.Choice(name=f, value=f) for f in VALID_ANTINUKE_FEATURES])
async def antinuke_cmd(interaction: discord.Interaction, action: Literal["enable", "disable"], feature: app_commands.Choice[str], vanity: str = None):
    if interaction.user != interaction.guild.owner:
        await interaction.response.send_message(f"{DENIED_EMOJI} Only the server owner can use this command.", ephemeral=True)
        return

    fname = feature.value.lower()

    if fname == "vanity protection":
        if action == "enable":
            if interaction.guild.premium_tier < 3:
                await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Server has not acquired level 3 boosts.", color=EMBED_COLOR))
                return
            if interaction.guild.id in vanity_protection:
                await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Vanity protection already enabled.", color=EMBED_COLOR))
                return
            if not vanity:
                await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} You must provide the vanity string to protect.", color=EMBED_COLOR))
                return
            vanity_protection[interaction.guild.id] = vanity
            await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Vanity protection enabled for `{vanity}`.", color=EMBED_COLOR))
        else:
            if interaction.guild.id not in vanity_protection:
                await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Vanity protection already disabled.", color=EMBED_COLOR))
                return
            vanity_protection.pop(interaction.guild.id)
            await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Vanity protection disabled.", color=EMBED_COLOR))
        return

    enabled_set = antinuke_settings[interaction.guild.id]
    if action == "enable":
        if fname in enabled_set:
            await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Antinuke {fname} already enabled.", color=EMBED_COLOR))
            return
        enabled_set.add(fname)
        await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Antinuke {fname} enabled.", color=EMBED_COLOR))
    else:
        if fname not in enabled_set:
            await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Antinuke {fname} already disabled.", color=EMBED_COLOR))
            return
        enabled_set.remove(fname)
        await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Antinuke {fname} disabled.", color=EMBED_COLOR))

@tree.command(name="ping-on-join", description="Enable or disable ping on member join in specified channels")
@app_commands.describe(action="Enable or disable pinging", channel="Channel to ping on join")
@app_commands.choices(action=[
    app_commands.Choice(name="enable", value="enable"),
    app_commands.Choice(name="disable", value="disable")
])
async def ping_on_join_cmd(interaction: discord.Interaction, action: app_commands.Choice[str], channel: discord.TextChannel):
    if interaction.user != interaction.guild.owner:
        await interaction.response.send_message(f"{DENIED_EMOJI} Only the server owner can use this command.", ephemeral=True)
        return

    if action.value == "enable":
        ping_on_join_channels[interaction.guild.id].add(channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{ACCEPTED_EMOJI} Ping on join enabled in {channel.mention}.", color=EMBED_COLOR))
    else:
        ping_on_join_channels[interaction.guild.id].discard(channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{DENIED_EMOJI} Ping on join disabled in {channel.mention}.", color=EMBED_COLOR))

@client.event
async def on_member_join(member):
    guild = member.guild
    if guild.id not in ping_on_join_channels:
        return
    for channel_id in ping_on_join_channels[guild.id]:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.send(f"{member.mention}")
                await asyncio.sleep(0.03)
                await msg.delete()
            except:
                pass

@tasks.loop(seconds=120)
async def rotate_status():
    statuses = [
        lambda: discord.Activity(type=discord.ActivityType.watching, name="🔗 discord.gg/heck"),
        lambda: discord.Activity(type=discord.ActivityType.watching, name=f"In {len(client.guilds)} Servers"),
        lambda: discord.Activity(type=discord.ActivityType.watching, name="Best Vanity Protection Bot")
    ]
    i = 0
    await client.wait_until_ready()
    while not client.is_closed():
        activity = statuses[i % len(statuses)]()
        await client.change_presence(status=discord.Status.idle, activity=activity)
        i += 1
        await asyncio.sleep(120)

@client.event
async def on_ready():
    await tree.sync()
    rotate_status.start()
    check_vanity.start()
    print(f"Logged in as {client.user}")

client.run(TOKEN)
