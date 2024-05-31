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
    QGraphicsTextItem, QScrollArea, QGraphicsRectItem
from PyQt6.QtGui import QFont, QPixmap, QIcon, QAction, QDesktopServices, QPalette, QColor, QPainter, QMovie
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QBarSet, QBarSeries, QValueAxis, QDateTimeAxis, \
    QBarCategoryAxis
from PyQt6.QtCore import Qt, QTimer, QUrl, QCoreApplication, QDateTime, QRectF, QPropertyAnimation, QSize

import numpy as np
import pandas as pd
import seaborn as sns

from load_json import load_capacity_history_from_json, load_life_estimates_from_json, load_recent_usage_from_json, \
    load_battery_usage_from_json, load_current_battery_life_estimate_from_json, read_json_file
from generate import generate_battery_report
from clean import clean_html
from extract import extract_data

# TODO: Replace with the current version
CURRENT_VERSION = "2.0.0"


class CustomChartView(QChartView):
    def __init__(self, chart, get_current_graph, parent=None):
        super().__init__(chart, parent)
        self.get_current_graph = get_current_graph
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Coordinate display item
        self.coord_item = QGraphicsTextItem(chart)
        self.coord_item.setZValue(5)
        self.coord_item.setDefaultTextColor(QColor("black"))
        font = QFont("Arial", 10)
        self.coord_item.setFont(font)

        # Background rectangle for the text
        self.bg_rect = QGraphicsRectItem(chart)
        self.bg_rect.setZValue(4)
        self.bg_rect.setBrush(QColor(255, 255, 255, 200))  # White with transparency
        self.bg_rect.setPen(QColor(0, 0, 0, 0))  # No border

        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        chart_item = self.chart().mapToValue(pos)

        x_val = QDateTime.fromMSecsSinceEpoch(int(chart_item.x())).toString("dd-MM-yyyy")
        y_val = int(chart_item.y())
        current_graph = self.get_current_graph()

        if current_graph == "Battery Capacity History":
            y_val = y_val / 1000
            text = f"{x_val}\n{y_val:.2f} Wh"
        elif current_graph == "Battery Life Estimates (Active)":
            text = f"{x_val}\n"
            if y_val >= 60:
                hr = int(y_val / 60)
                text += f"{hr} hr "
                min = int(y_val % 60)
            else:
                min = y_val
            text += f"{min} min (Active)"
        elif current_graph == "Battery Life Estimates (Standby)":
            text = f"{x_val}\n"
            if y_val >= 60:
                hr = int(y_val / 60)
                text += f"{hr} hr "
                min = int(y_val % 60)
            else:
                min = y_val
            text += f"{min} min (Standby)"
        else:
            text = ""

        self.coord_item.setPlainText(text)

        # Set the position of the text item
        self.coord_item.setPos(pos.x() + 15, pos.y() - 30)

        # Update the background rectangle
        text_rect = self.coord_item.boundingRect()
        self.bg_rect.setRect(text_rect.adjusted(-5, -5, 5, 5))  # Add padding
        self.bg_rect.setPos(pos.x() + 15, pos.y() - 30)

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.coord_item.setPlainText("")
        self.bg_rect.setRect(QRectF())
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Battery Health Report Generator')

        # Set the size of the window on initialization
        self.setGeometry(500, 100, 1024, 832)

        # Set the default theme on initialization
        self.theme = 'accent'
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

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Update the maximum width of suggestion_label based on the window width
        if self.centralWidget() is not None:
            widget_width = self.centralWidget().width()
            widget_heigth = self.centralWidget().height()

            # Set maximum width of suggestion label to 75% of the window width
            suggestion_label = self.centralWidget().findChild(QLabel, "SuggestionLabel")
            max_label_width = int(widget_width * 0.75)
            if suggestion_label is not None:
                suggestion_label.setMaximumWidth(max_label_width)

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
        about_text = (
            f"<h2 style='color: #6957db;'>Battery Health Report Generator v{CURRENT_VERSION}</h2>"
            "<p>Created by <b>Lala Arnav Vatsal</b></p>"
            "<p>Email: <a href='mailto:arnav.vatsal2213@gmail.com'>arnav.vatsal2213@gmail.com</a></p>"
            "<p>LinkedIn: <a href='https://www.linkedin.com/in/lala-arnav-vatsal/'>Lala Arnav Vatsal</a></p>"
            "<p>This application provides detailed battery health reports and analysis.</p>"
            "<p>Visit our <a href='https://arnav003.github.io/battery-health'>product website</a> for more information.</p>"
        )
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
        self.table_widget1.setMinimumHeight(300)

        # Create the second table widget
        self.table_widget2 = QTableWidget()
        self.table_widget2.setColumnCount(2)
        self.setup_table_style(self.table_widget2)
        self.load_data_into_table(self.table_widget2, 'data/installed-batteries.json')
        self.table_widget2.setMinimumHeight(300)

        # Load data
        self.capacity_df = load_capacity_history_from_json('data/battery-capacity-history.json')
        self.life_estimates_df = load_life_estimates_from_json('data/battery-life-estimates.json')
        self.recent_usage_df = load_recent_usage_from_json('data/recent-usage.json')
        self.battery_usage_df = load_battery_usage_from_json('data/battery-usage.json')

        # Create scroll area
        self.main_window_scroll = QScrollArea()
        self.main_window_scroll.setWidgetResizable(True)
        self.main_window_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.main_window_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCentralWidget(self.main_window_scroll)

        # Create central widget
        self.central_widget = QWidget()
        self.main_window_scroll.setWidget(self.central_widget)

        # Create layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Add battery health icon and percentage
        self.battery_health_layout = self.update_battery_health_label()
        self.layout.addWidget(self.battery_health_layout, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add suggestion
        self.suggestion_label = self.get_suggestion_label()
        self.layout.addWidget(self.suggestion_label, alignment=Qt.AlignmentFlag.AlignCenter)

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

        self.combo_box_label = QLabel("Choose the graph to display: ")

        # Create a horizontal layout to center the combo box
        self.combo_box_layout = QHBoxLayout()
        self.combo_box_layout.addStretch(1)  # Add stretchable space before the combo box
        self.combo_box_layout.addWidget(self.combo_box_label)
        self.combo_box_layout.addWidget(self.combo_box)
        self.combo_box_layout.addStretch(1)  # Add stretchable space after the combo box

        self.layout.addLayout(self.combo_box_layout)
        self.layout.addStretch(1)  # Add stretchable space after the combo box to push it up

        # Create the chart and add it to the layout
        self.chart = QChart()
        self.chart_view = CustomChartView(self.chart, self.get_current_graph)
        self.chart_view.setMinimumHeight(500)
        self.layout.addWidget(self.chart_view)

        # List to keep track of axes
        self.current_axes = []

        # Initial plot
        self.update_plot()

        # Create the chart and add it to the layout
        self.recent_usage_chart = QChart()
        self.recent_usage_chart_view = QChartView(self.recent_usage_chart)
        self.recent_usage_chart_view.setMinimumHeight(500)
        self.recent_usage_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.layout.addWidget(self.recent_usage_chart_view)

        # List to keep track of axes
        self.recent_usage_current_axes = []

        # Slider for scrolling
        self.sl = QSlider(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.sl)

        self.plot_recent_usage()

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

        self.progress_dialog.close()

    def calculate_battery_health(self):
        # Load installed batteries data
        battery_data = read_json_file('data/installed-batteries.json')
        design_capacity = int(battery_data["DESIGN CAPACITY"].replace(',', '').split(' ')[0])
        full_charge_capacity = int(battery_data["FULL CHARGE CAPACITY"].replace(',', '').split(' ')[0])
        battery_health_percentage = (full_charge_capacity / design_capacity) * 100
        return battery_health_percentage

    def update_battery_health_label(self):
        battery_health_icon = 'icons/battery-animation-transparent-cropped.gif'

        icon_label = QLabel()
        icon_movie = QMovie(battery_health_icon)
        icon_movie.setScaledSize(QSize(48, 48))
        icon_label.setMovie(icon_movie)
        icon_movie.start()

        # battery_health_icon = QPixmap('icons/battery_icon.png')
        #
        # icon_label = QLabel()
        # icon_label.setPixmap(battery_health_icon.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio,
        #                                                 Qt.TransformationMode.SmoothTransformation))

        percentage_label = QLabel(f'Battery Health: {self.battery_health_percentage:.2f}%')
        percentage_label.setFont(QFont('Arial', 16))

        layout = QHBoxLayout()
        layout.addWidget(icon_label)
        layout.addWidget(percentage_label)

        container = QWidget()

        container.setStyleSheet(f"""
            color: #fff;
            background: #6957db;
            border-radius: 30px;
            font-weight: bold;
        """)

        container.setLayout(layout)

        return container

    def get_suggestion_label(self):
        suggestion_icon = QPixmap('icons/i_icon.png')
        suggestion_label_icon = QLabel()
        suggestion_label_icon.setPixmap(suggestion_icon.scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio,
                                                               Qt.TransformationMode.SmoothTransformation))

        if self.battery_health_percentage > 75:
            suggestion_text = "Battery Health: Excellent - Your battery is in great condition."
        elif 50 < self.battery_health_percentage <= 75:
            suggestion_text = "Battery Health: Good - Your battery is still healthy, but consider optimizing usage to maintain its condition."
        elif 25 < self.battery_health_percentage <= 50:
            suggestion_text = "Battery Health: Fair - Your battery health is moderate. Try reducing usage or adjusting settings to prolong battery life."
        else:
            suggestion_text = "Battery Health: Poor - Your battery health is low. Consider replacing your battery or seeking professional assistance."

        suggestion_label = QLabel()
        suggestion_label.setTextFormat(Qt.TextFormat.RichText)
        suggestion_label.setText(suggestion_text)
        suggestion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # suggestion_label.setWordWrap(True)
        suggestion_label.setMinimumWidth(512)
        suggestion_label.setObjectName("SuggestionLabel")

        suggestion_label.setStyleSheet('''
        color: #ffeb3b;
        font-weight: bold;    
        ''')

        layout = QHBoxLayout()
        layout.addWidget(suggestion_label_icon)
        layout.addWidget(suggestion_label)

        container = QWidget()

        container.setStyleSheet(f"""
                    background: #6957db;
                    border-radius: 15px;
                    font-weight: bold;
                """)

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

        current_percentage_label = QLabel(f'Battery Percent: {self.current_battery_info["Percent"]}%')

        charging_state_label = QLabel(f'Plugged in: {self.current_battery_info["Plugged in"]}')

        estimated_remaining_time_label = QLabel(
            f'Estimated remaining time: {self.current_battery_info["Seconds left"]}')

        # Apply styles
        self.apply_label_style(current_percentage_label, self.current_battery_info["Percent"])
        self.apply_label_style(charging_state_label)
        self.apply_label_style(estimated_remaining_time_label)

        layout = QHBoxLayout()
        layout.addWidget(current_percentage_label)
        layout.addWidget(charging_state_label)
        layout.addWidget(estimated_remaining_time_label)

        container = QWidget()
        container.setLayout(layout)

        return container

    def apply_label_style(self, label, value=None):
        # Apply common style
        label.setFont(QFont('Arial', 16))
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Apply specific style based on value (e.g., battery percentage)
        if value is not None:
            if value > 75:
                label.setStyleSheet("color: #27ae60;")  # Green
            elif value > 25:
                label.setStyleSheet("color: #f39c12;")  # Orange
            else:
                label.setStyleSheet("color: #e74c3c;")  # Red

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

    def recent_usage_clear_axes(self):
        for axis in self.recent_usage_current_axes:
            self.recent_usage_chart.removeAxis(axis)
        self.recent_usage_current_axes = []

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

        self.hours_to_show = 12

        # Adding scroll functionality
        self.sl.setMinimum(0)
        self.sl.setMaximum(len(df_resampled) - self.hours_to_show)
        self.sl.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sl.setTickInterval(6)

        self.sl.valueChanged.connect(self.update_recent_usage)
        self.sl.setValue(len(df_resampled) - self.hours_to_show)

    def update_recent_usage(self):
        self.recent_usage_clear_axes()
        self.recent_usage_chart.removeAllSeries()

        pos = int(self.sl.value())

        # Create bar series and add bar sets
        bar_series = QBarSeries()

        bar_set = QBarSet("")
        x_labels = []

        # Populate bar sets
        for i in range(pos, pos + self.hours_to_show):
            time = self.recent_usage_df['START TIME'].iloc[i]

            current_date = datetime.datetime.now().date()

            if time.date() == current_date:
                time = time.strftime("%H:%M")
            else:
                time = time.strftime("%d-%m %H:%M")

            capacity = self.recent_usage_df['CAPACITY REMAINING (%)'].iloc[i]

            bar_set.append(capacity)

            x_labels.append(time)

        bar_set.setLabel(self.recent_usage_df['START TIME'].iloc[pos + self.hours_to_show - 1].strftime("%m/%d"))

        # for i, bar in enumerate(bar_set):
        #     source = self.recent_usage_df['SOURCE'].astype(str).iloc[i]
        #
        #     if source == 'AC':
        #         bar_set.setColor(Qt.GlobalColor.green)
        #     elif source == 'Battery':
        #         bar_set.setColor(Qt.GlobalColor.blue)
        #     else:
        #         bar_set.setColor(Qt.GlobalColor.yellow)

        bar_series.append(bar_set)

        self.recent_usage_chart.addSeries(bar_series)
        # self.recent_usage_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Create and customize x-axis as QDateTimeAxis
        axis_x = QBarCategoryAxis()
        axis_x.setTitleText("Time")
        axis_x.setLabelsAngle(-45)
        axis_x.append(x_labels)

        # Create and customize y-axis as QValueAxis
        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setTitleText("Capacity Remaining (%)")

        self.recent_usage_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.recent_usage_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        # Customize chart
        self.recent_usage_chart.setTitle('Recent Battery Levels')
        self.recent_usage_chart.setBackgroundBrush(QColor("#f0f0f0"))
        self.recent_usage_chart.setTitleFont(QFont("Arial", 14, QFont.Weight.Bold))

        # Add axes to current_axes list
        self.recent_usage_current_axes.extend([axis_x, axis_y])

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

    apply_stylesheet(app, "stylesheets/light_stylesheet.css")


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

    apply_stylesheet(app, "stylesheets/accent_stylesheet.css")


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

    apply_stylesheet(app, "stylesheets/dark_stylesheet.css")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icons/app_icon.ico'))
    app.setStyle(QStyleFactory.create("windows11"))  # ['windows11', 'windowsvista', 'Windows', 'Fusion']
    # apply_stylesheet(app, "stylesheets/custom_stylesheet.css")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
