for i in range(1):
    print(i)


"""import torch

print("Number of GPU: ", torch.cuda.device_count())
print("GPU Name: ", torch.cuda.get_device_name())
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('Using device:', device)
"""

"""from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '127.0.0.1'
    comm.ProcessorSlot = 0
    tag = "CAMARA_15"  # Nombre del tag en el P
    resultado = comm.Read(tag)
    print(resultado)"""

"""with PLC() as comm:
    comm.IPAddress = '127.0.0.1'
    comm.ProcessorSlot = 0
    tag = "Prueba"  # Nombre del tag en el P
    valor_a_escribir = 0
    resultado = comm.Write(tag, valor_a_escribir)
    print(resultado)
"""

"""import yagmail

yag = yagmail.SMTP("fotosmet825@gmail.com", "jxwz lfzl bmuz zvrz")
destinatarios = ['esancan@unsa.edu.pe', 'elvissn79@gmail.com']
yag.send(
    to=destinatarios,
    subject="Prueba inline con yagmail 📸",
    contents=[
        "<h3>Hola!</h3>",
        "Aquí tienes una imagen dentro del mensaje:",
        "Saludos 👋"
    ]
)

print("Correo con imagen inline enviado ✅")"""

"""import os

print(os.listdir("C:/D/MoliendaBateas/SSD_MobilNet_Doble/"))"""


