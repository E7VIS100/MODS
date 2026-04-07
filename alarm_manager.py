# alarm_manager.py
from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect


class AlarmManager(QObject):

    def __init__(self, parent=None, sound_path="D:/PythonFiles/Anomaly.wav", volume=0.7):
        super().__init__(parent)
        self._prev_has_trash = False

        self.sound = QSoundEffect(self)
        self.sound.setSource(QUrl.fromLocalFile(sound_path))
        self.sound.setVolume(volume)  # 0.0 a 1.0
        self.sound.setLoopCount(1)    # una sola vez por evento

    def handle_alarm_state(self, has_trash: bool):

        if has_trash and not self._prev_has_trash:
            self.sound.play()

        self._prev_has_trash = has_trash
