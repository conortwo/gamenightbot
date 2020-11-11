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
reactions = {'🇹': "Thursday",'🇫': "Friday", '🇸': "Saturday", '☀️': "Sunday", '🇲': "Monday", '2️⃣': "Tuesday", '🇼': "Wednesday", '🚫': "Can't attend"}
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


four_player_bgg = {
    "Azul": "https://boardgamegeek.com/boardgame/230802/azul",
    "Burgle Bros": "https://boardgamegeek.com/boardgame/172081/burgle-bros",
    "Champions of Midgard": "https://boardgamegeek.com/boardgame/172287/champions-midgard",
    "Clank!": "https://boardgamegeek.com/boardgame/201808/clank-deck-building-adventure",
    "Cryptid": "https://boardgamegeek.com/boardgame/246784/cryptid",
    "Decrypto": "https://boardgamegeek.com/boardgame/225694/decrypto",
    "Dice Throne": "https://boardgamegeek.com/boardgame/216734/dice-throne-season-one",
    "Everdell": "https://boardgamegeek.com/boardgame/199792/everdell",
    "Forbidden Island": "https://boardgamegeek.com/boardgame/65244/forbidden-island",
    "Fort": "https://boardgamegeek.com/boardgame/296912/fort",
    "Ghost Stories": "https://boardgamegeek.com/boardgame/37046/ghost-stories",
    "Gloomhaven": "https://boardgamegeek.com/boardgame/174430/gloomhaven",
    "Root": "https://boardgamegeek.com/boardgame/237182/root",
    "Smash up": "https://boardgamegeek.com/boardgame/122522/smash",
    "Survive: Escape From Atlantis!": "https://boardgamegeek.com/boardgame/2653/survive-escape-atlantis",
    "Suburbia": "https://boardgamegeek.com/boardgame/123260/suburbia",
    "Terraforming Mars": "https://boardgamegeek.com/boardgame/167791/terraforming-mars",
    "T.I.M.E Stories": "https://boardgamegeek.com/boardgame/146508/time-stories",
    "Crokinole": "https://boardgamegeek.com/boardgame/521/crokinole",
    "Tragedy Looper": "https://boardgamegeek.com/boardgame/148319/tragedy-looper",
    "XCOM: The Board game": "https://boardgamegeek.com/boardgame/163602/xcom-board-game"
}

default_bgg = {
    "Cockroach Poker": "https://boardgamegeek.com/boardgame/11971/cockroach-poker",
    "7 Wonders": "https://boardgamegeek.com/boardgame/68448/7-wonders",
    "Betrayal at Baldur's Gate": "https://boardgamegeek.com/boardgame/228660/betrayal-baldurs-gate",
    "Blood Rage": "https://boardgamegeek.com/boardgame/170216/blood-rage",
    "Mysterium": "https://boardgamegeek.com/boardgame/181304/mysterium",
    "Coup": "https://boardgamegeek.com/boardgame/131357/coup",
    "Dead of Winter": "https://boardgamegeek.com/boardgame/150376/dead-winter-crossroads-game",
    "Eldritch Horror": "https://boardgamegeek.com/boardgame/146021/eldritch-horror",
    "Epic Spell Wars": "https://boardgamegeek.com/boardgame/112686/epic-spell-wars-battle-wizards-duel-mt-skullzfyre",
    "Forbidden Desert": "https://boardgamegeek.com/boardgame/136063/forbidden-desert",
    "Formula D": "https://boardgamegeek.com/boardgame/37904/formula-d",
    "Fury of Dracula": "https://boardgamegeek.com/boardgame/181279/fury-dracula-thirdfourth-edition",
    "Game of Thrones": "https://boardgamegeek.com/boardgame/103343/game-thrones-board-game-second-edition",
    "Lords of Vegas": "https://boardgamegeek.com/boardgame/20437/lords-vegas",
    "King of New York": "https://boardgamegeek.com/boardgame/160499/king-new-york",
    "Horrified": "https://boardgamegeek.com/boardgame/282524/horrified",
    "Lovecraft Letter": "https://boardgamegeek.com/boardgame/198740/lovecraft-letter",
    "Mansions of Madness": "https://boardgamegeek.com/boardgame/205059/mansions-madness-second-edition",
    "Pandemic: The Cure": "https://boardgamegeek.com/boardgame/150658/pandemic-cure",
    "Red Dragon Inn": "https://boardgamegeek.com/boardgame/24310/red-dragon-inn",
    "Rising Sun": "https://boardgamegeek.com/boardgame/205896/rising-sun",
    "Scythe": "https://boardgamegeek.com/boardgame/169786/scythe",
    "Shadows over Camelot": "https://boardgamegeek.com/boardgame/15062/shadows-over-camelot",
    "Sheriff of Nottingham": "https://boardgamegeek.com/boardgame/157969/sheriff-nottingham",
    "Space Alert": "https://boardgamegeek.com/boardgame/38453/space-alert",
    "Star Wars: Imperial Assault": "https://boardgamegeek.com/boardgame/164153/star-wars-imperial-assault",
    "Sub Terra": "https://boardgamegeek.com/boardgame/204472/sub-terra",
    "Quacks of Quedlinburg": "https://boardgamegeek.com/boardgame/244521/quacks-quedlinburg",
    "The Settlers of Catan": "https://boardgamegeek.com/boardgame/13/catan",
    "Ticket to Ride Europe": "https://boardgamegeek.com/boardgame/14996/ticket-ride-europe",
    "War of Whispers": "https://boardgamegeek.com/boardgame/253499/war-whispers",
    "Welcome To...": "https://boardgamegeek.com/boardgame/233867/welcome",
    "Western Legends": "https://boardgamegeek.com/boardgame/232405/western-legends",
}

