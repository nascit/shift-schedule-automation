import random
import calendar
from datetime import datetime, time
from typing import Dict, List, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Change year/month
YEAR = 2023
MONTH = 10

SHIFT_DAY_OF_WEEK = 6 # Sunday has weekday value 6
MORNING_SHIFT_START = time(11, 0)
EVENING_SHIFT_START = time(19, 0)
MORNING_SHIFT_CAPACITY = 2
EVENING_SHIFT_CAPACITY = 1


def get_average_shifts_per_worker(worker_shift_count: Dict[str, int]) -> float:
    """
    Calculate the average number of shifts per worker.

    :param worker_shift_count: A dictionary of worker names and their assigned shifts.
    :return: The average number of shifts per worker.
    """
    total_shifts = sum(worker_shift_count.values())
    return total_shifts / len(worker_shift_count)


def get_monthly_shifts(year: int, month: int) -> Dict[datetime, int]:
    """
    Get the list of shifts in a given month.
    :param year: year to  check for shifts in the month.
    :param month: month to check for shifts in the year.
    :return: list of shifts in the month.
    """
    monthly_shifts: Dict[datetime, int] = {}
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        for day in week:
            if day != 0 and calendar.weekday(year, month, day) == SHIFT_DAY_OF_WEEK:
                # Add morning
                shift_date = datetime(year, month, day, MORNING_SHIFT_START.hour, MORNING_SHIFT_START.minute)
                monthly_shifts[shift_date] = MORNING_SHIFT_CAPACITY
                # Add evening
                shift_date = datetime(year, month, day, EVENING_SHIFT_START.hour, EVENING_SHIFT_START.minute)
                monthly_shifts[shift_date] = EVENING_SHIFT_CAPACITY

    return monthly_shifts


def get_available_workers_per_shift(monthly_shifts: Dict[datetime, int], unavailable_dates: Dict[str, List[datetime]]) -> Dict[datetime, List[str]]:
    """
    Get the list of available workers for each shift in the month.
    :param monthly_shifts: dictionary of shifts in the month.
    :param unavailable_dates: dictionary of unavailable dates for each worker.
    :return: dictionary of available workers for each shift in the month.
    """
    available_workers_per_shift: Dict[datetime, List[str]] = {}
    for shift in monthly_shifts:
        available_workers = [worker for worker in unavailable_dates.keys() if shift not in unavailable_dates[worker]]
        available_workers_per_shift[shift] = available_workers

    return available_workers_per_shift


def get_shifts_sorted_by_least_available_workers(available_workers_per_shift: Dict[datetime, List[str]]) -> List[datetime]:
    """
    Get the list of shifts sorted by the least number of available workers.
    :param available_workers_per_shift: dictionary of available workers for each shift in the month.
    :return: dictionary of shifts sorted by the least number of available workers.
    """
    shifts: List[datetime] = list(available_workers_per_shift.keys())
    random.shuffle(shifts)
    # Sort the shifts by the number of available workers
    return sorted(shifts, key=lambda shift: len(available_workers_per_shift[shift]))


def assign_shifts(year: int, month: int, unavailable_dates: Dict[str, List[datetime]]) -> Dict[datetime, List[str]]:
    """
    Assign shifts to workers in a given month.
    :param year: year to assign shifts to.
    :param month: month to assign shifts to.
    :param unavailable_dates: dictionary of unavailable dates for each worker.
    :return: dictionary of available workers for each shift in the month.
    """
    # Get the list of shifts in the given month and the list of available workers for each
    shifts_capacity = get_monthly_shifts(year, month)
    available_workers_per_shift = get_available_workers_per_shift(shifts_capacity, unavailable_dates)

    # Sort the workers by the least number of available shifts
    shifts_sorted_by_least_available_workers = get_shifts_sorted_by_least_available_workers(available_workers_per_shift)

    # Initialize the final shift schedule
    final_shift_schedule: Dict[datetime, List[str]] = {}
    worker_shift_count: Dict[str, int] = {}

    # Assign shifts to workers
    for shift in shifts_sorted_by_least_available_workers:
        # Sort the available workers by the number of shifts they have already been assigned
        available_workers = available_workers_per_shift.get(shift, [])
        available_workers = sorted(available_workers, key=lambda available: worker_shift_count.get(available, 0), reverse=True)
        assigned_workers = final_shift_schedule.get(shift, [])

        # Assign workers to the shift until the shift capacity is reached
        while (shifts_capacity[shift] > 0
               and len(available_workers) > len(assigned_workers)):
            # Assign a random worker to the shift based on the availability for that shift
            worker = available_workers.pop()
            if worker not in assigned_workers:
                shifts_capacity[shift] -= 1
                worker_shift_count[worker] = worker_shift_count.get(worker, 0) + 1
                final_shift_schedule[shift] = assigned_workers + [worker]
                assigned_workers = final_shift_schedule[shift]

    # Sort the shifts by date
    final_shift_schedule = dict(sorted(final_shift_schedule.items()))
    return final_shift_schedule


