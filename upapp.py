import sys
import requests
from bs4 import BeautifulSoup
import time
from tabulate import tabulate
from datetime import datetime
import pymysql
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QTextEdit, QSizePolicy
from PyQt5.QtCore import Qt, QTimer

class PFMScraperApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.login_url = 'https://pfm.smartcitylk.org/wp-login.php'
        self.target_url = 'https://pfm.smartcitylk.org/wp-admin/admin.php?page=actual+'
        self.username = 'kiruba00004@gmail.com'
        self.password = 'TAFpfm#99283'

        self.db_host = 'localhost'
        self.db_user = 'root'
        self.db_password = ''
        self.db_name = 'tpfm'

        self.session = requests.Session()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PFM Scraper App')
        self.setGeometry(100, 100, 800, 600)

        self.status_label = QLabel('Status: Not logged in')
        self.status_label.setAlignment(Qt.AlignCenter)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.start_button = QPushButton('Start Scraping')
        self.start_button.clicked.connect(self.start_scraping)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_output)
        layout.addWidget(self.start_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_scraping(self):
        self.log_output.clear()
        self.log_output.append('Logging in...')
        
        login_payload = {
            'log': self.username,
            'pwd': self.password,
            'wp-submit': 'Log In',
            'redirect_to': self.target_url,
        }
        login_response = self.session.post(self.login_url, data=login_payload)

        if 'wp-admin' in login_response.url:
            self.log_output.append('Login successful')

            self.previous_content = self.fetch_page()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check_update)
            self.timer.start(3000)  # Set the interval to 3 seconds (adjust as needed)
        else:
            self.log_output.append('Login failed')

    def fetch_page(self):
        target_page = self.fetch_page_with_retries()
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

    def fetch_page_with_retries(self):
        max_retries = 3
        retries = 0

        while retries < max_retries:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                target_page = self.session.get(self.target_url, headers=headers, timeout=10)
                return target_page
            except requests.exceptions.RequestException as e:
                self.log_output.append(f"Error: {e}")
                retries += 1
                time.sleep(5)  # Add a delay before retrying

        raise Exception("Failed to fetch page after multiple retries")

    def check_update(self):
        try:
            current_content = self.fetch_page()

            for i in range(len(current_content)):
                if self.is_updated(self.previous_content[i], current_content[i]):
                    self.log_output.append(f'Table {i + 1} updated. Displaying updated details.')
                    self.log_output.append(f'Date and Time: {datetime.now()}')
                    headers = current_content[i][0]
                    table_data = current_content[i][1:]
                    self.log_output.append(tabulate(table_data, headers=headers, tablefmt="grid"))
                    self.previous_content[i] = current_content[i]
                    self.update_database(i + 1, current_content[i])
                else:
                    self.log_output.append(f'Table {i + 1} not updated.')
        except Exception as e:
            self.log_output.append(f'Error: {e}')

    def is_updated(self, previous_content, current_content):
        return str(previous_content) != str(current_content)

    def update_database(self, table_index, table_content):
        table_name = f'table{table_index}_{int(time.time())}'
        conn = pymysql.connect(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name)
        cursor = conn.cursor()

        cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} (id INT AUTO_INCREMENT PRIMARY KEY)')

        for i in range(20):
            column_name = f'column_{i + 1}'
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(255)')

        for row_content in table_content[1:]:
            row_content = row_content[:20] + [''] * (20 - len(row_content))
            values = ', '.join(f'"{value}"' for value in row_content)
            cursor.execute(f'INSERT INTO {table_name} VALUES (NULL, {values})')

        conn.commit()
        conn.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = PFMScraperApp()
    main_app.show()
    sys.exit(app.exec_())