five_player_bgg = {
    "The Resistance": "https://boardgamegeek.com/boardgame/41114/resistance",
    "A Fake Artist Goes to New York": "https://boardgamegeek.com/boardgame/135779/fake-artist-goes-new-york",
    "Battlestar Galactica": "https://boardgamegeek.com/boardgame/37111/battlestar-galactica-board-game",
    "Cash' n Guns": "https://boardgamegeek.com/boardgame/19237/cah-n-gun",
    "Deception: Murder in Hong Kong": "https://boardgamegeek.com/boardgame/156129/deception-murder-hong-kong",
    "Just One": "https://boardgamegeek.com/boardgame/254640/just-one",
    "The Resistance: Avalon": "https://boardgamegeek.com/boardgame/128882/resistance-avalon",
    "The Thing": "https://boardgamegeek.com/boardgame/226634/thing-infection-outpost-31",
    "Wavelength": "https://boardgamegeek.com/boardgame/262543/wavelength"
}

# default_games = {
#     "Bang! The Dice Game": "https://boardgamegeek.com/boardgame/143741/bang-dice-game",
#     "Betrayal Legacy": "https://boardgamegeek.com/boardgame/240196/betrayal-legacy",
#     "Camel Up": "https://boardgamegeek.com/boardgame/153938/camel",
#     "Cosmic Encounter": "https://boardgamegeek.com/boardgame/39463/cosmic-encounter",
#     "Deep Sea Adventure": "https://boardgamegeek.com/boardgame/169654/deep-sea-adventure",
#     "Lords of Waterdeep": "https://boardgamegeek.com/boardgame/110327/lords-waterdeep".
#     "Nemesis": "https://boardgamegeek.com/boardgame/167355/nemesis",
#     "Secret Hitler": "https://boardgamegeek.com/boardgame/188834/secret-hitler",
#     "Skull": "https://boardgamegeek.com/boardgame/92415/skull",
#     "Small World": "https://boardgamegeek.com/boardgame/40692/small-world",
#     "Wingspan": "https://boardgamegeek.com/boardgame/266192/wingspan",
#     "Camp Grizzly": "https://boardgamegeek.com/boardgame/143096/camp-grizzly",
#     "Inis": "https://boardgamegeek.com/boardgame/155821/inis",
#     "Zombicide": "https://boardgamegeek.com/boardgame/113924/zombicide"
#     "king of tokyo" : "",
#     "tokaido": "",
#     "Arkham horror the card game": "",
#     "Pandemic": "",
#     "Food Chain M": "",
#     "Love Letter": "",
#     "Mechs vs minions": "",
#     "Among us",
#     "Left 4 Dead 2",
#     "Garrys Mod",
#     "Jackbox PP",
#     "Pummel Party",
#     "Skribbl.io",
#     "Human Fall Flat",
#     "Golf with your friends"
# }


load_from_s3("state.json")
with open("state.json") as file:
    state = json.load(file)


