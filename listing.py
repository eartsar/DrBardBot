import argparse
import arrow
import pygsheets


# This is the date format that the google form tags rows with as a timestamp.
# Google doesn't specify a time-zone, but it seems to be my current, which is EDT at the time
# of writing this.
#
# Note that when these times are loaded by the arrow library, arrow assumes this is in UTC
# time.
#
# TODO: Figure out a way to have the google form specify a timezone, or output in ISO format
DATE_FORMAT = 'M/D/YYYY HH:mm:ss'


class Listing():
    '''A simple data class that holds the bard listing information'''
    def __init__(self, name, circle, role, focuses, avail, when=None):
        self.name = name
        self.circle = circle
        self.role = role
        self.focuses = focuses
        self.avail = avail
        self.when = when


    def set_last_updated(self, when):
        self.when = when



def listing_sheet_rows_to_listings(rows):
    '''Data transformation helper function that converts a 2D list of raw google
    sheets cell data into a list of Listing objects. Data supplied to this function
    is likely pulled from the pygsheets Worksheet.get_all_values() functionality.

    NB: This function does no validation on the data coming in, and assumes row indices
    have not changed. If the listing table in sheets adds/removes columns, this must
    be updated!

    TODO: Dervice information from column headers, not from raw index
    '''
    listings = []
    for row in rows:
        name = row[0].lower().capitalize()
        circle = row[1]
        role = row[2]
        focuses = [_ if _ else '' for _ in row[3:7]]
        avail = {
            'Mon': row[8],
            'Tue': row[9],
            'Wed': row[10],
            'Thu': row[11],
            'Fri': row[12],
            'Sat': row[13],
            'Sun': row[14]
        }
        
        listings.append(Listing(name, circle, role, focuses, avail))
    return listings


def listings_to_sheet_rows(listings):
    '''Data transformation helper function that converts a list of Listing objects
    into a 2D list of raw data for google sheets. Data returned by this function
    is likely to be used with the pygsheets Worksheet.update_values() functionality.

    NB: This function does no validation on the data coming in, and assumes row indices
    have not changed. If the listing table in sheets adds/removes columns, this must
    be updated!

    TODO: Dervice information from column headers, not from raw index
    '''
    rows = []
    for listing in listings:
        row = []
        focuses = [_ if _ else '' for _ in listing.focuses]
        for i in range(len(focuses), 4):
            focuses.append('')

        row += (listing.name.capitalize(), listing.circle, listing.role)
        row += focuses
        row.append('') # Spacer column
        row += [
            listing.avail['Mon'] if 'Mon' in listing.avail else '',
            listing.avail['Tue'] if 'Tue' in listing.avail else '',
            listing.avail['Wed'] if 'Wed' in listing.avail else '',
            listing.avail['Thu'] if 'Thu' in listing.avail else '',
            listing.avail['Fri'] if 'Fri' in listing.avail else '',
            listing.avail['Sat'] if 'Sat' in listing.avail else '',
            listing.avail['Sun'] if 'Sun' in listing.avail else ''
        ]
        rows.append(row)
    return rows


def form_sheet_rows_to_listings(rows):
    '''Data transformation helper function that converts a 2D list of raw google
    sheets cell data into a list of Listing objects. Data supplied to this function
    is likely pulled from the pygsheets Worksheet.get_all_values() functionality.

    NB: This function does no validation on the data coming in, and assumes row indices
    have not changed. If the google form changes fields, and thus, the form submissions
    table in sheets adds/removes columns, thus must be updated!

    TODO: Dervice information from column headers, not from raw index
    '''
    listings = []
    for row in rows:

        # Special case, if the timestamp doesn't exist, it could be because we've got
        # an empty row in the form submission data, potentially due to it having been
        # cleared, or some manual intervention.
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
        
        listings.append(Listing(name, circle, role, focuses, avail, when=arrow.get(row[0], DATE_FORMAT)))
    return listings


