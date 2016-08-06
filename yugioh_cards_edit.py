import traceback
import struct
import re
from io import BytesIO
from copy import copy, deepcopy
from os import path
from timeit import default_timer

from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication
from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QListWidget,
                             QLineEdit, QTextEdit, QListWidgetItem)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
#from bw_level_edit import catch_exception

CARDS = {}
try:
    with open("cardlist.txt", "r") as f:
        for i, card in enumerate(f):
            trimmed_card = card.strip()
            assert trimmed_card != ""
            CARDS[i] = trimmed_card
except:
    traceback.print_exc()
    CARDS = None # I guess we can't show card names then.

# Algorithm taken from https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
# because i am a lazy person
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]



def get_name(card_id):
    if CARDS is None:
        return "---"
    elif card_id not in CARDS:
        return "id_out_of_bounds"
    else:
        return CARDS[card_id]

def match_name(name):
    lowername = name.lower()
    if CARDS is not None:
        for i, card in CARDS.items():
            if card.lower() == lowername:
                return i, card

        return None, None
    else:
        return None, None

def match_partly(name):
    lowername = name.lower()
    if CARDS is not None:
        pattern = ".*{0}.*".format(lowername)
        matches = []

        for i, card in CARDS.items():
            match = re.match(pattern, card.lower())
            if match is not None:
                matches.append((i, card))
        if len(matches) == 0:
            return None, None
        elif len(matches) == 1:
            return matches[0]
        else:
            return matches
    else:
        return None, None

