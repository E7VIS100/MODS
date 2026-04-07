# detection_utils.py
import os
from datetime import datetime
import cv2
import yagmail
from tensorflow import function
from tensorflow.compat.v2.train import Checkpoint
from object_detection.utils import config_util
from object_detection.builders import model_builder
from pylogix import PLC

def check_plc_and_tag(plc_ip: str, plc_tag: str, slot: int = 0, timeout_ms: int = 2000):
    try:
        with PLC() as comm:
            comm.IPAddress = plc_ip
            comm.ProcessorSlot = slot

            try:
                comm.Timeout = timeout_ms
            except Exception:
                pass

            res = comm.Read(plc_tag)

            if hasattr(res, "Status") and str(res.Status) == "Success":
                return True, None
            return False, f"Read falló: Status={getattr(res, 'Status', 'desconocido')}"
    except Exception as e:
        return False, f"Excepción: {e}"

def load_model(config_path, checkpoint_path):
    configs = config_util.get_configs_from_pipeline_file(config_path)
    detection_model = model_builder.build(model_config=configs['model'], is_training=False)
    ckpt = Checkpoint(model=detection_model)
    ckpt.restore(checkpoint_path).expect_partial()
    return detection_model

@function
def detect_fn(image, detection_model):
    image, shapes = detection_model.preprocess(image)
    prediction_dict = detection_model.predict(image, shapes)
    detections = detection_model.postprocess(prediction_dict, shapes)
    return detections

def save_frame_and_send_mail(frame_bgr, out_dir, camera_tag):
    timestamp = datetime.now().strftime("%d-%m-%Y  %H-%M-%S")
    filename = f"{timestamp}  {camera_tag}.jpg"
    path = os.path.join(out_dir, filename)
    cv2.imwrite(path, frame_bgr)

    """yag = yagmail.SMTP('fotosmet825@gmail.com', 'jxwz lfzl bmuz zvrz')
    yag.send(
        to=['esancan@unsa.edu.pe', 'elvissn79@gmail.com'],
        subject='MODS: SYSTEM DETECTION',
        contents=[
            "<h3>Hola!</h3><p>Detección hecha:</p>",
            yagmail.inline(path),
            "<p>Saludos"
        ]
    )"""

def path_to_refresh_images():
    return 'D:/CarpetaProyecto/Resultados/'                                                                             #'C:/D/Resultados/'
