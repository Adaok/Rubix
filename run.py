import asyncio
import discord
import random

_VERSION="1.0.5"

if not discord.opus.is_loaded():
    discord.opus.load_opus("libopus-0.x64.dll")

class Audio:
    def __init__(self,message,url):
        self.requester = message.author
        self.channel = message.channel
        self.url=url

class Bot(discord.Client):
    def __init__(self):
        super().__init__()
        self.songs=asyncio.Queue()
        self.play_next=asyncio.Event()
        self.player=None
        self.current=None
        self.afkusers=[]

    def roll(self,dice):
        count = int(dice.split("d")[0])
        if count > 10:
            return False
        tp = int(dice.split("d")[1])
        results = [None] * count
        for i in range(count):
            results[i]=random.randint(1,tp)
        print(results)
        return results

    def isOp(self,member,server):
        ops = open("data/ops.txt","r")
        for line in ops:
            op=line.split("@")[0].strip()
            sv=line.split("@")[1].strip()
            if sv=="*" or sv==server.name:
                if op=="*" or op==member.id:
                    ops.close()
                    return True
        ops.close()
        return False

    def toggle_next_song(self):
        self.loop.call_soon_threadsafe(self.play_next.set)

    def is_playing(self):
        return self.player is not None and self.player.is_playing()

    async def on_message(self,message):
        if message.author == self.user:
            return

        if message.channel.is_private:
            await self.send_message(message.channel,"Sorry, I don't work in private messaging!")
            return

        if message.content.startswith("!"):
            await self.delete_message(message)
            print("Command received from "+ message.author.name +": "+ message.content)
        else:
            for member in message.mentions:
                if member.id in self.afkusers:
                    await self.send_message(message.channel, member.mention +" is marked as afk. I'll deliver your message to them by PM.")
                    await self.send_message(member, message.author.mention +" tried to say something to you while you were afk. Their message was:\n"+ message.content)
            

        if "deez nutz" in message.content.lower() or "deez nuts" in message.content.lower():
            await self.send_message(message.channel,"Got Eem!")

        bannedwords = open("data/bannedwords.txt","r")

        for word in bannedwords:
            word=word.strip().lower()
            if word == message.content or " "+word in message.content or word+" " in message.content:
                print("Detected vulgarity in "+message.channel.name+"@"+message.server.name)
                isAllowed=False
                nsfwchannels = open("data/nsfwchannels.txt","r")
                for entry in nsfwchannels:
                    channel=entry.split("@")[0].strip()
                    server=entry.split("@")[1].strip()
                    if server=="*" or server==message.server.name:
                        if channel=="*" or channel==message.channel.name:
                            print("\tIgnoring due to whitelist.")
                            isAllowed=True
                if not isAllowed:
                    print("\tActing")
                    await self.delete_message(message)
                    await self.send_message(message.author,"Uh oh, looks like you were trying to say something vulgar in a channel where it isn't allowed. Your message was:\n" + message.content)
                nsfwchannels.close()
        bannedwords.close()
        
        if message.content.startswith("!help"):
            await self.send_message(message.channel,"""`Rubix help
\t!ping                   Ensure Rubix is running with a simple command.
\t!help                   Shows this dialogue.
\t!join <Voice Channel>   Makes Rubix join a voice channel.
\t!leave                  Makes Rubix leave the voice channel he's in.
\t!queue <url>            Queues a Youtube link for playback.
\t!play                   Starts playing the first song on the queue.
\t!about                  Displays information about Rubix.
\t!banword <word>         [OP] Bans a word from being used in sfw channels.
\t!getid <name>           Says the id of the named user. @Mention for multiple.
\t!afk                    Toggles afk status.`""")

        elif message.content.startswith("!ping"):
            await self.send_message(message.channel, "Pong!")

        elif message.content.startswith("!about"):
            await self.send_message(message.channel, "`Rubix 1.0.0`")
            if self.is_voice_connected():
                await self.send_message(message.channel, "Is in a voice channel.")
            else:
                await self.send_message(message.channel, "Is not in a voice channel.")
            counter = 0
            for server in self.servers:
                counter+=1
            await self.send_message(message.channel, "Serving "+ str(counter) +" servers.")

        elif message.content.startswith("!afk"):
            for user in self.afkusers:
                if user == message.author.id:
                    self.afkusers.remove(user)
                    await self.send_message(message.channel, message.author.mention +" is no longer afk.")
                    return
            self.afkusers.append(message.author.id)
            await self.send_message(message.channel, message.author.mention +" is now afk.")

        elif message.content.startswith("!banword"):
            word=message.content[8:].strip()
            if self.isOp(message.author,message.server):
                bannedwords=open("data/bannedwords.txt","a")
                bannedwords.write("\n"+word)
                bannedwords.close()
                await self.delete_message(message)
            else:
                await self.send_message(message.channel, "You don't have permission to use that.")

        elif message.content.startswith("!getid"):
            name=message.content[6:].strip()
            if name=="":
                name=message.author.name
            for member in message.server.members:
                if member.name == name:
                    await self.send_message(message.channel, "The ID of "+ member.mention +" is "+ member.id +".")
                    return
                else:
                    for member in message.mentions:
                        await self.send_message(message.channel, "The ID of "+ member.mention +" is "+ member.id +".")
                    return
            await self.send_message(message.channel, "I couldn't find anyone by that name.")

        elif message.content.startswith("!roll"):
            rolls=self.roll(message.content[5:].strip())
            if rolls==False:
                await self.send_message(message.channel,"Easy now, "+ message.author.mention +". No more than 10 dice rolls.")
                return
            for roll in rolls:
                await self.send_message(message.channel,message.author.mention +" rolled a "+ str(roll) +" on a d"+ message.content[5:].strip().split("d")[1] +".")
        
        elif message.content.startswith("!join"):
            if self.is_voice_connected():
                await self.send_message(message.channel, "I'm busy in another voice channel right now!")
            channel_name = message.content[5:].strip()
            check = lambda c: c.name == channel_name and c.type == discord.ChannelType.voice
            channel = discord.utils.find(check, message.server.channels)
            if channel is None:
                await self.send_message(message.channel, "I can't find that channel.")
            else:
                await self.join_voice_channel(channel)


        elif message.content.startswith("!leave"):
            await self.voice.disconnect()

        elif message.content.startswith("!queue"):
            url = message.content[6:].strip()
            await self.songs.put(Audio(message, url))
            await self.send_message(message.channel,"Queued your link.")

        elif message.content.startswith("!play"):
            if self.player is not None and self.player.is_playing():
                await self.send_message(message.channel, "I'm already playing something.")
                return
            while True:
                if not self.is_voice_connected():
                    await self.send_message(message.channel, "Not connected, can't play anything.")
                    return
                self.play_next.clear()
                self.current = await self.songs.get()
                self.player = await self.voice.create_ytdl_player(self.current.url, after=self.toggle_next_song)
                self.player.start()
                fmt = "Playing {1.title}, requested by {0.requester.mention}"
                await self.send_message(self.current.channel, fmt.format(self.current,self.player))
                await self.play_next.wait()
                
    async def on_ready(self):
        print("Rubix "+ _VERSION)
        print("--------------")

rubix=Bot()
rubix.run("isaakrogers1@gmail.com","Xeta1230")
