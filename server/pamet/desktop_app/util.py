from __future__ import annotations

import hashlib
import io
import shutil
from pathlib import Path
from typing import List, Tuple

from fusion.logging import get_logger
from fusion.util.rectangle import Rectangle
from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRect, QRectF, Qt
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QGuiApplication,
    QImage,
    QImageReader,
    QPainter,
)
from PySide6.QtWidgets import QApplication

import pamet
from pamet.constants import NO_SCALE_LINE_SPACING
from pamet.util import resource_dir

log = get_logger(__name__)
EMPTY_LINE = ""


def control_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ControlModifier


def shift_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ShiftModifier


def current_window() -> WindowWidget:
    return QApplication.activeWindow()


def current_tab() -> TabWidget:
    return current_window().current_tab()


def convert_image_with_pil(image_data: bytes):
    bytes_io = io.BytesIO(image_data)
    img_byte_arr = io.BytesIO()

    try:  # Probe if Pillow can handle the image
        pil_image = Image.open(bytes_io)  # @IgnoreException
        pil_image.save(img_byte_arr, "png")
    except Exception as e:
        raise Exception(f'Could not read image with PIL: "{e}"')

    return img_byte_arr.read()


def get_image_and_md5_from_bytearray(bytearray: QByteArray) -> Tuple[QImage, str]:
    if not isinstance(bytearray, QByteArray) or bytearray.isEmpty():
        raise Exception("Bytearray is wrong type or empty")

    # create buffer
    image_data = bytearray.data()
    buffer = QBuffer(bytearray)
    image_reader = QImageReader(buffer)

    # If Qt doesn't support the format (e.g. WebP)
    # try to convert it with Pillow to PNG
    if image_reader.format() not in image_reader.supportedImageFormats():

        image_data = convert_image_with_pil(image_data)
        if not image_data:
            return QImage(), None
        buffer = QBuffer(QByteArray(image_data))
        image_reader = QImageReader(buffer)

    image = image_reader.read()
    if image.isNull():
        raise Exception(f"Could not load image. Error: {image_reader.errorString()}")

    # get md5
    md5sum = hashlib.md5(image_data).hexdigest()

    return image, md5sum


def jpeg_blob_from_image(image: QImage, quality: int = 100) -> bytes:
    if image.isNull():
        raise Exception("Image is null")

    blob = QByteArray()
    buffer = QBuffer(blob)
    buffer.open(QIODevice.WriteOnly)
    ok = image.save(buffer, "jpg", quality)
    if not ok:
        raise Exception("Could not save image to buffer")

    return blob
