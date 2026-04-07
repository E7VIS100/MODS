# main.py
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from object_detection.utils import label_map_util

from detection_utils import load_model, check_plc_and_tag
from main_window import MainWindow

def preflight_plc(checks):

    errors = []
    for i, chk in enumerate(checks, 1):
        ok, err = check_plc_and_tag(chk["ip"], chk["tag"], slot=chk.get("slot", 0))
        if not ok:
            errors.append(f"[{i}] IP={chk['ip']} TAG={chk['tag']} -> {err}")
    if errors:
        QMessageBox.critical(None, "PLC/Tag no disponible",
                             "No se pudo verificar PLC/Tag:\n\n" + "\n".join(errors))
        sys.exit(1)

def main():
    # Rutas de tu modelo
    CONFIG_PATH = r"D:/PythonFiles/SSD_MobilNet_Doble/pipeline.config"                                                  #r"C:/D/PythonFiles/SSD_MobilNet_Doble/pipeline.config"
    CHECKPOINT_PATH = r"D:/PythonFiles/SSD_MobilNet_Doble/ckpt-8"                                                       #r"C:/D/PythonFiles/SSD_MobilNet_Doble/ckpt-8"
    LABEL_MAP = r"D:/PythonFiles/label_map_Doble.pbtxt"                                                                 #r"C:/D/PythonFiles/label_map_Doble.pbtxt"

    # Iniciamos la app
    app = QApplication(sys.argv)

    # Comprobando estado del PLC
    preflight_plc([
        {"ip": "10.60.1.2", "tag": "CAMARA_FAJA_N15", "slot": 0},
        #{"ip": "127.0.0.1", "tag": "CAMARA_15", "slot": 0}
        #{"ip": "127.0.0.1", "tag": "CAMARA_16", "slot": 0},
    ])

    # Cargar modelo
    detection_model = load_model(CONFIG_PATH, CHECKPOINT_PATH)
    category_index = label_map_util.create_category_index_from_labelmap(LABEL_MAP)

    # Recorte de Imagen
    # ROI_NORM = (Inicio_x, Inicio_y, Fin_x, Fin_y)
    ROI_NORM = (0.2, 0, 0.95, 1)

    # Crear la ventana principal
    window = MainWindow(
        detection_model=detection_model,
        category_index=category_index,
        roi_norm=ROI_NORM
    )
    window.show()

    # Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
