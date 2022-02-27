import time
import sys
import random
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtWidgets import (QApplication, QMainWindow, QGraphicsScene,
                               QPushButton, QGraphicsView, QGraphicsItem,
                               QAction, QDialog, QLineEdit, QVBoxLayout,
                               QLabel, QRadioButton, QTextEdit, QFileDialog,
                               QFrame)
from PySide2.QtGui import QBrush, QPen, QFont, QTextCursor, QImage, QTextOption
from PySide2.QtCore import Qt, QRectF
import numpy as np
import socket
import json
import xml.etree.ElementTree as ET


class Server(QtCore.QThread):

    connected_signal = QtCore.Signal()
    passed_pos_signal = QtCore.Signal()
    end_turn_signal = QtCore.Signal()

    def __init__(self, ip="localhost", port=10000):
        QtCore.QThread.__init__(self)
        self.received_move = ""
        self.received_pos_x = 0
        self.received_pos_y = 0
        self.turn_number = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # adres IP własnej maszyny i port
        server_address = (ip, port)
        print('starting up on {} port {}'.format(*server_address))
        self.sock.bind(server_address)
        # Nasłuchiwanie
        self.sock.listen(1)

    def run(self):
        while True:
            # Oczekiwanie na połączenie
            print('waiting for a connection')
            self.connection, self.client_address = self.sock.accept()
            try:
                print('connection from', self.client_address)
                time.sleep(0.5)
                self.connected_signal.emit()
                # Receive the data in small chunks and retransmit it
                while True:
                    data = self.connection.recv(512)
                    if data:
                        if "pos" in str(data):
                            data = str(data)
                            data = data.replace("b'posx ", "")
                            data = data.replace(" posy", "")
                            data = data.replace("'", "")
                            self.received_pos_x = int(data[0])
                            self.received_pos_y = int(data[1])
                            self.passed_pos_signal.emit()
                        else:
                            data = str(data)
                            data = data.replace("b'", "")
                            data = data.replace("'", "")
                            self.received_move = data
                            self.turn_number += 1
                            self.end_turn_signal.emit()

            finally:
                # Clean up the connections
                self.connection.close()

    def send_move(self, direction):
        message = bytes(direction, 'utf-8')
        self.connection.sendall(message)

    def send_pos(self, pos_x, pos_y):
        message = bytes("posx " + str(pos_x) + " posy" + str(pos_y), 'utf-8')
        self.connection.sendall(message)

    def send_size(self, size):
        message = bytes("size " + str(size), 'utf-8')
        self.connection.sendall(message)


class Client(QtCore.QThread):

    passed_pos_signal = QtCore.Signal()
    end_turn_signal = QtCore.Signal()
    passed_size_signal = QtCore.Signal()

    def __init__(self, server_ip="localhost"):
        QtCore.QThread.__init__(self)
        self.received_size = 3
        self.received_move = ""
        self.received_pos_x = None
        self.received_pos_y = None
        self.turn_number = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (server_ip, 10000)
        print('connecting to {} port {}'.format(*self.server_address))
        self.sock.connect(self.server_address)

    def run(self):
        while True:
            data = self.sock.recv(512)
            if data:
                if "pos" in str(data):
                    data = str(data)
                    data = data.replace("b'posx ", "")
                    data = data.replace(" posy", "")
                    data = data.replace("'", "")
                    self.received_pos_x = int(data[0])
                    self.received_pos_y = int(data[1])
                    self.passed_pos_signal.emit()
                elif "size" in str(data):
                    data = str(data)
                    data = data.replace("b'size ", "")
                    data = data.replace("'", "")
                    self.received_size = int(data)
                    self.passed_size_signal.emit()
                else:
                    data = str(data)
                    data = data.replace("b'", "")
                    data = data.replace("'", "")
                    self.received_move = data
                    self.turn_number += 1
                    self.end_turn_signal.emit()

    def send_move(self, direction):
        message = bytes(direction, 'utf-8')
        self.sock.sendall(message)

    def send_pos(self, pos_x, pos_y):
        message = bytes("posx " + str(pos_x) + " posy" + str(pos_y), 'utf-8')
        self.sock.sendall(message)


