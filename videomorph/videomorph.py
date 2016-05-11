#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# File name: videomorph.py
#
#   VideoMorph - A PyQt5 frontend to ffmpeg
#   Copyright 2015-2016 VideoMorph Development Team

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
import shlex
from functools import partial

from PyQt5.QtWidgets import (QMainWindow,
                             QApplication,
                             QWidget,
                             QVBoxLayout,
                             QHBoxLayout,
                             QSizePolicy,
                             QGroupBox,
                             QLabel,
                             QSpacerItem,
                             QComboBox,
                             QProgressBar,
                             QToolBar,
                             QTableWidget,
                             QTableWidgetItem,
                             QLineEdit,
                             QAction,
                             QStyle,
                             QAbstractItemView,
                             QFileDialog,
                             QMessageBox,
                             QHeaderView,
                             QToolButton,
                             QItemDelegate,
                             qApp)
from PyQt5.QtCore import (QSize,
                          Qt,
                          QSettings,
                          QDir,
                          QPoint,
                          QProcess,
                          QLocale,
                          QTranslator,
                          QLibraryInfo)
from PyQt5.QtGui import QPixmap, QIcon

from videomorph.converter.presets import PRESETS
from videomorph.converter.presets import PROFILES
from videomorph.converter.media import STATUS

from videomorph.converter import converter
from videomorph.converter import media
from videomorph.converter import utils
from videomorph.about import AboutVM
from videomorph import VERSION

# Table columns
NAME, DURATION, QUALITY, PROGRESS = range(4)


