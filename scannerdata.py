# -*- coding: utf-8 -*-

import datetime
import epics
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
import time

from epics.pv import PV

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

version = 1.12
scanner_list = ['melba_020:scan:', 'melba_050:scan:']


#############################
# PandasTable
#############################
class PandasTable(QAbstractTableModel):
    # https://stackoverflow.com/questions/44603119/how-to-display-a-pandas-data-frame-with-pyqt5
    def __init__(self, df=pd.DataFrame(), parent=None):
        QAbstractTableModel.__init__(self, parent=parent)
        self.df = df

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()

        if orientation == Qt.Horizontal:
            try:
                return self.df.columns.tolist()[section]
            except (IndexError,):
                return QVariant()
        elif orientation == Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self.df.index.tolist()[section]
            except (IndexError,):
                return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()

        if not index.isValid():
            return QVariant()

        return QVariant(str(self.df.ix[index.row(), index.column()]))

    def setData(self, index, value, role):
        row = self.df.index[index.row()]
        col = self.df.columns[index.column()]
        if hasattr(value, 'toPyObject'):
            # PyQt4 gets a QVariant
            value = value.toPyObject()
        else:
            # PySide gets an unicode
            dtype = self.df[col].dtype
            if dtype != object:
                value = None if value == '' else dtype.type(value)
        self.df.set_value(row, col, value)
        return True

    def rowCount(self, parent=QModelIndex()):
        return len(self.df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self.df.columns)

    def sort(self, column, order):
        col_name = self.df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self.df.sort_values(col_name, ascending=order == Qt.AscendingOrder, inplace=True)
        self.df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()


#############################
# Custom Dialog: Select Channel
#############################
class MyInputDialog(QDialog):

    def __init__(self, ch_list=[0, 1, 2], scan="melba_020:scan"):
        super().__init__()

        # Channels
        self._cb = {}
        self.ch_list = ch_list

        # Scanner
        self._scanner = scan
        self._cb_scanner = QComboBox()
        self.ui_init()

    def ui_init(self):

        # Channel selection
        lyt_cb = QGridLayout()
        grid = [(i, j) for i in range(2) for j in range(4)]

        for i in range(8):
            self._cb[i] = QCheckBox('{}'.format(i), self)
            if i in self.ch_list:
                self._cb[i].setChecked(True)
            lyt_cb.addWidget(self._cb[i], grid[i][0], grid[i][1])

        for i in enumerate(self._cb):
            self._cb[i[0]].stateChanged.connect(self.change_list)

        btn_all = QPushButton("All")
        btn_all.clicked.connect(self.select_all)
        btn_none = QPushButton("None")
        btn_none.clicked.connect(self.select_none)

        # Scanner selection
        global scanner_list
        self._cb_scanner.addItems(scanner_list)
        self._cb_scanner.currentIndexChanged.connect(self.change_scanner)
        # Set scanner selection to last selected scanner
        idx = self._cb_scanner.findText(self._scanner)
        self._cb_scanner.setCurrentIndex(idx)

        # Layout
        lyt_btn = QHBoxLayout()
        lyt_btn.addWidget(btn_all)
        lyt_btn.addWidget(btn_none)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        lyt_global = QVBoxLayout()
        lyt_global.addLayout(lyt_cb)
        lyt_global.addLayout(lyt_btn)
        lyt_global.addWidget(self._cb_scanner)
        lyt_global.addWidget(btn_box)

        self.setWindowTitle("Select Channels")
        self.setMinimumWidth(200)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setLayout(lyt_global)
        self.show()

    def change_list(self):
        self.ch_list = [itm[0] for itm in enumerate(self._cb) if self._cb[itm[0]].isChecked() is True]

    def change_scanner(self):
        self._scanner = self._cb_scanner.itemText(self._cb_scanner.currentIndex())

    def return_list(self):
        return self.ch_list, self._scanner

    def select_all(self):
        for i in enumerate(self._cb):
            self._cb[i[0]].stateChanged.disconnect(self.change_list)
            self._cb[i[0]].setChecked(True)
            self._cb[i[0]].stateChanged.connect(self.change_list)
        self.change_list()

    def select_none(self):
        for i in enumerate(self._cb):
            self._cb[i[0]].stateChanged.disconnect(self.change_list)
            self._cb[i[0]].setChecked(False)
            self._cb[i[0]].stateChanged.connect(self.change_list)
        self.change_list()


