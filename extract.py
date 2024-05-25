import json
import re

from bs4 import BeautifulSoup


def extract_battery_report(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h1', string=lambda text: text and header_text in text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Extract details from the table
    details = {}
    rows = table.find_all('tr')
    if not rows:
        print("No rows found.")
        return

    for row in rows:
        label_cell = row.find('td', class_='label')
        value_cell = label_cell.find_next('td') if label_cell else None
        if label_cell and value_cell:
            label = label_cell.get_text(strip=True)
            value = value_cell.get_text(strip=True)
            details[label] = value

    # Print the extracted details
    # if details:
    #     for key, value in details.items():
    #         print(f"{key}: {value}")
    # else:
    #     print("No details found.")

    # Save data to JSON file
    output_json = "data/battery-report.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(details, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_installed_batteries(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h2', string=lambda text: text and header_text in text)
    # header = soup.find('h2', string=header_text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Extract details from the table
    details = {}
    rows = table.find_all('tr')
    for row in rows:
        label_cell = row.find('span', class_='label')
        value_cell = label_cell.find_next('td') if label_cell else None
        if label_cell and value_cell:
            label = label_cell.get_text(strip=True)
            value = value_cell.get_text(strip=True)
            details[label] = value

    # Print the extracted details
    # for key, value in details.items():
    #     print(f"{key}: {value}")
    # else:
    #     print("No rows found.")

    # Save data to JSON file
    output_json = "data/installed-batteries.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(details, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_usage(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h2', string=lambda text: text and header_text in text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Extract details from the table
    rows = table.find_all('tr')
    if not rows:
        print("No rows found.")
        return

    # Extracting the table headers
    headers = [th.get_text(strip=True) for th in rows[0].find_all('td')]

    # Extracting the table data
    data = []
    for row in rows[1:]:
        cells = row.find_all('td')
        cell_data = []
        for cell in cells:
            cell_data.append(cell.get_text(strip=True))
        data.append(dict(zip(headers, cell_data)))

    # Print the extracted details
    # for entry in data:
    #     print(entry)

    # Save data to JSON file
    output_json = "data/" + header_text.split(' ')[0].lower() + "-usage.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_usage_history(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h2', string=lambda text: text and header_text in text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Extract details from the table
    rows = table.find_all('tr')
    if not rows:
        print("No rows found.")
        return

    # Extracting the table headers
    headers = [th.get_text(strip=True) for th in rows[1].find_all('td')]

    # Extracting the table data
    data = []
    for row in rows[2:]:
        cells = row.find_all('td')
        cell_data = [cell.get_text(strip=True) for cell in cells]
        data.append(cell_data)

    # Print the extracted details
    # for entry in data:
    #     print(dict(zip(headers, entry)))

    # Save data to JSON file
    output_json = "data/usage-history.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_battery_capacity_history(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h2', string=lambda text: text and header_text in text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Extract details from the table
    rows = table.find_all('tr')
    if not rows:
        print("No rows found.")
        return

    # Extracting the table headers
    headers = [th.get_text(strip=True) for th in rows[0].find_all('td')]

    # Extracting the table data
    data = []
    for row in rows[1:]:
        cells = row.find_all('td')
        cell_data = [cell.get_text(strip=True) for cell in cells]
        data.append(cell_data)

    # Print the extracted details
    # for entry in data:
    #     print(dict(zip(headers, entry)))

    # Save data to JSON file
    output_json = "data/battery-capacity-history.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_battery_life_estimates(file_path, header_text):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find the header with the specific text
    header = soup.find('h2', string=lambda text: text and header_text in text)
    if not header:
        print(f"Header '{header_text}' not found.")
        return

    # Find the next table after the header
    table = header.find_next('table')
    if not table:
        print("No table found after the header.")
        return

    # Find all rows in the table
    rows = table.find_all('tr')[2:]  # Skipping the first two header rows
    if not rows:
        print("No rows found.")
        return

    # Initialize a list to hold the extracted data
    data = []

    # Loop through each row and extract the columns
    for row in rows:
        columns = row.find_all('td')

        period = columns[0].text.strip()
        active_full_charge = columns[1].text.strip()

        connected_standby_full_charge = columns[2].text.strip()

        connected_standby_full_charge_drain = columns[2].find('span')
        if connected_standby_full_charge_drain:
            connected_standby_full_charge_drain = connected_standby_full_charge_drain.text
        else:
            connected_standby_full_charge_drain = ""

        active_design_capacity = columns[4].text.strip()

        connected_standby_design_capacity = columns[5].text.strip()

        connected_standby_design_capacity_drain = columns[5].find('span')

        if connected_standby_design_capacity_drain:
            connected_standby_design_capacity_drain = connected_standby_design_capacity_drain.text
        else:
            connected_standby_design_capacity_drain = ""

        # Append the extracted data to the list
        data.append({
            'PERIOD': period,
            'ACTIVE (FULL CHARGE)': active_full_charge,
            'CONNECTED STANDBY (FULL CHARGE)': connected_standby_full_charge,
            'CONNECTED STANDBY (FULL CHARGE) DRAIN': connected_standby_full_charge_drain,
            'ACTIVE (DESIGN CAPACITY)': active_design_capacity,
            'CONNECTED STANDBY (DESIGN CAPACITY)': connected_standby_design_capacity,
            'CONNECTED STANDBY (DESIGN CAPACITY) DRAIN': connected_standby_design_capacity_drain,
        })

    # Print the extracted data
    # for entry in data:
    #     print(entry)

    # Save data to JSON file
    output_json = "data/battery-life-estimates.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_data():
    file_path = 'cleaned_battery-report.html'
    print('Extracting battery report')
    extract_battery_report(file_path, 'Battery report')
    print('Extracting installed batteries')
    extract_installed_batteries(file_path, 'Installed batteries')
    print('Extracting recent usage')
    extract_usage(file_path, 'Recent usage')
    print('Extracting battery usage')
    extract_usage(file_path, 'Battery usage')
    print('Extracting usage history')
    extract_usage_history(file_path, 'Usage history')
    print('Extracting battery capacity history')
    extract_battery_capacity_history(file_path, 'Battery capacity history')
    print('Extracting battery life estimates')
    extract_battery_life_estimates(file_path, 'Battery life estimates')


if __name__ == "__main__":
    extract_data()