@client.event
async def on_ready():
    print(f"Bot start up. Loaded state={state}")
    check_time.start()


async def get_date_for_day(channel_id, weekday):
    day = dow[weekday.lower()]
    ts = state[channel_id].get("next_poll_at")
    future_date = datetime.utcfromtimestamp(ts)
    while future_date.weekday() != day:
        future_date -= timedelta(days=1)
    return weekday + future_date.strftime(" %B %d, %Y")


async def save_state(channel_id, field, value):
    state[channel_id][field] = value
    print(f"state saved {state[channel_id]} with field={field} value={value}")
    with open("state.json", "w") as fh:
        json.dump(state, fh)
    save_to_s3("state.json")
    return


async def update_poll_status(channel_id, message, status):
    channel = client.get_channel(int(channel_id))
    message = await channel.fetch_message(message.id)
    if message.embeds:
        embed = message.embeds[0]
        embed.clear_fields()
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


async def winners(channel_id, message, is_timeslot):
    emojis = timeslots if is_timeslot else reactions
    counts = {r: r.count-1 for r in message.reactions if r.emoji in emojis}
    cancel = [react for react in message.reactions if react.emoji == '🚫'][0]
    opt_outs = counts[cancel]
    max_players = len(state[channel_id].get("users")) - opt_outs
    if opt_outs > max_players:
        return {cancel: opt_outs}
    else:
        winning = {r: counts[r] for r in counts if counts[r] == max_players}
        total_voters = []
        users = state[channel_id].get("users")
        for k in counts:
            voters = await k.users().flatten()
            total_voters.append(voters)
        flat_list = [voter for sublist in total_voters for voter in sublist]
        voter_ids = set([voter.id for voter in flat_list])
        non_voters = set(users) - voter_ids
        if len(non_voters) == 0:
            await save_state(channel_id, "late", None)
        elif len(non_voters) == 1:
            late = await client.fetch_user(non_voters.pop())
            nudgee = state[channel_id].get("late", None)
            if nudgee and nudgee == late.id:
                pass
            else:
                await save_state(channel_id, "nudge_at", (datetime.now() + timedelta(hours=1)).timestamp())
                await save_state(channel_id, "late", late.id)
        return winning


async def nudge(channel_id, late):
    await late.send(f"""Hey {late.name}! Looks like your vote could help close out a poll in <#{channel_id}>. Get voting!""")
    await save_state(channel_id, "nudge_at", float('Inf'))
    await save_state(channel_id, "late", None)


async def prompt_host(channel_id, host, options):
    game_night = state[channel_id].get("game_night", "game day")
    attendees = await fetch_attendees(channel_id, game_night.split()[0])
    await save_state(channel_id, "attendees", attendees[:])
    attendees.remove(host.id)
    mentions = f"""<@{'>, <@'.join(str(a) for a in attendees[:-1])}> and <@{attendees[
    -1]}>""" if len(attendees) > 1 else f"<@{attendees[0]}>"
    timeslot = ""
    if len(options) == 1:
        timeslot = f"""A time between **{options[0]}** best suits the group so try to stick to that range!"""
    elif len(options) > 1:
        timeslot = f"""**{', '.join(options[:-1])} and {options[-1]}** have {"both" if (len(options) == 2) else "all"} tied as times that suit the group.
Feel free to pick a time slot that falls in any of those ranges!"""
    await host.send(f"""Howdy {host.name}! You are this week's host!
**{len(attendees)}** players ({mentions}) will be joining you on {game_night}.
Type ```/suggest [start_time] [game_name]``` to make a suggestion.
`start_time` should be one word e.g `8pm` while `game_name` can be any number of words. Timezone is UTC.
{timeslot}
Your suggestion will be announced in the channel where the poll took place. Choose wisely!
""")