class Field(QGraphicsItem):
    # Klasa dla pojedyńczego pola na planszy
    def __init__(self, did_move, is_empty, value, is_enemy, size):
        super().__init__()
        self.is_empty = is_empty
        self.did_move = did_move
        self.value = value
        self.size = size
        self.is_enemy = is_enemy
        self.handleSize = 8.0
        self.handleSpace = -4.0

        self.setX(0)
        self.setY(0)

    def boundingRect(self):
        return QtCore.QRect(0, 0, 0, 0)

    def paint(self, painter, option, widget):
        if self.value != 0:
            font = QFont("Helvetica",
                         (3 / self.size) * (40 - 4 * len(str(self.value))))
            img = QImage()
            if self.is_enemy:
                img.load("img/hex_enemy.png")  # inna grafika dla pola wroga
                painter.setPen(QtGui.QColor(54, 9, 14, 255))

            else:
                img.load("img/hex.png")
                painter.setPen(QtGui.QColor(46, 59, 81, 255))
            rect = QRectF((self.x() - 40 * (3 / self.size)),
                          (self.y() - 70 * (3 / self.size)),
                          100 * (3 / self.size), 100 * (3 / self.size))
            painter.drawImage(rect, img)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, str(self.value))


class FormIP(QDialog):
    # Okno do zmiany IP
    def __init__(self, parent=None, ip=None):
        super(FormIP, self).__init__(parent)
        self.label = QLabel("Wpisz IP:")
        self.edit = QLineEdit(ip)
        self.button = QPushButton("OK")
        self.ip = ip
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.button.clicked.connect(self.save_ip)

    def save_ip(self):
        self.ip = self.edit.text()
        self.close()

    def pass_ip(self):
        return self.ip


class ConnectWithDialog(QDialog):
    # Okno do zmiany IP
    def __init__(self, parent=None):
        super(ConnectWithDialog, self).__init__(parent)
        self.label = QLabel("IP of your opponent: ")
        self.edit = QLineEdit("localhost")
        self.button = QPushButton("Connect")
        self.ip = None
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.button.clicked.connect(self.save_ip)

    def save_ip(self):
        self.ip = self.edit.text()
        self.close()

    def pass_ip(self):
        return self.ip


class ConnectingDialog(QDialog):
    # okno mówiące o oczekiwaniu na garcza
    def __init__(self, parent=None):
        super(ConnectingDialog, self).__init__(parent)
        self.label = QLabel("Wainting for connection...")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    def found_player(self):
        self.label.setText("Player found!")
        self.layout.addWidget(self.label)
        self.button = QPushButton("OK")
        self.layout.addWidget(self.button)
        self.button.clicked.connect(self.close)


class WaitDialog(QDialog):
    # okno mówiące o oczekiwaniu na ruch garcza
    def __init__(self, parent=None):
        super(WaitDialog, self).__init__(parent)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.label = QLabel("Waiting for your opponent...")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)


class EndGameDialog(QDialog):
    # okno mówiące o oczekiwaniu na garcza
    def __init__(self, parent=None, text="Game Over!"):
        super(EndGameDialog, self).__init__(parent)
        self.label = QLabel(text)
        self.layout = QVBoxLayout()
        self.button = QPushButton("OK")
        self.button.clicked.connect(self.close)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)


class FormPort(QDialog):
    # Okno do zmiany portu
    def __init__(self, parent=None, port=None):
        super(FormPort, self).__init__(parent)
        self.label = QLabel("Type port:")
        self.edit = QLineEdit(str(port))
        self.button = QPushButton("OK")
        self.port = port
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.button.clicked.connect(self.save_port)

    def save_port(self):
        self.port = self.edit.text()
        self.close()

    def pass_port(self):
        return self.port


class FormSize(QDialog):
    # Okno do zmiany rozmiaru
    def __init__(self, parent=None, size=3):
        super(FormSize, self).__init__(parent)
        self.label = QLabel(
            "Select size:\n(Selecting size will start a new game!)")
        self.size = size
        self.button_3x = QRadioButton("3x3x3")
        self.button_4x = QRadioButton("4x4x4")
        self.button_5x = QRadioButton("5x5x5")
        self.button_save = QPushButton("OK")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button_3x)
        layout.addWidget(self.button_4x)
        layout.addWidget(self.button_5x)
        layout.addWidget(self.button_save)
        self.button_save.clicked.connect(self.save_size)
        self.setLayout(layout)

    def save_size(self):
        if self.button_3x.isChecked():
            self.size = 3
        if self.button_4x.isChecked():
            self.size = 4
        if self.button_5x.isChecked():
            self.size = 5
        self.close()

    def pass_size(self):
        return self.size


