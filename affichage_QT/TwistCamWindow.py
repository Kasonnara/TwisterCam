import sys

import time
from PyQt4 import QtGui

from PyQt4.QtCore import QSize, QObject, pyqtSignal, Qt
from PyQt4.QtGui import QApplication, QDesktopWidget, QVBoxLayout, QBoxLayout, QHBoxLayout

from LifeWidget import LifeWidget
from TimerWidget import TimerWidget
from PoseWidget import PoseWidget


class TwistCamWindow:

    def __init__(self, ressource_directory,
                 validation_callback: callable,
                 exit_callback: callable,
                 play_callback: callable,
                 screen_id=-1,
                 nb_player=1,
                 nb_life=3,
                 timer_proportions=(0.14, 0.25),
                 life_proportions=(0.12, 0.75),
                 player_proportions=(1, 0.7),
                 player_spacing_proportion=0.33,
                 border_proportion=0.03,
                 multi_life_spacing_proportion=0.12,
                 alpha_color="FF00FF",
                 validate_keys=(65, 32, 16777220, 43), # keys : 'a', space, enter, '+'
                 dev_mode=False):

        if dev_mode:  # TODO utiliser logger
            print(" Initalisation TwistCanWindow (en mode développeur)")
        # ----- Init de la fenêtre -----
        self.main_app = QApplication(sys.argv)
        self.main_app.setOverrideCursor(Qt.BlankCursor)

        # ----- Analyse des paramètres du constructeur -----
        # Ajouter le '#' dans les html color
        if type(alpha_color) == str and len(alpha_color) == 6:
            alpha_color = "#" + alpha_color

        self.validate_keys = validate_keys
        self.validation_callback = validation_callback
        self.play_callback = play_callback

        self.exit_callback = exit_callback

        # récupérer les dimension de l'écran selectioné
        if screen_id < 0:
            screen_id = QDesktopWidget().screenCount()
        screen_size = QDesktopWidget().screenGeometry(screen_id).size()
        border_size = screen_size.width() * border_proportion
        timer_size = QSize(round((screen_size.width() - border_size * 2) * timer_proportions[0]),
                           round((screen_size.height() - border_size * 2) * timer_proportions[1]))
        player_size = QSize(round(screen_size.width() * player_proportions[0]),
                            round(screen_size.height() * player_proportions[1]))
        life_size = QSize(round((screen_size.width() - border_size * 2) * life_proportions[0]),
                          round((screen_size.height() - border_size * 2) * life_proportions[1]))

        # ----- Construction de l'interface -----
        # Pose widget
        if dev_mode:
            print("  Initialisation Background")
        self.pose_widget = PoseWidget(ressource_directory, screen_size, player_size,
                                      player_spacing_proportion, alpha_color=alpha_color,
                                      key_press_event_callback=self.keyPressEventCallback,
                                      dev_mode=dev_mode)
        self.pose_widget.setWindowTitle("TwistCam")
        # self.setWindowIcon(QtGui.QIcon('web.png'))
        print("Déplacement du jeu sur l'écran le plus a droite [==>]")
        # TODO impove avec l'id du screen
        self.pose_widget.move(QDesktopWidget().width() - 1, 0)
        self.pose_widget.showFullScreen()
        # Pose Layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(border_size, border_size, border_size, border_size)
        self.pose_widget.setLayout(main_layout)
        # Timer
        push_right_layout = QBoxLayout(QBoxLayout.RightToLeft)
        main_layout.addLayout(push_right_layout)
        self.timer = TimerWidget(ressource_directory,
                                 timer_size,
                                 dev_mode=dev_mode)  # TODO setup clock_dim and clock_color from config
        push_right_layout.addWidget(self.timer)
        push_right_layout.setSpacing(0)
        push_right_layout.addSpacing(screen_size.width() - 2 * border_size - timer_size.width())
        # Lifes
        if nb_player == 1:
            # setup special pour 1 seul joueur
            push_right_layout_2 = QBoxLayout(QBoxLayout.RightToLeft)
            push_right_layout_2.setSpacing(0)
            main_layout.addLayout(push_right_layout_2)
            self.lifes = [LifeWidget(ressource_directory, life_size, nb_life, dev_mode=dev_mode)]
            push_right_layout_2.addWidget(self.lifes[0])
            push_right_layout_2.addSpacing(
                screen_size.width() - 2 * border_size - life_size.width() - (timer_size.width() - life_size.width()))
        else:
            multi_life_layout = QHBoxLayout()
            life_size.setWidth(self.pose_widget.player_pixel_spacing * nb_player)
            life_offset = (screen_size.width() - 2 * border_size - life_size.width()) * 0.5
            multi_life_layout.setContentsMargins(life_offset, 0, life_offset, 0)
            multi_life_layout.setSpacing(self.pose_widget.player_pixel_spacing * multi_life_spacing_proportion)
            self.lifes = [LifeWidget(ressource_directory,
                                     QSize(self.pose_widget.player_pixel_spacing * (1 - multi_life_spacing_proportion),
                                           life_size.height()),
                                     nb_life, dev_mode=dev_mode)
                          for k in range(nb_player)]
            for life in self.lifes:
                multi_life_layout.addWidget(life)
            main_layout.addSpacing(screen_size.height() - 2 * border_size - timer_size.height() - life_size.height())
            main_layout.addLayout(multi_life_layout)
        # ----- Signaux -----
        self.s = self.Signaux(self)

    def set_lifes_alive(self, nbs_alive):
        """
        Set l'état vivant/mort des coeurs des différents LifeWidget.
        :param nbs_alive: int tuple, un tuple indiquant pour chaque LifeWidget le nombre de coeur mort.
        :return: None
        :raise: ValueError, si le nombre d'int fourni ne correspond pas au nombre de LifeWidget.
        """
        if not len(nbs_alive) == len(self.lifes):
            raise ValueError("Nombre de valeures fournies (%d) différent du nombre de LifeWidget (%d)"
                             % (len(nbs_alive), len(self.lifes)))
        for i, life in enumerate(self.lifes):
            life.set_alive(nbs_alive[i])

    def set_poses_visibility(self, new_states):
        """
        Set l'état visible/cache des différents LifeWidget et des silhouettes.
        :param new_states: boolean tuple
        :return: None
        :raise: ValueError, si le nombre de boolean fourni ne correspond pas au nombre de LifeWidget.
        """
        if not len(new_states) == len(self.lifes):
            raise ValueError("Nombre de valeures fournies (%d) différent du nombre de LifeWidget (%d)"
                             % (len(new_states), len(self.lifes)))
        for i, life in enumerate(self.lifes):
            life.setVisibleKeepingSpace(new_states[i])

    def force_exit(self):
        # TODO balancer l'animation plutot que de couper
        print(" |Display jeu : commande force_exit")
        self.pose_widget.setWindowState(Qt.WindowMinimized)
        self.pose_widget.setWindowOpacity(0)
        self.exit_callback()
        self.main_app.exit()

    # ----- Key reaction -----
    def keyPressEventCallback(self, e):
        #print(e.key())
        if e.key() == Qt.Key_Escape:
            self.force_exit()
        elif e.key() in self.validate_keys:
            self.validation_callback(self.validate_keys.index(e.key()))
        elif e.key() == 80:  # Todo config key
            self.play_callback()

    class Signaux(QObject):
        set_timer = pyqtSignal(int)
        set_poses = pyqtSignal(tuple)
        set_lifes_alive = pyqtSignal(list)
        set_poses_visibility = pyqtSignal(tuple)
        update_pose = pyqtSignal()
        force_exit = pyqtSignal()

        def __init__(self, tc_win):
            super().__init__()
            self.target = tc_win
            self.set_timer.connect(tc_win.timer.set_timer_value)
            self.set_poses.connect(tc_win.pose_widget.set_poses)
            self.set_lifes_alive.connect(tc_win.set_lifes_alive)
            self.set_poses_visibility.connect(tc_win.set_poses_visibility)
            self.update_pose.connect(tc_win.pose_widget.repaint)
            self.force_exit.connect(tc_win.force_exit)


