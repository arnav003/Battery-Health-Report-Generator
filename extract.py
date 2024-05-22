import json
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
    if details:
        for key, value in details.items():
            print(f"{key}: {value}")
    else:
        print("No details found.")

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
    for key, value in details.items():
        print(f"{key}: {value}")
    else:
        print("No rows found.")

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
    for entry in data:
        print(entry)

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
    for entry in data:
        print(dict(zip(headers, entry)))

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
    for entry in data:
        print(dict(zip(headers, entry)))

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

    # Extract details from the table
    rows = table.find_all('tr')
    if not rows:
        print("No rows found.")
        return

    # Extracting the table headers
    headers = [th.get_text(strip=True) for th in rows[1].find_all('td')]
    headers = [header.replace('\xa0', ' ').strip() for header in headers if header]

    # Extracting the table data
    data = []
    for row in rows[2:]:
        cells = row.find_all('td')
        cell_data = [cell.get_text(strip=True) for cell in cells]
        data.append(cell_data)

    # Print the extracted details
    for entry in data:
        # Merging the columns for easier display
        print(dict(zip(headers, entry)))

    # Save data to JSON file
    output_json = "data/battery-life-estimates.json"
    with open(output_json, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print(f"Data successfully saved to {output_json}")


def extract_data():
    file_path = 'cleaned_battery-report.html'
    print('Battery report')
    extract_battery_report(file_path, 'Battery report')
    print('Installed batteries')
    extract_installed_batteries(file_path, 'Installed batteries')
    print('Recent usage')
    extract_usage(file_path, 'Recent usage')
    print('Battery usage')
    extract_usage(file_path, 'Battery usage')
    print('Usage history')
    extract_usage_history(file_path, 'Usage history')
    print('Battery capacity history')
    extract_battery_capacity_history(file_path, 'Battery capacity history')
    print('Battery life estimates')
    extract_battery_life_estimates(file_path, 'Battery life estimates')


if __name__ == "__main__":
    extract_data()