async def prompt_bonus_host(channel_id, host):
    game_night = state[channel_id].get("bonus_night", "bonus game day")
    attendees = state[channel_id].get("bonus_attendees", [])
    attendees = attendees[:]
    attendees.remove(host.id)
    mentions = f"""<@{'>, <@'.join( str(a) for a in attendees[:-1])}> and <@{attendees[
    -1]}>""" if len(attendees) > 1 else f"<@{attendees[0]}>"
    await host.send(f"""Hey there {host.name}! You are this week's lucky **bonus** host!
**{len(attendees)}** players ({mentions}) will be joining you on {game_night}.
Type ```/bonus [start_time] [game_name]``` to make a suggestion.
`start_time` should be one word e.g `8pm` while `game_name` can be any number of words. Timezone is UTC.
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

async def poll_timeslot(channel_id, weekend, count):
    message = f"""@everyone
{reactions[weekend]}({weekend}) has won with {count} votes!
Weekends are a busier time so let's try to narrow down a range for the start time. All times are UTC.
1️⃣ - Starting between 1pm and 3pm
2️⃣ - Starting between 3pm and 5pm
3️⃣ - Starting between 5pm and 7pm
4️⃣ - Starting between 7pm and 9pm
5️⃣ - Starting between 9pm and 11pm
:no_entry_sign: - Can't attend

    """
    channel = client.get_channel(int(channel_id))
    msg = await channel.send(message)
    for reaction in timeslots.keys():
        await msg.add_reaction(reaction)
    await save_state(channel_id, "side_poll", msg.id)
    await save_state(channel_id, "weekend", reactions[weekend])

async def choose_host(channel, choices):
    channel_id = str(channel.id)
    users = state[channel_id].get("users")
    last_host = state[channel_id].get("last_host", users[0])
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
    host = await client.fetch_user(new_host)
    announce = f""" <@{host.id}> is this week's host. {"They will first be asked to break the tie between the winning votes." if len(choices) > 1 else ""}
They will receive a DM which will allow them to suggest a start time and game for the winning day.
    """
    await channel.send(announce)
    weekend = state[channel_id].get("weekend", None)
    emojis = timeslots if weekend else reactions
    if weekend:
        await save_state(channel_id, "side_poll", None)
        await save_state(channel_id, "weekend", None)
        day_and_date = await get_date_for_day(channel_id, weekend)
        await save_state(channel_id, "game_night", day_and_date)
        options = [emojis[choice] for choice in choices]
        await prompt_host(channel_id, host, options)
    elif len(choices) == 1:
        day_and_date = await get_date_for_day(channel_id, reactions[choices[0]])
        await save_state(channel_id, "game_night", day_and_date)
        await prompt_host(channel_id, host, [])
    else:
        await save_state(channel_id, "tied", [emojis[choice] for choice in choices])
        await prompt_tiebreaker(host, choices)
    await save_state(channel_id, "last_host", host.id)


async def tally(channel_id, message , is_timeslot=False):
    leading = await winners(channel_id, message, is_timeslot)
    if len(leading) == 0:
        return
    is_closing = await update_poll_status(channel_id, message, "closing")
    if not is_closing:
        return
    await asyncio.sleep(30)
    channel = client.get_channel(int(channel_id))
    message = await channel.fetch_message(message.id)
    recount = await winners(channel_id, message, is_timeslot)
    channel = client.get_channel(int(channel_id))
    emojis = timeslots if is_timeslot else reactions

    if len(recount) == 1:
        key, count = recount.popitem()
        await save_state(channel_id, "open_poll", None)
        if key.emoji == '🚫':
            resp = f"""Game day is **CANCELLED** as a majority({count}) of players have indicated they can't attend({key.emoji}).
See you all next week for more games!               
            """
            await channel.send(resp)
        elif key.emoji in ['🇸', '☀️']:
            await poll_timeslot(channel_id, key.emoji, count)
        else:
            resp = f"{emojis[key.emoji]}({key.emoji}) has won with {count} votes!"
            await channel.send(resp)
            await choose_host(channel, [key])
        await update_poll_status(channel_id, message, "closed")
    elif len(recount) >= 1:
        tied = []
        choices = []
        await save_state(channel_id, "open_poll", None)
        for key in recount:
            tied.append(f"{emojis[key.emoji]}({key.emoji})")
            choices.append(key)
        _, count = recount.popitem()
        await channel.send(f"""{", ".join(tied[:-1])} and {tied[-1]} have {"both" if (len(tied) == 2 )  else "all"} tied with {count} votes! This tie will be broken by this week's host.""")
        await choose_host(channel, choices)
        await update_poll_status(channel_id, message, "closed")


async def bonus_go_no_go(channel_id, message):
    counts = {r: r.count-1 for r in message.reactions if r.emoji in ['👍', '👎'] }
    winning = {r: counts[r] for r in counts if counts[r] >= 3}
    total_voters = []
    users = state[channel_id].get("users")
    for k in counts:
        voters = await k.users().flatten()
        total_voters.append(voters)
    flat_list = [voter for sublist in total_voters for voter in sublist]
    voter_ids = set([voter.id for voter in flat_list])
    non_voters = set(users) - set(voter_ids)
    if len(voter_ids) == 5:
        await save_state(channel_id, "late", None)
        await save_state(channel_id, "bonus_poll", None)
        for k in winning:
            if k.emoji == '👍':
                voters = await k.users().flatten()
                voters = [voter.id for voter in voters if
                          voter.id != 643411373346521088]
                await save_state(channel_id, "bonus_attendees", voters[:])
                voters.remove(state[channel_id].get("last_host"))
                host_id = random.choice(voters)
                await client.fetch_user(host_id)
                channel = client.get_channel(int(channel_id))
                bonus_night = state[channel_id].get("bonus_night", "the bonus night")
                announce = f""" <@{host_id}> is this week's randomly selected **bonus** host. 
They will receive a DM which will allow them to suggest a start time and game for additional games on {bonus_night}
"""
                await save_state(channel_id, "bonus_host", host_id)
                await channel.send(announce)
                host = await client.fetch_user(host_id)
                await prompt_bonus_host(channel_id, host)
    elif len(non_voters) == 1:
        late = await client.fetch_user(non_voters.pop())
        nudgee = state[channel_id].get("late", None)
        if nudgee and nudgee == late.id:
            pass
        else:
            await save_state(channel_id, "nudge_at",
                             (datetime.now() + timedelta(hours=1)).timestamp())
            await save_state(channel_id, "late", late.id)
@client.event
async def on_raw_reaction_add(payload):
    channel_id = str(payload.channel_id)
    open_poll = state[channel_id].get("open_poll", None)
    side_poll = state[channel_id].get("side_poll", None)
    bonus_poll = state[channel_id].get("bonus_poll", None)
    channel = client.get_channel(int(channel_id))
    if side_poll and side_poll == payload.message_id:
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji.name
        if emoji in timeslots and len(message.reactions) >= len(timeslots):
            print(f"Reaction {emoji} is in {timeslots}")
            await tally(channel_id, message, True)
    elif open_poll and open_poll == payload.message_id:
        message = await channel.fetch_message(payload.message_id)
        emoji = payload.emoji.name
        if emoji in reactions and len(message.reactions) >= len(reactions):
            print(f"Reaction {emoji} is in {reactions}")
            await tally(channel_id, message)
    elif bonus_poll and bonus_poll == payload.message_id:
        message = await channel.fetch_message(payload.message_id)
        await bonus_go_no_go(channel_id, message)


async def remind(channel_id, reminder):
    channel = client.get_channel(int(channel_id))
    emoji = get(channel.guild.emojis, name='rollHigh')
    attendees = state[channel_id].get("attendees", [])
    mentions = f"""<@{'>, <@'.join(str(a) for a in attendees[:-1])}> and <@{attendees[
    -1]}>""" if attendees else "@everyone"
    message = f"""{mentions}!
It's game day!
Today we will be playing **{reminder['game_name']}** @ **{reminder['start_time']}**(approximately 1 hour from now), Have fun! {emoji}
    """
    await channel.send(message)
    await save_state(channel_id, "remind_at", float('Inf'))
    await save_state(channel_id, "reminder", None)



async def bonus_remind(channel_id, reminder):
    channel = client.get_channel(int(channel_id))
    emoji = get(channel.guild.emojis, name='rollHigh')
    attendees = state[channel_id].get("bonus_attendees", None)
    mentions = f"""<@{'>, <@'.join( str(a) for a in attendees[:-1])}> and <@{attendees[
    -1]}>""" if attendees else "@everyone"
    message = f"""{mentions}!
Today we will be playing **{reminder['game_name']}** @ **{reminder['start_time']}**(approximately 1 hour from now), Have fun! {emoji}
    """
    await channel.send(message)
    await save_state(channel_id, "bonus_remind_at", float('Inf'))
    await save_state(channel_id, "bonus_reminder", None)

async def poll_time(channel_id):
    message = """@everyone
The weekly poll is ready! Please indicate your availability below:
:regional_indicator_t: - Thursday
:regional_indicator_f: - Late night Friday (starting from 10pm UTC)
:regional_indicator_s: - Saturday (A secondary poll to pick a time slot will follow)
:sunny: - Sunday (A secondary poll to pick a time slot will follow)
:regional_indicator_m: - Monday
2️⃣ - Tuesday
:regional_indicator_w: - Wednesday
:no_entry_sign: - Can't attend
A winning day will be announced once everyone has voted.
    """
    channel = client.get_channel(int(channel_id))
    msg = await channel.send(message)
    today = date.today().strftime("%B %d, %Y")
    embed = discord.Embed(title=f"Weekly game day poll - {today}")
    await msg.edit(embed=embed)
    for reaction in reactions.keys():
        await msg.add_reaction(reaction)
    await save_state(channel_id, "open_poll", msg.id)
    await save_state(channel_id, "bonus_check", msg.id)
    next_poll = datetime.now() + timedelta(days=7)
    print(f"next poll is at {next_poll}")
    await save_state(channel_id, "next_poll_at", next_poll.timestamp())


async def check_dm_with_host(ctx):
    possible_hosts = []
    for channel_id in state.keys():
        host = state[channel_id].get("last_host", None)
        if host:
            possible_hosts.append(host)
    if ctx.message.channel.type != discord.ChannelType.private:
        await ctx.message.add_reaction('🙉')
        await ctx.author.send(f"Sorry the command you tried to invoke (`/{ctx.command.name}`) in #{ctx.message.channel.name} on {ctx.message.channel.guild} is limited to direct message only,")
        return False
    elif ctx.author.id not in possible_hosts:
        await ctx.author.send("Sorry, only the weekly host can perform this action.")
        return False
    return True

async def check_dm_with_bonus_host(ctx):
    possible_hosts = []
    for channel_id in state.keys():
        host = state[channel_id].get("bonus_host", None)
        if host:
            possible_hosts.append(host)
    if ctx.message.channel.type != discord.ChannelType.private:
        await ctx.message.add_reaction('🙉')
        await ctx.author.send(f"Sorry the command you tried to invoke (`/{ctx.command.name}`) in #{ctx.message.channel.name} on {ctx.message.channel.guild} is limited to direct message only,")
        return False
    elif ctx.author.id not in possible_hosts:
        await ctx.author.send("Sorry, only the bonus host can perform this "
                              "action.")
        return False
    return True

async def fetch_attendees(channel_id, weekday):
    weekday = weekday.capitalize()
    ivd = {v: k for k, v in reactions.items()}
    winner = ivd.get(weekday, None)
    poll = state[channel_id].get("bonus_check", None)
    channel = client.get_channel(int(channel_id))
    message = await channel.fetch_message(int(poll))
    if winner and poll:
        for r in message.reactions:
            if r.emoji == winner:
                voters = await r.users().flatten()
                return [voter.id for voter in voters if voter.id != 643411373346521088]
    return []

async def check_bonus(channel_id):
    channel = client.get_channel(int(channel_id))
    poll = state[channel_id].get("bonus_check", None)
    weekday = state[channel_id].get("game_night", "game day").split()[0].capitalize()
    ivd = {v: k for k, v in reactions.items()}
    winner = ivd.get(weekday, None)
    if winner and poll:
        message = await channel.fetch_message(int(poll))
        counts = {r: r.count-1 for r in message.reactions if r.emoji in
                  reactions and r.emoji != winner}
        options = {r: counts[r] for r in counts if counts[r] >= 3}
        make_up = {}
        attendees = state[channel_id].get("attendees", [])
        for k in options:
            voters = await k.users().flatten()
            voter_ids = [voter.id for voter in voters if voter.id != 643411373346521088 ]
            make_up[k] = set(voter_ids) - set(attendees)
        if len(make_up) > 0:
            best_opt = max(make_up, key=lambda k: len(make_up[k]))
            tied = [k for k in make_up.keys() if len(make_up[k]) == len(make_up[best_opt])]
            if weekday in ["Friday", "Saturday", "Sunday"]:
                filtered = [ k for k in tied if k.emoji not in ['🇫', '🇸', '☀️']]
            else:
                filtered = [ k for k in tied if k.emoji in ['🇫', '🇸', '☀️']]
            if len(filtered) > 0:
                best_opt = random.choice(filtered)
            else:
                best_opt = random.choice(tied)
            mentions = f"""This way, <@{'>, + <@'.join(str(a) for a in make_up[best_opt])}> can still play this week."""  if len(make_up[best_opt]) > 0 else ""
            if len(make_up[best_opt]) == 0:
                best_opt = max(options, key=options.get)
                tied = [k for k in options.keys() if options[k] == options[best_opt]]
                if weekday in ["Friday", "Saturday", "Sunday"]:
                    filtered = [k for k in tied if
                                k.emoji not in ['🇫', '🇸', '☀️']]
                else:
                    filtered = [k for k in tied if
                                k.emoji in ['🇫', '🇸', '☀️']]
                if len(filtered) > 0:
                    best_opt = random.choice(filtered)
                else:
                    best_opt = random.choice(tied)
            audience = await best_opt.users().flatten()
            audience_ids = [voter.id for voter in audience if voter.id != 643411373346521088 ]
            prompt = f"""<@{'>, <@'.join( str(a) for a in audience_ids[:-1])}> and <@{audience_ids[
            -1]}>"""
            bonus_msg = f"""{prompt}
I see that {reactions[best_opt.emoji]}({best_opt.emoji}) has {options[
best_opt]} votes. Want me to setup an additional bonus game night for then?
{mentions}
"""
            msg = await channel.send(bonus_msg)
            for reaction in ['👍', '👎']:
                await msg.add_reaction(reaction)
            await save_state(channel_id, "bonus_poll", msg.id)
            await save_state(channel_id, "bonus_check", None)
            day_and_date = await get_date_for_day(channel_id, reactions[best_opt.emoji])
            await save_state(channel_id, "bonus_night", day_and_date)


@commands.check(check_dm_with_bonus_host)
@client.command()
async def bonus(ctx, start_time, *gamename):
    if len(gamename) < 0:
        await ctx.send(
            f"You must specify a game name.")
        return
    for chan in state.keys():
        host = state[chan].get("bonus_host", None)
        if ctx.message.author.id == host:
            channel_id = chan
    host = ctx.message.author
    game_name = " ".join(gamename)
    reminder = {"start_time": start_time, "game_name": game_name}
    game_night = state[channel_id].get("bonus_night", "game day")
    attendees = state[channel_id].get("bonus_attendees", [])
    mentions = f"""<@{'>, <@'.join(str(a) for a in attendees[:-1])}> and <@{attendees[
    -1]}>""" if len(attendees) > 1 else f"@<{attendees[0]}>"
    remind_at = parse(f"{start_time} {game_night}")
    if remind_at is None or remind_at.timestamp() <= time.time():
        await ctx.send(f"Sorry I had trouble understanding {start_time} as a a start time. Please try again.")
        return
    await ctx.send(f"Ok, I'll announce your suggestion of {game_name} @ {start_time} on {game_night}.")
    await save_state(channel_id, "bonus_remind_at", (remind_at - timedelta(
        hours=1)).timestamp())
    await save_state(channel_id, "bonus_reminder", reminder)
    channel = client.get_channel(int(channel_id))
    announce = f"""Okay, I've setup a ✨ **bonus** ✨ game day for {mentions}.
{host.mention} has suggested we play **{game_name}** @ **{start_time}** on **{game_night}**.
I'll remind this channel an hour before then."""
    await channel.send(announce)


@commands.check(check_dm_with_host)
@client.command()
async def suggest(ctx, start_time, *gamename):
    if len(gamename) < 0:
        await ctx.send(
            f"You must specify a game name.")
        return
    if gamename[-1] == "double_host":
        channel_id = gamename[-2]
        gamename = gamename[:-2]
    else:
        for chan in state.keys():
            host = state[chan].get("last_host", None)
            if ctx.message.author.id == host:
                channel_id = chan
    host = ctx.message.author
    game_name = " ".join(gamename)
    reminder = {"start_time": start_time, "game_name": game_name}
    game_night = state[channel_id].get("game_night", "game day")
    remind_at = parse(f"{start_time} {game_night}")
    if remind_at is None or remind_at.timestamp() <= time.time():
        await ctx.send(f"Sorry I had trouble understanding {start_time} as a a start time. Please try again.")
        return
    await ctx.send(f"Ok, I'll announce your suggestion of {game_name} @ {start_time} on {game_night}.")
    await save_state(channel_id, "remind_at", (remind_at - timedelta(hours=1)).timestamp())
    await save_state(channel_id, "reminder", reminder)
    channel = client.get_channel(int(channel_id))
    announce = f"""@everyone The poll has concluded. 
{host.mention} has suggested we play **{game_name}** @ **{start_time}** on **{game_night}**.
I'll remind this channel an hour before then."""
    await channel.send(announce)
    await check_bonus(channel_id)


@commands.check(check_dm_with_host)
@client.command()
async def tiebreak(ctx, weekday, *args):
    channel_id = None
    if len(args) > 0 and args[-1] == "double_host":
        channel_id = args[-2]
    else:
        for chan in state.keys():
            host = state[chan].get("last_host", None)
            if ctx.message.author.id == host:
                channel_id = chan

    weekday = weekday.capitalize()
    options = state[channel_id].get("tied", [])
    if len(options) == 0:
        await ctx.send("Sorry, there doesn't seem to be a tie for you to break this week.")
    if weekday == "Random":
        weekday = random.choice(options)
        await ctx.send(f"Sure, I've chosen {weekday} at random for you.")
    if weekday in options:
        await ctx.send(f"Ok, I'll set {weekday} as the game day.")
        day_and_date = await get_date_for_day(channel_id, weekday)
        await save_state(channel_id, "game_night", day_and_date)
        await save_state(channel_id, "tied", [])
        ivd = {v: k for k, v in reactions.items()}
        if weekday in ["Saturday", "Sunday"]:
            users = state[channel_id].get("users")
            last_host = state[channel_id].get("last_host", users[0])
            before = users.index(last_host) - 1
            await save_state(channel_id, "last_host", users[before])
            await poll_timeslot(channel_id, ivd[weekday], "the most")
        else:
            host = ctx.message.author
            await prompt_host(channel_id, host,  [])
    else:
        await ctx.send(f"Sorry, I didn't recognize {weekday} as one of the options for the tie break. Try again. ")

async def output_boardgames(ctx, options, num_players, num_games):
    games = random.sample(list(options), num_games)
    nl = "\n"
    bgames = f"""{''.join(f'**• {game}** - {options[game]}{nl}' for game in games)}"""
    await ctx.send(f"""Okay <@{ctx.author.id}>, I've chosen **{num_games}** board games which play well with **{num_players}** players:
{bgames}""")

@client.command()
async def random_boardgame(ctx, num_players=None, num_games="3"):
    if num_players is None:
        await ctx.send(""" You must specify a number of players to find board games for. Currently supported: 4 or 5
Type ```/random_boardgame [player_count] [num_games](default 3)``` to get random games for that many players.
e.g ```/random_boardgame 4 5``` gets 5 games which can be played with 4 players.""")
    else:
        try:
            games = int(num_games)
            if games > 5:
                await ctx.send("Sorry, that's too many games. Please keep the number at 5 or under.")
            elif num_players == "4":
                options = {**four_player_bgg, **default_bgg}
                await output_boardgames(ctx, options, "4", games)
            elif num_players == "5":
                options = {**five_player_bgg, **default_bgg}
                await output_boardgames(ctx, options, "5", games)
            else:
                await ctx.send(
                    """Sorry, I'm not aware of which games can be played with that many players.""")
        except ValueError:
            await ctx.send(f"Sorry, I don't understand {num_games} as a number.")


@tasks.loop(minutes=1)
async def check_time():
    keys = state.keys()
    for channel_id in keys:
        if state[channel_id].get("next_poll_at", 0) <= time.time():
            print("Poll starting")
            await poll_time(channel_id)
        if state[channel_id].get("remind_at", float('Inf')) <= time.time():
            print(f"remind")
            reminder = state[channel_id].get("reminder", None)
            if reminder:
                await remind(channel_id, reminder)
        if state[channel_id].get("bonus_remind_at", float('Inf')) <= \
                time.time():
            print(f"bonus")
            reminder = state[channel_id].get("bonus_reminder", None)
            if reminder:
                await bonus_remind(channel_id, reminder)
        if state[channel_id].get("nudge_at", float('Inf')) <= time.time():
            print(f"nudge")
            nudgee = state[channel_id].get("late", None)
            if nudgee:
                late = await client.fetch_user(nudgee)
                await nudge(channel_id, late)
            else:
                await save_state(channel_id, "nudge_at", float('Inf'))
        print("looped")


client.run(os.environ.get("DISCORD_BOT_TOKEN"))