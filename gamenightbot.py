import asyncio
from datetime import date, datetime, timedelta
from dateparser import parse
import time
import discord
import random
from discord.utils import get
from discord.ext import commands, tasks
import json
import os
import boto3

client = commands.Bot(command_prefix='/', help_command=None)
reactions = {'🇲': "Monday", '2️⃣': "Tuesday", '🇼': "Wednesday", '🇹': "Thursday", '🇫': "Friday", '🚫': "Can't attend"}
users = [int(user) for user in os.environ.get("USERS").split(',')]
channel_id = int(os.environ.get("CHANNEL"))
dow={d:i for i,d in
         enumerate('monday,tuesday,wednesday,thursday,friday'.split(','))}
S3_BUCKET = os.environ.get('S3_BUCKET')


def save_to_s3(file_name):
    s3_client = boto3.client('s3')
    s3_client.upload_file(file_name, S3_BUCKET, file_name)


def load_from_s3(file_name):
    s3_client = boto3.client('s3')
    s3_client.download_file(S3_BUCKET, file_name, file_name)

load_from_s3("state.json")
with open("state.json") as file:
    state = json.load(file)

@client.event
async def on_ready():
    print(f"Bot start up. Loaded state={state}")
    check_time.start()


async def get_date_for_day(weekday):
    day = dow[weekday.lower()]
    date = datetime.today()
    while date.weekday() != day:
        date += timedelta(days=1)
    return weekday + date.strftime(" %B %d, %Y")


async def save_state(field,value):
    state[field] = value
    print(f"state saved {state} with field={field} value={value}")
    with open("state.json", "w") as fh:
        json.dump(state, fh)
    save_to_s3("state.json")
    return


async def update_poll_status(message, status):
    if message.embeds:
        embed = message.embeds[0]
        fields = embed.fields
        if len(fields) == 0 or status == "closed":
            embed.clear_fields()
            embed.add_field(name="poll_status", value=status, inline=True)
            await message.edit(embed=embed)
            return True
        elif status == "open":
            embed.clear_fields()
            await message.edit(embed=embed)
            return False
        else:
            return False
    else:
        embed = discord.Embed()
        embed.add_field(name="poll_status", value=status, inline=True)
        if status == "open":
            embed.clear_fields()
        await message.edit(embed=embed)
        return True


async def winners(message):
    counts = {r.emoji: r.count-1 for r in message.reactions if r.emoji in reactions}
    opt_outs = counts['🚫']
    max_players = len(users) - opt_outs
    if opt_outs > max_players:
        return {'🚫': opt_outs}
    else:
        return {r: counts[r] for r in counts if counts[r] == max_players}


async def prompt_host(host):
    await host.send(f"""Howdy {host.name}! You are this week's host!
Type ```/suggest [start_time] [game_name]``` to make a suggestion.
`start_time` should be one word e.g `8pm` while `game_name` can be any number of words.
Your suggestion will be announced in the channel where the poll took place. Choose wisely!
    """)


async def prompt_tiebreaker(host, choices):
    tied = []
    for key in choices:
        tied.append(f"{reactions[key]}({key})")
    await host.send(f"""{', '.join(tied[:-1])} and {tied[-1]} have {"both" if (len(tied) == 2) else "all"} tied.
As the host you can break the tie by choosing which of these days you would prefer.
Type ```/tiebreak [day_of_the_week]``` to break the tie.
Day of the week should be expressed as a word, e.g ```/tiebreak Monday```
Can't decide? Type `/tiebreak random` and I'll break the tie for you!
    """)


async def choose_host(channel, choices):
    last_host = state.get("last_host", users[0])
    new_host_idx = users.index(last_host) + 1
    if new_host_idx >= len(users):
        new_host_idx = 0
    new_host = users[new_host_idx]
    print(f" {last_host} has been succeeded by new host {new_host}")
    host = client.get_user(new_host)
    announce = f""" <@{host.id}> is this week's host.
{"They will first be asked to break the tie between the winning votes." if len(choices) > 1 else ""}
They will receive a DM which will allow them to suggest a start time and game for {reactions[choices[0]] if len(choices) == 0 else "the winning"} night.
    """
    await channel.send(announce)
    if len(choices) == 1:
        day_and_date = await get_date_for_day(reactions[choices[0]])
        await save_state("game_night", day_and_date)
        await prompt_host(host)
    else:
        await save_state("tied", [reactions[choice] for choice in choices])
        await prompt_tiebreaker(host, choices)
    await save_state("last_host", host.id)


