import sys
import json
import os
import requests
from pathlib import Path
import subprocess
import mplcursors
import numpy as np
import pandas as pd
import seaborn as sns
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QTableWidget, QTableWidgetItem, \
    QHBoxLayout, QLabel, QProgressDialog, QMenuBar, QMessageBox
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction, QDesktopServices
from PyQt6.QtCore import Qt, QTimer, QUrl, QCoreApplication
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qdarkstyle import _load_stylesheet
from qdarkstyle.palette import Palette

from load_json import load_capacity_history_from_json, load_life_estimates_from_json, load_recent_usage_from_json, \
    load_battery_usage_from_json, load_current_battery_life_estimate_from_json, read_json_file
from generate import generate_battery_report
from clean import clean_html
from extract import extract_data

# TODO: Replace with the current version
CURRENT_VERSION = "1.6.0"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Battery Health Report Generator')
        self.setGeometry(100, 100, 800, 600)
        self.theme = 'light'
        palette = Palette()
        palette.ID = self.theme
        self.setStyleSheet(_load_stylesheet(palette=palette))

        # Add menu bar
        self.menu_bar = self.create_menu_bar()
        self.setMenuBar(self.menu_bar)

        # Show loading indicator
        self.show_loading_indicator()
        self.progress_dialog.show()

        # Get all required data
        data_files = [
            "data/battery-capacity-history.json",
            "data/battery-life-estimates.json",
            "data/battery-report.json",
            "data/battery-usage.json",
            "data/installed-batteries.json",
            "data/recent-usage.json",
            "data/usage-history.json"
        ]

        if not all(os.path.exists(file) for file in data_files):
            QTimer.singleShot(2000, self.get_data)
        else:
            # Load all data into widgets
            self.load_data()

    def create_menu_bar(self):
        menu_bar = QMenuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Show battery-report.html action
        show_report_action = QAction("Show battery-report.html", self)
        show_report_action.triggered.connect(self.show_battery_report)
        file_menu.addAction(show_report_action)

        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)

        # Toggle theme action
        self.toggle_theme_action = QAction("Toggle Theme", self)
        self.toggle_theme_action.triggered.connect(self.toggle_theme)
        file_menu.addAction(self.toggle_theme_action)

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        # About us action
        about_action = QAction("About Us", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Update software action
        update_action = QAction("Update Software", self)
        update_action.triggered.connect(self.update_software)
        help_menu.addAction(update_action)

        # Send feedback action
        feedback_action = QAction("Send Feedback", self)
        feedback_action.triggered.connect(self.send_feedback)
        help_menu.addAction(feedback_action)

        return menu_bar

    def show_battery_report(self):
        file_path = 'battery-report.html'
        if file_path:
            os.startfile(file_path)

    def refresh_data(self):
        self.show_loading_indicator()
        self.progress_dialog.show()
        QTimer.singleShot(2000, self.get_data)

    def toggle_theme(self):
        if self.theme == 'light':
            self.theme = 'dark'
        elif self.theme == 'dark':
            self.theme = 'light'

        palette = Palette()
        palette.ID = self.theme
        self.setStyleSheet(_load_stylesheet(palette=palette))

    def show_about_dialog(self):
        about_text = "Battery Health Report Generator\n\nCreated by Lala Arnav Vatsal\narnav.vatsal2213@gmail.com\n\nThis application provides detailed battery health reports and analysis."
        QMessageBox.about(self, "About Us", about_text)

    def check_for_updates(self):
        # GitHub repository details
        repo_owner = "arnav003"
        repo_name = "Battery-Health-Report-Generator"

        # GitHub API URL for releases
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"]
                download_url = None
                for asset in latest_release['assets']:
                    if asset['name'].endswith('.exe'):
                        download_url = asset['browser_download_url']
                        break
                return latest_version, download_url
            else:
                print("Failed to fetch release information from GitHub:", response.text)
                return None, None
        except Exception as e:
            print("Error checking for updates:", e)
            return None, None

    def download_and_install_update(self, download_url, installer_path):
        # Create a QMessageBox to show download progress
        progress_dialog = QMessageBox(self)
        progress_dialog.setWindowTitle("Downloading Update")
        progress_dialog.setText("Downloading update...")
        progress_dialog.setStandardButtons(QMessageBox.StandardButton.Cancel)
        progress_dialog.show()

        try:
            # Download the installer
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress = int((downloaded_size / total_size) * 100)
                        progress_dialog.setText(f"Downloading update... {progress}%")
                        QCoreApplication.processEvents()  # Process pending events to update UI
                    else:
                        break

            # Close the progress dialog
            progress_dialog.close()

            # Open file explorer at the directory containing the installer
            installer_directory = os.path.dirname(installer_path)
            subprocess.Popen(['explorer', installer_directory])

            # Exit the application
            sys.exit()
        except Exception as e:
            print("Error downloading updates:", e)
            QMessageBox.critical(self, "Update Error", "Failed to download updates. Please try again later.")

    def update_software(self):
        # Check for updates
        latest_version, download_url = self.check_for_updates()
        if latest_version is None or download_url is None:
            QMessageBox.critical(self, "Update Error", "Failed to check for updates. Please try again later.")
            return

        current_version = CURRENT_VERSION
        latest_version = latest_version.lstrip("v")
        if latest_version > current_version:
            # Prompt user to download and install updates
            reply = QMessageBox.question(self, "Update Available",
                                         f"A new version ({latest_version}) is available. Do you want to download and install it?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                # Download and install updates
                # You can use a library like requests to download the file
                # For simplicity, let's assume the download URL is in `download_url`
                # and the file is downloaded to the current directory
                try:
                    installer_path = str(Path.home() / "Downloads") + f"\latest_installer_v{latest_version}.exe"
                    self.download_and_install_update(download_url, installer_path)
                    QMessageBox.information(self, "Update Complete",
                                            "The software has been updated successfully. Please restart the application.")
                except Exception as e:
                    print("Error downloading updates:", e)
                    QMessageBox.critical(self, "Update Error", "Failed to download updates. Please try again later.")
        else:
            QMessageBox.information(self, "No Updates", "You are already using the latest version of the software.")

    def send_feedback(self):
        feedback_form_url = "http://arnav003.github.io/battery-health.html#feedback"
        QDesktopServices.openUrl(QUrl(feedback_form_url))

    def show_loading_indicator(self):
        self.progress_dialog = QProgressDialog("Loading data...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)

    def get_data(self):
        generate_battery_report()
        clean_html()
        self.create_directory("data")
        extract_data()

        # Load all data into widgets
        self.load_data()

    def create_directory(self, directory_path):
        try:
            os.makedirs(directory_path)
            print(f"Directory '{directory_path}' created successfully.")
        except FileExistsError:
            print(f"Directory '{directory_path}' already exists.")

    def load_data(self):
        # Calculate battery health percentage
        self.battery_health_percentage = self.calculate_battery_health()

        # Create the first table widget
        self.table_widget1 = QTableWidget()
        self.table_widget1.setColumnCount(2)
        self.setup_table_style(self.table_widget1)
        self.load_data_into_table(self.table_widget1, 'data/battery-report.json')

        # Create the second table widget
        self.table_widget2 = QTableWidget()
        self.table_widget2.setColumnCount(2)
        self.setup_table_style(self.table_widget2)
        self.load_data_into_table(self.table_widget2, 'data/installed-batteries.json')

        # Load data
        self.capacity_df = load_capacity_history_from_json('data/battery-capacity-history.json')
        self.life_estimates_df = load_life_estimates_from_json('data/battery-life-estimates.json')
        self.recent_usage_df = load_recent_usage_from_json('data/recent-usage.json')
        self.battery_usage_df = load_battery_usage_from_json('data/battery-usage.json')

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Add battery health icon and percentage
        self.battery_health_layout = self.update_battery_health_label()
        layout.addWidget(self.battery_health_layout, alignment=Qt.AlignmentFlag.AlignCenter)

        # Create horizontal layout for tables
        table_layout = QHBoxLayout()

        # Add table widgets to layout
        table_layout.addWidget(self.table_widget1)
        table_layout.addWidget(self.table_widget2)

        layout.addLayout(table_layout)

        # Create combo box for selecting data
        self.combo_box = QComboBox()
        self.combo_box.addItem("Battery Capacity History")
        self.combo_box.addItem("Battery Life Estimates (Active)")
        self.combo_box.addItem("Battery Life Estimates (Standby)")
        self.combo_box.addItem("Recent Usage")
        self.combo_box.addItem("Battery Usage")
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.combo_box)

        # Create canvas for plotting
        self.canvas = FigureCanvas(Figure())
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()

        # Initial plot
        self.update_plot()

        self.progress_dialog.close()

    def calculate_battery_health(self):
        # Load installed batteries data
        battery_data = read_json_file('data/installed-batteries.json')
        design_capacity = int(battery_data["DESIGN CAPACITY"].replace(',', '').split(' ')[0])
        full_charge_capacity = int(battery_data["FULL CHARGE CAPACITY"].replace(',', '').split(' ')[0])
        battery_health_percentage = (full_charge_capacity / design_capacity) * 100
        return battery_health_percentage

    def update_battery_health_label(self):
        battery_health_icon = QPixmap('battery_icon.png')
        icon_label = QLabel()
        icon_label.setPixmap(battery_health_icon.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation))

        percentage_label = QLabel(f'Battery Health: {self.battery_health_percentage:.2f}%')
        percentage_label.setFont(QFont('Arial', 16))
        percentage_label.setStyleSheet("color: green;")

        layout = QHBoxLayout()
        layout.addWidget(icon_label)
        layout.addWidget(percentage_label)

        container = QWidget()
        container.setLayout(layout)

        return container

    def setup_table_style(self, table_widget):
        # Set table properties
        table_widget.horizontalHeader().setStretchLastSection(True)
        table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        table_widget.setAlternatingRowColors(True)
        table_widget.verticalHeader().setVisible(False)
        table_widget.horizontalHeader().setVisible(False)
        table_widget.setSortingEnabled(True)

        # Set font
        font = QFont()
        font.setPointSize(10)
        table_widget.setFont(font)

        # Set cell padding
        table_widget.setStyleSheet("QTableWidget::item { padding: 10px; }")

    def load_data_into_table(self, table_widget, file_path):
        # Read data from JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Set number of rows
        table_widget.setRowCount(len(data))

        # Populate table with data
        for row, (key, value) in enumerate(data.items()):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(str(value))
            table_widget.setItem(row, 0, key_item)
            table_widget.setItem(row, 1, value_item)

    def update_plot(self):
        self.ax.clear()
        selected_data = self.combo_box.currentText()

        if selected_data == "Battery Capacity History":
            self.plot_capacity_history()
        elif selected_data == "Battery Life Estimates (Active)":
            self.plot_life_estimates('active')
        elif selected_data == "Battery Life Estimates (Standby)":
            self.plot_life_estimates('standby')
        elif selected_data == 'Recent Usage':
            self.plot_recent_usage()
        elif selected_data == 'Battery Usage':
            self.plot_battery_usage()

        self.canvas.draw()

    def plot_capacity_history(self):
        x_values = np.asarray(self.capacity_df['START DATE'])
        y_values = self.capacity_df['FULL CHARGE CAPACITY']
        line, = self.ax.plot(x_values, y_values)
        self.ax.set_title('Battery Capacity History')
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Full Charge Capacity (mWh)')

        #  Adjust the limits of y-axis
        # self.ax.set_ylim(0, self.capacity_df['DESIGN CAPACITY'][0])

        # Angle the x-axis labels
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=45, ha='right')

        # Adjust layout to make room for the labels
        self.canvas.figure.tight_layout()

        # Make the plot interactive
        cursor = mplcursors.cursor(line, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f'{(matplotlib.dates.num2date(sel.target[0])).strftime("%Y-%m-%d")}\n{int(sel.target[1])} mWh'))

    def plot_life_estimates(self, state):
        x_values = np.asarray(self.capacity_df['START DATE'])

        data = load_current_battery_life_estimate_from_json('data/current-battery-life-estimate.json')

        design_capacity_estimate = None
        if state == 'active':
            columns_to_plot = ['ACTIVE (FULL CHARGE)', 'ACTIVE (DESIGN CAPACITY)']
            design_capacity_estimate = data["ACTIVE (DESIGN CAPACITY)"][0]
            self.ax.set_title('Battery Life Estimates (Active)')
        elif state == 'standby':
            columns_to_plot = ['CONNECTED STANDBY (FULL CHARGE) (time)', 'CONNECTED STANDBY (DESIGN CAPACITY) (time)']
            design_capacity_estimate = data["CONNECTED STANDBY (DESIGN CAPACITY)"][0]
            self.ax.set_title('Battery Life Estimates (Standby)')

        y_values_in_sec = (self.life_estimates_df[columns_to_plot[0]] / self.life_estimates_df[
            columns_to_plot[1]]) * design_capacity_estimate
        y_values = y_values_in_sec / 60

        # Plot each column
        # for i, column in enumerate(columns_to_plot):
        #     self.ax.plot(x_values, y_values[column], label=column)
        line, = self.ax.plot(x_values, y_values)

        # self.ax.legend(loc="upper right")
        self.ax.set_ylabel('Drain Time (in minutes)')

        # Set common xlabel
        self.ax.set_xlabel('Period')

        # Rotate x-axis labels for better readability
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=45, ha='right')

        # Adjust layout
        self.canvas.figure.tight_layout()

        # Make the plot interactive
        cursor = mplcursors.cursor(line, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f'{(matplotlib.dates.num2date(sel.target[0])).strftime("%Y-%m-%d")}\n{int(sel.target[1])} min'))

    def plot_recent_usage(self):
        df = self.recent_usage_df

        # Set START TIME as index
        df.set_index('START TIME', inplace=True)

        # Resample numeric columns to hourly frequency
        numeric_cols = ['CAPACITY REMAINING (%)', 'CAPACITY REMAINING (mWh)']
        df_numeric_resampled = df[numeric_cols].resample('h').mean()

        # Interpolate missing values in numeric columns
        df_numeric_resampled['CAPACITY REMAINING (%)'] = df_numeric_resampled['CAPACITY REMAINING (%)'].interpolate()
        df_numeric_resampled['CAPACITY REMAINING (mWh)'] = df_numeric_resampled[
            'CAPACITY REMAINING (mWh)'].interpolate()

        # Handle non-numeric columns
        # Forward-fill non-numeric columns to propagate last valid observation
        non_numeric_cols = ['STATE', 'SOURCE']
        df_non_numeric_resampled = df[non_numeric_cols].resample('h').ffill()

        # Combine resampled numeric and non-numeric columns
        df_resampled = pd.concat([df_numeric_resampled, df_non_numeric_resampled], axis=1)

        # Reset index to get START TIME as a column again
        df_resampled.reset_index(inplace=True)

        sns.barplot(x='START TIME', y='CAPACITY REMAINING (%)', hue='SOURCE',
                    data=df_resampled.iloc[-24:, :], ax=self.ax)
        self.ax.set_title('Recent Battery Levels')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Capacity Remaining (%)')

        tick_labels = self.ax.get_xticklabels()

        # Extract the text from tick labels
        tick_texts = [label.get_text() for label in tick_labels]

        # Convert to datetime format and then format to hours and minutes
        formatted_tick_labels = [pd.to_datetime(text).strftime('%H:%M') for text in tick_texts]

        # Update the x-axis with the formatted tick labels and rotate for better readability
        self.ax.set_xticklabels(formatted_tick_labels, rotation=45, ha='right')

        # Adjust layout
        self.canvas.figure.tight_layout()

    def plot_battery_usage(self):
        sns.barplot(data=self.battery_usage_df, x='START TIME', y='ENERGY DRAINED (mWh)', hue='STATE',
                    ax=self.ax)
        self.ax.set_ylabel('Energy Drained (mWh)')
        self.ax.set_xlabel('Start Time')
        self.ax.set_title('Battery Drains')

        tick_labels = self.ax.get_xticklabels()

        # Extract the text from tick labels
        tick_texts = [label.get_text() for label in tick_labels]

        # Convert to datetime format and then format to hours and minutes
        formatted_tick_labels = [pd.to_datetime(text).strftime('%H:%M') for text in tick_texts]

        # Update the x-axis with the formatted tick labels and rotate for better readability
        self.ax.set_xticklabels(formatted_tick_labels, rotation=45, ha='right')

        self.canvas.figure.tight_layout()


def apply_stylesheet(app, STYLESHEET_PATH):
    if STYLESHEET_PATH.exists():
        app.setStyleSheet(STYLESHEET_PATH.read_text())
    else:
        print(f"Stylesheet not found: {STYLESHEET_PATH}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('app_icon.ico'))
    # app.setStyle("fusion")
    # STYLESHEET_PATH = Path(__file__).parent / "custom_stylesheet.qss"
    # apply_stylesheet(app, STYLESHEET_PATH)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