class EmittingStream(QtCore.QObject):

    text_written = QtCore.Signal(str)
    _stream = sys.stdout

    def write(self, text):
        self._stream.write(str(text))
        self.text_written.emit(str(text))

    def flush(self):
        pass


class Window(QtWidgets.QMainWindow):
    # Klasa głównego okna aplikacji
    def __init__(self, board, size):
        super().__init__()

        self.Scene()
        self.View()

        self.score_label = QLabel(self)
        self.size = size
        self.board = board
        self.boards_history = []
        self.score = 2
        self.score_1 = 0
        self.score_2 = 0
        self.score_3 = 0
        self.score_label_text = "Score: " + str(self.score)
        self.start_pos = None  # pozycja startowa przy kliknięciu (do obłsługi gestów)
        self.name = "Player"

        # zmienne do trybu wieloosobowego
        self.first_loop = QtCore.QEventLoop()
        self.loop_buttons = QtCore.QEventLoop()
        self.loop = QtCore.QEventLoop()
        self.mulitplayer_mode = False
        self.is_server = False
        self.turn_number = 0  # numer tury
        self.enemy_board = None
        self.enemy_score = 2
        self.enemy_score_label = QLabel(self)
        self.enemy_score_label_text = "Score: " + str(self.enemy_score_label)
        self.width = 600
        self.height = 600
        self.ip_addr = "localhost"
        self.port = 10000

        self.setMinimumHeight(self.height)
        self.setMinimumWidth(self.width)
        self.setMaximumHeight(self.height)
        self.setMaximumWidth(self.width)
        self.setMouseTracking(True)
        self.create_buttons()
        self.create_board_GUI()
        self.create_menu_bar()
        gen_number(self.board)
        print_board(self.board)
        self.show()

    def Scene(self):
        # Tworzenie sceny
        self.scene = QGraphicsScene(self)
        background_brush = QBrush(QtGui.QColor(207, 203, 206, 255))
        self.scene.setBackgroundBrush(background_brush)

    def View(self):
        # Tworzenie widoku
        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(600, 800)
        self.setCentralWidget(self.view)
        self.view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        # obsługa gestów
        if obj is self.view.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self.start_pos = event.pos()
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                x1 = 0
                y1 = -100
                x2 = event.pos().x() - self.start_pos.x()
                y2 = event.pos().y() - self.start_pos.y()
                dot = x1 * x2 + y1 * y2
                det = x1 * y2 - y1 * x2
                angle = np.arctan2(det, dot) * 180 / np.pi
                if angle >= 0 and angle < 60:
                    self.handle_buttons("e")
                if angle >= 60 and angle < 120:
                    self.handle_buttons("d")
                if angle >= 120 and angle < 180:
                    self.handle_buttons("x")
                if angle >= -60 and angle < 0:
                    self.handle_buttons("w")
                if angle >= -120 and angle < -60:
                    self.handle_buttons("a")
                if angle >= -180 and angle < -120:
                    self.handle_buttons("z")
        return QtWidgets.QWidget.eventFilter(self, obj, event)

    def create_buttons(self):
        # Tworzenie przycisków w GUI
        button_up_right = QPushButton("↗", self)
        button_up_left = QPushButton("↖", self)
        button_right = QPushButton("➡", self)
        button_left = QPushButton("⬅", self)
        button_down_right = QPushButton("↘", self)
        button_down_left = QPushButton("↙", self)

        button_up_right.setGeometry(self.width / 2, 450, 50, 50)
        button_up_left.setGeometry(self.width / 2 - 43, 450, 50, 50)
        button_right.setGeometry(self.width / 2, 500, 50, 50)
        button_left.setGeometry(self.width / 2 - 43, 500, 50, 50)
        button_down_right.setGeometry(self.width / 2, 550, 50, 50)
        button_down_left.setGeometry(self.width / 2 - 43, 550, 50, 50)

        button_up_right.clicked.connect(lambda: self.handle_buttons("e"))
        button_up_left.clicked.connect(lambda: self.handle_buttons("w"))
        button_left.clicked.connect(lambda: self.handle_buttons("a"))
        button_right.clicked.connect(lambda: self.handle_buttons("d"))
        button_down_right.clicked.connect(lambda: self.handle_buttons("x"))
        button_down_left.clicked.connect(lambda: self.handle_buttons("z"))

    def handle_buttons(self, direction):
        # Obsługa przycisków od sterownia (i gestów)
        if not self.mulitplayer_mode:
            self.main_game_loop(direction)
            # aktualizacja wyniku
            self.update_score(self.board, self.score_label,
                              self.score_label_text, self.score)
            self.boards_history.append(self.board)
        else:
            # dla trybu wieloosobowego
            self.turn_number += 1
            if self.is_server:
                self.server.send_move(direction)
                # dopóki przeciwnik nie wykona ruchu
                if self.turn_number != self.server.turn_number:
                    self.wait_for_move_dialog = WaitDialog(self)
                    self.wait_for_move_dialog.show()
                    self.loop_buttons.exec_()
                    self.wait_for_move_dialog.close()
                    self.wait_for_move_dialog = None
                enemy_direction = str(self.server.received_move)

            else:
                self.client.send_move(direction)
                # dopóki przeciwnik nie wykona ruchu
                if self.turn_number != self.client.turn_number:
                    self.wait_for_move_dialog = WaitDialog(self)
                    self.wait_for_move_dialog.show()
                    self.loop_buttons.exec_()
                    self.wait_for_move_dialog.close()
                    self.wait_for_move_dialog = None
                enemy_direction = str(self.client.received_move)
            #print("ruch przeciwnika: ", enemy_direction)
            # czekaj na ruch przeciwnika
            self.multiplayer_game_loop(direction, enemy_direction)
            # aktualizacja wyniku gracza i przeciwnika
            self.update_score(self.board, self.score_label,
                              self.score_label_text, self.score)
            self.update_score(self.enemy_board, self.enemy_score_label,
                              self.enemy_score_label_text, self.enemy_score)

    def create_menu_bar(self):
        # Menu bar z opcjiami
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        options_menu = menu_bar.addMenu("Options")

        new_game_action = QAction("New game", self)
        new_game_action.setShortcut("Ctrl+N")
        new_game_action.triggered.connect(self.new_game)

        save_game_action = QAction("Save game", self)
        save_game_action.setShortcut("Ctrl+S")
        save_game_action.triggered.connect(self.save_game)

        save_config_action = QAction("Save configuration", self)
        save_config_action.triggered.connect(self.save_configuration)

        load_config_action = QAction("Load configuration", self)
        load_config_action.triggered.connect(self.load_configuration)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+X")
        exit_action.triggered.connect(self.exit_app)

        search_palyer_action = QAction("Search for oponnet", self)
        search_palyer_action.triggered.connect(self.start_server)
        connect_player_action = QAction("Connect to other player", self)
        connect_player_action.triggered.connect(self.connect_to_other_player)

        ip_acction = QAction("IP adress", self)
        ip_acction.triggered.connect(self.create_dialog_ip)
        port_action = QAction("Port", self)
        port_action.triggered.connect(self.create_dialog_port)
        size_acction = QAction("Board size", self)
        size_acction.triggered.connect(self.create_dialog_size)

        file_menu.addAction(new_game_action)
        file_menu.addAction(save_game_action)
        file_menu.addAction(save_config_action)
        file_menu.addAction(load_config_action)
        file_menu.addAction(exit_action)
        edit_menu.addAction(search_palyer_action)
        edit_menu.addAction(connect_player_action)
        options_menu.addAction(ip_acction)
        options_menu.addAction(port_action)
        options_menu.addAction(size_acction)

    def create_dialog_ip(self):
        form_ip = FormIP(self, self.ip_addr)
        form_ip.exec_()
        self.ip_addr = form_ip.pass_ip()

    def create_dialog_port(self):
        form_port = FormPort(self, self.port)
        form_port.exec_()
        self.port = int(form_port.pass_port())

    def create_dialog_size(self):
        form_size = FormSize(self, self.size)
        form_size.exec_()
        self.size = form_size.pass_size()
        self.new_game()

    def new_game(self):
        self.mulitplayer_mode = False
        self.scene.clear()
        self.board = create_board(self.size, False)
        self.view.setFixedSize(600, 800)
        gen_number(self.board)
        print_board(self.board)
        self.score = 2
        self.create_board_GUI()
        self.scene.update()

    def save_game(self):
        # okno do zapisu
        name = QFileDialog.getSaveFileName(self, "Save game")
        # zapis do xml
        data = ET.Element("data")
        size_el = ET.SubElement(data, "size")
        size_el.text = str(self.size)
        for board in self.boards_history:
            board_el = ET.SubElement(data, "board")
            for j in range(len(board)):
                for i in range(len(board)):
                    val = ET.SubElement(board_el, "val")
                    if board[i][j] is not None:
                        val.text = str(board[i][j].value)
                    else:
                        val.text = str("None")
        try:
            tree = ET.ElementTree(data)
            tree.write(name[0] + ".xml", encoding='utf-8')
            print("\nSaved: " + name[0] + ".xml \n")
        except FileNotFoundError as error:
            print(error)

    def load_game(self):
        # otwórz plik xml
        self.mulitplayer_mode = False
        name = QFileDialog.getOpenFileName(None, "Load game", "",
                                           "XML files (*.xml)")

        parser = ET.XMLParser(encoding="utf-8")
        tree = ET.parse(name[0], parser=parser)
        root = tree.getroot()

        # pierwszy element- rozmiar planszy
        self.size = int(root[0].text)

        # stworzenie nowej planszy o danym rozmiarze
        self.board = create_board(self.size, False)
        self.mulitplayer_mode = False
        self.scene.clear()
        self.boards_history = []
        self.score = 2
        self.create_board_GUI()
        self.view.setFixedSize(600, 600)

        # dane z xml (zapisane wartości planszy) do tablicy board
        i = 0
        j = -1
        for element in root:
            for n, sub_element in enumerate(element):
                i = n % len(board)
                if i == 0:
                    j += 1
                    j = j % len(board)
                if sub_element.text != "None":
                    self.board[i][j].value = int(sub_element.text)
                else:
                    self.board[i][j] = None

        print("\nGame loaded!\n")
        print_board(self.board)

    def save_configuration(self):
        data = {
            "name": self.name,
            "IP": self.ip_addr,
            "port": self.port,
            "score_1": self.score_1,
            "score_2": self.score_2,
            "score_3": self.score_3
        }

        with open("config.json", "w") as json_file:
            json.dump(data, json_file)

    def load_configuration(self):
        try:
            with open("config.json") as json_file:
                data = json.load(json_file)
                print("Name: " + data["name"])
                print("IP: " + data["IP"])
                print("Port: " + str(data["port"]))
                print("Score 1: " + str(data["score_1"]))
                print("Score 2: " + str(data["score_2"]))
                print("Score 3: " + str(data["score_3"]))
                self.name = data["name"]
                self.ip_addr = data["IP"]
                self.port = data["port"]
                self.score_1 = data["score_1"]
                self.score_2 = data["score_2"]
                self.score_3 = data["score_3"]
        except FileNotFoundError as error:
            print(error)
            print("No previous configuration!")

    def update_score(self, board, label, label_text, score):
        for j in range(len(board)):
            for i in range(len(board)):
                if board[i][j] is not None:
                    if board[i][j].value > score:
                        score = board[i][j].value
        label_text = "Score: " + str(score)
        label.setText(label_text)
        self.scene.update()

    def create_board_GUI(self):
        self.width = 600
        self.setMinimumWidth(self.width)
        self.setMaximumWidth(self.width)
        self.view.setFixedSize(600, 600)
        self.scene.clear()

        taupe_brush = QBrush(QtGui.QColor(207, 203, 206, 255))
        cornflower_pen = QPen(QtGui.QColor(91, 133, 160, 255))
        cornflower_pen.setWidth(5)

        center_points = self.draw_board(0, cornflower_pen, taupe_brush)

        self.set_fields_positions(center_points, self.board)
        # label z wynikiem
        self.score_label.move(500, 600)
        self.update_score(self.board, self.score_label, self.score_label_text,
                          self.score)

    def create__muliplayer_GUI(self):
        # zmiana rozmiarów GUI na tryb wieloosobowy
        self.width = 1200
        self.setMinimumWidth(self.width)
        self.setMaximumWidth(self.width)
        self.view.setFixedSize(1200, 600)
        self.scene.clear()

        # rysowanie planszy gracza
        taupe_brush = QBrush(QtGui.QColor(207, 203, 206, 255))
        cornflower_pen = QPen(QtGui.QColor(91, 133, 160, 255))
        cornflower_pen.setWidth(5)

        center_points = self.draw_board(-600 * (1 + (self.size - 3) * 0.3),
                                        cornflower_pen, taupe_brush)
        self.set_fields_positions(center_points, self.board)
        # label z wynikiem
        self.score_label.move(500, 600)
        self.update_score(self.board, self.score_label, self.score_label_text,
                          self.score)

        # rysowanie planszy przeciwnika
        darkred_pen = QPen(QtGui.QColor(141, 24, 36, 255))
        darkred_pen.setWidth(5)

        center_points_enemy = self.draw_board(0, darkred_pen, taupe_brush)
        self.set_fields_positions(center_points_enemy, self.enemy_board)

        self.enemy_score_label.move(1100, 600)
        self.update_score(self.enemy_board, self.enemy_score_label,
                          self.enemy_score_label_text, self.enemy_score)

    def draw_board(self, shift, pen, brush):
        # rysowanie planszy na scenie
        x = []
        y = []
        center_points = []

        for i in range(2 * self.size - 1):
            if i < self.size / 2 + 1:
                n = self.size + i
                space = 45 * (self.size - i)
            else:
                n = 3 * self.size - i - 2
                space = 45 * (i - (self.size - 2))
            for j in range(n, 0, -1):
                x, y = find_edges(i, j, n)
                p1 = []
                center_points.append([
                    (3 / self.size) * (50 * x[0] + shift / 2 + space / 2 - 5),
                    (3 / self.size) * (50 * y[0] - 15)
                ])
                for n in range(len(x)):
                    p1.append(
                        QtCore.QPoint(
                            (3 / self.size) * (100 * x[n] + shift + space),
                            (3 / self.size) * (100 * y[n])))
                self.scene.addPolygon(p1, pen, brush)

        # zwraca środki heksagonów
        return center_points

    def set_fields_positions(self, center_points, board):
        n_center = 0  # określa indeks tablicy zawierającej punkt- środek heksagonu
        center_points.reverse()
        for j in range(len(board)):
            for i in range(len(board)):
                if board[i][j] is not None:
                    board[i][j].setX(center_points[n_center][0])
                    board[i][j].setY(center_points[n_center][1])
                    self.scene.addItem(board[i][j])
                    n_center += 1

    def start_server(self):
        #print("Uruchamianie serwerwa...")
        try:
            self.server = Server(self.ip_addr, self.port)
            self.wait_dialog = ConnectingDialog(self)
            self.wait_dialog.show()
            self.server.connected_signal.connect(self.first_loop.quit)
            self.server.passed_pos_signal.connect(self.loop.quit)
            self.server.end_turn_signal.connect(self.loop_buttons.quit)
            self.server.start()
            self.is_server = True
            self.mulitplayer_mode_start()
        except OSError as error:
            print(error)

    def connect_to_other_player(self):
        #print("Tworzenie kilenta...")
        self.connect_dialog = ConnectWithDialog(self)
        self.connect_dialog.exec_()
        server_ip = self.connect_dialog.pass_ip()
        try:
            self.client = Client(server_ip)
            self.client.passed_pos_signal.connect(self.loop.quit)
            self.client.end_turn_signal.connect(self.loop_buttons.quit)
            self.client.passed_size_signal.connect(self.first_loop.quit)
            self.client.start()
            self.mulitplayer_mode_start()
        except ConnectionRefusedError as error:
            print(error)
        except OSError as error:
            print(error)

    def mulitplayer_mode_start(self):
        self.first_loop.exec_()
        if self.is_server:
            self.server.send_size(self.size)
            self.wait_dialog.found_player()
        else:
            self.size = self.client.received_size
        self.mulitplayer_mode = True
        self.board = create_board(self.size, False)
        my_pos_x, my_pos_y = gen_number_multiplayer(self.board)
        self.enemy_board = create_board(self.size, True)
        # wyślij lokalizację nowego klocka do przeciwnika i pobierz jego
        if self.is_server:
            self.server.send_pos(my_pos_x, my_pos_y)
            # czeka na pozycje od przeciwnika
            self.loop.exec_()
            enemy_pos_x = self.server.received_pos_x
            enemy_pos_y = self.server.received_pos_y
        else:
            self.client.send_pos(my_pos_x, my_pos_y)
            # czeka na pozycje od przeciwnika
            self.loop.exec_()
            enemy_pos_x = self.client.received_pos_x
            enemy_pos_y = self.client.received_pos_y

        print("\nPlayer board: ")
        print_board(self.board)
        update_enemy_board(self.enemy_board, enemy_pos_x, enemy_pos_y)
        print("\nOpponent board: ")
        print_board(self.enemy_board)
        self.score = 2
        self.enemy_score = 2
        self.create__muliplayer_GUI()
        self.scene.update()

    def multiplayer_game_loop(self, direction, enemy_direction):
        game_over_player = check_game_over(self.board, self.size)
        game_over_enemy = check_game_over(self.enemy_board, self.size)
        if not game_over_player and not game_over_enemy:
            players_move(self.board, direction)
            players_move(self.enemy_board, enemy_direction)
            my_pos_x, my_pos_y = gen_number_multiplayer(self.board)
            if self.is_server:
                self.server.send_pos(my_pos_x, my_pos_y)
                # czeka na pozycje od przeciwnika
                self.loop.exec_()
                enemy_pos_x = self.server.received_pos_x
                enemy_pos_y = self.server.received_pos_y
            else:
                self.client.send_pos(my_pos_x, my_pos_y)
                # czeka na pozycje od przeciwnika
                self.loop.exec_()
                enemy_pos_x = self.client.received_pos_x
                enemy_pos_y = self.client.received_pos_y
            update_enemy_board(self.enemy_board, enemy_pos_x, enemy_pos_y)
            print("\nPlayer board: ")
            print_board(self.board)
            print("\nOponent board: ")
            print_board(self.enemy_board)
        elif game_over_enemy:
            print("Game over- You won!")
            self.end_dialog = EndGameDialog(self, "Game over- You won!")
            self.end_dialog.show()
            self.new_game()
        elif game_over_player:
            print("Game over- You lost!")
            self.end_dialog = EndGameDialog(self, "Game over- You lost!")
            self.end_dialog.show()
            self.new_game()

    def main_game_loop(self, direction):
        if not check_game_over(self.board, self.size):
            players_move(self.board, direction)
            gen_number(self.board)
            print_board(self.board)
        else:
            if self.score > self.score_1:
                self.score_1 = self.score
            if self.score > self.score_2:
                self.score_2 = self.score
            if self.score > self.score_3:
                self.score_3 = self.score
            print("Game over")
            self.end_dialog = EndGameDialog(self, "Game over")
            self.end_dialog.show()
            self.new_game()

    def exit_app(self):
        # wyjście z aplikacji
        self.close()

    def __del__(self):
        # Restore sys.stdout
        sys.stdout = sys.__stdout__


