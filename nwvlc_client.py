import platform
import os
import sys

from PyQt5 import QtWidgets, QtGui, QtCore
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
        self.last_action = None
        self.should_stop = False

   

class Player(QtWidgets.QMainWindow):
    """A simple Media Player using VLC and Qt
    """
    
    def send_status(self):
        if self.media_name is not None:
            #print({'media_name': self.media_name, 'current_ts': self.current_media_ts, 'current_status': self.current_media_status, 'action': self.last_action})
            try:
                res = requests.post(self.url,
                                    json={'media_name': self.media_name,
                                          'current_ts': self.current_media_ts,
                                          'current_status': self.current_media_status,
                                          'action': self.last_action,
                                          'user': self.uname})
                sdata = res.json()
                if 'last_action' in sdata:
                    if sdata['last_action'] == 'play':
                        if not self.mediaplayer.is_playing():
                            self.positionslider.setValue(sdata['current_ts'])
                            self.set_position()
                            self.play_pause()
                    if sdata['last_action'] == 'pause':
                        if self.mediaplayer.is_playing():
                            self.play_pause()
                            self.positionslider.setValue(sdata['current_ts'])
                            self.set_position()
            except:
                print("Error sending status")
        if self.last_action is not None:
            self.last_action = None
            
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
    
    def update_status(self, name=None, ts=None, action=None):
        if name is not None:
            self.media_name = name
        if ts is not None:
            self.current_media_ts = ts
        if action is not None:
            self.last_action = action

    def set_mname(self):
        self.media_name = self.mname_box.text()
    
    def set_uname(self):
        self.uname = self.uname_box.text()

    def __init__(self, master=None, url="http://127.0.0.1:4270/poll_status"):
        QtWidgets.QMainWindow.__init__(self, master)
        self.url = url
        self.media_name = None
        self.username = None
        self.current_media_ts = None
        self.current_media_status = None
        self.last_action = None
        self.should_stop = False
        
        self.nthread = None
        self.setWindowTitle("Media Player")

        # Create a basic vlc instance
        self.instance = vlc.Instance()

        self.media = None

        # Create an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

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
        
        self.hnamebox = QtWidgets.QHBoxLayout()
        self.mname_box = QtWidgets.QLineEdit("media name")
        self.hnamebox.addWidget(self.mname_box)
        
        self.mnamebutton = QtWidgets.QPushButton("udpate mname")
        self.hnamebox.addWidget(self.mnamebutton)
        self.mnamebutton.clicked.connect(self.set_mname)
        
        self.uname_box = QtWidgets.QLineEdit("username")
        self.hnamebox.addWidget(self.uname_box)
        
        self.unamebutton = QtWidgets.QPushButton("udpate uname")
        self.hnamebox.addWidget(self.unamebutton)
        self.unamebutton.clicked.connect(self.set_uname)

        self.hbuttonbox.addStretch(1)
        self.hnamebox.addStretch(1)
        self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.hbuttonbox.addWidget(self.volumeslider)
        self.volumeslider.valueChanged.connect(self.set_volume)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)
        self.vboxlayout.addLayout(self.hnamebox)

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

    def play_pause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.is_paused = True
            self.last_action = 'pause'
            self.current_media_ts = self.positionslider.value()
            self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return

            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.last_action = 'play'
            self.current_media_ts = self.positionslider.value()
            self.timer.start()
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
        if not filename:
            return

        # getOpenFileName returns a tuple, so use only the actual file name
        self.media = self.instance.media_new(filename[0])

        # Put the media in the media player
        self.mediaplayer.set_media(self.media)

        # Parse the metadata of the file
        self.media.parse()

        # Set the title of the track as window title
        self.setWindowTitle(self.media.get_meta(0))

        # The media player has to be 'connected' to the QFrame (otherwise the
        # video would be displayed in it's own window). This is platform
        # specific, so we must give the ID of the QFrame (or similar object) to
        # vlc. Different platforms have different functions for this
        if platform.system() == "Linux": # for Linux using the X Server
            self.mediaplayer.set_xwindow(int(self.videoframe.winId()))
        elif platform.system() == "Windows": # for Windows
            self.mediaplayer.set_hwnd(int(self.videoframe.winId()))
        elif platform.system() == "Darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
        
        self.play_pause()
        
        if self.media_name is not None:
            self.update_status(name=self.media_name, ts=0, action='play')
        else:
            self.update_status(name=self.media.get_meta(0), ts=0, action='play')
        
        self.nthread = threading.Thread(target=self.schedule_pings, kwargs={'interval_ms': 200}, daemon=True)
        self.nthread.start()

    def set_volume(self, volume):
        """Set the volume
        """
        self.mediaplayer.audio_set_volume(volume)

    def set_position(self):
        """Set the movie position according to the position slider.
        """

        # The vlc MediaPlayer needs a float value between 0 and 1, Qt uses
        # integer variables, so you need a factor; the higher the factor, the
        # more precise are the results (1000 should suffice).

        # Set the media position to where the slider was dragged
        self.timer.stop()
        pos = self.positionslider.value()
        #print(pos)
        self.mediaplayer.set_position(pos / 2147483647)
        self.timer.start()

    def update_ui(self):
        """Updates the user interface"""

        # Set the slider's position to its corresponding media position
        # Note that the setValue function only takes values of type int,
        # so we must first convert the corresponding media position.
        media_pos = int(self.mediaplayer.get_position() * 2147483647)
        self.positionslider.setValue(media_pos)

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()

            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.stop()

def main():
    """Entry point for our simple vlc player
    """
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    player.show()
    player.resize(640, 480)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()