#############################
# FigureCanvas
#############################
class PlotCanvas(FigureCanvas):
    msg2str = pyqtSignal(str)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Figure
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plot(self, df):
        print("Start Plotting")
        fontsize = 10
        # Clear last figure
        self.figure.clf()

        # Axes
        main_ax = self.figure.add_subplot(1, 1, 1)
        #main_ax.plot(df.loc, df.loc[:,i], label=df.iloc[i].name)
        for i in range(len(df.columns)):
            if df.columns[0] == 'ch0':
                x = df['ch0']
                xlabel = "ch0"
            else:
                x = df.index
                xlabel = "Index"
            main_ax.plot(x, df.iloc[:,i], label=df.columns[i])

        main_ax.legend(fontsize=fontsize)
        main_ax.tick_params(labelsize=fontsize)
        main_ax.set_xlabel(xlabel, fontsize=fontsize)
        main_ax.set_ylabel('y [Counts]', fontsize=fontsize)
        main_ax.grid(color='w', alpha=0.5, linestyle='dashed', linewidth=0.5)

        # Second x and y axis in micrometer
        # scld_xticks = np.around(self.pxl2um * np.arange(min(self.data_x[0]), max(self.data_x[0]), 250), 2)
        # scld_yticks = np.around(self.pxl2um * np.arange(min(self.data_y[0]), max(self.data_y[0]), 250), 2)
        #
        # main_ax_x2 = main_ax.twiny()
        # main_ax_x2.set_xticks(scld_xticks)
        # main_ax_x2.set_xlabel("Micrometer")
        #
        # main_ax_y2 = main_ax.twinx()
        # main_ax_y2.set_yticks(scld_yticks)
        # main_ax_y2.invert_yaxis()
        # main_ax_y2.set_ylabel("Micrometer")

        # ax_y.set_xlabel('I / \u03a3 I [%]', fontsize=14)
        # ax_x.set_ylabel('I / \u03a3 I [%]', fontsize=14)

        self.draw()


#############################
# MainWindow
#############################
class MyMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Screen Attributes
        screen_size = QDesktopWidget().availableGeometry()
        screen_res = [screen_size.width(), screen_size.height()]

        # Geometry
        self.my_left = round(0.05 * screen_res[0])
        self.my_top = round(0.05 * screen_res[1])
        self.my_height = round(0.9 * screen_res[1])
        
        if screen_res[0] >= 1280 or screen_res[1] >= 1980:
            self.my_left = round(0.3 * screen_res[0])
            self.my_top = round(0.3 * screen_res[1])
            self.my_height = round(0.4 * screen_res[1])

        self.my_width = self.my_height * 16 / 9  # round(0.8 * screen_res[0])

        # Widgets
        self.form_widget = FormWidget(self)
        # self.statusbar = self.statusBar()
        # self.form_widget.ch0.msg2str.connect(self.statusbar.showMessage)

        self.init_ui()

    def init_ui(self):
        self.setCentralWidget(self.form_widget)

        # Menu bar
        exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(qApp.quit)
        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')
        filemenu.addAction(exitAct)

        self.setGeometry(self.my_left, self.my_top, self.my_width, self.my_height)
        global version
        self.setWindowTitle('MELBA Scanner Data Acquisition '
                            'GUI Version {}'.format(version))
        self.show()
        self.center()

    def center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())