class MMWindow(QMainWindow):
    """Main Window class."""

    def __init__(self):
        """Class initializer."""
        super(MMWindow, self).__init__()
        # App data structures
        # Create the Media list object
        self.media_list = media.MediaList()
        # Variables for calculating total progress
        self.time_jump = 0.0
        self.partial_time = 0.0
        self.total_time = 0.0
        self.total_duration = 0.0

        # Create and setup FFmpegConverter object
        self.converter = converter.FFmpegConverter()
        self.converter.setProcessChannelMode(QProcess.MergedChannels)
        self.converter.readyRead.connect(self._read_encoding_output)
        self.converter.finished.connect(self.finish_file_encoding)

        # App interface setup
        # Window size
        self.resize(680, 576)
        # Set window title
        self.setWindowTitle('VideoMorph' + ' ' + VERSION)
        # Define and set app icon
        icon = QIcon()
        icon.addPixmap(QPixmap('/usr/share/icons/videomorph.png'))
        self.setWindowIcon(icon)
        # Define app central widget
        self.central_widget = QWidget(self)
        # Difine layouts
        self.vl = QVBoxLayout(self.central_widget)
        self.hl = QHBoxLayout()
        self.vl1 = QVBoxLayout()
        self.vl2 = QVBoxLayout()
        # Define groups
        self.group_settings()
        self.fix_layout()
        self.group_tasks_list()
        self.group_output_directory()
        self.group_progress()
        # Create the toolbar
        self.create_toolbar()
        # Add layouts
        self.hl.addLayout(self.vl2)
        self.vl.addLayout(self.hl)
        # Set central widget
        self.setCentralWidget(self.central_widget)
        # Create actions
        self.create_actions()
        # Populate PROFILES combo box
        self.populate_profiles()
        # Read app settings
        self.read_app_settings()

        # Disable presets and profiles combo boxes
        self.cb_presets.setEnabled(False)
        self.cb_profiles.setEnabled(False)

        # Create app main menu bar
        self.create_main_menu()

        # Create app status bar
        self.create_status_bar()

        # Set tool buttons style
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

    def group_settings(self):
        """Settings group."""
        gb_settings = QGroupBox(self.central_widget)
        gb_settings.setTitle(self.tr('Conversion Presets'))
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            gb_settings.sizePolicy().hasHeightForWidth())
        gb_settings.setSizePolicy(sizePolicy)
        hl = QHBoxLayout(gb_settings)
        vl = QVBoxLayout()
        hl1 = QHBoxLayout()
        label = QLabel(self.tr('Convert to:'))
        hl1.addWidget(label)
        spacerItem = QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hl1.addItem(spacerItem)
        vl.addLayout(hl1)
        self.cb_profiles = QComboBox(
            gb_settings,
            statusTip=self.tr('Select desired video format'))
        self.cb_profiles.setMinimumSize(QSize(200, 0))
        vl.addWidget(self.cb_profiles)
        hl2 = QHBoxLayout()
        label = QLabel(self.tr('Target Quality:'))
        hl2.addWidget(label)
        spacerItem1 = QSpacerItem(40,
                                  20,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Minimum)
        hl2.addItem(spacerItem1)
        vl.addLayout(hl2)
        self.cb_presets = QComboBox(
            gb_settings,
            statusTip=self.tr('Select desired video quality'))
        self.cb_presets.setMinimumSize(QSize(200, 0))
        self.cb_profiles.currentIndexChanged.connect(partial(
            self.populate_presets, self.cb_presets))
        self.cb_presets.activated.connect(self.update_media_files_status)
        vl.addWidget(self.cb_presets)
        hl.addLayout(vl)
        self.vl1.addWidget(gb_settings)

    def fix_layout(self):
        """Fix widgets layout."""
        spacer_item = QSpacerItem(20,
                                 40,
                                 QSizePolicy.Minimum,
                                 QSizePolicy.Expanding)
        self.vl1.addItem(spacer_item)
        self.hl.addLayout(self.vl1)

    def group_tasks_list(self):
        """Define the Tasks Group arrangement."""
        gb_tasks = QGroupBox(self.central_widget)
        gb_tasks.setTitle(self.tr('List of Conversion Tasks'))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(gb_tasks.sizePolicy().hasHeightForWidth())
        gb_tasks.setSizePolicy(sizePolicy)
        hl = QHBoxLayout(gb_tasks)
        self.tb_tasks = QTableWidget(gb_tasks)
        self.tb_tasks.setColumnCount(4)
        self.tb_tasks.setRowCount(0)
        self.tb_tasks.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tb_tasks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tb_tasks.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        # self.tb_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tb_tasks.setHorizontalHeaderLabels(
            [self.tr('Name'),
             self.tr('Duration'),
             self.tr('Target Quality'),
             self.tr('Progress')])
        self.tb_tasks.cellClicked.connect(self._enable_remove_file_action)
        # Create a combo box for Target quality
        self.tb_tasks.setItemDelegate(TargetQualityDelegate(parent=self))
        hl.addWidget(self.tb_tasks)
        self.vl2.addWidget(gb_tasks)
        self.tb_tasks.doubleClicked.connect(self.update_edit_triggers)

    def update_edit_triggers(self):
        if (int(self.tb_tasks.currentColumn()) == QUALITY and not
                self.converter.is_running()):
            self.tb_tasks.setEditTriggers(
                QAbstractItemView.AllEditTriggers)
        else:
            self.tb_tasks.setEditTriggers(
                QAbstractItemView.NoEditTriggers)

    def group_output_directory(self):
        """Define the output directory Group arrangement."""
        gb_output = QGroupBox(self.central_widget)
        gb_output.setTitle(self.tr('Output Directory'))
        vl = QVBoxLayout(gb_output)
        vl1 = QVBoxLayout()
        hl = QHBoxLayout()
        self.le_output = QLineEdit(
            str(QDir.homePath()),
            statusTip=self.tr('Select output directory'))
        self.le_output.setReadOnly(True)
        hl.addWidget(self.le_output)
        self.tb_output = QToolButton(
            gb_output,
            statusTip=self.tr('Select output directory'))
        self.tb_output.setText('...')
        self.tb_output.clicked.connect(self.output_directory)
        hl.addWidget(self.tb_output)
        vl1.addLayout(hl)
        vl.addLayout(vl1)
        self.vl2.addWidget(gb_output)

    def group_progress(self):
        """Define the Progress Group arrangement."""
        gb_progress = QGroupBox(self.central_widget)
        gb_progress.setTitle(self.tr('Progress'))
        vl = QVBoxLayout(gb_progress)
        label_progress = QLabel(gb_progress)
        label_progress.setText('Operation Progress')
        vl.addWidget(label_progress)
        self.pb_progress = QProgressBar(gb_progress)
        self.pb_progress.setProperty('value', 0)
        vl.addWidget(self.pb_progress)
        label_total_progress = QLabel(gb_progress)
        label_total_progress.setText('Total Progress')
        vl.addWidget(label_total_progress)
        self.pb_total_progress = QProgressBar(gb_progress)
        self.pb_total_progress.setProperty('value', 0)
        vl.addWidget(self.pb_total_progress)
        self.vl2.addWidget(gb_progress)

    def read_app_settings(self):
        """Read the app settings."""
        settings = QSettings(QDir.homePath() + '/.videomorph/config.ini',
                             QSettings.IniFormat)
        pos = settings.value("pos", QPoint(600, 200), type=QPoint)
        size = settings.value("size", QSize(1096, 510), type=QSize)
        self.resize(size)
        self.move(pos)
        if 'profile' and 'preset' in settings.allKeys():
            prof = settings.value('profile')
            pres = settings.value('preset')
            self.cb_profiles.setCurrentIndex(int(prof))
            self.cb_presets.setCurrentIndex(int(pres))
        if 'output_dir' in settings.allKeys():
            self.le_output.setText(str(settings.value('output_dir')))

    def write_app_settings(self):
        """Write app settings on exit."""
        settings = QSettings(
            QDir.homePath() + '/.videomorph/config.ini', QSettings.IniFormat)
        settings.setValue("pos", self.pos())
        settings.setValue("size", self.size())
        settings.setValue("profile", self.cb_profiles.currentIndex())
        settings.setValue("preset", self.cb_presets.currentIndex())
        settings.setValue("output_dir", self.le_output.text())

    def closeEvent(self, event):
        """Things to todo on close."""
        # Disconnect the finished signal
        self.converter.finished.disconnect(self.finish_file_encoding)
        # Close communication and kill the encoding process
        if self.converter.state() == QProcess.Running:
            self.converter.close()
            self.converter.kill()
        # Save settings
        self.write_app_settings()
        event.accept()

    def check_ffmpeg(self):
        """Check if ffmpeg and ffprobe are installed on the system."""
        if utils.which('ffmpeg') and utils.which('ffprobe'):
            return True
        else:
            msg_box = QMessageBox(
                QMessageBox.Critical,
                self.tr(u'Error!'),
                self.tr('ffmpeg/ffprobe binary not found in your system'),
                QMessageBox.NoButton, self)
            msg_box.addButton("&Ok", QMessageBox.AcceptRole)
            if msg_box.exec_() == QMessageBox.AcceptRole:
                qApp.closeAllWindows()
                return False

    def create_actions(self):
        """Create the actions and connect them to the tool bar buttons."""
        self.add_media_file_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogOpenButton),
            self.tr('&Open'),
            self,
            shortcut="Ctrl+O",
            enabled=True,
            statusTip=self.tr('Add media files to the '
                              'list of conversion tasks'),
            triggered=self.add_media)

        self.clear_media_list_action = QAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            self.tr('Clear &List'),
            self,
            shortcut="Ctrl+Del",
            enabled=False,
            statusTip=self.tr('Clear the media list'),
            triggered=self.clear_media_list)

        self.remove_media_file_action = QAction(
            self.style().standardIcon(QStyle.SP_BrowserStop),
            self.tr('&Remove File'),
            self,
            shortcut="Del",
            enabled=False,
            statusTip=self.tr('Remove media files from the list'),
            triggered=self.remove_media_file)

        self.convert_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaPlay),
            self.tr('&Convert'),
            self,
            shortcut="Ctrl+R",
            enabled=False,
            statusTip=self.tr('Start conversion process'),
            triggered=self.start_encoding)

        self.stop_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaStop),
            self.tr('&Stop'),
            self,
            shortcut="Ctrl+P",
            enabled=False,
            statusTip=self.tr('Stop media file conversion'),
            triggered=self.stop_file_encoding)

        self.about_action = QAction(
            self.style().standardIcon(QStyle.SP_MessageBoxInformation),
            self.tr('&About'),
            self,
            shortcut="Ctrl+H",
            enabled=True,
            statusTip=self.tr('About VideoMorph {v}'.format(v=VERSION)),
            triggered=self.about)

        self.exit_action = QAction(
            self.style().standardIcon(QStyle.SP_DialogCloseButton),
            self.tr('&Exit'),
            self,
            shortcut="Ctrl+Q",
            enabled=True,
            statusTip=self.tr('Exit VideoMorph {v}'.format(v=VERSION)),
            triggered=self.close)

        # Add actions to the tool bar
        self.tool_bar.addAction(self.add_media_file_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.clear_media_list_action)
        self.tool_bar.addAction(self.remove_media_file_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.convert_action)
        self.tool_bar.addAction(self.stop_action)

    def create_main_menu(self):
        self.file_menu = self.menuBar().addMenu(self.tr('&File'))
        self.file_menu.addAction(self.add_media_file_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.edit_menu = self.menuBar().addMenu(self.tr('&Edit'))
        self.edit_menu.addAction(self.clear_media_list_action)
        self.edit_menu.addAction(self.remove_media_file_action)

        self.convet_menu = self.menuBar().addMenu(self.tr('&Convert'))
        self.convet_menu.addAction(self.convert_action)
        self.convet_menu.addAction(self.stop_action)

        self.hel_menu = self.menuBar().addMenu(self.tr('&Help'))
        self.hel_menu.addAction(self.about_action)

    def create_toolbar(self):
        """Create and add a tool bar to the interface."""
        self.tool_bar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.tool_bar)

    def create_status_bar(self):
        self.statusBar().showMessage(self.tr('Ready'))

    def about(self):
        a = AboutVM()
        a.exec_()

    def populate_profiles(self):
        """Populate profiles combo box."""
        self.cb_profiles.addItems(PROFILES)

    def populate_presets(self, cb_presets):
        """Populate presets combo box."""
        profile = self.cb_profiles.currentText()
        cb_presets.clear()

        for preset in PRESETS:
            if profile == PRESETS[preset].profile_name:
                cb_presets.addItem(PRESETS[preset].profile_label)
        self.update_media_files_status()

    def output_directory(self):
        """Choose output directory."""
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr('Choose output directory'),
            QDir.homePath(),
            options=options)

        if directory:
            self.le_output.setText(directory)

    def add_media(self):
        """Add media files to the list of conversion tasks."""
        # Dialog title
        title = self.tr('Select Files')
        # Media filters
        v_filter = (self.tr('Video files') +
                    '(*.mkv *.ogg *.mp4 *.mpg *.dat '
                    '*.f4v *.flv *.wv *.3gp *.avi *.webm '
                    '*.wmv *.mov *.vob *.ogv *.ts)')
        # Select media files and store their path
        media_paths, _ = QFileDialog.getOpenFileNames(self,
                                                      title,
                                                      QDir.homePath(),
                                                      v_filter)
        # If no file is selected then return
        if not media_paths:
            return

        # Count rows in the tasks table
        rows = self.tb_tasks.rowCount()

        # This rewind the encoding list if the encoding process is not running
        if not self.converter.is_running():
            self.media_list.running_index = -1

        # Add selected medias to the table and to MediaList
        for media_path in media_paths:
            # Create the file and add it to the list
            media_file = media.MediaFile(media_path)
            try:
                self.media_list.add(media_file)
                self.tb_tasks.setRowCount(rows + 1)
            except media.FileAddedError:
                continue

            item = QTableWidgetItem()
            item.setText(media_file.get_file_name(with_extension=True))
            self.tb_tasks.setItem(rows, NAME, item)
            item = QTableWidgetItem()
            file_duration = str(
                utils.write_time(media_file.info.format_duration))
            item.setText(file_duration)
            self.tb_tasks.setItem(rows, DURATION, item)
            item = QTableWidgetItem()
            target_quality = str(self.cb_presets.currentText())
            item.setText(target_quality)

            # Initialize the MediaFile.target_quality
            media_file.target_quality = target_quality

            self.tb_tasks.setItem(rows, QUALITY, item)
            item = QTableWidgetItem()
            item.setText(self.tr(STATUS.todo))
            self.tb_tasks.setItem(rows, PROGRESS, item)
            # Next table row
            rows += 1

        # After adding files to the list, recalculate the list duration
        self.total_duration = self.media_list.duration
        # Update tool buttons so you can convert, or add, or clear...
        self.update_interface(stop=False, remove=False)

    def remove_media_file(self):
        """Remove selected media file from the list."""
        item = self.tb_tasks.currentItem().row()
        if item is not None:
            # Delete file from table
            self.tb_tasks.removeRow(item)
            # If all files are deleted... update the interface
            if not self.tb_tasks.rowCount():
                self.update_interface(convert=False,
                                      clear=False,
                                      remove=False,
                                      stop=False,
                                      presets=False,
                                      profiles=False)
            # Remove file from MediaList
            self.media_list.delete_file(file_index=item)
            self.total_duration = self.media_list.duration

    def clear_media_list(self):
        """Clear media conversion list with user confirmation."""
        msg_box = QMessageBox(
            QMessageBox.Warning,
            self.tr('Warning!'),
            self.tr('Clear all tasks?'),
            QMessageBox.NoButton, self)

        msg_box.addButton(self.tr("&Yes"), QMessageBox.AcceptRole)
        msg_box.addButton(self.tr("&No"), QMessageBox.RejectRole)

        if msg_box.exec_() == QMessageBox.AcceptRole:
            # If use says YES clear table of conversion tasks
            self.tb_tasks.clearContents()
            self.tb_tasks.setRowCount(0)
            # Clear MediaList.medias so it does not contain any element
            self.media_list.clear()
            # Update buttons so user cannot convert, clear, or stop if there
            # is no file in the list
            self.update_interface(convert=False,
                                  clear=False,
                                  remove=False,
                                  stop=False,
                                  presets=False,
                                  profiles=False)

    def start_encoding(self):
        """Start the encoding process."""
        # Update tool buttons state
        self.update_interface(presets=False,
                              profiles=False,
                              convert=False,
                              clear=False,
                              remove=False)

        # Increment the the MediaList index
        self.media_list.running_index += 1

        running_media = self.media_list.get_running_file()
        profile = PRESETS[running_media.target_quality]

        if (not running_media.status == STATUS.done and not
                running_media.status == STATUS.stopped):
            output_file = (self.le_output.text() +
                           '/' +
                           profile.profile_tag +
                           ' ' +
                           running_media.get_file_name() +
                           profile.profile_extension)

            cmd = ['-i', running_media.path] + \
                  shlex.split(profile.profile_params) + \
                  ['-y', output_file]

            self.converter.start(cmd)

        else:
            self.end_encoding_process()

    def stop_file_encoding(self):
        """Stop file encoding process and continue with the list."""
        # Set MediaFile.status attribute
        self.media_list.get_running_file().status = STATUS.stopped
        # Update the list duration and partial time for total progress bar
        self.total_duration = self.media_list.duration
        self.time_jump = 0.0
        self.partial_time = 0.0
        self.total_time = 0.0
        # Terminate the file encoding process
        self.converter.terminate()
        if self.converter.state() == QProcess.Running:
            self.converter.kill()

    def finish_file_encoding(self):
        """Finish the file encoding process."""
        if not self.media_list.get_running_file().status == STATUS.stopped:
            # Close and kill the converter process
            self.converter.close()
            # Check if the process finished OK
            if self.converter.exitStatus() == QProcess.NormalExit:
                # When finished a file conversion...
                self.tb_tasks.item(self.media_list.running_index, 3).setText(
                    self.tr(STATUS.done))
                self.media_list.get_running_file().status = STATUS.done
                self.pb_progress.setProperty("value", 0)
            # Attempt to end the conversion process
            self.end_encoding_process()
        else:
            # If the process was stopped
            if self.converter.state() == QProcess.NotRunning:
                self.tb_tasks.item(self.media_list.running_index, 3).setText(
                    self.tr(STATUS.stopped))
            # Attempt to end the conversion process
            self.end_encoding_process()

    def end_encoding_process(self):

        # Test if running_index is out of range
        if self.media_list.running_index + 1 >= self.media_list.length:
            # List is done
            msg_box = QMessageBox(
                QMessageBox.Information,
                self.tr(u'Finished!'),
                self.tr(u'Encoding process successfully finished!'),
                QMessageBox.Ok,
                self)
            msg_box.show()
            self.statusBar().showMessage(self.tr('Ready'))
            # Reset all progress related variables
            self.pb_progress.setProperty("value", 0)
            self.pb_total_progress.setProperty("value", 0)
            self.time_jump = 0.0
            self.partial_time = 0.0
            self.total_time = 0.0
            self.total_duration = self.media_list.duration
            # Reset the running_index
            self.media_list.running_index = -1
            # Update tool buttons
            self.update_interface(convert=False, stop=False, remove=False)
        else:
            self.start_encoding()

    def _read_encoding_output(self):
        """Read the encoding output from the self.converter stdout."""
        time_pattern = re.compile(r'time=([0-9.:]+) ')
        ret = str(self.converter.readAll())
        time = time_pattern.findall(ret)

        if time:
            # Convert time to seconds
            if ':' in time[0]:
                time_in_secs = 0
                for part in time[0].split(':'):
                    time_in_secs = 60 * time_in_secs + float(
                        part)
            else:
                time_in_secs = float(time[0])

            # Calculate operation progress percent
            op_time = self.media_list.get_running_file().info.format_duration
            operation_progress = int(time_in_secs / float(op_time) * 100)

            # Update the table and the operation progress bar
            self.pb_progress.setProperty("value", operation_progress)
            self.tb_tasks.item(self.media_list.running_index, 3).setText(
                str(operation_progress) + "%")

            # Calculate total time
            if self.partial_time > time_in_secs:
                self.time_jump += self.partial_time
                self.total_time = self.time_jump + time_in_secs
                self.partial_time = time_in_secs
            else:
                self.total_time = self.time_jump + time_in_secs
                self.partial_time = time_in_secs

            # Calculate total progress percent
            total_progress = int(self.total_time /
                                 float(self.total_duration) *
                                 100)
            # Update the total progress bar
            self.pb_total_progress.setProperty("value",
                                               total_progress)

            self.statusBar().showMessage(
                self.tr('Converting: {m}\t\t\t '
                        'Operation remaining time: {rt}\t\t\t '
                        'Total remaining time: {trt}').format(
                    m=self.media_list.get_running_file().get_file_name(True),
                    rt=utils.write_time(float(op_time) - time_in_secs),
                    trt=utils.write_time(
                        self.total_duration - self.total_time)))

    # TODO: Review this and setEditorData for repeated code
    def update_media_files_status(self):
        """Update target Quality."""
        # Current item
        item = self.tb_tasks.currentItem()
        if item is not None:
            # Update target_quality in table
            self.tb_tasks.item(item.row(), QUALITY).setText(
                str(self.cb_presets.currentText()))
            # Update file target_quality
            self.media_list.get_file(item.row()).target_quality = str(
                self.cb_presets.currentText())
            # Update table Progress field if file is: Done or Stopped
            if (self.media_list.get_status(item.row()) == STATUS.done or
                    self.media_list.get_status(item.row()) == STATUS.stopped):
                self.tb_tasks.item(item.row(), PROGRESS).setText(
                    self.tr(STATUS.todo))
            # Update file Done or Stopped status
            self.media_list.set_status(file_index=item.row(),
                                       status=STATUS.todo)
            # Update total duration of the new tasks list
            self.total_duration = self.media_list.duration
            # Update the interface
            self.update_interface(clear=False, stop=False, remove=False)
        else:
            if self.tb_tasks.rowCount():
                for i in range(self.tb_tasks.rowCount()):
                    self.tb_tasks.item(i, QUALITY).setText(
                        str(self.cb_presets.currentText()))

                    if (self.media_list.get_status(i) == STATUS.done or
                            self.media_list.get_status(i) == STATUS.stopped):
                        self.tb_tasks.item(i, PROGRESS).setText(
                            self.tr(STATUS.todo))

                    self.media_list.get_file(i).target_quality = str(
                        self.cb_presets.currentText())
                self.update_interface(clear=False, stop=False, remove=False)
            self._set_media_status()
            self.total_duration = self.media_list.duration

    def _set_media_status(self):
        """Update media files state of conversion."""
        for media_ in self.media_list:
            media_.status = STATUS.todo
        self.media_list.running_index = -1

    def update_interface(self,
                         add=True,
                         convert=True,
                         clear=True,
                         remove=True,
                         stop=True,
                         presets=True,
                         profiles=True):
        self.add_media_file_action.setEnabled(add)
        self.convert_action.setEnabled(convert)
        self.clear_media_list_action.setEnabled(clear)
        self.remove_media_file_action.setEnabled(remove)
        self.stop_action.setEnabled(stop)
        self.cb_presets.setEnabled(presets)
        self.cb_profiles.setEnabled(profiles)
        self.tb_tasks.setCurrentItem(None)

    def _enable_remove_file_action(self):
        if not self.converter.is_running():
            self.remove_media_file_action.setEnabled(True)