# ______________________________________
# _______________FUNKCJE________________
# ______________________________________


def find_edges(i, j, n):
    # funkcja zawraca punkty krawędzi hexagonu

    x = [(2 * j + 1) * np.sqrt(3) / 4, (j + 1) * np.sqrt(3) / 2,
         (j + 1) * np.sqrt(3) / 2, (2 * j + 1) * np.sqrt(3) / 4,
         j * np.sqrt(3) / 2, j * np.sqrt(3) / 2, (2 * j + 1) * np.sqrt(3) / 4]

    y = [
        1 - (3 / 4 * i), 3 / 4 - (3 / 4 * i), 1 / 4 - (3 / 4 * i),
        0 - (3 / 4 * i), 1 / 4 - (3 / 4 * i), 3 / 4 - (3 / 4 * i),
        1 - (3 / 4 * i)
    ]

    return x, y


def create_board(size, is_enemy):
    # Tworzenie hexagonalnej planszy o podanym rozmiarze
    board = []

    for j in range(2 * size - 1):
        row = []
        for i in range(2 * size - 1):
            # siatka heksagonalna w kształcie heksagonu
            if (i + j >= size - 1 and j < size) or (i + j <= 3 *
                                                    (size - 1) and j >= size):
                field = Field(False, True, 0, is_enemy, size)
                row.append(field)
            else:
                row.append(None)
        board.append(row)

    return board


