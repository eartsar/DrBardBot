import arrow
import pygsheets
import asyncio
import concurrent


# This is the date format that the google form tags rows with as a timestamp. It doesn't say timezone.
DATE_FORMAT = 'M/D/YYYY HH:mm:ss'


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
            self.data = await loop.run_in_executor(executor, sync, self.creds, self.sheet_key)
            await asyncio.sleep(60)

    


# Simple object that encapsulates a mentor or student entry
class ListingRow():
    def __init__(self, name, circle, role, focuses, avail, when):
        self.name = name
        self.circle = circle
        self.role = role
        self.focuses = focuses
        self.avail = avail
        self.when = when


# Convenience function to get a value in a 2D-list given a cell string
# Only works up to column 'Z'
def get_cell(data, cell):
        col = ord(cell[0]) - ord('A')
        row = int(cell[1:]) - 1
        return data[row][col]


# Convert 2D list (sheet dump) into a list of ListingRow objects
def data_to_rows(data, when):
    rows = []
    for data_row in data:
        name = data_row[0].lower().capitalize()
        circle = data_row[1]
        role = data_row[2]
        focuses = [_ if _ else '' for _ in data_row[3:7]]
        avail = {}
        avail['Mon'] = data_row[8]
        avail['Tue'] = data_row[9]
        avail['Wed'] = data_row[10]
        avail['Thu'] = data_row[11]
        avail['Fri'] = data_row[12]
        avail['Sat'] = data_row[13]
        avail['Sun'] = data_row[14]
        rows.append(ListingRow(name, circle, role, focuses, avail, when))
    return rows


# Convert a list of ListingRow objects into a 2D list for loading into a sheet
def rows_to_data(rows):
    data = []
    for row in rows:
        data_row = []
        focuses = [_ if _ else '' for _ in row.focuses]
        for i in range(len(focuses), 4):
            focuses.append('')

        data_row += (row.name.capitalize(), row.circle, row.role)
        data_row += focuses
        data_row.append('')
        data_row += [
            row.avail['Mon'] if 'Mon' in row.avail else '',
            row.avail['Tue'] if 'Tue' in row.avail else '',
            row.avail['Wed'] if 'Wed' in row.avail else '',
            row.avail['Thu'] if 'Thu' in row.avail else '',
            row.avail['Fri'] if 'Fri' in row.avail else '',
            row.avail['Sat'] if 'Sat' in row.avail else '',
            row.avail['Sun'] if 'Sun' in row.avail else ''
        ]
        data.append(data_row)
    return data


# Connect to the google sheet with the service account credentials
def sync(creds, sheet_key):
    gc = pygsheets.authorize(service_file=creds)
    spreadsheet = gc.open_by_key(sheet_key)

    # Sheet with bard entries
    listing_worksheet = spreadsheet.worksheet_by_title('Listing')
    # Sheet with form submission data
    form_worksheet = spreadsheet.worksheet_by_title('Registration Form Responses')

    # Grab all the data in the listing table
    current_listing_raw = listing_worksheet.get_all_values()

    # Grab the marker that says when the table was last updated
    last_updated = arrow.get(listing_worksheet.get_value('S1'), DATE_FORMAT)

    # Create ListingRow objects
    existing_listing = data_to_rows(current_listing_raw[1:], last_updated)


    # A cache we're constructing. name --> ListingRow
    # We start with what's in the current table, and if we see a more recent entry, we update
    new_listing_cache = {}
    # Create a cache of the current table
    for row in existing_listing:
        new_listing_cache[row.name] = row

    # Get the form data, convert into ListingRows
    form_cache = {}
    form_raw = form_worksheet.get_all_values()
    form_raw = form_raw[1:]
    for row in form_raw:
        if not row[0]:
            continue
        name = row[1].lower().capitalize()
        role = row[2]
        circle = row[11]
        focuses = [_.strip() for _ in row[3].split(',')]
        avail = {
            'Mon': row[4],
            'Tue': row[5],
            'Wed': row[6],
            'Thu': row[7],
            'Fri': row[8],
            'Sat': row[9],
            'Sun': row[10]
        }
        form_cache[name] = ListingRow(name, circle, role, focuses, avail, arrow.get(row[0], DATE_FORMAT))

    # Merge updated form data into the listing cache, if the form data is more recent than the publish
    # timestamp of the table
    for key in form_cache:
        row = form_cache[key]
        if key not in new_listing_cache:
            new_listing_cache[key] = row
        elif row.when > new_listing_cache[key].when:
            new_listing_cache[key] = row


    # Get a 2D list representation of the data, and do a mass update of the table
    to_update = rows_to_data(sorted(new_listing_cache.values(), key=lambda x: x.name))
    listing_worksheet.update_values(crange=f'A2:O{1+len(to_update)}', values=to_update, extend=True)


    # Edge case - if we removed data (somehow), cut off tail rows
    num_rows = len(existing_listing)
    if num_rows - 1 > len(to_update):
        num_to_delete = num_rows - len(to_update)
        listing_worksheet.delete_rows(len(to_update) + 2, number=num_to_delete)


    # Clear form data by deleting all non-header rows except one, and blanking that last row out
    # This is a limitation of the form sheet.
    if len(form_raw) > 1:
        form_worksheet.delete_rows(3, number=len(form_raw) - 1)
    
    form_worksheet.clear(start='A2')

    # Set the timestamp on the listing table to denote that it's now updated to, well, "now"
    listing_worksheet.update_value('S1', arrow.now().format(DATE_FORMAT))
    return new_listing_cache

