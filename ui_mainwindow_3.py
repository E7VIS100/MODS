# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_mainwindowCkgCKr.ui'
##
## Created by: Qt User Interface Compiler version 6.4.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QLayout,
    QListView, QMainWindow, QSizePolicy, QWidget)
import Molienda_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1395, 600)
        MainWindow.setMinimumSize(QSize(1200, 600))
        MainWindow.setMaximumSize(QSize(16777215, 16777215))
        MainWindow.setSizeIncrement(QSize(0, 0))
        MainWindow.setStyleSheet(u"background-color: rgb(232, 232, 232);")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setStyleSheet(u"")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SetNoConstraint)
        self.gridLayout.setHorizontalSpacing(400)
        self.gridLayout.setVerticalSpacing(30)
        self.gridLayout.setContentsMargins(80, 50, 100, 60)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(0, 400))
        self.label.setStyleSheet(u"border-image: url(:/prefijoNuevo/cameraoffline.jpg);")

        self.gridLayout.addWidget(self.label, 0, 1, 1, 1)

        self.listView = QListView(self.centralwidget)
        self.listView.setObjectName(u"listView")
        self.listView.setMaximumSize(QSize(16777215, 200))
        self.listView.setStyleSheet(u"background-color: rgb(227, 227, 227);")

        self.gridLayout.addWidget(self.listView, 1, 1, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText("")
    # retranslateUi