"""
# detection_thread.py
import time
from collections import deque

import cv2
import numpy as np
from cv2 import VideoCapture
from numpy import ndarray, array, expand_dims, int64
from tensorflow import convert_to_tensor, float32

from PySide6.QtCore import QThread, Signal

from detection_utils import detect_fn, save_frame_and_send_mail
from object_detection.utils import visualization_utils as viz_utils

from pylogix import PLC


class DetectionThread(QThread):

    # Hilo que captura frames, corre inferencia, filtra frames glitcheados
    # y acciona el PLC cuando detecta basura (Advertencia) de forma consistente.

    frame_ready = Signal(ndarray)
    alarm_signal = Signal(bool)   # <--- NUEVO: True si hay basura en este frame

    def __init__(
            self,
            camera_index,
            detection_model,
            category_index,
            plc_ip=None,
            plc_tag=None,
            action_executed=False,
            last_detection_time=None,
            reset_wait_time=30,     # segs para volver a permitir una nueva parada
            roi_norm=None,
            parent=None,
            # IMPORTANTE: en tu modelo, clase=1 => "ANOMALY_DETECTION"
            trash_classes=(1,),     # IDs de clases del MODELO que representan basura
            score_thresh_plc=0.65,  # umbral de score para ACCIONAR PLC
            min_positive_frames=3,  # nº mínimo de frames positivos recientes
            history_len=5           # ventana de historial para el filtro temporal
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self.detection_model = detection_model
        self.category_index = category_index
        self.plc_ip = plc_ip
        self.plc_tag = plc_tag
        self.action_executed = action_executed
        self.last_detection_time = last_detection_time
        self.reset_wait_time = reset_wait_time
        self.roi_norm = roi_norm

        # Umbral de score solo para DIBUJAR
        self.min_score_thresh = 0.4

        self._running = True
        self.cap = None

        # Para filtrar frames glitcheados (comparación con último bueno)
        self.last_good_frame = None
        self.last_good_gray = None

        # Parámetros de detección de basura
        self.trash_classes = set(int(c) for c in trash_classes)
        self.score_thresh_plc = score_thresh_plc

        # Filtro temporal de detecciones
        self.detection_history = deque(maxlen=history_len)
        self.min_positive_frames = min_positive_frames

    # -------------------- ROI --------------------
    def _apply_roi(self, frame_roi: np.ndarray) -> np.ndarray:
        if not self.roi_norm:
            return frame_roi

        h, w = frame_roi.shape[:2]
        x0n, y0n, x1n, y1n = self.roi_norm
        x0 = max(0, min(w - 1, int(x0n * w)))
        y0 = max(0, min(h - 1, int(y0n * h)))
        x1 = max(x0 + 1, min(w, int(x1n * w)))
        y1 = max(y0 + 1, min(h, int(y1n * h)))
        return frame_roi[y0:y1, x0:x1].copy()

    # -------------------- Filtro de frames glitcheados --------------------
    def _is_frame_glitched(self, frame: np.ndarray) -> bool:

        #Devuelve True si el frame parece roto comparado con el último bueno:
        #cambio brutal de intensidades en gran parte de la imagen.

        if self.last_good_gray is None:
            return False  # aún no hay referencia

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        except Exception:
            return True

        if gray.shape != self.last_good_gray.shape:
            return True

        # Diferencia absoluta
        diff = cv2.absdiff(gray, self.last_good_gray)

        # Sólo cambios fuertes
        _, diff_bin = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        change_ratio = diff_bin.mean() / 255.0

        # Si más del 60% del frame cambió violentamente, asumimos glitch
        if change_ratio > 0.6:
            print(f"[WARN] Frame glitcheado descartado (change_ratio={change_ratio:.2f})")
            return True

        return False

    # -------------------- Lógica de detección de basura --------------------
    def _has_trash_detection(self, detections) -> bool:

        #Revisa las detecciones y devuelve True si hay basura con:
        #- clase en trash_classes
        #- score >= score_thresh_plc
        #(sin filtro por área de bbox, por ahora)

        classes = detections['detection_classes']      # array 1D: [0, 1, 0, ...]
        scores = detections['detection_scores']        # array 1D: [0.9, 0.3, ...]
        num = detections['num_detections']             # nº de detecciones válidas

        # DEBUG opcional:
        # print(f"\n[DEBUG] num_detections = {num}")
        # print("classes:", classes[:num])
        # print("scores:", scores[:num])

        for i in range(num):
            cls = int(classes[i])       # 0 = NORMAL_OP, 1 = ANOMALY_DETECTION
            score = float(scores[i])

            if cls not in self.trash_classes:
                continue
            if score < self.score_thresh_plc:
                continue

            # Detección convincente de basura (por clase + score)
            print(f"[INFO] Frame con basura: cls={cls}, score={score:.2f}")
            return True

        return False

    # -------------------- PLC --------------------
    def _try_trigger_plc(self, image_np_with_detections: np.ndarray) -> None:

        #Usa el historial de detecciones para decidir si acciona el PLC.

        # Cooldown: si ya se ejecutó acción, esperar reset_wait_time
        if self.action_executed:
            elapsed_time = time.time() - self.last_detection_time
            if elapsed_time > self.reset_wait_time:
                self.action_executed = False
                self.detection_history.clear()
            else:
                return  # aún dentro del tiempo de espera

        positives = sum(self.detection_history)
        if positives < self.min_positive_frames:
            return

        try:
            print("[INFO] Basura confirmada. Enviando señal al PLC...")
            # DESCOMENTA ESTO CUANDO YA QUIERAS ACCIONAR REALMENTE EL PLC
            # self.comm.Write(self.plc_tag, 1)
            time.sleep(0.5)
            # self.comm.Write(self.plc_tag, 0)

            save_frame_and_send_mail(
                frame_bgr=image_np_with_detections,
                out_dir='C:/D/Resultados/',
                camera_tag=self.plc_tag
            )

            self.action_executed = True
            self.last_detection_time = time.time()

        except Exception as e:
            print("Error al accionar PLC:", e)

    # -------------------- Bucle principal --------------------
    def run(self) -> None:
        self.cap = VideoCapture(self.camera_index)

        self.comm = PLC()
        self.comm.IPAddress = self.plc_ip
        self.comm.ProcessorSlot = 0

        while self._running:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                time.sleep(0.01)
                continue

            # 1) Filtro de frames glitcheados
            if self._is_frame_glitched(frame):
                if self.last_good_frame is not None:
                    self.frame_ready.emit(self.last_good_frame)
                time.sleep(0.01)
                # informamos que NO hay basura en este frame glitcheado
                self.alarm_signal.emit(False)
                continue

            # Actualizar referencia de frame "bueno"
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            except Exception:
                time.sleep(0.01)
                continue

            self.last_good_frame = frame.copy()
            self.last_good_gray = gray.copy()

            # 2) ROI
            roi_frame = self._apply_roi(frame)
            image_np = array(roi_frame)

            # 3) Inferencia TF
            input_tensor = convert_to_tensor(expand_dims(image_np, 0), dtype=float32)
            detections = detect_fn(input_tensor, self.detection_model)

            num_detections = int(detections.pop('num_detections'))
            detections = {
                key: value[0, :num_detections].numpy()
                for key, value in detections.items()
            }
            detections['num_detections'] = num_detections
            detections['detection_classes'] = detections['detection_classes'].astype(int64)

            # 4) Visualizar bounding boxes
            image_np_with_detections = image_np.copy()
            viz_utils.visualize_boxes_and_labels_on_image_array(
                image_np_with_detections,
                detections['detection_boxes'],
                detections['detection_classes'] + 1,   # offset para label_map (1-based)
                detections['detection_scores'],
                self.category_index,
                use_normalized_coordinates=True,
                max_boxes_to_draw=1,
                min_score_thresh=self.min_score_thresh,
                agnostic_mode=False
            )

            # 5) Actualizar historial de detecciones de basura
            has_trash = self._has_trash_detection(detections)
            self.detection_history.append(int(has_trash))

            # 🔔 Enviar estado de alarma a la GUI
            self.alarm_signal.emit(has_trash)

            # 6) Intentar accionar PLC según historial
            if has_trash:
                self._try_trigger_plc(image_np_with_detections)

            # 7) Enviar frame a la GUI
            self.frame_ready.emit(image_np_with_detections)

        self.cap.release()
        self.comm.Close()

    def stop(self) -> None:
        Detiene el hilo.
        self._running = False
"""