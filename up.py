import requests
from bs4 import BeautifulSoup
import time
from tabulate import tabulate
from datetime import datetime
import pymysql

login_url = 'https://pfm.smartcitylk.org/wp-login.php'
target_url = 'https://pfm.smartcitylk.org/wp-admin/admin.php?page=actual+'
username = 'kiruba00004@gmail.com'
password = 'TAFpfm#99283'

session = requests.Session()

def fetch_page_with_retries():
    max_retries = 3
    retries = 0

    while retries < max_retries:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            target_page = session.get(target_url, headers=headers, timeout=10)
            return target_page
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            retries += 1
            time.sleep(5)  # Add a delay before retrying

    raise Exception("Failed to fetch page after multiple retries")

def fetch_page():
    target_page = fetch_page_with_retries()
    soup = BeautifulSoup(target_page.content, 'html.parser')
    tables = soup.find_all('table')[1:]  # Exclude the first table
    all_table_content = []

    for table in tables:
        rows = table.find_all('tr')
        table_content = []
        headers = [header.text.strip() for header in rows[0].find_all('th')]
        table_content.append(headers)

        for row in rows[1:]:
            cells = row.find_all('td')
            row_content = [cell.text.strip() for cell in cells]
            table_content.append(row_content)

        all_table_content.append(table_content)

    return all_table_content

def is_updated(previous_content, current_content):
    return str(previous_content) != str(current_content)

def update_database(table_index, table_content):
    # Create a unique table name based on the current timestamp
    table_name = f'table{table_index}_{int(time.time())}'
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id INT AUTO_INCREMENT PRIMARY KEY)')

    # Ensure the table has at least 20 columns
    for i in range(20):
        column_name = f'column_{i + 1}'
        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255)')

    # Insert the updated table content into the new table
    for row_content in table_content[1:]:
        # Truncate or pad row content to fit 20 columns
        row_content = row_content[:20] + [''] * (20 - len(row_content))
        values = ', '.join(f'"{value}"' for value in row_content)
        cursor.execute(f'INSERT INTO {table_name} VALUES (NULL, {values})')

    # Commit the changes
    conn.commit()

# MySQL database connection settings
db_host = 'localhost'
db_user = 'root'
db_password = ''
db_name = 'tpfm'

conn = pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)
cursor = conn.cursor()

login_payload = {
    'log': username,
    'pwd': password,
    'wp-submit': 'Log In',
    'redirect_to': target_url,
}
login_response = session.post(login_url, data=login_payload)

if 'wp-admin' in login_response.url:
    print("Login successful")
    previous_content = fetch_page()

    while True:
        try:
            time.sleep(3)
            current_content = fetch_page()

            for i in range(len(current_content)):
                if is_updated(previous_content[i], current_content[i]):
                    print(f"Table {i + 1} updated. Displaying updated details.")
                    print("Date and Time:", datetime.now())
                    headers = current_content[i][0]
                    table_data = current_content[i][1:]
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                    previous_content[i] = current_content[i]
                    update_database(i + 1, current_content[i])
                else:
                    print(f"Table {i + 1} not updated.")
        except Exception as e:
            print(f"Error: {e}")
else:
    print("Login failed")
