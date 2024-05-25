import json
import pandas as pd
import numpy as np


def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def load_capacity_history_from_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    capacity_history = []
    for entry in data:
        start_date = entry[0].split('\n')[0]  # Extracting the period from the first element
        try:
            end_date = entry[0].split('\n')[1]
        except:
            end_date = ""
        full_charge_capacity = float(
            entry[1].replace(' mWh', '').replace(',', ''))  # Extracting and converting full charge capacity
        design_capacity = float(
            entry[2].replace(' mWh', '').replace(',', ''))  # Extracting and converting design capacity

        capacity_history.append(
            {'START DATE': start_date, 'END DATE': end_date, 'FULL CHARGE CAPACITY': full_charge_capacity,
             'DESIGN CAPACITY': design_capacity})

    capacity_history_df = pd.DataFrame(capacity_history)
    capacity_history_df['START DATE'] = pd.to_datetime(capacity_history_df['START DATE'])
    capacity_history_df['END DATE'] = pd.to_datetime(capacity_history_df['END DATE'])
    return capacity_history_df


def load_life_estimates_from_json(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(data)

    # Clean up the 'PERIOD' column to make it more readable
    df['PERIOD'] = df['PERIOD'].str.replace('\n', ' ')

    # Separate 'PERIOD' into 'START DATE' and 'END DATE'
    df[['START DATE', 'END DATE']] = df['PERIOD'].str.split(' - ', expand=True)
    df.drop(columns=['PERIOD'], inplace=True)

    df['CONNECTED STANDBY (FULL CHARGE) DRAIN (%)'] = df['CONNECTED STANDBY (FULL CHARGE) DRAIN'].str.extract(
        r'(\d+ %)')
    df['CONNECTED STANDBY (FULL CHARGE) (time)'] = df['CONNECTED STANDBY (FULL CHARGE)'].str.extract(
        r'(\d{1,2}:\d{2}:\d{2})')
    df.drop(columns=['CONNECTED STANDBY (FULL CHARGE)'], inplace=True)
    df.drop(columns=['CONNECTED STANDBY (FULL CHARGE) DRAIN'], inplace=True)

    df['CONNECTED STANDBY (DESIGN CAPACITY) DRAIN (%)'] = df['CONNECTED STANDBY (DESIGN CAPACITY) DRAIN'].str.extract(
        r'(\d+ %)')
    df['CONNECTED STANDBY (DESIGN CAPACITY) (time)'] = df['CONNECTED STANDBY (DESIGN CAPACITY)'].str.extract(
        r'(\d{1,2}:\d{2}:\d{2})')
    df.drop(columns=['CONNECTED STANDBY (DESIGN CAPACITY)'], inplace=True)
    df.drop(columns=['CONNECTED STANDBY (DESIGN CAPACITY) DRAIN'], inplace=True)

    df['START DATE'] = pd.to_datetime(df['START DATE'])
    df['END DATE'] = pd.to_datetime(df['END DATE'])

    # Function to preprocess time data
    def preprocess_time(time_str):
        if isinstance(time_str, float) and np.isnan(time_str):
            return np.nan  # Return NaN if the value is NaN
        components = time_str.split(':')
        total_hours = int(components[0])
        days = int(total_hours // 24)  # Calculate number of days
        hours = int(total_hours % 24)  # Extract remaining hours
        minutes = int(components[1])
        seconds = int(components[2])
        # return f'{days} days {hours:02d}:{minutes:02d}:{seconds:02d}'
        return int(((days * 24 + hours) * 60 + minutes) * 60 + seconds)

    # Apply preprocessing function to time column
    df['ACTIVE (FULL CHARGE)'] = df['ACTIVE (FULL CHARGE)'].apply(preprocess_time)
    df['ACTIVE (DESIGN CAPACITY)'] = df['ACTIVE (DESIGN CAPACITY)'].apply(preprocess_time)
    df['CONNECTED STANDBY (FULL CHARGE) (time)'] = df['CONNECTED STANDBY (FULL CHARGE) (time)'].apply(preprocess_time)
    df['CONNECTED STANDBY (DESIGN CAPACITY) (time)'] = df['CONNECTED STANDBY (DESIGN CAPACITY) (time)'].apply(preprocess_time)

    return df


def load_battery_usage_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(data)

    # Convert 'START TIME' to datetime
    df['START TIME'] = pd.to_datetime(df['START TIME'], format='%Y-%m-%d %H:%M:%S')

    # Convert 'DURATION' to timedelta
    df['DURATION'] = pd.to_timedelta(df['DURATION'])

    # Clean up the 'ENERGY DRAINED (%)' column
    df['ENERGY DRAINED (%)'] = df['ENERGY DRAINED (%)'].str.replace(' %', '')
    df['ENERGY DRAINED (%)'] = pd.to_numeric(df['ENERGY DRAINED (%)'], errors='coerce')

    # Clean up the 'ENERGY DRAINED (mWh)' column
    df['ENERGY DRAINED (mWh)'] = df['ENERGY DRAINED (mWh)'].str.replace(' mWh', '').str.replace(',', '')
    df['ENERGY DRAINED (mWh)'] = pd.to_numeric(df['ENERGY DRAINED (mWh)'], errors='coerce')

    # Replace NaN values with 0 or any appropriate placeholder
    df['ENERGY DRAINED (%)'].fillna(0, inplace=True)
    df['ENERGY DRAINED (mWh)'].fillna(0, inplace=True)

    return df


if __name__ == "__main__":
    pass
    # capacity_history_df = load_capacity_history_from_json('data/battery-capacity-history.json')
    # print(capacity_history_df)
    # df = load_life_estimates_from_json('data/battery-life-estimates.json')
    # print(df.iloc[0])
    # data = read_json_file('data/battery-report.json')
    # print(data)
    df = load_battery_usage_from_json('data/battery-usage.json')
    print(df.iloc[0])