async def tally(message):
    leading = await winners(message)
    if len(leading) == 0:
        return
    is_closing = await update_poll_status(message, "closing")
    if not is_closing:
        return
    await asyncio.sleep(10)
    recount = await winners(message)
    channel = client.get_channel(channel_id)
    if len(recount) == 1:
        key, count = recount.popitem()
        if key == '🚫':
            resp = f"""Game night is **CANCELLED** as a majority({count}) of players have indicated they can't attend({key}).
See you all next week for more games!               
            """
            await channel.send(resp)
        else:
            resp = f"{reactions[key]}({key}) has won with {count} votes!"
            await channel.send(resp)
            await choose_host(channel, [key])
        await update_poll_status(message, "closed")
    elif len(recount) >= 1:
        tied = []
        choices = []
        for key in recount:
            tied.append(f"{reactions[key]}({key})")
            choices.append(key)
        _, count = recount.popitem()
        await channel.send(f"""{", ".join(tied[:-1])} and {tied[-1]} have {"both" if (len(tied) == 2 )  else "all"} tied with {count} votes! This tie will be broken by this weeks host.""")
        await choose_host(channel, choices)
        await update_poll_status(message, "closed")
    else:
        await update_poll_status(message, "open")


@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id != channel_id:
        return
    channel = client.get_channel(channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = payload.emoji.name
    is_poll = False
    if message.embeds:
        embed = message.embeds[0]
        if embed.title != embed.Empty and embed.title.startswith("Weekly"):
            print("embed weekly")
            is_poll = True
    elif message.mention_everyone and "weekly poll" in message.content:
        print("everyone_plus_text")
        is_poll = True
    if is_poll:
        if emoji in reactions and len(message.reactions) >= len(reactions):
            print(f"Reaction {emoji} is in {reactions}")
            await tally(message)


async def remind(reminder):
    message = f"""@everyone
It's game night!
Tonight we will be playing {reminder['game_name']} @ {reminder['start_time']}. Have fun! :rollHigh:
    """
    channel = client.get_channel(channel_id)
    await channel.send(message)
    await save_state("remind_at", float('Inf'))
    await save_state("reminder", None)


async def poll_time():
    message = """@everyone
The weekly poll is ready! Please indicate your availability below:
:regional_indicator_m: - Monday
2️⃣ - Tuesday
:regional_indicator_w: - Wednesday
:regional_indicator_t: - Thursday
:regional_indicator_f: - Friday
:no_entry_sign: - Can't attend
A winning day will be announced once everyone has voted.
    """
    channel = client.get_channel(channel_id)
    msg = await channel.send(message)
    today = date.today().strftime("%B %d, %Y")
    embed = discord.Embed(title=f"Weekly game night poll - {today}")
    await msg.edit(embed=embed)
    for reaction in reactions.keys():
        await msg.add_reaction(reaction)
    next_poll = datetime.now() + timedelta(days=7)
    print(f"next poll is at {next_poll}")
    await save_state("next_poll_at", next_poll.timestamp())


async def check_dm_with_host(ctx):
    host = state.get("last_host", 0)
    if ctx.message.channel.type != discord.ChannelType.private:
        await ctx.message.add_reaction('🙉')
        await ctx.author.send(f"Sorry the command you tried to invoke (`/{ctx.command.name}`) in #{ctx.message.channel.name} on {ctx.message.channel.guild} is limited to direct message only,")
        return False
    elif ctx.author.id != host:
        await ctx.author.send("Sorry, only the weekly host can perform this action.")
        return False
    return True


@commands.check(check_dm_with_host)
@client.command()
async def suggest(ctx, start_time, *gamename):
    host = ctx.message.author
    game_name = " ".join(gamename)
    reminder = {"start_time": start_time, "game_name": game_name}
    game_night = state.get("game_night", "game night")
    remind_at = parse(f"{start_time} {game_night}")
    if remind_at is None:
        await ctx.send(f"Sorry I had trouble understanding {start_time} as a a start time. Please try again.")
        return
    await ctx.send(f"Ok, I'll announce your suggestion of {game_name} @ {start_time} on {game_night}.")
    await save_state("remind_at", (remind_at - timedelta(hours=1)).timestamp())
    await save_state("reminder", reminder)
    channel = client.get_channel(channel_id)
    announce = f"""@everyone The poll has concluded. 
{host.mention} has suggested we play **{game_name}** @ **{start_time}** on **{game_night}**.
I'll remind this channel an hour before then."""
    await channel.send(announce)


@commands.check(check_dm_with_host)
@client.command()
async def tiebreak(ctx, weekday):
    weekday = weekday.capitalize()
    host = ctx.message.author
    options = state.get("tied", [])
    if len(options) == 0:
        await ctx.send("Sorry, there doesn't seem to be a tie for you to break this week.")
    if weekday == "Random":
        weekday = random.choice(options)
        await ctx.send(f"Sure, I've chosen {weekday} at random for you.")
    if weekday in options:
        await ctx.send(f"Ok, I'll set {weekday} as the game night.")
        day_and_date = await get_date_for_day(weekday)
        await save_state("game_night", day_and_date)
        await save_state("tied", [])
        await prompt_host(host)
    else:
        await ctx.send(f"Sorry, I didn't recognize {weekday} as one of the options for the tie break. Try again. ")


@tasks.loop(minutes=15)
async def check_time():
    if state.get("next_poll_at", 0) <= time.time():
        print("Poll starting")
        await poll_time()
    if state.get("remind_at", float('Inf')) <= time.time():
        reminder = state.get("reminder", None)
        if reminder:
            await remind(reminder)


client.run(os.environ.get("DISCORD_BOT_TOKEN"))