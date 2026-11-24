import sys
import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time
import ctypes
import shutil
import hashlib
import subprocess
import calendar
from keyauth import api
import json
from cryptography.fernet import Fernet
import requests
import qrcode

import re
import base64
from io import BytesIO
from decimal import Decimal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QListWidget, QListWidgetItem, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QFormLayout,
                             QLineEdit, QDateEdit, QComboBox, QScrollArea, QDoubleSpinBox,
                             QInputDialog, QProgressBar, QFileDialog, QMessageBox,
                             QCalendarWidget, QDialog, QGridLayout, QSpinBox, QCheckBox,
                             QSizePolicy, QAbstractItemView, QCompleter, QProgressDialog, QTabWidget,
                             QGroupBox, QDialogButtonBox)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import subprocess
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from bcb import sgs
import traceback