def print_board(board):
    # rysowanie planszy w konsoli
    for j in range(len(board)):
        if j < len(board) / 2:
            space = 2 * (len(board) - 2 - j) * (" ")
        if j > len(board) / 2:
            space = 2 * (j - 1) * (" ")
        print(space, end=" ")
        for i in range(len(board)):
            if board[i][j] is not None:
                if board[i][j].value == 0:
                    print('{0:3n}'.format(board[i][j].value), end=' ')
                else:
                    print('\033[94m' + '{0:3n}'.format(board[i][j].value) +
                          '\033[0m',
                          end=' ')

        print("")


def gen_number(board):
    # generuje pojawinie się nowej liczby na planszy
    num = 2
    pos_x = random.randint(0, len(board) - 1)
    pos_y = random.randint(0, len(board) - 1)

    if board[pos_x][pos_y] is not None:
        if board[pos_x][pos_y].is_empty:
            board[pos_x][pos_y].value = num
            board[pos_x][pos_y].is_empty = False
        else:
            gen_number(board)
    else:
        gen_number(board)


def gen_number_multiplayer(board):
    # generuje pojawinie się nowej liczby na planszy
    num = 2
    pos_x = random.randint(0, len(board) - 1)
    pos_y = random.randint(0, len(board) - 1)

    if board[pos_x][pos_y] is not None:
        if board[pos_x][pos_y].is_empty:
            board[pos_x][pos_y].value = num
            board[pos_x][pos_y].is_empty = False
            return pos_x, pos_y
        else:
            pos_x, pos_y = gen_number_multiplayer(board)
            return pos_x, pos_y
    else:
        pos_x, pos_y = gen_number_multiplayer(board)
        return pos_x, pos_y


