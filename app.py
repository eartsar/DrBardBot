import os
import re
import argparse
import yaml
import discord

from sheets import MentorshipManager
from util import ValueRetainingRegexMatcher

# replit work-around script to keep the process running
from keep_alive import keep_alive


parser = argparse.ArgumentParser(description='Run the bot.')
parser.add_argument('--config', type=str, required=True, 
                    help='The path to the configuration yml.')
args = parser.parse_args()

# Load the config file
config = {}
with open(args.config, 'r') as f:
    config = yaml.safe_load(f)

BOT_TOKEN = config['bot_token'] if 'bot_token' in config else os.getenv("BOT_TOKEN")
GOOGLE_CREDENTIALS_PATH = config['google_service_account_creds']
GOOGLE_SHEETS_KEY = config['google_sheets_key']


HELP_TEXT = '''\
 BOT UTILITY FUNCTIONS
-----------------------
!ping                           Checks if online
!help                           Displays this message'''


PING_REGEX = re.compile(r'!ping')
HELP_REGEX = re.compile(r'!help')



class DRBardBot(discord.Client):

    def __init__(self):
        super().__init__()
        self.mm = MentorshipManager(self, GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEETS_KEY)


    async def on_ready(self):
        print("Initializing DRBardBot...")
        await self.mm.initialize()
        print('Ready!')


    async def on_message(self, message):
        # Bot ignores itself. This is how you avoid the singularity.
        if message.author == self.user:
            return

        # Ignore anything that doesn't start with the magic token
        if not message.content.startswith('!'):
            return

        # Match against the right command, grab args, and go
        from util import ValueRetainingRegexMatcher
        m = ValueRetainingRegexMatcher(message.content)
        
        if m.match(PING_REGEX):
            await message.channel.send(f'{message.author.mention} pong!')
        elif m.match(HELP_REGEX):
            await message.channel.send(HELP_TEXT)



def main():
    keep_alive()
    client = DRBardBot()
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