#############################
# FormWidget
#############################
class FormWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        # PV objects
        global scanner_list
        self._scanner = scanner_list[0]
        self._ch_select = [0, 1, 2]
        self._ch = {}

        # Progressbar for pvs
        self.pbar = QProgressBar()
        # self.pbar.setGeometry(QRect(30, 70, 481, 23))
        self.pbar.setProperty("value", 0)
        # Displayed Table
        self.model = None

        # Results
        self.lst_rst = pd.DataFrame()

        # Widgets
        self.btn_number = 8
        self.btn_list = {}
        self.btn_clear = None
        self.btn_close = None

        # Table for displaying result
        self.tableView = QTableView()

        # Plot Canvas
        self.m = PlotCanvas(self, 2 * parent.my_width, 2.5 * parent.my_height)
        self.m_toolbar = NavigationToolbar(self.m, self)
        self.m.msg2str[str].connect(self.append_to_txt_info)

        # Info text
        self.ln_info = QLineEdit()
        self.txt_info = QTextEdit()
        self.txt_info.setMinimumHeight(parent.my_height/6)

        # Select channels and scanner at startup
        self.select_ch_scan(True)

        self.init_ui(parent)

    def init_ui(self, parent):
        # Buttons
        lyt_btn = QHBoxLayout()

        for i in range(self.btn_number):
            self.btn_list[i] = QPushButton("Button{}".format(i))
            if i == self.btn_number - 2:
                lyt_btn.addStretch(1)
            lyt_btn.addWidget(self.btn_list[i])

        self.btn_list[0].setText("Load File")
        self.btn_list[0].clicked.connect(self.read_file)

        self.btn_list[1].setText("Info")
        self.btn_list[1].clicked.connect(self.get_info)

        self.btn_list[2].setText("Retrieve data")
        self.btn_list[2].clicked.connect(self.retrieve_data)

        self.btn_list[3].setText("Save Table")
        self.btn_list[3].clicked.connect(self.save_rst)

        self.btn_list[4].setText("Change Channel")
        self.btn_list[4].clicked.connect(self.select_ch_scan)

        self.btn_list[5].setText("Plot Table")
        self.btn_list[5].clicked.connect(self.plot_table)

        self.btn_clear = self.btn_list[len(self.btn_list) - 2]
        self.btn_clear.setText("Clear Table")
        self.btn_clear.clicked.connect(self.clear)

        self.btn_close = self.btn_list[len(self.btn_list) - 1]
        self.btn_close.setText("Close")
        self.btn_close.clicked.connect(self.quit)

        # Table
        self.tableView.setObjectName("tableView")
        self.tableView.setMinimumWidth(2*parent.my_width / 5)
        self.tableView.setMinimumHeight(parent.my_height / 2)

        # Info texts
        self.ln_info.setReadOnly(True)
        self.ln_info.setText("Selected channel: {} @Scanner {}".format(self._ch_select, self._scanner))
        self.txt_info.setMaximumHeight(200)

        # Sub Layout Channel box and progressbar
        lyt_info = QHBoxLayout()
        lyt_info.addWidget(self.ln_info)
        lyt_info.addWidget(self.pbar)

        # Sub Layout Plot
        lyt_plot = QVBoxLayout()
        lyt_plot.addWidget(self.m)
        lyt_plot.addWidget(self.m_toolbar)

        # Sub Layout Table and Plot
        lyt_tbl_plt = QHBoxLayout()
        lyt_tbl_plt.addWidget(self.tableView)
        lyt_tbl_plt.addLayout(lyt_plot)

        # Global Layout
        lyt_global = QVBoxLayout()
        lyt_global.setSpacing(1)
        lyt_global.addWidget(QLabel("Last results:"))
        lyt_global.addLayout(lyt_tbl_plt)
        lyt_global.addWidget(QLabel("Infobox:"))
        lyt_global.addLayout(lyt_info)
        lyt_global.addWidget(self.txt_info)
        lyt_global.addLayout(lyt_btn)

        # Set global Layout
        self.setLayout(lyt_global)

    def append_to_txt_info(self, text):
        now = datetime.datetime.now()
        tmp_txt = "{}  {}\n----------".format(now.strftime("%Y-%m-%d %H:%M:%S"), text)
        self.txt_info.append(tmp_txt)
        c = self.txt_info.textCursor()
        c.movePosition(QTextCursor.End)
        self.txt_info.setTextCursor(c)

    def assign_pvs(self):
        self.append_to_txt_info("Assigning channels: {} @Scanner {}".format(self._ch_select, self._scanner))
        self.ln_info.setText("Selected channel: {} @Scanner {}".format(self._ch_select, self._scanner))
        self._ch = {}
        for i in self._ch_select:
            self._ch[i] = ChannelData(i, self._scanner)
            self._ch[i].msg2str[str].connect(self.append_to_txt_info)
            self._ch[i].tick.connect(self.pbar.setValue)
        self.get_info()

    def clear(self):
        if not self.lst_rst.empty:
            dlg_save_bfr_quit = QMessageBox.question(self, 'Delete last results', "Do you really want to delete "
                                                                                  "the last result?",
                                                     QMessageBox.Yes | QMessageBox.No,
                                                     QMessageBox.No)
            if dlg_save_bfr_quit == QMessageBox.Yes:
                self.lst_rst = pd.DataFrame()
                self.display_df_table(self.lst_rst)
                self.append_to_txt_info("Cleared last results")
            else:
                return
        else:
            self.append_to_txt_info("No data yet to be cleared")
            return

    def display_df_table(self, df):
        self.model = PandasTable(df)
        self.tableView.setModel(self.model)
        self.plot_table()

    def get_info(self):
        for i in enumerate(self._ch):
            self._ch[i[1]].show_info()
        if not self._ch_select:
            self.append_to_txt_info("No channel selected yet")
            return

    def plot_table(self):
        if self.lst_rst.empty:
            self.txt_info.append("No data to be plotted")
            return
        # x = self.model.df.iloc[:, 0]
        # y = self.model.df.iloc[:, 1]
        self.m.plot(self.lst_rst)

    def read_file(self):
        self.txt_info.append("Please choose a data file...")
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                              "Images (*.csv)", options=options)
        if not file:
            self.txt_info.append('No file chosen')
            return None

        self.txt_info.append('{} loaded'.format(file))
        df = pd.read_csv(file, index_col=0, header=0)
        self.display_df_table(df)

    def retrieve_data(self):
        if not self._ch_select:
            self.append_to_txt_info("No channel selected yet")
            return

        # Reference value
        first_channel = next(iter(self._ch))

        if not int == type(self._ch[first_channel].pv['samples'].value):
            number_of_values = self._ch[first_channel].pv['samples'].value.shape[0] \
                               + self._ch[first_channel].pv['nos'].value
        else:
            number_of_values = self._ch[first_channel].pv['nos'].value

        if not all(
                self._ch[i[1]].pv['nos'].value == number_of_values or
                self._ch[i[1]].pv['samples'].value.shape[0] == number_of_values
                for i in enumerate(self._ch)
        ):
            self.append_to_txt_info("All channels must have the same number of samples. Cancel retrieving.")
            return

        # self.get_info()
        tmp_rst = pd.DataFrame()

        for i in enumerate(self._ch):
            self._ch[i[1]].retrieve_data()
            if self._ch[i[1]].data is not None:
                tmp_rst['ch{}'.format(i[1])] = self._ch[i[1]].data

        if tmp_rst.empty:
            self.append_to_txt_info("No values received")
            return

        self.lst_rst = tmp_rst
        self.display_df_table(self.lst_rst)
        # self.save_rst()

    def save_rst(self):
        if self.model.df.empty:
            self.txt_info.append("No data to be saved")
            return
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        now = datetime.datetime.now()
        save_str = "{}_last_rsl.csv".format(now.strftime("%y%m%d_%H%M"))
        my_path, _ = QFileDialog.getSaveFileName(self, "Save to", save_str,
                                                 "CSV-File (*.csv);;All Files (*)", options=options)

        if not my_path:
            self.txt_info.append("Saving aborted!")
            return
        self.model.df.to_csv(my_path)
        self.txt_info.append('Table saved to {}'.format(my_path))

    def select_ch_scan(self, init=False):
        self.txt_info.append("Assigning new channels, please wait...")
        dlg = MyInputDialog(self._ch_select, self._scanner)
        if dlg.exec_():
            self._ch_select, self._scanner = dlg.return_list()
            self.assign_pvs()
        else:
            if init:
                quit()
            self.txt_info.append("Keeping old channels: ".format(self._ch_select))

    def quit(self):
        if not self.lst_rst.empty:
            dlg_save_bfr_quit = QMessageBox.question(self, 'Save before quit!', "Do you want to save the last result?",
                                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                                     QMessageBox.Yes)
            if dlg_save_bfr_quit == QMessageBox.Yes:
                self.save_rst()
                dlg_now_quit = QMessageBox.question(self, 'Save before quit!', "Do you want to save the last result?",
                                                    QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if dlg_now_quit == QMessageBox.Cancel:
                    return
            elif dlg_save_bfr_quit == QMessageBox.Cancel:
                return

        qApp.quit()


#############################
# EPICS data storage
#############################
class ChannelData(PV, QObject):
    msg2str = pyqtSignal(str)
    tick = pyqtSignal(int, str)

    def __init__(self, ch=0, ch_scanner='melba_020:scan:'):
        QObject.__init__(self)  # Initiate pyqtSignal

        self.ch = ch
        self.scanner = ch_scanner
        self.data = pd.Series()
        self.delay = 0.5  # Predefined delay in seconds between processing of record

        self.pv = {
            'nos': PV(self.scanner + 'datach' + str(self.ch) + '_noofsamples_get'),
            'samples': PV(self.scanner + 'datach' + str(self.ch) + '_samples_get')
        }

        self.pv['nos'].get()
        time.sleep(0.2)
        self.pv['samples'].get()
        time.sleep(0.2)
        # Debug
        for k in self.pv.keys():
            print("ch{} : self.pv[{}].value = {}".format(self.ch, k, self.pv[k].value))
            print("ch{} : type(self.pv[{}].value) = {}".format(self.ch, k, type(self.pv[k].value)))

    def append_to_data(self, samples):
        if self.data.empty:
            self.data = pd.Series(samples)

        else:
            self.data = self.data.append(pd.Series(samples), ignore_index=True)

    def clear_saved_data(self):
        self.data = pd.Series()

    def process(self):
        epics.caput(self.pv['samples'].pvname + '.PROC', 1, wait=True)
        time.sleep(self.delay)
        self.pv['samples'].get()

    def update_pbar(self, imax=0):
        ip = self.pv['nos'].value
        if imax != 0:
            send_int = int(round((1 - ip / imax) * 100))
        else:
            send_int = 100
        self.tick.emit(send_int, "Channel {}".format(self.ch))

    def retrieve_data(self):
        # Check if data is available at all, else abort retrieving data
        if self.pv['nos'].value == 0:

            # Exit if no data is available at all
            if not type(self.pv['samples']) == int and self.pv['samples'].value.shape[0] == 0:
                self.msg2str.emit("No datapoints available for channel {}".format(self.ch))
                return pd.Series()
            # If samples already available, append and return them
            else:
                self.append_to_data(self.pv['samples'].value)
                self.update_pbar()
                self.return_data()

        else:  # nos != 0
            # Timer
            nos_max = self.pv['nos'].value
            # If samples are already available, append them
            self.msg2str.emit("Start receiving datapoints for channel {}".format(self.ch))
            print("ch{}: self.pv['samples'] = {}".format(self.ch, self.pv['samples']))
            if int == type(self.pv['samples'].value) or not self.pv['samples'].value.shape[0] == 0:
                self.append_to_data(self.pv['samples'].value)
                self.update_pbar(nos_max)

            while self.pv['nos'].value != 0:
                self.show_info()
                self.msg2str.emit("Processing channel {}".format(self.ch))
                self.process()
                time.sleep(0.5)
                self.append_to_data(self.pv['samples'].value)
                self.update_pbar(nos_max)

                self.return_data()

    def return_data(self):
        return self.data

    def show_info(self):
        try:
            if not int == type(self.pv['samples'].value):
                self.msg2str.emit("ch{}: nos = {}; "
                                  "samples = {}".format(self.ch, self.pv['nos'].value,
                                                        self.pv['samples'].value.shape[0]))
            else:
                self.msg2str.emit("ch{}: nos = {}; "
                                  "samples = {}".format(self.ch, self.pv['nos'].value,
                                                        self.pv['samples'].value))
        except:
            self.msg2str.emit("ch{}: Error showing info".format(self.ch))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MyMainWindow()
    # md = MyInputDialog()
    sys.exit(app.exec_())  # Mainloop
