from enum import Enum, auto
import os
import sys
import uuid
import zipfile
from time import sleep

import numpy as np
import qrcode
import skimage as ski
from gpiozero import LED, Button
from libcamera import controls, Transform
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QRunnable, QThread, QThreadPool, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow, QStackedWidget,
                             QVBoxLayout, QWidget)

import filters
from applyFilters import apply_random_filters


class App:

    TEMP_DIR = "/tmp/schnappischuss/"

    def runGUI(self):
        app = QApplication(sys.argv)
        window = SchnappiWindow(self.camera)
        window.show()
        self.camera.startFeed()
        app.exec_()

    def __init__(self) -> None:

        self.camera = SchnappiCamera()

        self.runGUI()


class SchnappiFilterApplier(QRunnable):
    def __init__(self, image, image_counter):
        super().__init__()
        self.image = image
        self.image_counter = image_counter

    def run(self):
        filtered_image = apply_random_filters(self.image)
        ski.io.imsave(
            "/tmp/schnappischuss/{}.jpg".format(self.image_counter), filtered_image
        )


class SchnappiCaptureWorker(QThread):
    imagesServed = pyqtSignal()

    def __init__(self, camera, doCapture, *, parent=None):
        super().__init__(parent)
        self.camera = camera
        doCapture.connect(self.captureImage)
        self.camera.captureDone.connect(self.filterAndServeImages)

    def applyFilters(self):
        try:
            os.mkdir(App.TEMP_DIR)
        except FileExistsError:
            pass

        image = ski.io.imread("/tmp/schnappischuss.jpg")
        QThreadPool.globalInstance().start(SchnappiFilterApplier(image, 1))
        QThreadPool.globalInstance().start(SchnappiFilterApplier(image, 2))
        QThreadPool.globalInstance().start(SchnappiFilterApplier(image, 3))
        QThreadPool.globalInstance().start(SchnappiFilterApplier(image, 4))

        QThreadPool.globalInstance().waitForDone(-1)

    def captureImage(self):
        self.camera.captureImage()

    def filterAndServeImages(self):
        self.applyFilters()
        self.serveImages()

    def run(self):
        self.exec_()

    def serveImages(self):
        archiveName = "{}.zip".format(uuid.uuid4())
        archivePath = "/var/www/html/img/{}".format(archiveName)
        with zipfile.ZipFile(archivePath, mode='x', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for image in os.listdir(App.TEMP_DIR):
                imagePath = os.path.join(App.TEMP_DIR, image)
                archive.write(imagePath, image)

        qrCode = qrcode.make("http://10.42.0.1/img/{}".format(archiveName))
        qrCode.save("/tmp/schnappi_qr.png")
        self.imagesServed.emit()


class SchnappiCoinButtonWorker(QThread):
    buttonPress = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.counter = Button(17)
        self.button = Button(22)
        self.led = LED(23)

    def waitForButton(self):
        self.button.wait_for_press()
        self.buttonPress.emit()
        sleep(1)

    def run(self):
        while True:
            self.counter.wait_for_press()
            self.led.on()
            self.waitForButton()
            self.led.off()
            self.waitForButton()
            self.waitForButton()


class SchnappiWindow(QMainWindow):
    doCapture = pyqtSignal()

    class State(Enum):
        Capture = auto()
        ResultPreview = auto()
        QrCode = auto()

    def __init__(self, camera):
        super().__init__()

        self.state = self.State.Capture

        self.buttonThread = SchnappiCoinButtonWorker()
        self.buttonThread.buttonPress.connect(self.handleButtonPress)
        self.buttonThread.start()

        self.captureThread = SchnappiCaptureWorker(camera, self.doCapture)
        self.captureThread.imagesServed.connect(self.showPreview)
        self.captureThread.start()

        self.stackedWidget = QStackedWidget()

        self.schnappiWidget = SchnappiWidget(self, camera)
        self.schnappiPreviewWidget = SchnappiPreviewWidget(self)
        self.schnappiQRWidget = SchnappiQRWidget(self)

        self.stackedWidget.addWidget(self.schnappiWidget)
        self.stackedWidget.addWidget(self.schnappiPreviewWidget)
        self.stackedWidget.addWidget(self.schnappiQRWidget)

        self.setWindowTitle("Schnappi - Die Schnappschusskiste")
        self.showFullScreen()
        self.setCentralWidget(self.stackedWidget)
        self.stackedWidget.setCurrentWidget(self.schnappiWidget)

    def handleButtonPress(self):
        if self.state == self.State.Capture:
            self.schnappiWidget.doCountdown(3)
            QTimer.singleShot(3000, lambda: self.doCapture.emit())
        elif self.state == self.State.ResultPreview:
            self.showQRCode()
        elif self.state == self.State.QrCode:
            self.showCamera()

    def showCamera(self):
        self.state = self.State.Capture
        self.stackedWidget.setCurrentWidget(self.schnappiWidget)
        self.schnappiWidget.showHint()

    def showPreview(self):
        self.state = self.State.ResultPreview
        self.schnappiPreviewWidget.loadImages()
        self.stackedWidget.setCurrentWidget(self.schnappiPreviewWidget)

    def showQRCode(self):
        self.state = self.State.QrCode
        self.schnappiQRWidget.loadQrCode()
        self.stackedWidget.setCurrentWidget(self.schnappiQRWidget)

class SchnappiWidget(QWidget):

    def __init__(self, parent, camera):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout()

        self.titleLabel = QLabel()
        self.titleLabel.setText("Schnappi - Die Schnappschusskiste")
        self.titleLabel.setFont(QFont("Quicksand", 30))
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.resize(200, 30)
        self.layout.addWidget(self.titleLabel)

        camera.qpicamera2 = QGlPicamera2(camera.picam2, width=1920, height=1080, keep_ar=True)
        self.layout.addWidget(camera.qpicamera2)

        self.descriptionLabel = QLabel()
        self.showHint()
        self.descriptionLabel.setFont(QFont("Quicksand", 30))
        self.descriptionLabel.setStyleSheet("color: orange;")
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.descriptionLabel.resize(200, 30)
        self.layout.addWidget(self.descriptionLabel)

        self.layout.setStretch(1,3)
        self.setLayout(self.layout)

    def showHint(self):
        self.descriptionLabel.setText("Wirf 1€ ein, drücke den Knopf und gehe einen Schritt zurück.")

    def doCountdown(self, n):
        self.descriptionLabel.setText("{}...".format(n))
        if n > 1:
            QTimer.singleShot(1000, lambda: self.doCountdown(n - 1))


class SchnappiQRWidget(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout()

        self.titleLabel = QLabel()
        self.titleLabel.setText("QRCODE")
        self.titleLabel.setFont(QFont("Quicksand", 30))
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.resize(200, 30)
        self.layout.addWidget(self.titleLabel)

        self.row = QHBoxLayout()
        self.layout.addLayout(self.row)
        self.col1 = QVBoxLayout()
        self.col2 = QVBoxLayout()
        self.row.addLayout(self.col1)
        self.row.addLayout(self.col2)

        self.wifiCode = QLabel()
        pixmap = QPixmap("/home/schnappi/Desktop/wlan_verbinden.png")
        self.wifiCode.setPixmap(pixmap)
        self.wifiCode.setAlignment(QtCore.Qt.AlignCenter)
        self.col1.addSpacing(200)
        self.col1.addWidget(self.wifiCode)
        self.wifiDescription = QLabel()
        self.wifiDescription.setText("1. Mit unserem WLAN verbinden.")
        self.wifiDescription.setFont(QFont("Quicksand", 30))
        self.wifiDescription.setStyleSheet("color: orange;")
        self.wifiDescription.setAlignment(QtCore.Qt.AlignCenter)
        self.col1.addWidget(self.wifiDescription)
        self.col1.addSpacing(200)

        self.downloadLink = QLabel()
        self.downloadLink.setAlignment(QtCore.Qt.AlignCenter)
        self.col2.addSpacing(200)
        self.col2.addWidget(self.downloadLink)
        self.downloadDescription = QLabel()
        self.downloadDescription.setText("2. Bilder herunterladen.")
        self.downloadDescription.setFont(QFont("Quicksand", 30))
        self.downloadDescription.setStyleSheet("color: orange;")
        self.downloadDescription.setAlignment(QtCore.Qt.AlignCenter)
        self.col2.addWidget(self.downloadDescription)
        self.col2.addSpacing(200)

        self.descriptionLabel = QLabel()
        self.descriptionLabel.setText("Drücke den Knopf, um wieder zum Anfang zu kommen.")
        self.descriptionLabel.setFont(QFont("Quicksand", 30))
        self.descriptionLabel.setStyleSheet("color: orange;")
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.descriptionLabel.resize(200, 30)
        self.layout.addWidget(self.descriptionLabel)

        self.layout.setStretch(1,2)
        self.setLayout(self.layout)

    def loadQrCode(self):
        pixmap = QPixmap("/tmp/schnappi_qr.png")
        self.downloadLink.setPixmap(pixmap)


class SchnappiPreviewWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.layout = QVBoxLayout()

        self.titleLabel = QLabel()
        self.titleLabel.setText("VORSCHAU")
        self.titleLabel.setFont(QFont("Quicksand", 30))
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.resize(200, 30)
        self.layout.addWidget(self.titleLabel)

        self.imageGrid = QVBoxLayout()
        self.row1 = QHBoxLayout()
        self.row2 = QHBoxLayout()
        self.imageGrid.addLayout(self.row1)
        self.imageGrid.addLayout(self.row2)
        self.layout.addLayout(self.imageGrid)

        self.images = [QLabel(), QLabel(), QLabel(), QLabel()]
        self.row1.addWidget(self.images[0])
        self.row1.addWidget(self.images[1])
        self.row2.addWidget(self.images[2])
        self.row2.addWidget(self.images[3])
        for image in self.images:
            image.setAlignment(QtCore.Qt.AlignCenter)
            image.setScaledContents(True)

        self.descriptionLabel = QLabel()
        self.descriptionLabel.setText("Drücke den Knopf, um zum Download der Bilder zu kommen.")
        self.descriptionLabel.setFont(QFont("Quicksand", 30))
        self.descriptionLabel.setStyleSheet("color: orange;")
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.descriptionLabel.resize(200, 30)
        self.layout.addWidget(self.descriptionLabel)

        self.layout.setStretch(1, 2)
        self.setLayout(self.layout)

    def loadImages(self):
        for i in range(4):
            pixmap = QPixmap("/tmp/schnappischuss/{}.jpg".format(i + 1))
            image = self.images[i]
            image.setPixmap(
                pixmap.scaled(image.width(), image.height(), QtCore.Qt.KeepAspectRatio)
            )


class SchnappiCamera(QObject):
    captureDone = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.picam2 = Picamera2()
        self.qpicamera2 = None

        self.picam2.configure(self.picam2.create_preview_configuration(main={"size": (1280, 720)}, raw={"size": (1280, 720)}, lores={"size": (1280, 720)}, display="lores", transform=Transform(hflip=True)))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    def startFeed(self):
        self.picam2.start()

    def captureImage(self):
        cfg = self.picam2.create_still_configuration(main={"size": (1920, 1080)}, raw={"size": (1920, 1080)}, lores={"size": (1920, 1080)}, display="lores", transform=Transform(hflip=True))

        targetPath="/tmp/schnappischuss.jpg"
        print("Bild aufgenommen und gespeichert")

        self.picam2.switch_mode_and_capture_file(cfg, targetPath, signal_function=lambda _: self.captureDone.emit())




app = App()