def print_shift_schedule(shift_schedule: Dict[datetime, List[str]], year: int, month: int):
    """
    Print the shift schedule.
    :param shifts: dictionary of shifts and their assigned workers.
    :param year: year to  check for shifts in the month.
    :param month: month to check for shifts in the year.
    """
    print(f"Shift Assignments for {calendar.month_name[month]} {year}:")
    print("Sunday\t\tTime\t\tTeam")
    for shift, workers in shift_schedule.items():
        print(f"{shift}: {', '.join(workers)}")

    # Calculate and return the number of assignments for each worker
    worker_shift_count = {}
    for shift, workers in shift_schedule.items():
        for worker in workers:
            worker_shift_count[worker] = worker_shift_count.get(worker, 0) + 1

    # Print the number of assignments for each worker
    print("\nNumber of Assignments for Each Worker:")
    for worker, count in worker_shift_count.items():
        print(f"{worker}: {count} assignments")


def parse_unavailable_dates(entries: List[str]) -> Dict[str, List[datetime]]:
    """
    Parse the unavailable dates from the Google Sheets document.
    :param entries: list of unavailable dates for each worker.
    :return: dictionary of unavailable dates for each worker.
    """
    unavailable_dates: Dict[str, List[datetime]] = {}
    # Build unavailable_dates entry
    for entry in entries:
        name = entry[0].strip()  # Remove leading/trailing spaces from the name
        dates = entry[1].split(', ')  # Split date string by comma and space
        # Initialize a list to store parsed dates
        date_list: List[datetime] = []
        # Parse each date string and add it to the date list
        for date_str in dates:
            date_obj = datetime.strptime(date_str, '%d/%m/%Y %H:%M:%S')
            date_list.append(date_obj)
        # Add the name and date list to the result dictionary
        unavailable_dates[name] = date_list

    return unavailable_dates


def read_data_spreadsheet(spreadsheet_id: str, sheet_name: str, range_name: str, credentials: Any) -> List[str]:
    """
    Read data from a Google Sheets document.
    :param spreadsheet_id: ID of the Google Sheets document.
    :param sheet_name: name of the sheet within the document.
    :param range_name: range of data to read (e.g., A1:C10).
    :return: list of data read from the Google Sheets document.
    """
    # Create a Google Sheets API service client
    service = build('sheets', 'v4', credentials=credentials)

    # Call the Google Sheets API to get the data
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values: List[str] = result.get('values', [])

    if not values:
        ValueError('No data found in spreadsheet.')

    return values


# Read data from Google spreadsheet
service_account_file = '<GOOGLE_SERVICE_ACCOUNT_CREDS_JSON_FILE>'

# Define the scopes and authenticate with the service account
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
creds = None

try:
    # Load the service account credentials from the JSON file and authenticate with the service account
    creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    # ID of the Google Sheets document you want to read (found in the URL)
    spreadsheet_id = '161FnYhSYyy1m3MmyOZnMhKtsamzQwT48ct8MC-7gL3M'
    # Name of the sheet within the document
    sheet_name = 'Respostas'
    # Define the range of data you want to read (e.g., A1:C10)
    range_name = 'B2:C30'

    # Call the Google Sheets API to get the data
    values = read_data_spreadsheet(spreadsheet_id, sheet_name, range_name, creds)
    unavailable_dates = parse_unavailable_dates(values)

    shift_schedule = assign_shifts(YEAR, MONTH, unavailable_dates)
    print_shift_schedule(shift_schedule, YEAR, MONTH)

except Exception as e:
    print(f"Failed to generate scale: {e}")
    exit(1)