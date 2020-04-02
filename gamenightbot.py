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
reactions = {'🇫': "Friday", '🇸': "Saturday", '☀️': "Sunday", '🇲': "Monday", '2️⃣': "Tuesday", '🇼': "Wednesday", '🇹': "Thursday", '🚫': "Can't attend"}
timeslots = {'1️⃣': "1pm - 3pm", '2️⃣': "3pm - 5pm", '3️⃣': "5pm - 7pm", '4️⃣': "7pm - 9pm", '5️⃣':"9pm-11pm", '🚫': "Can't attend"}
dow={d:i for i,d in
         enumerate('monday,tuesday,wednesday,thursday,friday,saturday,sunday'.split(','))}
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
    ts = state.get("next_poll_at")
    future_date = datetime.utcfromtimestamp(ts)
    while future_date.weekday() != day:
        future_date -= timedelta(days=1)
    return weekday + future_date.strftime(" %B %d, %Y")


async def save_state(field,value):
    state[field] = value
    print(f"state saved {state} with field={field} value={value}")
    with open("state.json", "w") as fh:
        json.dump(state, fh)
    save_to_s3("state.json")
    return


async def update_poll_status(message, status):
    channel = client.get_channel(state.get("channel_id"))
    message = await channel.fetch_message(message.id)
    if message.embeds:
        embed = message.embeds[0]
        fields = embed.fields
        if len(fields) == 0 or status == "closed":
            embed.clear_fields()
            embed.add_field(name="poll_status", value=status, inline=True)
            await message.edit(embed=embed)
            return True
        else:
            return False
    else:
        embed = discord.Embed()
        embed.add_field(name="poll_status", value=status, inline=True)
        await message.edit(embed=embed)
        return True


async def winners(message, is_timeslot):
    emojis = timeslots if is_timeslot else reactions
    counts = {r: r.count-1 for r in message.reactions if r.emoji in emojis}
    cancel = [react for react in message.reactions if react.emoji == '🚫'][0]
    opt_outs = counts[cancel]
    max_players = len(state.get("users")) - opt_outs
    if opt_outs > max_players:
        return {cancel: opt_outs}
    else:
        winning = {r: counts[r] for r in counts if counts[r] == max_players}
        total_voters = []
        users = state.get("users")
        for k in counts:
            voters = await k.users().flatten()
            total_voters.append(voters)
        flat_list = [voter for sublist in total_voters for voter in sublist]
        voter_ids = set([voter.id for voter in flat_list])
        non_voters = set(users) - set(voter_ids)
        if len(non_voters) == 0:
            await save_state("late", None)
        elif len(non_voters) == 1:
            late = client.get_user(non_voters.pop())
            nudgee = state.get("late", None)
            if nudgee and nudgee == late.id:
                pass
            else:
                await save_state("nudge_at", (datetime.now() + timedelta(hours=2)).timestamp())
                await save_state("late", late.id)
        return winning


async def nudge(late):
    channel_id = state.get("channel_id")
    await late.send(f"""Hey {late.name}! Looks like your vote could help close out a poll in <#{channel_id}>. Get voting!""")
    await save_state("nudge_at", float('Inf'))
    await save_state("late", None)


