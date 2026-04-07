# main_window.py
from cv2 import cvtColor, COLOR_BGR2RGB
from numpy import ndarray

import os
from pathlib import Path

from PySide6.QtWidgets import QMainWindow,QApplication
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Slot, QTimer, QStringListModel                                                                                 #""" Aqui nuevo """

from ui_mainwindow_3 import Ui_MainWindow  # <-- Tu archivo .py generado por pyside6-uic
from detection_thread import DetectionThread

from alarm_manager import AlarmManager                                                                                  #""" Aqui nuevo """

class MainWindow(QMainWindow):
    def __init__(
        self,
        detection_model,
        category_index,
        camera_index1= "rtsp://Prueba:Sistemas10$@192.168.11.189:554/stream2",
        camera_index2=0,
        roi_norm=None,
    ):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Ajustar los QLabel para escalar la imagen
        self.ui.label.setScaledContents(True)
        #self.ui.label_2.setScaledContents(True)

        # Guardamos refs a BD y modelo, etc.
        self.detection_model = detection_model
        self.category_index = category_index

        # ----- ESTADO DE ALARMA Y PARPADEO -----                                                                       """ Aqui nuevo """
        self.alarm_on = False  # ¿hay detección de basura en este momento?
        self.blink_state = False  # estado actual del parpadeo
        self.base_stylesheet = self.styleSheet()  # estilo original (con imagen de fondo)

        # Timer para hacer parpadear toda la ventana
        self.alarm_timer = QTimer(self)
        self.alarm_timer.setInterval(100)  # ms, puedes ajustar
        self.alarm_timer.timeout.connect(self._blink_alarm)

        self.alarm_on = True
        self.blink_state = False
        self.alarm_timer.start()

        # Sonido                                                                                                        """ Aqui nuevo """
        self.alarm_manager = AlarmManager(
            parent=self,
            sound_path="D:/PythonFiles/Anomaly.wav",  # ruta de sonido                                                  C:/D/PythonFiles/Anomaly.wav
            volume=0.1
        )

        # ListView

        self.results_dir = Path('D:/CarpetaProyecto/Resultados/')                                                       #C:/D/Resultados/
        self.files_model = QStringListModel(self)
        self.ui.listView.setModel(self.files_model)

            #Carga inicial
        self.refresh_results_list()

            #abrir al click
        self.ui.listView.clicked.connect(self.open_selected_file)

        # Creamos 2 hilos de detección, cada uno para una cámara distinta
        self.detection_thread1 = DetectionThread(
            camera_index=camera_index1,
            detection_model=self.detection_model,
            category_index=self.category_index,
            plc_ip = '10.60.1.2',                                                                                       #plc_ip = '127.0.0.1',
            plc_tag= 'CAMARA_FAJA_N15',                                                                                 #plc_tag='CAMARA_15',
            reset_wait_time= 30,
            roi_norm=roi_norm,
        )

        """self.detection_thread2 = DetectionThread(
            camera_index=camera_index2,
            detection_model=self.detection_model,
            category_index=self.category_index,
            plc_ip = '127.0.0.1',
            plc_tag= 'CAMARA_16',
            reset_wait_time= 30,
            roi_norm=roi_norm,
        )"""

        # Conectamos las señales frame_ready de cada hilo al slot correspondiente
        self.detection_thread1.frame_ready.connect(self.update_label_cam1)
        #self.detection_thread2.frame_ready.connect(self.update_label_cam2)
        self.detection_thread1.alarm_signal.connect(self.on_alarm_signal)                                               #""" Aqui nuevo """

        #Refrescar listView
        self.detection_thread1.file_saved.connect(self.on_file_saved)

        # Iniciar hilos
        self.detection_thread1.start()
        #self.detection_thread2.start()

    #ListView helpers

    def refresh_results_list(self):
        if not self.results_dir.exists():
            self.files_model.setStringList([])
            return

        files = sorted(
            [p.name for p in self.results_dir.iterdir() if p.is_file()],
            reverse=True
        )
        self.files_model.setStringList(files)

    @Slot(str)
    def on_file_saved(self, saved_path: str):
        # Cada vez que el hilo guarda una foto, refrescamos la lista
        self.refresh_results_list()

    @Slot()
    def open_selected_file(self, index):
        filename = self.files_model.data(index)
        if not filename:
            return
        fullpath = str(self.results_dir / filename)
        if os.path.exists(fullpath):
            os.startfile(fullpath)

    # Camara 1
    @Slot(ndarray)
    def update_label_cam1(self, frame):
        # Convertir BGR->RGB
        rgb_frame = cvtColor(frame, COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.ui.label.setPixmap(pixmap)

    """@Slot(ndarray)
    def update_label_cam2(self, frame):
        # Convertir BGR->RGB
        rgb_frame = cvtColor(frame, COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.ui.label_2.setPixmap(pixmap)"""


    ####################################################################################################################""" Aqui nuevo """
    @Slot(bool)
    def on_alarm_signal(self, has_trash: bool):

        # 1) Sonido con flanco de subida
        self.alarm_manager.handle_alarm_state(has_trash)

        if has_trash:
            if not self.alarm_on:
                self.alarm_on = True
                self.blink_state = False
                self.alarm_timer.start()
                # Hace "flash" en el icono de la barra de tareas (Windows)
                QApplication.alert(self)
        else:
            # Cuando deja de haber basura, apagamos la alarma visual
            if self.alarm_on:
                self.alarm_on = False
                self.alarm_timer.stop()
                self.blink_state = False
                self.setWindowTitle("MODS - Monitoreo Faja")
                # Volver al estilo original (imagen de fondo)
                self.setStyleSheet(self.base_stylesheet)

    def _blink_alarm(self):

        if not self.alarm_on:
            return

        self.blink_state = not self.blink_state

        if self.blink_state:
            # Estado ON de alarma: superponer fondo rojo translúcido
            # Mantenemos el estilo base y añadimos color de fondo a QMainWindow
            self.setWindowTitle("⚠ BASURA DETECTADA ⚠")
            self.setStyleSheet("QMainWindow { background-color: rgba(230, 60, 70, 180); }")
            #self.setStyleSheet(self.base_stylesheet + "\nQMainWindow { background-color: rgba(255, 0, 0, 120); }")
           # self.ui.label.setStyleSheet("border: 4px solid red;")

        else:
            # Estado OFF de parpadeo: solo el estilo original
            self.setWindowTitle("MODS - Monitoreo Faja")
            self.setStyleSheet(self.base_stylesheet)

        ################################################################################################################


    def closeEvent(self, event):
        # Detener hilos
        self.detection_thread1.stop()
        #self.detection_thread2.stop()
        self.detection_thread1.wait()
        #self.detection_thread2.wait()

        # Desconectar DB
        super().closeEvent(event)