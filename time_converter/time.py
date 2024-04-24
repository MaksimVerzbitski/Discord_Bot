from datetime import datetime, timedelta
import pytz

def update_time_in_estonia_from_pdt():
    pdt_tz = pytz.timezone('America/Los_Angeles')  # Los Angeles for PDT
    estonia_tz = pytz.timezone('Europe/Tallinn')

    start_time_pdt_str = input("Enter the start time of the update in PDT (HH:MM): ")
    duration_hours = int(input("Enter the duration hours: "))
    duration_minutes = int(input("Enter the duration minutes: "))

    # Correctly localize the time to PDT timezone
    today = datetime.now(pdt_tz).date()
    naive_start_time_pdt = datetime.strptime(f"{today} {start_time_pdt_str}", '%Y-%m-%d %H:%M')
    start_time_pdt = pdt_tz.localize(naive_start_time_pdt)

    # Convert to UTC and then to Estonian time
    start_time_utc = start_time_pdt.astimezone(pytz.utc)
    start_time_estonia = start_time_utc.astimezone(estonia_tz)

    duration = timedelta(hours=duration_hours, minutes=duration_minutes)
    end_time_estonia = start_time_estonia + duration

    print(f"Update start time in Estonian time: {start_time_estonia.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Update end time in Estonian time: {end_time_estonia.strftime('%Y-%m-%d %H:%M:%S')}")

update_time_in_estonia_from_pdt()