class YugiohDeckEntry(QListWidgetItem):
    def __init__(self, starter, number, offset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_starter = starter
        self.number = number
        self.deck_offset = offset

def set_default_path(path):
    print("WRITING", path)
    try:
        with open("default_path2.cfg", "wb") as f:
            f.write(bytes(path, encoding="utf-8"))
    except Exception as error:
        print("couldn't write path")
        traceback.print_exc()
        pass


def get_default_path():
    print("READING")
    try:
        with open("default_path2.cfg", "rb") as f:
            path = str(f.read(), encoding="utf-8")
        return path
    except:
        return None


class DeckEditorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()

        self.stringfile = None
        self.reset_in_process = False

        path = get_default_path()
        if path is None:
            self.default_path = ""
        else:
            self.default_path = path

        self.deck_list.currentItemChanged.connect(self.action_listwidget_change_item)
        self.button_set_deck.pressed.connect(self.action_button_set_deck)
        #self.button_set_message.pressed.connect(self.action_button_set_message)
        #self.button_add_message.pressed.connect(self.action_button_add_message)
        #self.button_remove_message.pressed.connect(self.action_button_delete_message)

        self.deck_data = None

    def reset(self):
        self.reset_in_process = True
        self.deck_list.clearSelection()
        self.deck_list.clear()
        """self.stringfile = None
        self.deck_list.clearSelection()
        self.deck_list.clear()
        self.textedit_content.clear()
        self.lineedit_path.clear()
        self.lineedit_playtime.clear()
        self.lineedit_audioname.clear()"""

        self.reset_in_process = False


    def action_button_set_deck(self):
        print("I was pressed")
        current = self.deck_list.currentItem()
        self.statusbar.clearMessage()
        if current is not None and self.deck_data is not None:
            try:
                leader, rank = self.lineedit_leader.text(), self.lineedit_leader_rank.text()

                deck_data = []

                if rank.isnumeric():
                    rank = int(rank)
                else:
                    self.statusbar.showMessage("Rank is not numeric")
                    return



                if leader.isnumeric():
                    leaderdata = (int(leader) & 0xFFF) | ((rank & 0xF) << 12)
                else:
                    match = match_partly(leader)

                    if isinstance(match, tuple) and match[0] is None:
                        self.statusbar.showMessage("No matching card found: '{0}'".format(leader))
                        return
                    elif isinstance(match, tuple):
                        index, card = match
                        leaderdata = (int(index) & 0xFFF) | ((rank & 0xF) << 12)
                    else:
                        if len(match) > 5:
                            self.statusbar.showMessage("Too many matches found ({0} matches)".format(len(match)))
                        else:
                            self.statusbar.showMessage("More than 1 match found: {0}".format(
                                ", ".join("{0} ({1})".format(x[1], x[0]) for x in match)))
                        return

                deck_data.append(leaderdata)

                cards = []
                for i in range(40):
                    textedit, indexlabel, cardname = self.card_slots[i][0:3]

                    card = textedit.text()
                    if card.isnumeric():
                        card = int(card) & 0xFFF
                        #cardname.setText(get_name(card))
                        deck_data.append(card)
                    else:
                        match = match_partly(card)

                        if isinstance(match, tuple) and match[0] is None:
                            self.statusbar.showMessage("No matching card found: '{0}'".format(card))
                            return
                        elif isinstance(match, tuple):
                            index, card = match

                            deck_data.append(index)
                        else:
                            if len(match) > 5:
                                self.statusbar.showMessage("Too many matches found ({0} matches)".format(len(match)))
                            else:
                                self.statusbar.showMessage("More than 1 match found: {0}".format(
                                    ", ".join("{0} ({1})".format(x[1], x[0]) for x in match)))
                            return

                if current.is_starter:
                    current.setText("[Starter] {0:>7} [rank:{1:>2}] {2}".format(leaderdata&0xFFF,
                                                                                rank, get_name(leaderdata & 0xFFF)))
                else:

                    current.setText("[CPU] {0:>7} [rank:{1:>2}] {2}".format(leader&0xFFF,
                                                                            rank, get_name(leaderdata & 0xFFF)))

                self.leader_label.setText(get_name(leaderdata & 0xFFF))
                self.lineedit_leader.setText(str(leaderdata & 0xFFF))


                print(len(deck_data))
                for i in range(40):
                    card = deck_data[1+i]
                    textedit, indexlabel, cardname = self.card_slots[i][0:3]
                    textedit.setText(str(card))
                    cardname.setText(get_name(card))

                print(type(self.deck_data))
                struct.pack_into("H"*41, self.deck_data, current.number*41*2, *deck_data)


            except:
                traceback.print_exc()


    def action_listwidget_change_item(self, current, previous):
        try:
            if current is not None:
                print(current, current.number, current.deck_offset)

                leader = struct.unpack_from("H", self.deck_data, current.number*41*2)[0]

                rank = leader >> 12
                leader_card = leader & 0xFFF

                self.lineedit_leader.setText(str(leader_card))
                self.lineedit_leader_rank.setText(str(rank))
                self.leader_label.setText(get_name(leader_card))

                for i in range(40):
                    card = struct.unpack_from("H", self.deck_data, current.number*41*2 + 2 + i*2)[0] & 0xFFF

                    textedit, indexlabel, cardname = self.card_slots[i][0:3]

                    textedit.setText(str(card))

                    cardname.setText(get_name(card))



                """print(current.xml_ref)
                msg = self.stringfile.messages[current.xml_ref]
                self.lineedit_audioname.setText(msg.get_name())
                self.lineedit_path.setText(msg.get_path())
                self.lineedit_playtime.setText(str(msg.playtime))
                self.textedit_content.setText(msg.get_message())"""
        except:
            traceback.print_exc()
            raise

    #@catch_exception
    def button_load_decks(self):
        try:
            print("ok", self.default_path)
            self.xmlPath = ""
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.default_path,
                "PS2 iso (*.iso);;All files (*)")
            print("doooone")
            if filepath:
                print("resetting")
                self.reset()
                print("done")

                with open(filepath, "rb") as f:
                    try:
                        f.seek(0x2A0A70)
                        self.deck_data = bytearray(f.read(17*41*2)) # 17 starter decks, each 41 bytes
                        f.seek(0x2A1316)
                        self.deck_data += f.read(24*41*2) # 24 CPU decks

                        self.default_path = filepath


                        for i in range(17):
                            leader_byte1, leader_byte2 = struct.unpack_from("BB", self.deck_data, i*41*2)
                            rank = leader_byte2 >> 4
                            leader = ((leader_byte2 & 0x0F) << 8) + leader_byte1
                            deck = YugiohDeckEntry(starter=True, number=i, offset=0x2A0A70+i*41*2)

                            cardname = get_name(leader)

                            deck.setText("[Starter] {0:>7} [rank:{1:>2}] {2}".format(leader, rank, cardname))
                            self.deck_list.addItem(deck)

                        for i in range(17, 17+24):

                            leader_byte1, leader_byte2 = struct.unpack_from("BB", self.deck_data, i*41*2)
                            rank = leader_byte2 >> 4
                            leader = ((leader_byte2 & 0x0F) << 8) + leader_byte1
                            deck = YugiohDeckEntry(starter=False, number=i, offset=0x2A1316+i*41*2
                                                   )

                            cardname = get_name(leader)

                            deck.setText("[CPU] {0:>7} [rank:{1:>1}] {2}".format(leader, rank,cardname))
                            self.deck_list.addItem(deck)

                        print("loaded decks")
                    except Exception as error:
                        print("error", error)

        except Exception as er:
            print("errrorrr", error)
            traceback.print_exc()
        print("loaded")

    def button_save_decks(self):
        if self.deck_data is not None:
            filepath, choosentype = QFileDialog.getSaveFileName(
                self, "Save File",
                self.default_path,
                "PS2 iso (*.iso);;All files (*)")
            print(filepath, "saved")
            if filepath:
                with open(filepath, "r+b") as f:
                    f.seek(0x2A0A70)
                    f.write(self.deck_data[0:17*41*2])
                    f.seek(0x2A1316)
                    f.write(self.deck_data[17*41*2:17*41*2+24*41*2])


                self.default_path = filepath
                set_default_path(filepath)
        else:
            pass # no level loaded, do nothing

    def setup_ui(self):
        self.setObjectName("MainWindow")
        self.resize(820, 760)
        self.setMinimumSize(QSize(720, 560))
        self.setWindowTitle("Yugioh Duelist of Roses - Deck Edit")


        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)


        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.deck_list = QListWidget(self.centralwidget)
        self.horizontalLayout.addWidget(self.deck_list)

        self.vertLayoutWidget = QWidget(self.centralwidget)
        self.verticalLayout = QVBoxLayout(self.vertLayoutWidget)
        self.button_set_deck = QPushButton(self.centralwidget)
        #self.button_remove_message = QPushButton(self.centralwidget)
        #self.button_set_message = QPushButton(self.centralwidget)

        self.button_set_deck.setText("Set Deck")

        self.leader_layoutwidget = QWidget(self.centralwidget)
        self.leader_layout = QHBoxLayout(self.leader_layoutwidget)
        self.leader_layoutwidget.setLayout(self.leader_layout)
        self.lineedit_leader = QLineEdit(self.centralwidget)
        self.leader_label = QLabel(self.centralwidget)

        self.leader_layout.addWidget(self.lineedit_leader)
        self.leader_layout.addWidget(self.leader_label)

        self.lineedit_leader_rank = QLineEdit(self.centralwidget)

        for widget in (self.button_set_deck, self.leader_layoutwidget, self.lineedit_leader_rank):
            self.verticalLayout.addWidget(widget)
        self.cards_scroll = QScrollArea(self.centralwidget)
        self.cards_scroll.setWidgetResizable(True)

        self.card_slots = []
        self.cards_verticalWidget = QWidget(self.centralwidget)
        #self.cards_scroll.setWidget(self.cards_verticalWidget)

        self.cards_vertical = QVBoxLayout(self.centralwidget)
        self.cards_verticalWidget.setLayout(self.cards_vertical)
        self.cards_scroll.setWidget(self.cards_verticalWidget)

        for i in range(40):
            layoutwidget = QWidget(self.centralwidget)
            layout = QHBoxLayout(layoutwidget)
            layoutwidget.setLayout(layout)

            index_text = QLabel(self.centralwidget)
            index_text.setText("{0:>2}".format(i))
            textedit = QLineEdit(self.centralwidget)
            textedit.setMinimumSize(20, 20)
            textedit.setMaximumSize(100, 5000)
            card_name_text = QLabel(self.centralwidget)
            card_name_text.setText("---")
            card_name_text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

            layout.addWidget(index_text)
            layout.addWidget(textedit)
            layout.addWidget(card_name_text)
            self.card_slots.append((textedit, index_text, card_name_text, layout, layoutwidget))

            self.cards_vertical.addWidget(layoutwidget)
            #self.verticalLayout.addWidget(self.card_slots[i])

        #self.verticalLayout.addWidget(self.cards_verticalWidget)
        self.verticalLayout.addWidget(self.cards_scroll)
        self.horizontalLayout.addWidget(self.vertLayoutWidget)

        self.menubar = self.menuBar()#QMenuBar(self)
        #self.menubar.setGeometry(QRect(0, 0, 820, 30))
        #self.menubar.setObjectName("menubar")
        self.file_menu = self.menubar.addMenu("File")#QMenu(self.menubar)
        self.file_menu.setObjectName("menuLoad")
        #self.menubar.addMenu(self.file_menu)


        self.file_load_action = QAction("Load", self)
        self.file_load_action.triggered.connect(self.button_load_decks)
        self.file_menu.addAction(self.file_load_action)
        self.file_save_action = QAction("Save", self)
        self.file_save_action.triggered.connect(self.button_save_decks)
        self.file_menu.addAction(self.file_save_action)

        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        #self.setMenuBar(self.menubar)
        print("done")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)


    bw_gui = DeckEditorMainWindow()

    bw_gui.show()
    err_code = app.exec()
    #traceback.print_exc()
    sys.exit(err_code)