def color_switching(tc_win, player_id, first_color, second_color, period, duration):
    print("color switching start")
    first_color = QtGui.QColor(first_color)
    second_color= QtGui.QColor(second_color)
    for k in range(round(duration / period)):
        tc_win.pose_widget.colors[player_id] = first_color
        #tc_win.s.update_pose.emit()
        time.sleep(period * 0.5)
        print("color toggle")
        tc_win.pose_widget.colors[player_id] = second_color
        #tc_win.s.update_pose.emit()
        tc_win.s.set_timer.emit()
        time.sleep(period * 0.5)
    print('color switching end.')

if __name__ == "__main__":
    print("TwistCamWindow test start...")
    ressources = "../ressources/"
    ALPHA_COLOR = "FF00FF"
    for k in range(1, 4):
        tc_win = TwistCamWindow(ressources, -1, k,
                                timer_proportions=((0.14, 0.25) if k == 1 else (0.21, 0.40)),
                                life_proportions=((0.12, 0.75) if k == 1 else (1., 0.15)),
                                alpha_color=ALPHA_COLOR,
                                dev_mode=False)
        tc_win.pose_widget.set_poses(list(tc_win.pose_widget.pose_dict.keys())[2:k + 2])
        tc_win.pose_widget.show()
        tc_win.main_app.exec_()
        del tc_win.main_app
    print("TwistCamWindow test finished.")
    sys.exit()