def listings_to_dict(listings):
    listing_dict = {}
    for listing in listings:
        listing_dict[listing.name] = listing
    return listing_dict



def sync(creds, sheet_key):
    '''Pull all google form submissions into the bard listing table, and return a dictionary
    of the data in the updated table. This function is indempotent, and can be run even without
    any new data.

    The returned dictionary is a mapping from
    bard name --> Listing object representing the row in question.'''
    
    gc = pygsheets.authorize(service_file=creds)
    spreadsheet = gc.open_by_key(sheet_key)

    # Grab the two worksheets within the google sheet
    form_worksheet = spreadsheet.worksheet_by_title('Registration Form Responses')
    listing_worksheet = spreadsheet.worksheet_by_title('Listing')

    # Grab the marker that says when the table was last updated
    last_sync = arrow.get(listing_worksheet.get_value('S1'), DATE_FORMAT)
    

    # Grab all the data in the listing table, and make a listing cache out of that data
    # where the key is the bard name, and the value is a listing object
    current_listing_raw = listing_worksheet.get_all_values()
    existing_listings = listing_sheet_rows_to_listings(current_listing_raw[1:])
    for listing in existing_listings:
        listing.set_last_updated(last_sync)

    existing_listing_cache = listings_to_dict(existing_listings)


    # Grab a similar cache, but from the form data that's been accrued
    form_raw = form_worksheet.get_all_values()
    form_listings = form_sheet_rows_to_listings(form_raw[1:])
    form_cache = listings_to_dict(form_listings)

    # Form the "update". Start with the current table, and then update as needed with the new form data
    # if the form data has been submitted more recently than the last table refresh.
    new_listing_cache = existing_listing_cache
    for key in form_cache:
        form_listing = form_cache[key]
        # Add listing if a new bard record, update listing if already exists and form listing is more recent
        if key not in new_listing_cache:
            new_listing_cache[key] = form_listing
        elif row.when > new_listing_cache[key].when:
            new_listing_cache[key] = form_listing


    # Get a 2D list representation of the data, and do a mass update of the listing table
    to_update = listings_to_sheet_rows(sorted(new_listing_cache.values(), key=lambda x: x.name))
    listing_worksheet.update_values(crange=f'A2:O{1+len(to_update)}', values=to_update, extend=True)


    # Clean up of the bard listing table in google sheets. If we removed data (somehow), cut off tail rows.
    num_rows = len(existing_listings)
    if num_rows - 1 > len(to_update):
        num_to_delete = num_rows - len(to_update)
        listing_worksheet.delete_rows(len(to_update) + 2, number=num_to_delete)


    # Clean up of the form data in google sheets. Since we've performed a sync, no need for those old submissions.
    # Remove them, and delete all rows. We need to keep one non-header row present, as this is a requirement imposed by
    # google sheets. So for that row, we'll just clear it out.
    form_worksheet.clear(start='A2')
    if form_worksheet.rows > 2:
        form_worksheet.delete_rows(3, number=len(form_raw) - 1)


    # Finally, update the "last synced" timestamp on the listing table in google sheets
    listing_worksheet.update_value('S1', arrow.now().format(DATE_FORMAT))
    return new_listing_cache



def main():
    '''Main function. If we're running this script directly, we can perform these management operations without
    needing to run the discord bot.'''
    parser = argparse.ArgumentParser(description='Manage bard listings in google sheets')
    parser.add_argument('--action', type=str, required=True, choices=['sync'], help='the action to perform')
    parser.add_argument('--creds', type=str, required=True, help='path to the json credentials for the google services account')
    parser.add_argument('--key', type=str, required=True, help='the google sheets key')
    args = parser.parse_args()

    if args.action == 'sync':
        print('Updating the bard listing table with the latest google form data...')
        sync(args.creds, args.key)
        print('done.')


if __name__ == '__main__':
    main()