import random
import calendar
from datetime import date, datetime
import math
import httplib2
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_average_shifts_per_worker(worker_shift_count):
    # Calculate the total number of shifts assigned to all workers
    total_shifts = sum(worker_shift_count.values())

    # Calculate the average shifts per worker
    return total_shifts / len(worker_shift_count)

def get_sundays(year, month):
    sundays = []
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        for day in week:
            if day != 0 and calendar.weekday(year, month, day) == 6:  # Sunday has weekday value 6
                sundays.append(date(year, month, day))
    
    return sundays

def assign_shifts(year, month, unavailable_dates):

    sundays = get_sundays(year, month)

    # Calculate the number of Sundays in the given month
    num_sundays = len(sundays)

    # Define your team members and their availability
    team_members = unavailable_dates.keys()

    # Initialize shift assignments and a counter for each worker's shifts
    shifts = {sunday: [] for sunday in sundays}
    # print(shifts)
    worker_shift_count = {worker: 0 for worker in team_members}

    # Determine the target number of shifts per worker
    target_shifts_per_worker = math.ceil((num_sundays * 3) / len(team_members))

    # Distribute morning and evening shifts alternately
    for sunday in sundays:
        available_workers = [worker for worker in team_members if sunday not in unavailable_dates.get(worker, [])]
        print("Available workers for Sunday " + str(sunday))
        # print(available_workers)

        morning_shift = []
        evening_shift = []

        if len(available_workers) >= 3:
            random.shuffle(available_workers)

            for worker in available_workers:
                if worker_shift_count[worker] < target_shifts_per_worker and worker_shift_count[worker] <= get_average_shifts_per_worker(worker_shift_count):
                    if len(morning_shift) < 2:
                        morning_shift.append(worker)
                        worker_shift_count[worker] += 1
                    elif len(evening_shift) == 0:
                        evening_shift.append(worker)
                        worker_shift_count[worker] += 1

        shifts[sunday].extend(morning_shift)
        shifts[sunday].extend(evening_shift)

    # Print the shift assignments in a table
    print(f"Shift Assignments for {calendar.month_name[month]} {year}:")
    print("Sunday\t\tMorning\t\tEvening")
    for sunday in sundays:
        morning_workers = shifts[sunday][:2]
        evening_worker = shifts[sunday][2] if len(shifts[sunday]) > 2 else "N/A"
        print(f"{sunday}\t{', '.join(morning_workers)}\t{evening_worker}")

    # Calculate and return the number of assignments for each worker
    assignments_count = {worker: sum(1 for sunday_shifts in shifts.values() if worker in sunday_shifts) for worker in team_members}
    return assignments_count

# Read data from Google spreadsheet

service_account_file = '<GOOGLE_SERVICE_ACCOUNT_CREDS_JSON_FILE>'

# Define the scopes and authenticate with the service account
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
creds = None

try:
    creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
except Exception as e:
    print(f"Authentication error: {e}")
    exit(1)

# Create a Google Sheets API service client
service = build('sheets', 'v4', credentials=creds)

# ID of the Google Sheets document you want to read (found in the URL)
spreadsheet_id = '161FnYhSYyy1m3MmyOZnMhKtsamzQwT48ct8MC-7gL3M'

# Name of the sheet within the document
sheet_name = 'Respostas'

# Define the range of data you want to read (e.g., A1:C10)
range_name = 'B2:C30'

# Call the Google Sheets API to get the data
try:
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print('No data found in spreadsheet.')

except Exception as e:
    print(f"Error reading data: {e}")

unavailable_dates = {}
# Build unavailable_dates entry
for entry in values:
    name = entry[0].strip()  # Remove leading/trailing spaces from the name
    dates = entry[1].split(', ')  # Split date string by comma and space
    # Initialize a list to store parsed dates
    date_list = []
    # Parse each date string and add it to the date list
    for date_str in dates:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
        date_list.append(date_obj)
    # Add the name and date list to the result dictionary
    unavailable_dates[name] = date_list

# print("Unavailable dates per member")
# print(unavailable_dates)

# Change year/month
year = 2023
month = 10
assignments_count = assign_shifts(year, month, unavailable_dates)

# Print the number of assignments for each worker
print("\nNumber of Assignments for Each Worker:")
for worker, count in assignments_count.items():
    print(f"{worker}: {count} assignments")
