import platform
import os
import sys
import json

from PyQt5 import QtWidgets, QtGui, QtCore
#from PySide6 import QtWidgets, QtGui, QtCore
from qt_material import apply_stylesheet
import vlc
import requests
import threading
from datetime import datetime, time, timedelta
import pause

class NWSyncer:
    def __init__(self, url="http://127.0.0.1:4270/poll_status"):
        self.url = url
        self.media_name = None
        self.current_media_ts = None
        self.current_media_status = None
        self.action = None
        self.should_stop = False

   

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
                print({'media_name': self.media_name,'current_ts': self.positionslider.value(),'action': self.action,'user': self.uname})
                print(res.json())
                self.action_queue += [res.json()]
        if self.action is not None:
            self.action = None
            
    def schedule_pings(self, interval_ms=200):
        clock_start = datetime.now()
        tdelta = timedelta(seconds=int(interval_ms/1000),milliseconds=interval_ms%1000)
        wait_until = clock_start + tdelta
        while not self.should_stop:
            if wait_until < datetime.now():  
                diff = (datetime.now() - wait_until)
                diff = int(int(diff.total_seconds()*1000)/interval_ms) + 1
                wait_until += diff*tdelta
            pause.until(wait_until)
            self.send_status()
    
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
                print("signal recieved to play at: " + str(sdata['current_ts']))
                self.positionslider.setValue(sdata['current_ts'])
                self.set_position()
                if not self.mediaplayer.is_playing():   
                    self.play_pause()
                    self.action = None
            if sdata['action'] == 'pause':
                print("signal recieved to pause at: " + str(sdata['current_ts']))
                if self.mediaplayer.is_playing():
                    self.play_pause()    
                    self.action = None
                self.positionslider.setValue(sdata['current_ts'])
                self.set_position()
            if sdata['action'] == 'seek':
                print("signal recieved to seek at: " + str(sdata['current_ts']))
                self.positionslider.setValue(sdata['current_ts'])
                self.set_position()

    def __init__(self, master=None, url="http://127.0.0.1:4270/poll_status"):
        QtWidgets.QMainWindow.__init__(self, master)
        if (os.path.isfile("config.json")):
            with open('config.json') as fr:
                cjdata = json.load(fr)
            if 'url' in cjdata:
                self.url = cjdata['url']
            if 'media_name' in cjdata:
                self.media_name = cjdata['media_name']
            if 'uname' in cjdata:
                self.uname = cjdata['uname']
        else:
            self.url = url
            self.media_name = None
            self.uname = None
        self.action = None
        self.should_stop = False
        
        self.nthread = None
        self.nthread_lock = threading.Lock()
        self.action_queue = []
        self.setWindowTitle("Media Player")

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

        # In this widget, the video will be drawn
        if platform.system() == "Darwin": # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        else:
            self.videoframe = QtWidgets.QFrame()

        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)
        self.videoframe.mouseDoubleClickEvent = self.toggle_fscreen

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
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
        #self.hnamebox.addStretch(1)
        self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
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
        #self.vboxlayout.addLayout(self.hnamebox)

        self.widget.setLayout(self.vboxlayout)

        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Add actions to file menu
        open_action = QtWidgets.QAction("Load Video", self)
        close_action = QtWidgets.QAction("Close App", self)
        file_menu.addAction(open_action)
        file_menu.addAction(close_action)

        open_action.triggered.connect(self.open_file)
        close_action.triggered.connect(sys.exit)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()

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
            #self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return

            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.action = 'play'
            #self.timer.start()
            self.is_paused = False

    def stop(self):
        """Stop player
        """
        self.mediaplayer.stop()
        self.should_stop = True
        self.nthread.join()
        self.playbutton.setText("Play")

    def open_file(self):
        """Open a media file in a MediaPlayer
        """

        dialog_txt = "Choose Media File"
        filename = QtWidgets.QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'))
        if not filename or not os.path.isfile(filename):
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
        
        if self.media_name is not None:
            self.update_status(name=self.media_name, action='none')
        else:
            self.update_status(name=self.media.get_meta(0), action='none')
            
        self.playbutton.setEnabled(False)
        self.stopbutton.setEnabled(False)
        self.positionslider.setEnabled(False)
        
        self.nthread = threading.Thread(target=self.schedule_pings, kwargs={'interval_ms': 1000}, daemon=True)
        self.nthread.start()

    def set_volume(self, volume):
        """Set the volume
        """
        self.mediaplayer.audio_set_volume(volume)

    def set_position(self):
        """Set the movie position according to the position slider.
        """
        #self.timer.stop()
        pos = self.positionslider.value()
        self.mediaplayer.set_position(pos / 2147483647)
        #self.timer.start()

    def update_ui(self):
        """Updates the user interface"""
        media_pos = int(self.mediaplayer.get_position() * 2147483647)
        self.positionslider.setValue(media_pos)
        
        with self.nthread_lock:
            for ev in self.action_queue:
                self.execute_action(ev)
            self.action_queue = []
        # No need to call this function if nothing is played
        #if not self.mediaplayer.is_playing():
            #self.timer.stop()
            #if not self.is_paused:
                #self.stop()

def main():
    """Entry point for our simple vlc player
    """
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    apply_stylesheet(app, theme='dark_teal.xml')
    player.show()
    #player.videoframe.show()
    player.resize(960, 600)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()