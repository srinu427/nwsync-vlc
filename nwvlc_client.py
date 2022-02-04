import os
import sys
import vlc
import json
import pathlib
import platform
import requests
import threading

from PyQt6 import QtWidgets, QtGui, QtCore
from qt_material import apply_stylesheet


class Player(QtWidgets.QMainWindow):
    """A simple Media Player using VLC and Qt
    """
    def send_status(self):
        if self.media_name is not None and self.uname is not None:
            with self.nthread_lock:
                try:
                    res = requests.post(self.url,
                                        json={'media_name': self.media_name,
                                              'current_ts': self.positionslider.value(),
                                              'action': self.action,
                                              'user': self.uname})
                except:
                    print("Error sending status")
                self.action_queue += [res.json()]
        if self.action is not None:
            self.action = None
            
    def spawn_nthread(self):
        nthread = threading.Thread(target=self.send_status, daemon=True)
        nthread.start()
        if self.should_stop_n:
            self.n_timer.stop()
    
    def update_status(self, name=None, action=None):
        if name is not None:
            self.media_name = name
        if action is not None:
            self.action = action

    def set_mname(self):
        self.media_name = self.mname_box.text()
    
    def set_uname(self):
        self.uname = self.uname_box.text()
        
    def execute_action(self, sdata):
        if 'synced' in sdata:
            if sdata['synced']:
                self.playbutton.setEnabled(True)
                self.stopbutton.setEnabled(True)
                self.positionslider.setEnabled(True)
            else:
                self.playbutton.setEnabled(False)
                self.stopbutton.setEnabled(False)
                self.positionslider.setEnabled(False)

        if 'action' in sdata:
            if sdata['action'] == 'play':
                #print("signal recieved to play at: " + str(sdata['current_ts']))
                if not self.mediaplayer.is_playing():
                    self.play_pause()
                    self.action = None
                with self.uthread_lock:
                    self.positionslider.setValue(sdata['current_ts'])
                self.set_position()
            if sdata['action'] == 'pause':
                #print("signal recieved to pause at: " + str(sdata['current_ts']))
                if self.mediaplayer.is_playing():
                    self.play_pause()
                    self.action = None
                with self.uthread_lock:
                    self.positionslider.setValue(sdata['current_ts'])
                self.set_position()
            if sdata['action'] == 'seek':
                #print("signal recieved to seek at: " + str(sdata['current_ts']))
                self.positionslider.setValue(sdata['current_ts'])
                self.set_position()

    def __init__(self, master=None, url="http://127.0.0.1:4270/poll_status"):
        QtWidgets.QMainWindow.__init__(self, master)
        self.url = url
        self.media_name = None
        self.uname = None
        self.nwpoll_interval_ms = 1000
        
        if (os.path.isfile("config.json")):
            with open('config.json') as fr:
                cjdata = json.load(fr)
            if 'url' in cjdata:
                self.url = cjdata['url']
            if 'media_name' in cjdata:
                self.media_name = cjdata['media_name']
            if 'uname' in cjdata:
                self.uname = cjdata['uname']
            if 'nwpoll_interval_ms' in cjdata:
                self.nwpoll_interval_ms = cjdata['nwpoll_interval_ms']
            
        self.action = None
        self.should_stop_u = False
        self.should_stop_n = False
        
        self.nthread_lock = threading.Lock()
        self.uthread_lock = threading.Lock()
        self.action_queue = []
        try:
            logopath = sys._MEIPASS + '/nwvlclog.png'
            if os.path.isfile(logopath):
                self.setWindowIcon(QtGui.QIcon(logopath))
            elif os.path.isfile('nwvlclog.png'):
                self.setWindowIcon(QtGui.QIcon('nwvlclog.png'))
        except:
            print("error looking for logo")
        self.setWindowTitle("NWVLC Player")

        # Create a basic vlc instance
        self.instance = vlc.Instance()

        self.media = None

        # Create an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()
        self.mediaplayer.video_set_mouse_input(False)
        self.mediaplayer.video_set_key_input(False)

        self.create_ui()
        self.is_paused = False

    def create_ui(self):
        """Set up the user interface, signals & slots
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)
        
        if self.media_name is None or self.uname is None:
            self.etextview = QtWidgets.QLabel()
            self.etextview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.etextview.setText("The fields media_name or uname not found in config.json\n" + \
                                   "please create one and try running. sample config.json\n\n" + \
                                   '{"url": "http://127.0.0.1:4270/poll_status",\n"media_name": "ex_media_name"\n,"uname": "user_name-123"\n,"nwpoll_interval_ms": 1000}')
            self.vboxlayout = QtWidgets.QVBoxLayout()
            self.vboxlayout.addWidget(self.etextview)
            self.widget.setLayout(self.vboxlayout)
            return
        conn_valid = False
        try:
            conn_valid = requests.post(self.url, data={}).status_code == 200
        except:
            conn_valid = False
        if not conn_valid:
            self.etextview = QtWidgets.QLabel()
            self.etextview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.etextview.setText("Cannot reach the URL " + self.url)
            self.vboxlayout = QtWidgets.QVBoxLayout()
            self.vboxlayout.addWidget(self.etextview)
            self.widget.setLayout(self.vboxlayout)
            return

        # In this widget, the video will be drawn
        if platform.system() == "Darwin": # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        else:
            self.videoframe = QtWidgets.QFrame()

        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)
        self.videoframe.mouseDoubleClickEvent = self.toggle_fscreen

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.positionslider.setStyleSheet("QScrollBar::handle:vertical {background: white;min-width: 0px;}")
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(2147483647)
        self.positionslider.sliderMoved.connect(self.set_position)
        self.positionslider.sliderPressed.connect(self.set_position)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.play_pause)

        self.stopbutton = QtWidgets.QPushButton("Stop")
        self.hbuttonbox.addWidget(self.stopbutton)
        self.stopbutton.clicked.connect(self.stop)
        
        self.hbuttonbox.addStretch(1)
        self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.hbuttonbox.addWidget(self.volumeslider)
        self.volumeslider.valueChanged.connect(self.set_volume)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.setContentsMargins(5, 5, 5, 5)
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)

        self.widget.setLayout(self.vboxlayout)

        menu_bar = self.menuBar()

        # Add menus
        file_menu = menu_bar.addMenu("File")
        self.aud_menu = menu_bar.addMenu("Audio")
        self.sub_menu = menu_bar.addMenu("Subtitles")
        
        self.aud_menu.menuAction().setVisible(False)
        self.sub_menu.menuAction().setVisible(False)

        # Add actions to file menu
        open_action = QtGui.QAction("Load Video", self)
        close_action = QtGui.QAction("Close App", self)
        file_menu.addAction(open_action)
        file_menu.addAction(close_action)

        open_action.triggered.connect(self.open_file)
        close_action.triggered.connect(sys.exit)

        self.u_timer = QtCore.QTimer(self)
        self.u_timer.setInterval(100)
        self.u_timer.timeout.connect(self.spawn_uui_thread)
        
        self.n_timer = QtCore.QTimer(self)
        self.n_timer.setInterval(self.nwpoll_interval_ms)
        self.n_timer.timeout.connect(self.spawn_nthread)

    def toggle_fscreen(self, args):
        if self.isFullScreen():
            self.vboxlayout.setContentsMargins(5, 5, 5, 5)
            self.showNormal()
            self.menuBar().show()
            self.positionslider.show()
            self.volumeslider.show()
            self.stopbutton.show()
            self.playbutton.show()
        else:
            self.menuBar().hide()
            self.positionslider.hide()
            self.volumeslider.hide()
            self.stopbutton.hide()
            self.playbutton.hide()
            self.vboxlayout.setContentsMargins(0, 0, 0, 0)
            self.showFullScreen()

    def play_pause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.is_paused = True
            self.action = 'pause'
        else:
            if self.media is None:
                self.open_file()
                return
            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.action = 'play'
            self.is_paused = False

    def stop(self):
        """Stop player
        """
        self.mediaplayer.stop()
        self.media = None
        self.aud_tracks = None
        self.sub_tracks = None
        self.aud_menu.menuAction().setVisible(False)
        self.sub_menu.menuAction().setVisible(False)
        self.should_stop_u = True
        self.action = 'stop'
        self.should_stop_n = True
        self.playbutton.setText("Play")

    def refresh_aud_sub_tracks(self):
        if self.media is None:
            return
        while (self.aud_tracks is None or self.sub_tracks is None):
            if self.mediaplayer.is_playing():
                # Add Sub track options
                if self.mediaplayer.video_get_spu_count() > 0 and self.sub_tracks is None:
                    self.sub_tracks = self.mediaplayer.video_get_spu_description()
                    selected_sub_track = self.mediaplayer.video_get_spu()
                    self.st_group = QtGui.QActionGroup(self);
                    self.sub_menu.clear()
                    for st in self.sub_tracks:
                        mitem = QtGui.QAction(st[1].decode("utf-8") , self.st_group)
                        mitem.setCheckable(True)
                        mitem.data = st
                        self.sub_menu.addAction(mitem)
                        if st[0] == selected_sub_track:
                            mitem.setChecked(True)
                        mitem.triggered.connect(self.set_sub_track)
                    self.sub_menu.menuAction().setVisible(True)
                # Add Audio track options
                if self.mediaplayer.audio_get_track_count() > 0 and self.aud_tracks is None:
                    self.aud_tracks = self.mediaplayer.audio_get_track_description()
                    selected_aud_track = self.mediaplayer.audio_get_track()
                    self.at_group = QtGui.QActionGroup(self);
                    self.aud_menu.clear()
                    for at in self.aud_tracks:
                        mitem = QtGui.QAction(at[1].decode("utf-8") , self.at_group)
                        mitem.setCheckable(True)
                        mitem.data = at
                        self.aud_menu.addAction(mitem)
                        if at[0] == selected_aud_track:
                            mitem.setChecked(True)
                        mitem.triggered.connect(self.set_aud_track)
                    self.aud_menu.menuAction().setVisible(True)
                # Add external subtitles
                load_subtitle_action = QtGui.QAction("Load Subtitle", self)
                self.sub_menu.addAction(load_subtitle_action)
                load_subtitle_action.triggered.connect(self.open_subtitle_file)

    def open_file(self):
        """Open a media file in a MediaPlayer
        """

        dialog_txt = "Choose Media File"
        filename = QtWidgets.QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'))
        if not filename or (filename is not None and not os.path.isfile(filename[0])):
            return

        # getOpenFileName returns a tuple, so use only the actual file name
        self.media = self.instance.media_new(filename[0])

        # Put the media in the media player
        self.mediaplayer.set_media(self.media)

        # Parse the metadata of the file
        self.media.parse()

        # Set the title of the track as window title
        self.setWindowTitle(self.media.get_meta(0))

        if platform.system() == "Linux": # for Linux using the X Server
            self.mediaplayer.set_xwindow(int(self.videoframe.winId()))
        elif platform.system() == "Windows": # for Windows
            self.mediaplayer.set_hwnd(int(self.videoframe.winId()))
        elif platform.system() == "Darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
        
        self.play_pause()
        
        self.aud_tracks = None
        self.sub_tracks = None
        
        self.refresh_aud_sub_tracks()
        
        if self.media_name is not None:
            self.update_status(name=self.media_name, action='none')
        else:
            self.update_status(name=self.media.get_meta(0), action='none')
        
        self.should_stop_u = False
        self.u_timer.start()
        
        self.playbutton.setEnabled(False)
        self.stopbutton.setEnabled(False)
        self.positionslider.setEnabled(False)
        
        self.should_stop_n = False
        self.n_timer.start()
        

    def set_volume(self, volume):
        """Set the volume
        """
        self.mediaplayer.audio_set_volume(volume)

    def set_position(self):
        """Set the movie position according to the position slider.
        """
        with self.uthread_lock:
            pos = self.positionslider.value()
            self.mediaplayer.set_position(pos / 2147483647)

    def set_sub_track(self):
        self.mediaplayer.video_set_spu(self.st_group.checkedAction().data[0])
        
    def set_aud_track(self):
        self.mediaplayer.audio_set_track(self.at_group.checkedAction().data[0])

    def spawn_uui_thread(self):
        uthread = threading.Thread(target=self.update_ui, daemon=True)
        uthread.start()
        if self.should_stop_u:
            self.u_timer.stop()

    def update_ui(self):
        """Updates the user interface"""
        with self.uthread_lock:
            media_pos = int(self.mediaplayer.get_position() * 2147483647)
            self.positionslider.setValue(media_pos)
            
        with self.nthread_lock:
            for ev in self.action_queue:
                self.execute_action(ev)
            self.action_queue = []
            
        with self.uthread_lock:
            if not self.mediaplayer.is_playing():
                if not self.is_paused:
                    self.stop()

    def open_subtitle_file(self):
        """
        Opens a file dialog box to choose srt file
        """
        dlg = QtWidgets.QFileDialog()
        dlg.setNameFilters(["Subtitle file (*.srt)"])
        filename=''
        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
        if not filename or (filename is not None and not os.path.isfile(filename)):
            return
        try:
            self.mediaplayer.add_slave(i_type=vlc.MediaSlaveType.subtitle, psz_uri=pathlib.Path(filename).as_uri(),
                                       b_select=True)
        except Exception as e:
            print(e)

        # TODO: refresh sub menu again after loading subs
            

def main():
    """Entry point for our simple vlc player
    """
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    apply_stylesheet(app, theme='dark_blue.xml')
    player.show()
    player.resize(960, 600)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()