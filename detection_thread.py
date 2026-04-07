# detection_thread.py
from cv2 import VideoCapture
import time
from numpy import ndarray, array, expand_dims, int64
from tensorflow import convert_to_tensor, float32

from PySide6.QtCore import QThread, Signal

from detection_utils import detect_fn, save_frame_and_send_mail, path_to_refresh_images
from object_detection.utils import visualization_utils as viz_utils

from pylogix import PLC

class DetectionThread(QThread):
    """Hilo que captura frames, corre inferencia, OCR, DB y emite la imagen procesada y la placa."""
    frame_ready = Signal(ndarray)  # Emite la imagen con detecciones (para mostrar en GUI)
    alarm_signal = Signal(bool)
    file_saved = Signal(str)

    def __init__(
            self,
            camera_index,
            detection_model,
            category_index,
            plc_ip= None,
            plc_tag= None,
            action_executed = False,
            last_detection_time = None,
            reset_wait_time = None,
            roi_norm= None,
            parent= None
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

        self.min_score_thresh = 0.2  # para visualizar y ejecutar acción de parar
        self._running = True

        self.cap = None

    def _apply_roi(self, frame_roi):
        """Recorta por ROI normalizada si existe."""
        if not self.roi_norm:
            return frame_roi

        h, w = frame_roi.shape[:2]
        x0n, y0n, x1n, y1n = self.roi_norm
        x0 = max(0, min(w - 1, int(x0n * w)))
        y0 = max(0, min(h - 1, int(y0n * h)))
        x1 = max(x0 + 1, min(w, int(x1n * w)))
        y1 = max(y0 + 1, min(h, int(y1n * h)))
        return frame_roi[y0:y1, x0:x1].copy()

    def run(self):
        self.cap = VideoCapture(self.camera_index)

        self.comm = PLC()
        self.comm.IPAddress = self.plc_ip
        self.comm.ProcessorSlot = 0

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            roi_frame = self._apply_roi(frame)
            image_np = array(roi_frame)

            # 1) Inferencia TF
            input_tensor = convert_to_tensor(expand_dims(image_np, 0), dtype=float32)
            detections = detect_fn(input_tensor, self.detection_model)
            num_detections = int(detections.pop('num_detections'))
            detections = {key: value[0, :num_detections].numpy()
                          for key, value in detections.items()}
            detections['num_detections'] = num_detections
            detections['detection_classes'] = detections['detection_classes'].astype(int64)

            # 2) Visualizar bounding boxes
            image_np_with_detections = image_np.copy()
            viz_utils.visualize_boxes_and_labels_on_image_array(
                image_np_with_detections,
                detections['detection_boxes'],
                detections['detection_classes'] + 1,  # label_id_offset
                detections['detection_scores'],
                self.category_index,
                use_normalized_coordinates=True,
                max_boxes_to_draw=1,
                min_score_thresh=self.min_score_thresh,
                agnostic_mode=False
            )

            # 3) PLC
            try:
                has_trash = (detections['detection_classes'][0] == 1) and (detections['detection_scores'][0] > 0.8)

                if has_trash:
                    if self.action_executed:
                        elapsed_time = time.time() - self.last_detection_time

                        if elapsed_time > self.reset_wait_time:
                            self.action_executed = False

                    else:

                        #turn_off = self.comm.Write(self.plc_tag, 1)
                        time.sleep(1.5)
                        #turn_on = self.comm.Write(self.plc_tag, 0)

                        save_frame_and_send_mail(frame_bgr=image_np_with_detections, out_dir='D:/CarpetaProyecto/Resultados/', camera_tag=self.plc_tag)

                        # Marcar la acción como ejecutada
                        self.action_executed = True
                        self.last_detection_time = time.time()

                        self.file_saved.emit(path_to_refresh_images())
                else:
                    pass

                self.alarm_signal.emit(has_trash)

            except Exception as e:
                print("Error", e)

            finally:
                # 4) Emitir la imagen procesada
                self.frame_ready.emit(image_np_with_detections)

        self.cap.release()
        self.comm.Close()

    def stop(self):
        """Detiene el hilo."""
        self._running = False