async def prompt_host(host, options):
    timeslot = ""
    if len(options) == 1:
        timeslot = f"""A time between **{options[0]}** best suits the group so try to stick to that range!"""
    elif len(options) > 1:
        timeslot = f"""**{', '.join(options[:-1])} and {options[-1]}** have {"both" if (len(options) == 2) else "all"} tied as times that suit the group.
Feel free to pick a time slot that falls in any of those ranges!"""
    await host.send(f"""Howdy {host.name}! You are this week's host!
Type ```/suggest [start_time] [game_name]``` to make a suggestion.
`start_time` should be one word e.g `8pm` while `game_name` can be any number of words. Timezone is GMT+1.
{timeslot}
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

async def poll_timeslot(weekend, count):
    message = f"""@everyone
{reactions[weekend]}({weekend}) has won with {count} votes!
Weekends are a busier time so let's try to narrow down a range for the start time. All times are GMT+!.
1️⃣ - Starting between 1pm and 3pm
2️⃣ - Starting between 3pm and 5pm
3️⃣ - Starting between 5pm and 7pm
4️⃣ - Starting between 7pm and 9pm
5️⃣ - Starting between 9pm and 11pm
:no_entry_sign: - Can't attend

    """
    channel = client.get_channel(state.get("channel_id"))
    msg = await channel.send(message)
    for reaction in timeslots.keys():
        await msg.add_reaction(reaction)
    await save_state("side_poll", msg.id)
    await save_state("weekend", reactions[weekend])

async def choose_host(channel, choices):
    users = state.get("users")
    last_host = state.get("last_host", users[0])
    filtered_choices = []
    new_host_idx = users.index(last_host)
    next_host_idx = users.index(last_host) + 1
    if next_host_idx >= len(users):
        next_host_idx = 0
    while len(filtered_choices) < 1:
        new_host_idx += 1
        if new_host_idx >= len(users):
            new_host_idx = 0
        new_host = users[new_host_idx]
        for vote in choices:
            voters = await vote.users().flatten()
            voter_ids = [voter.id for voter in voters]
            if new_host in voter_ids:
                filtered_choices.append(vote.emoji)
    choices = filtered_choices
    users[new_host_idx], users[next_host_idx] = users[next_host_idx], users[new_host_idx]
    print(f" {last_host} has been succeeded by new host {new_host}")
    host = client.get_user(new_host)
    announce = f""" <@{host.id}> is this week's host. {"They will first be asked to break the tie between the winning votes." if len(choices) > 1 else ""}
They will receive a DM which will allow them to suggest a start time and game for the winning day.
    """
    await channel.send(announce)
    weekend = state.get("weekend", None)
    emojis = timeslots if weekend else reactions
    if weekend:
        await save_state("side_poll", None)
        await save_state("weekend", None)
        day_and_date = await get_date_for_day(weekend)
        await save_state("game_night", day_and_date)
        options = [emojis[choice] for choice in choices]
        await prompt_host(host, options)
    elif len(choices) == 1:
        day_and_date = await get_date_for_day(reactions[choices[0]])
        await save_state("game_night", day_and_date)
        await prompt_host(host, [])
    else:
        await save_state("tied", [emojis[choice] for choice in choices])
        await prompt_tiebreaker(host, choices)
    await save_state("last_host", host.id)


async def tally(message , is_timeslot=False):
    leading = await winners(message, is_timeslot)
    if len(leading) == 0:
        return
    is_closing = await update_poll_status(message, "closing")
    if not is_closing:
        return
    await asyncio.sleep(30)
    channel = client.get_channel(state.get("channel_id"))
    message = await channel.fetch_message(message.id)
    recount = await winners(message, is_timeslot)
    channel = client.get_channel(state.get("channel_id"))
    emojis = timeslots if is_timeslot else reactions

    if len(recount) == 1:
        key, count = recount.popitem()
        await save_state("open_poll", None)
        if key.emoji == '🚫':
            resp = f"""Game day is **CANCELLED** as a majority({count}) of players have indicated they can't attend({key.emoji}).
See you all next week for more games!               
            """
            await channel.send(resp)
        elif key.emoji in ['🇸', '☀️']:
            await poll_timeslot(key.emoji, count)
        else:
            resp = f"{emojis[key.emoji]}({key.emoji}) has won with {count} votes!"
            await channel.send(resp)
            await choose_host(channel, [key])
        await update_poll_status(message, "closed")
    elif len(recount) >= 1:
        tied = []
        choices = []
        await save_state("open_poll", None)
        for key in recount:
            tied.append(f"{emojis[key.emoji]}({key.emoji})")
            choices.append(key)
        _, count = recount.popitem()
        await channel.send(f"""{", ".join(tied[:-1])} and {tied[-1]} have {"both" if (len(tied) == 2 )  else "all"} tied with {count} votes! This tie will be broken by this weeks host.""")
        await choose_host(channel, choices)
        await update_poll_status(message, "closed")


@client.event
async def on_raw_reaction_add(payload):
    open_poll = state.get("open_poll", None)
    side_poll = state.get("side_poll", None)
    if payload.channel_id == state.get("channel_id") and side_poll and side_poll == payload.message_id:
        channel = client.get_channel(state.get("channel_id"))
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji.name
        if emoji in timeslots and len(message.reactions) >= len(timeslots):
            print(f"Reaction {emoji} is in {timeslots}")
            await tally(message, True)
    elif payload.channel_id == state.get("channel_id") and open_poll and open_poll == payload.message_id:
        channel = client.get_channel(state.get("channel_id"))
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji.name
        if emoji in reactions and len(message.reactions) >= len(reactions):
            print(f"Reaction {emoji} is in {reactions}")
            await tally(message)


async def remind(reminder):
    channel = client.get_channel(state.get("channel_id"))
    emoji = get(channel.guild.emojis, name='rollHigh')
    message = f"""@everyone
It's game day!
Today we will be playing **{reminder['game_name']}** @ **{reminder['start_time']}**(approximately 1 hour from now), Have fun! {emoji}
    """
    await channel.send(message)
    await save_state("remind_at", float('Inf'))
    await save_state("reminder", None)


async def poll_time():
    message = """@everyone
The weekly poll is ready! Please indicate your availability below:
:regional_indicator_f: - Late night Friday (starting from 10pm GMT+1)
:regional_indicator_s: - Saturday (A secondary poll to pick a time slot will follow)
:sunny: - Sunday (A secondary poll to pick a time slot will follow)
:regional_indicator_m: - Monday
2️⃣ - Tuesday
:regional_indicator_w: - Wednesday
:regional_indicator_t: - Thursday
:no_entry_sign: - Can't attend
A winning day will be announced once everyone has voted.
    """
    channel = client.get_channel(state.get("channel_id"))
    msg = await channel.send(message)
    today = date.today().strftime("%B %d, %Y")
    embed = discord.Embed(title=f"Weekly game day poll - {today}")
    await msg.edit(embed=embed)
    for reaction in reactions.keys():
        await msg.add_reaction(reaction)
    await save_state("open_poll", msg.id)
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
    game_night = state.get("game_night", "game day")
    remind_at = parse(f"{start_time} {game_night}")
    if remind_at is None or remind_at.timestamp() <= time.time():
        await ctx.send(f"Sorry I had trouble understanding {start_time} as a a start time. Please try again.")
        return
    await ctx.send(f"Ok, I'll announce your suggestion of {game_name} @ {start_time} on {game_night}.")
    await save_state("remind_at", remind_at.timestamp())
    await save_state("reminder", reminder)
    channel = client.get_channel(state.get("channel_id"))
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
        await ctx.send(f"Ok, I'll set {weekday} as the game day.")
        day_and_date = await get_date_for_day(weekday)
        await save_state("game_night", day_and_date)
        await save_state("tied", [])
        ivd = {v: k for k, v in reactions.items()}
        if weekday in ["Saturday", "Sunday"]:
            users = state.get("users")
            last_host = state.get("last_host", users[0])
            before = users.index(last_host) - 1
            await save_state("last_host", users[before])
            await poll_timeslot(ivd[weekday], "the most")
        else:
            await prompt_host(host, [])
    else:
        await ctx.send(f"Sorry, I didn't recognize {weekday} as one of the options for the tie break. Try again. ")


@tasks.loop(minutes=1)
async def check_time():
    if state.get("next_poll_at", 0) <= time.time():
        print("Poll starting")
        await poll_time()
    if state.get("remind_at", float('Inf')) <= time.time():
        reminder = state.get("reminder", None)
        if reminder:
            await remind(reminder)
    if state.get("nudge_at", float('Inf') <= time.time()):
        nudgee = state.get("late", None)
        if nudgee:
            late = client.get_user(nudgee)
            await nudge(late)
        else:
            await save_state("nudge_at", float('Inf'))


client.run(os.environ.get("DISCORD_BOT_TOKEN"))