import datetime
import sys
import json
import os
import requests
import psutil
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QTableWidget, QTableWidgetItem, \
    QHBoxLayout, QLabel, QProgressDialog, QMenuBar, QMessageBox, QSlider, QHeaderView, QStyleFactory, QMenu, \
    QGraphicsTextItem
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction, QDesktopServices, QPalette, QColor, QPainter, QBrush
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from PyQt6.QtCore import Qt, QTimer, QUrl, QCoreApplication, QDateTime

import numpy as np
import pandas as pd
import seaborn as sns

from load_json import load_capacity_history_from_json, load_life_estimates_from_json, load_recent_usage_from_json, \
    load_battery_usage_from_json, load_current_battery_life_estimate_from_json, read_json_file
from generate import generate_battery_report
from clean import clean_html
from extract import extract_data

# TODO: Replace with the current version
CURRENT_VERSION = "1.7.0"


class CustomChartView(QChartView):
    def __init__(self, chart, get_current_graph, parent=None):
        super().__init__(chart, parent)
        self.get_current_graph = get_current_graph
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.coord_item = QGraphicsTextItem(chart)
        self.coord_item.setZValue(5)
        self.coord_item.setDefaultTextColor(QColor("black"))
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        chart_item = self.chart().mapToValue(pos)
        self.coord_item.setPos(pos)
        x_val = QDateTime.fromMSecsSinceEpoch(int(chart_item.x())).toString("dd-MM-yyyy")
        y_val = chart_item.y()
        current_graph = self.get_current_graph()
        if current_graph == "Battery Capacity History":
            self.coord_item.setPlainText(f"{x_val}\n{y_val:.2f} mWh")
        elif current_graph == "Battery Life Estimates (Active)":
            self.coord_item.setPlainText(f"{x_val}\n{y_val:.2f} min (Active)")
        elif current_graph == "Battery Life Estimates (Standby)":
            self.coord_item.setPlainText(f"{x_val}\n{y_val:.2f} min (Standby)")
        super().mouseMoveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Battery Health Report Generator')
        # self.setGeometry(50, 50, 768, 960) # Limit the size of window
        self.resize(768, 960)
        self.theme = 'light'
        set_accent_palette(app)

        # palette = Palette()
        # palette.ID = self.theme
        # self.setStyleSheet(_load_stylesheet(palette=palette))
        # self.setStyleSheet(create_custom_qss_from_palette("light", "", set_light_palette()))

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

        # Change theme submenu
        theme_menu = QMenu("Change Theme", self)
        self.light_theme_action = QAction("Light Theme", self)
        self.light_theme_action.triggered.connect(lambda: self.set_theme('light'))
        theme_menu.addAction(self.light_theme_action)

        self.dark_theme_action = QAction("Dark Theme", self)
        self.dark_theme_action.triggered.connect(lambda: self.set_theme('dark'))
        theme_menu.addAction(self.dark_theme_action)

        self.accent_theme_action = QAction("Accent Theme", self)
        self.accent_theme_action.triggered.connect(lambda: self.set_theme('accent'))
        theme_menu.addAction(self.accent_theme_action)

        file_menu.addMenu(theme_menu)

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

    def set_theme(self, theme_name):
        # if self.theme == 'light':
        #     self.theme = 'dark'
        # elif self.theme == 'dark':
        #     self.theme = 'light'
        # palette = Palette()
        # palette.ID = self.theme
        # self.setStyleSheet(_load_stylesheet(palette=palette))

        self.theme = theme_name
        if theme_name == 'light':
            set_light_palette(app)
        elif theme_name == 'dark':
            set_dark_palette(app)
        elif theme_name == 'accent':
            set_accent_palette(app)

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

        # Calculate current battery info
        self.current_battery_info = self.get_current_battery_info()

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
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Add battery health icon and percentage
        self.battery_health_layout = self.update_battery_health_label()
        self.layout.addWidget(self.battery_health_layout, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add current battery percentage and charging state
        self.current_battery_info_layout = None

        def func():
            self.current_battery_info_layout = self.update_current_battery_info_label()
            self.layout.addWidget(self.current_battery_info_layout, alignment=Qt.AlignmentFlag.AlignCenter)

        func()

        # Add a QTimer instance as a class variable
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(func)
        self.update_timer.start(10000)  # Update every 10000 milliseconds (1 second)

        # Create horizontal layout for tables
        self.table_layout = QHBoxLayout()

        # Add table widgets to layout
        self.table_layout.addWidget(self.table_widget1)
        self.table_layout.addWidget(self.table_widget2)

        self.layout.addLayout(self.table_layout)

        # Create combo box for selecting data
        self.combo_box = QComboBox()
        self.combo_box.addItem("Battery Capacity History")
        self.combo_box.addItem("Battery Life Estimates (Active)")
        self.combo_box.addItem("Battery Life Estimates (Standby)")
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        self.layout.addWidget(self.combo_box)

        # Create the chart and add it to the layout
        self.chart = QChart()
        self.chart_view = CustomChartView(self.chart, self.get_current_graph)
        self.layout.addWidget(self.chart_view)

        # List to keep track of axes
        self.current_axes = []

        # Initial plot
        self.update_plot()

        # Create canvas for plotting
        # self.canvas_recent_usage = MplCanvas(self, width=5, height=4, dpi=100)
        # self.ax_recent_usage = self.canvas_recent_usage.ax
        # self.layout.addWidget(self.canvas_recent_usage)

        # self.sl = QSlider(Qt.Orientation.Horizontal)

        # self.plot_recent_usage()

        # self.layout.addWidget(self.sl)

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

    def get_current_battery_info(self):
        battery = psutil.sensors_battery()

        if battery.secsleft < 0:
            time_remaining = '- -'
        else:
            time_remaining = datetime.timedelta(seconds=battery.secsleft)
        if battery.power_plugged:
            is_plugged = 'Yes'
        else:
            is_plugged = 'No'
        if battery:
            battery_info = {
                'Percent': battery.percent,
                'Seconds left': time_remaining,
                'Plugged in': is_plugged
            }
            return battery_info
        else:
            return "No battery information available"

    def update_current_battery_info_label(self):
        print("running...")
        if self.current_battery_info_layout is not None:
            self.current_battery_info_layout.deleteLater()

        # Calculate current battery info
        self.current_battery_info = self.get_current_battery_info()

        current_percentage_label = QLabel(f'Battery Percent: {self.current_battery_info["Percent"]:.2f}%')
        current_percentage_label.setFont(QFont('Arial', 16))
        current_percentage_label.setStyleSheet("color: green;")

        charging_state_label = QLabel(f'Plugged in: {self.current_battery_info["Plugged in"]}')
        charging_state_label.setFont(QFont('Arial', 16))
        charging_state_label.setStyleSheet("color: green;")

        estimated_remaining_time_label = QLabel(
            f'Estimated remaining time: {self.current_battery_info["Seconds left"]}')
        estimated_remaining_time_label.setFont(QFont('Arial', 16))
        estimated_remaining_time_label.setStyleSheet("color: green;")

        layout = QHBoxLayout()
        layout.addWidget(current_percentage_label)
        layout.addWidget(charging_state_label)
        layout.addWidget(estimated_remaining_time_label)

        container = QWidget()
        container.setLayout(layout)

        # Update the current_battery_info_layout attribute
        # self.current_battery_info_layout = container
        return container

    def setup_table_style(self, table_widget):
        pass
        # Set table properties
        table_widget.verticalHeader().setVisible(False)
        table_widget.horizontalHeader().setVisible(False)
        table_widget.resizeColumnsToContents()

        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Set font
        font = QFont()
        font.setPointSize(10)
        table_widget.setFont(font)

        # Set cell padding
        table_widget.setStyleSheet("""
                QTableWidget::item { 
                    padding: 10px; 
                }
                QTableWidget::item:hover {
                    background-color: none;
                    border: none;
                }
            """)

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

    def get_current_graph(self):
        return self.combo_box.currentText()

    def clear_axes(self):
        for axis in self.current_axes:
            self.chart.removeAxis(axis)
        self.current_axes = []

    def update_plot(self):
        # Clear previous chart data
        self.chart.removeAllSeries()
        self.clear_axes()

        selected_data = self.get_current_graph()

        if selected_data == "Battery Capacity History":
            self.plot_capacity_history()
        elif selected_data == "Battery Life Estimates (Active)":
            self.plot_life_estimates('active')
        elif selected_data == "Battery Life Estimates (Standby)":
            self.plot_life_estimates('standby')

    def plot_capacity_history(self):
        x_values = np.asarray(self.capacity_df['START DATE'])
        y_values = self.capacity_df['FULL CHARGE CAPACITY']

        series = QLineSeries()
        for date, value in zip(x_values, y_values):
            datetime_obj = pd.to_datetime(date).to_pydatetime()
            series.append(QDateTime(datetime_obj).toMSecsSinceEpoch(), value)

        # Customize series
        series.setColor(QColor("#0078d7"))
        series.setPointsVisible(True)

        self.chart.addSeries(series)
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Create and customize x-axis as QDateTimeAxis
        axis_x = QDateTimeAxis()
        axis_x.setTitleText("Date")
        axis_x.setFormat("dd-MM-yyyy")
        axis_x.setLabelsAngle(-45)
        axis_x.setTickCount(10)  # Adjust number of ticks as needed

        # Create and customize y-axis as QValueAxis
        axis_y = QValueAxis()
        axis_y.setTitleText("Full Charge Capacity (mWh)")

        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        # Add axes to current_axes list
        self.current_axes.extend([axis_x, axis_y])

        # Customize chart
        self.chart.setTitle('Battery Capacity History')
        self.chart.setBackgroundBrush(QColor("#f0f0f0"))
        self.chart.setTitleFont(QFont("Arial", 14, QFont.Weight.Bold))

    def plot_life_estimates(self, state):
        x_values = np.asarray(self.capacity_df['START DATE'])

        data = load_current_battery_life_estimate_from_json('data/current-battery-life-estimate.json')

        design_capacity_estimate = None
        if state == 'active':
            columns_to_plot = ['ACTIVE (FULL CHARGE)', 'ACTIVE (DESIGN CAPACITY)']
            design_capacity_estimate = data["ACTIVE (DESIGN CAPACITY)"][0]
            self.chart.setTitle('Battery Life Estimates (Active)')
        elif state == 'standby':
            columns_to_plot = ['CONNECTED STANDBY (FULL CHARGE) (time)', 'CONNECTED STANDBY (DESIGN CAPACITY) (time)']
            design_capacity_estimate = data["CONNECTED STANDBY (DESIGN CAPACITY)"][0]
            self.chart.setTitle('Battery Life Estimates (Standby)')

        y_values_in_sec = (self.life_estimates_df[columns_to_plot[0]] / self.life_estimates_df[
            columns_to_plot[1]]) * design_capacity_estimate
        y_values = y_values_in_sec / 60

        series = QLineSeries()
        for date, value in zip(x_values, y_values):
            datetime_obj = pd.to_datetime(date).to_pydatetime()
            series.append(QDateTime(datetime_obj).toMSecsSinceEpoch(), value)

        # Customize series
        series.setColor(QColor("#0078d7"))
        series.setPointsVisible(True)

        self.chart.addSeries(series)
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Create and customize x-axis as QDateTimeAxis
        axis_x = QDateTimeAxis()
        axis_x.setTitleText("Date")
        axis_x.setFormat("dd-MM-yyyy")
        axis_x.setLabelsAngle(-45)
        axis_x.setTickCount(10)  # Adjust number of ticks as needed

        # Create and customize y-axis as QValueAxis
        axis_y = QValueAxis()
        axis_y.setTitleText("Drain Time (in minutes)")

        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        # Add axes to current_axes list
        self.current_axes.extend([axis_x, axis_y])

        # Customize chart
        self.chart.setBackgroundBrush(QColor("#f0f0f0"))
        self.chart.setTitleFont(QFont("Arial", 14, QFont.Weight.Bold))

    def plot_recent_usage(self):
        df = self.recent_usage_df

        # Drop duplicate START TIME values
        df = df.drop_duplicates(subset=['START TIME'])

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

        self.recent_usage_df = df_resampled

        # Adding scroll functionality
        self.sl.setMinimum(0)
        self.sl.setMaximum(len(df_resampled) - 24)
        self.sl.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sl.setTickInterval(24)

        self.sl.valueChanged.connect(self.update_recent_usage)
        self.sl.setValue(len(df_resampled) - 24)

    def update_recent_usage(self):
        pos = int(self.sl.value())
        self.ax_recent_usage.clear()

        # Plotting the data
        sns.barplot(x='START TIME', y='CAPACITY REMAINING (%)', hue='SOURCE',
                    data=self.recent_usage_df.iloc[pos:pos + 24, :], ax=self.ax_recent_usage)
        self.ax_recent_usage.set_title('Recent Battery Levels')
        self.ax_recent_usage.set_xlabel('Time')
        self.ax_recent_usage.set_ylabel('Capacity Remaining (%)')

        # Change background color
        self.ax_recent_usage.set_facecolor('#f0f0f0')  # Light grey background inside graph area
        # self.canvas_recent_usage.figure.set_facecolor('#f0f0f0')  # Light grey background around graph area

        tick_labels = self.ax_recent_usage.get_xticks()
        tick_texts = pd.to_datetime(self.recent_usage_df['START TIME'].iloc[pos:pos + 24].values).strftime(
            '%d/%m %H:%M')
        self.ax_recent_usage.set_xticklabels(tick_texts, rotation=45, ha='right')

        # Adjust layout
        self.canvas_recent_usage.figure.tight_layout()

        self.canvas_recent_usage.draw_idle()
        self.canvas_recent_usage.flush_events()

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


def apply_stylesheet(app, file_name):
    STYLESHEET_PATH = Path(__file__).parent / file_name
    if STYLESHEET_PATH.exists():
        app.setStyleSheet(STYLESHEET_PATH.read_text())
    else:
        print(f"Stylesheet not found: {STYLESHEET_PATH}")


def set_light_palette(app):
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

    # Highlight colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.Accent, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Menubar colors
    palette.setColor(QPalette.ColorRole.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Dark, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.Mid, QColor(180, 180, 180))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(160, 160, 160))

    app.setPalette(palette)

    apply_stylesheet(app, "light_stylesheet.css")


def set_accent_palette(app):
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))  # Light gray background
    palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))  # Dark text
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))  # White for input fields
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))  # Slightly darker for alternate rows
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))  # Red for bright text

    # Highlight colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 204))  # Accent color for highlights
    palette.setColor(QPalette.ColorRole.Accent, QColor(0, 122, 204))  # Accent color for focus
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))  # White text on highlight

    # Menubar colors
    palette.setColor(QPalette.ColorRole.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Dark, QColor(200, 200, 200))
    palette.setColor(QPalette.ColorRole.Mid, QColor(180, 180, 180))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(160, 160, 160))

    app.setPalette(palette)

    apply_stylesheet(app, "accent_stylesheet.css")


def set_dark_palette(app):
    palette = QPalette()

    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

    # Additional colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

    app.setPalette(palette)

    apply_stylesheet(app, "dark_stylesheet.css")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('app_icon.ico'))
    app.setStyle(QStyleFactory.create("windows11"))  # ['windows11', 'windowsvista', 'Windows', 'Fusion']
    # apply_stylesheet(app, "custom_stylesheet.css")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