class TargetQualityDelegate(QItemDelegate):
    # TODO: can be omitted if nothing more is to be done
    def __init__(self, parent=None):
        super(TargetQualityDelegate, self).__init__(parent)
        self.parent = parent

    def createEditor(self, parent, option, index):
        if index.column() == QUALITY:
            editor = QComboBox(parent)
            self.parent.populate_presets(cb_presets=editor)
            editor.activated.connect(partial(self.update,
                                             editor,
                                             index))
            return editor
        else:
            return QItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        if index.column() == QUALITY:
            i = editor.findText(text)
            if i == -1:
                i = 0
            editor.setCurrentIndex(i)

        else:
            QItemDelegate.setEditorData(self, editor, index)

    def update(self, editor, index):
        # Update file target_quality
        selected_file = self.parent.media_list.get_file(index.row())
        selected_file.target_quality = editor.currentText()
        # Update table Progress field if file is: Done or Stopped
        if (self.parent.media_list.get_status(index.row()) == STATUS.done or
             self.parent.media_list.get_status(index.row()) == STATUS.stopped):
            self.parent.tb_tasks.item(index.row(), PROGRESS).setText(
                self.tr(STATUS.todo))
        # Update file status
        self.parent.media_list.set_status(file_index=index.row(),
                                          status=STATUS.todo)
        # Update total duration of the new tasks list
        self.parent.total_duration = self.parent.media_list.duration
        # Update the interface
        self.parent.update_interface(clear=False,
                                     stop=False,
                                     remove=False)

        selected_file = self.parent.media_list.get_file(index.row())
        selected_file.target_quality = editor.currentText()
        self.parent.tb_tasks.setEditTriggers(
            QAbstractItemView.NoEditTriggers)


def main():
    """ Function doc """
    import sys
    from os.path import dirname, realpath, exists
    app = QApplication(sys.argv)
    filePath = dirname(realpath(__file__))
    locale = QLocale.system().name()
    if locale == 'es_CU':
        locale = 'es_ES'
    appTranslator = QTranslator()
    if exists(filePath + '/translations/'):
        appTranslator.load(filePath + "/translations/videomorph_" + locale)
    else:
        appTranslator.load(
            "/usr/share/videomorph/translations/videomorph_" + locale)
    app.installTranslator(appTranslator)
    qtTranslator = QTranslator()
    qtTranslator.load("qt_" + locale,
                      QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator)
    mainWin = MMWindow()
    if mainWin.check_ffmpeg():
        mainWin.show()
        sys.exit(app.exec_())


if __name__ == '__main__':
    main()
