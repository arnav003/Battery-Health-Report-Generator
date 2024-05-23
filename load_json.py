import json
import pandas as pd


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
            {'START DATE': start_date, 'END DATE': end_date, 'FULL CHARGE CAPACITY': full_charge_capacity, 'DESIGN CAPACITY': design_capacity})

    capacity_history_df = pd.DataFrame(capacity_history)
    capacity_history_df['START DATE'] = pd.to_datetime(capacity_history_df['START DATE'])
    capacity_history_df['END DATE'] = pd.to_datetime(capacity_history_df['END DATE'])
    return capacity_history_df


if __name__ == "__main__":
    pass
    capacity_history_df = load_capacity_history_from_json('data/battery-capacity-history.json')
    print(capacity_history_df)
    # data = read_json_file('data/battery-report.json')
    # print(data)
