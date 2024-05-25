import sys
import json
import os
import datetime
import mplcursors
import numpy as np
import pandas as pd
import seaborn as sns
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QTableWidget, QTableWidgetItem, \
    QHBoxLayout, QLabel
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qdarkstyle import _load_stylesheet
from qdarkstyle.palette import Palette

from load_json import load_capacity_history_from_json, load_life_estimates_from_json, load_battery_usage_from_json, \
    read_json_file
from generate import generate_battery_report
from clean import clean_html
from extract import extract_data


class BatteryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # TODO: remove comment
        # self.get_data()
        self.setWindowTitle('Battery Data Dashboard')
        self.setGeometry(100, 100, 800, 600)
        palette = Palette()
        palette.ID = 'light'
        self.setStyleSheet(_load_stylesheet(palette=palette))

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
        self.combo_box.addItem("Battery Usage")
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.combo_box)

        # Create canvas for plotting
        self.canvas = FigureCanvas(Figure())
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()

        # Initial plot
        self.update_plot()

    def get_data(self):
        generate_battery_report()
        clean_html()
        self.create_directory("data")
        extract_data()

    def create_directory(self, directory_path):
        try:
            os.makedirs(directory_path)
            print(f"Directory '{directory_path}' created successfully.")
        except FileExistsError:
            print(f"Directory '{directory_path}' already exists.")

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

    # def load_json(self, file_name):
    #     with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
    #         return json.load(f)

    def update_plot(self):
        self.ax.clear()
        selected_data = self.combo_box.currentText()

        if selected_data == "Battery Capacity History":
            self.plot_capacity_history()
        elif selected_data == "Battery Life Estimates (Active)":
            self.plot_life_estimates('active')
        elif selected_data == "Battery Life Estimates (Standby)":
            self.plot_life_estimates('standby')
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
        self.ax.set_ylim(0, self.capacity_df['DESIGN CAPACITY'][0])

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
        if state == 'active':
            columns_to_plot = ['ACTIVE (FULL CHARGE)', 'ACTIVE (DESIGN CAPACITY)']
        elif state == 'standby':
            columns_to_plot = ['CONNECTED STANDBY (FULL CHARGE) (time)', 'CONNECTED STANDBY (DESIGN CAPACITY) (time)']

        y_values = self.life_estimates_df[columns_to_plot]

        # Plot each column
        for i, column in enumerate(columns_to_plot):
            self.ax.plot(x_values, y_values[column], label=column)

        self.ax.legend(loc="upper right")
        self.ax.set_ylabel('Drain Time (in seconds)')

        # Set common xlabel
        self.ax.set_xlabel('Period')

        # Rotate x-axis labels for better readability
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=45, ha='right')

        # Adjust layout
        self.canvas.figure.tight_layout()

    def plot_battery_usage(self):
        print(self.battery_usage_df['START TIME'])
        print(self.battery_usage_df['ENERGY DRAINED (%)'])
        sns.lineplot(data=self.battery_usage_df, x='START TIME', y='ENERGY DRAINED (mWh)', hue='STATE', marker='o', ax=self.ax)
        self.ax.set_ylabel('Energy Drained (%)')
        self.ax.set_xlabel('Start Time')
        self.ax.tick_params(axis='y')
        self.canvas.figure.tight_layout()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('app_icon.ico'))
    window = BatteryApp()
    window.show()
    sys.exit(app.exec())
