import asyncio
import functools 
import textwrap
import pygsheets

from cells import sheet_index


class SheetManager():
    def __init__(self, creds_path, bot):
        self.creds_path = creds_path
        self.bot = bot
        self.lock = asyncio.Lock()
        self.data = {}


    async def initialize(self):
        async with self.lock:
            print("  Authenticating to google web services...")
            await self.get_gc()
            print("  Done.")


    async def sync(self):
        async with self.lock:
            gc = await sync_to_async(pygsheets.authorize)(service_file=self.creds_path)
            spreadsheet = await sync_to_async(gc.open_by_key)(self.google_sheet_key)
            worksheet = await sync_to_async(spreadsheet.worksheet_by_title)('Character Sheet')
            return await sync_to_async(worksheet.get_all_values)()


    def _access(self, data, cell):
        col = ord(cell[0]) - ord('A')
        row = int(cell[1:]) - 1
        return data[row][col]


