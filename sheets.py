import asyncio
import concurrent
import listing


class MentorshipManager():
    def __init__(self, bot, creds, sheet_key):
        self.bot = bot
        self.creds = creds
        self.sheet_key = sheet_key
        self.task = None
        self.data = {}


    async def initialize(self):
        self.task = asyncio.create_task(self.sync_endlessly())


    async def sync_endlessly(self):
        while True:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
            loop = asyncio.get_event_loop()
            self.data = await loop.run_in_executor(executor, listing.sync, self.creds, self.sheet_key)
            await asyncio.sleep(60)