def update_enemy_board(board, pos_x, pos_y):
    num = 2
    board[pos_x][pos_y].value = num
    board[pos_x][pos_y].is_empty = False


def calculate_next_position(board, i, j, direction_i, direction_j):
    # obliczenie następnej możliwej pozycji
    next_i = i + direction_i
    next_j = j + direction_j
    can_join = False

    while True:
        # jeżeli nie jest poza planszą
        if next_i >= 0 and next_i < len(
                board) and next_j >= 0 and next_j < len(
                    board) and board[next_i][next_j] is not None:
            if board[next_i][next_j].is_empty:
                next_i = next_i + direction_i
                next_j = next_j + direction_j
            # jeżeli może się złączyć z innym
            elif board[i][j].value == board[next_i][next_j].value:
                can_join = True
                break
            else:
                next_i = next_i - direction_i
                next_j = next_j - direction_j
                break
        else:
            next_i = next_i - direction_i
            next_j = next_j - direction_j
            break

    return next_i, next_j, can_join


def resest_did_move(board):
    # resetuje did_move- umożliwia dalszy ruch w nasęponych kolejkach
    for i in range(len(board)):
        for j in range(len(board)):
            if board[i][j] is not None:
                board[i][j].did_move = False


def players_move(board, move):
    print("")
    direction_i = -1
    direction_j = 1

    if move == "e":
        direction_i = 1
        direction_j = -1
    if move == "d":
        direction_i = 1
        direction_j = 0
    if move == "x":
        direction_i = 0
        direction_j = 1
    if move == "z":
        direction_i = -1
        direction_j = 1
    if move == "a":
        direction_i = -1
        direction_j = 0
    if move == "w":
        direction_i = 0
        direction_j = -1

    # inna kolejność interacji dla innych ruchów (aby pola nie blokowały innych pól)
    if move == "w" or move == "a" or move == "z":
        for i in range(len(board)):
            for j in range(len(board)):
                update_pos(board, i, j, direction_i, direction_j)
    else:
        for i in range(len(board) - 1, -1, -1):
            for j in range(len(board) - 1, -1, -1):
                update_pos(board, i, j, direction_i, direction_j)

    resest_did_move(board)


def update_pos(board, i, j, direction_i, direction_j):
    if board[i][j] is not None and not board[i][j].is_empty and not board[i][
            j].did_move:
        next_i, next_j, can_join = calculate_next_position(
            board, i, j, direction_i, direction_j)
        if not (next_i == i and next_j == j):
            if can_join:
                board[next_i][next_j].value = 2 * board[next_i][next_j].value
            else:
                board[next_i][next_j].value = board[i][j].value
            board[next_i][next_j].is_empty = False
            board[next_i][next_j].did_move = True
            board[i][j].value = 0
            board[i][j].is_empty = True


def check_game_over(board, size):
    game_over = True
    for i in range(len(board)):
        for j in range(len(board)):
            if board[i][j] is not None:
                # jeżeli jest jakieś puste pole
                if board[i][j].is_empty:
                    game_over = False

    return game_over


if __name__ == "__main__":
    size = 3
    board = create_board(size, False)
    app = QtWidgets.QApplication([])

    window = Window(board, size)
    window.show()
    sys.exit(app.exec_())
