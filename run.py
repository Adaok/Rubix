import asyncio
import discord
import random
import os

_VERSION="1.1.0"

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

    def prepend(self,file,newentry):
        f = open(file,"r")
        old = f.read()
        f.close()

        f = open(file,"w")
        f.write(newentry)
        f.write(old)
        f.close()

    async def on_member_update(self,old,new):
        if old.name == new.name:
            return

        nickfile = open("data/usr/"+old.id+"/nicks","r")
        oldnames = nickfile.read()
        nickfile.close()

        if new.name in oldnames:
            return

        nickfile = open("data/usr/"+old.id+"/nicks","w")
        nickfile.write(new.name+"\n")
        nickfile.write(oldnames)
        nickfile.close()

    async def on_error(self,event,args):
        await self.send_message(self.current.channel,"uh oh, something went wrong!\n`"+event+"`")

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
            await self.send_message(message.channel,"""```Rubix help
\t!ping                   Ensure Rubix is running with a simple command.
\t!help                   Shows this dialogue.
\t!join <Voice Channel>   Makes Rubix join a voice channel.
\t!leave                  Makes Rubix leave the voice channel he's in.
\t!queue <url>            Queues a Youtube link for playback.
\t!play                   Starts playing the first song on the queue.
\t!nowplaying             Says the name of the currently playing track.
\t!skip                   Skip the currently playing song.
\t!about                  Displays information about Rubix.
\t!banword <word>         [OP] Bans a word from being used in sfw channels.
\t!getid [name]           Says the id of the named user. @Mention for multiple.
\t!afk                    Toggles afk status.
\t!whatgame               Tells what games are being played in this server.
\t!whois [name]           Tell the name history of someone.```""")

        elif message.content.startswith("!ping"):
            await self.send_message(message.channel, "Pong!")

        elif message.content.startswith("!about"):
            await self.send_message(message.channel, "`Rubix "+ _VERSION +"`")
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
                await self.send_message(message.channel, "You don't have permission to use that, "+ message.author.mention +".")

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

        elif message.content.startswith("!whois"):
            name=message.content[6:].strip()
            targetid=0
            if name=="":
                name=message.author.name
            for member in message.server.members:
                if member.name==name:
                    targetid=member.id
            if targetid == 0: ##try mentions
                for member in message.mentions:
                    targetid=member.id
                    break
            if targetid==0:
                await self.send_message(message.channel, "I couldn't find anyone by that name.")
            else:
                nicklist = open("data/usr/"+targetid+"/nicks","r")
                user = discord.utils.get(message.server.members,id=targetid)

                await self.send_message(message.channel, user.mention +" has also used the names:")
                for nick in nicklist:
                    await self.send_message(message.channel,nick)
        
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
            await self.send_message(message.channel, message.author.mention + " removed me from the voice channel.")
            await self.voice.disconnect()

        elif message.content.startswith("!queue"):
            url = message.content[6:].strip()
            await self.songs.put(Audio(message, url))
            await self.send_message(message.channel,"Queued your link, "+ message.author.mention +".")

        elif message.content.startswith("!skip"):
            if not self.is_voice_connected or not self.player.is_playing():
                await self.send_message(message.channel, "I'm not playing anything, "+ message.author.mention)
            self.player.stop()
            self.loop.call_soon_threadsafe(self.play_next.set)
            

        elif message.content.startswith("!play"):
            if self.player is not None and self.player.is_playing():
                await self.send_message(message.channel, "I'm already playing something, " + message.author.mention +".")
                return
            while True:
                if not self.is_voice_connected():
                    await self.send_message(message.channel, "Not connected, I can't play anything. Try making me !join first, "+ message.author.mention +".")
                    return
                self.play_next.clear()
                self.current = await self.songs.get()
                self.player = await self.voice.create_ytdl_player(self.current.url, after=self.toggle_next_song)
                self.player.start()
                fmt = "Playing {1.title}, requested by {0.requester.mention}."
                await self.send_message(self.current.channel, fmt.format(self.current,self.player))
                await self.play_next.wait()

        elif message.content.startswith("!nowplaying"):
            if self.player is not None and self.player.is_playing():
                fmt = "Playing {1.title}."
                await self.send_message(message.channel, fmt.format(self.current,self.player))
            else:
                await self.send_message(message.channel, "I'm not playing anything, " + message.author.mention +".")

        elif message.content.startswith("!whatgame"):
            players={}
            none=0
            for member in message.server.members:
                if member!=self.user:
                    if member.game == None:
                        none+=1
                    else:
                        if str(member.game) not in players:
                            players[str(member.game)]=1
                        else:
                            players[str(member.game)]+=1
            if players=={}:
                await self.send_message(message.channel,"Nobody on the server is playing anything.")
            else:
                for game in players:
                    if players[game] == 1:
                        await self.send_message(message.channel,"1 person is playing "+ game +".")
                    else:
                        await self.send_message(message.channel,str(players[game]) +" people are playing "+ game +".")
                if none == 1:
                    await self.send_message(message.channel,"1 person isn't playing anything.")
                else:
                    await self.send_message(message.channel,str(none) +" people aren't playing anything.")

        elif message.content.startswith("!"):
            await self.send_message(message.channel,"I didn't understand that command, "+ message.author.mention +".")
                
    async def on_ready(self):
        print("Rubix "+ _VERSION)
        print("--------------")
        for server in self.servers:
            for member in server.members:
                if not os.path.exists("data/usr/"+member.id):
                    os.makedirs("data/usr/"+member.id)
                try:
                    nickfile = open("data/usr/"+member.id+"/nicks","r")
                except FileNotFoundError:
                    nickfile = open("data/usr/"+member.id+"/nicks","w")
                    nickfile.close()
                    nickfile = open("data/usr/"+member.id+"/nicks","r")

                exists=False
                
                for line in nickfile:
                    if member.name==line.strip():
                        exists=True

                if not exists: ##New nickname
                    nickfile.close()

                    self.prepend("data/usr/"+member.id+"/nicks",member.name)
                        
rubix=Bot()
rubix.run("isaakrogers1@gmail.com","Xeta1230")
