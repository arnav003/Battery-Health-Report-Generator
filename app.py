import sys
import json
import os
import pandas as pd
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from load_json import load_capacity_history_from_json

class BatteryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Battery Data Dashboard')
        self.setGeometry(100, 100, 800, 600)

        # Load data
        self.capacity_df = load_capacity_history_from_json('data/battery-capacity-history.json')
        # self.life_estimates_df = load_life_estimates_from_json('data/battery-life-estimates.json')

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create combo box for selecting data
        self.combo_box = QComboBox()
        self.combo_box.addItem("Battery Capacity History")
        self.combo_box.addItem("Battery Life Estimates")
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.combo_box)

        # Create canvas for plotting
        self.canvas = FigureCanvas(Figure())
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()

        # Initial plot
        self.update_plot()

    def load_json(self, file_name):
        with open(os.path.join(os.path.dirname(__file__), file_name), 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_plot(self):
        self.ax.clear()
        selected_data = self.combo_box.currentText()

        if selected_data == "Battery Capacity History":
            self.plot_capacity_history()
        elif selected_data == "Battery Life Estimates":
            # self.plot_life_estimates()
            pass

        self.canvas.draw()

    def plot_capacity_history(self):
        # self.capacity_df['START DATE'] = pd.to_datetime(self.capacity_df['START DATE'])
        self.capacity_df.set_index('START DATE', inplace=True)
        self.capacity_df.plot(ax=self.ax, title='Battery Capacity History')

    # def plot_life_estimates(self):
    #     self.life_estimates_df['PERIOD'] = pd.to_datetime(self.life_estimates_df['PERIOD'])
    #     self.life_estimates_df.set_index('PERIOD', inplace=True)
    #     self.life_estimates_df.plot(ax=self.ax, title='Battery Life Estimates')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BatteryApp()
    window.show()
    sys.exit(app.exec())
