
import tkinter as tk
import sys
from client_net import Client
import re

# General
USAGE_ERR = "Usage : python client.py hostname port user_name group"
VALID_NAME_ERR="Error: username and group can contain only letters and numbers"
COLOR_LIST = ["black", "red", "green", "yellow", "blue", "violet", "orange"]
DEFAULT_COLOR = 0  # Meaning black color
WIDTH_SCREEN = 500
HEIGHT_SCREEN = 500
NORM_FONT = ("Helvetica", 10)

# Messages from client_net
MSG_USERNAME = 0  # index in the client_net messages
MSG_SHAPE = 1
MSG_COOR = 2  # *coordinates
MSG_COLOR = 3

# Messages to client_net
TOPIC = 0  # place of the topic in the list of message elements
JOIN = 'join'
SHAPE = 'shape'
LEAVE = 'leave'

# Coordinates
FIRST_COOR = 0  # in the coordinates list
SECOND_COOR = 1
THIRD_COOR = 2

#Shapes
LINE = ('line', 2)  # the second element is used for counting down the points
# needed to draw each shape
OVAL = ('oval', 2)
RECTANGLE = ('rectangle', 2)
TRIANGLE = ('triangle', 3)
SHAPE_NAME = 0  # the place in the above tuple
SHAPE_COUNTDOWN = 1
DEFAULT_SHAPE = LINE
SHAPE_LIST = [LINE, TRIANGLE, RECTANGLE, OVAL]
TEXT_FIX = 10  # for the text tags near each shape

# Help
HELP_B1 = "Help"
HELP_TITLE = "How to play"
HELP_MSG = """Use the shapes and colors buttons to draw a colored
           shapes for all your friends to see!
           You need to click on three places on the canvas for draw a triangle,
           and to 2 for the all rest of the shapes! So much fun! Can't wait!"""
HELP_B2 = "Got it!"

# Leaving
CLOSE_TITLE = 'Leaving'
CLOSE_MSG = 'Are you sure you want to leave?'
CLOSE_B_TXT = 'Hell yeah!'
CANCEL = 'Hell no!'


class Graphics:
    """
    A class responsible for the client's GUI, for instance: updating
    the group information, draw different shapes in different colors,
    and responding to the help and close buttons. The window will be divided
    into left and right frames
    Note: We are going to use coors=coordinates.
    """
    def __init__(self, parent, user_name, group_name):
        self._client_net = ""  # created because we want Graphics to have an
        # attribute of the Client class from client_net file,
        # but the gui is created first. When Client is created (in __main__)
        # it also makes this attribute not-empty
        # using set_client_net method in Graphics
        self._parent = parent
        self._user_name = user_name
        self._group_name = group_name
        self.users_list = []
        self._cur_shape = DEFAULT_SHAPE
        self._coor_list = [] # for drawing shapes accordingly
        self._canvas_binder = False  # for appending coors to the above list
        # only after pressing a shape button
        self._coor_countdown = DEFAULT_SHAPE[SHAPE_COUNTDOWN]  # will count
        # down according to the current shape the coors for drawing
        # the shape

        # joining
        self._joining(self._user_name)

        # creating right and left frames
        self._left_frame = tk.Frame(self._parent)
        self._left_frame.pack(side=tk.LEFT, fill=tk.BOTH,
                              expand=True)
        self._right_frame = tk.Frame(self._parent)
        self._right_frame.pack(side=tk.LEFT, fill=tk.BOTH,
                               expand=True)

        # parent
        self._window_label(parent, user_name, group_name)
        self._cur_color = tk.StringVar(parent)#needed for the OptionMenu widget

        # left frame
        self._create_help_button(self._left_frame)
        self._create_colors_options(self._left_frame)
        self._users_listbox = self._create_users_listbox(self._left_frame, group_name)

        # right frame
        self._canvas = self._draw_canvas(self._right_frame)
        self._create_shape_button(self._right_frame)

    #################################
    #          Get Methods          #
    #################################
    def get_user_name(self):
        """returns the user_name"""
        return self._user_name

    def get_group_name(self):
        """returns the group's name"""
        return self._group_name

    def get_cur_shape_name(self):
        """return the current shape name"""
        return self._cur_shape[SHAPE_NAME]

    def get_cur_color_str(self):
        """returns color name as a string"""
        return str(self._cur_color.get())

    def get_parent(self):
        """return the parent (root). used for the after method"""
        return self._parent

    #################################
    #      Shape related Methods    #
    #################################
    def _countdowner(self):
        """
        Substracts from the countdown value 1 (which stands for 1 coor has
        been drawn)
        """
        self._coor_countdown -= 1

    def _create_shape_button(self, right_frame):
        """
        Creates the four shapes buttons and assign the shape_event_h to them
        """
        for shape in SHAPE_LIST:
            button = tk.Button(right_frame, text=shape[SHAPE_NAME],
                               command=self._shape_event_h(shape))
            button.pack(side=tk.RIGHT)

    def _coor_appender(self, event):
        """
        Appends coordinates to the coor_list as tuple of (x,y),
        calls the countdowner to reduce the countdown value
        (used by the canvas's 'bind')
        """
        if self._canvas_binder:
            self._countdowner()
            self._coor_list.append((event.x, event.y))
        if self._coor_countdown == 0:  # to make the shape when
            # countdown is zero
            self._shape_event_h(self._cur_shape)

    def _shape_event_h(self, shape):
        """
        Deals with two kinds of events: #1 for choosing a shape
        and counting the coordinates, #2  for calling the client_net method for
        sending the correct shape message.
        It uses the countdown value to decide which inner function it should
        call.
        :param shape: the shape tuple of: name, countdown value
        :return: Inner functions, either shape_press for event #1
        or create_shape for event #2
        """
        def shape_press():
            """Starts the draw initial data gathering process,
            by assigning a shape and 'turning on' the canvas binding"""
            self._coor_list = []  # in case user changes shapes before
            # finishing clicking the canvas, the coordinates will be reset
            self._cur_shape = shape
            self._coor_countdown = shape[SHAPE_COUNTDOWN]
            self._canvas_binder = True

        def create_shape():
            """
            Calls a method from the Client class  with the shape and all the
            needed data, to be sent to the server, using send_to_client method.
            The shapes will be drawn only when the client gets a message
            about it from the server"""
            shape = self.get_cur_shape_name()  # here we're only using
            # the name of the shape
            color = self.get_cur_color_str()
            p1 = self._coor_list[FIRST_COOR]
            p2 = self._coor_list[SECOND_COOR]

            if shape != TRIANGLE[SHAPE_NAME]:  # line, oval and rectangle
                self._send_to_client([SHAPE, shape, color], [p1, p2])
            if shape == TRIANGLE[SHAPE_NAME]:
                # only the triangle needs three coordinates
                p3 = self._coor_list[THIRD_COOR]
                self._send_to_client([SHAPE, shape, color], [p1, p2, p3])

        if self._coor_countdown >= 2:  # meaning the user has just pressed
            # one of the shapes' buttons
            return shape_press
        elif self._coor_countdown == 0:
            create_shape()
            self._reset()

    def add_shape(self, client_message):
        """
        Called by client_net (which gets it from the server)
        as a list of: username, shape, coordinates and color. It will
        use each element for drawing the shape to the gui canvas
        :param client_message: a list of string elements
        """
        user_name = client_message[MSG_USERNAME]
        shape = client_message[MSG_SHAPE]
        color = client_message[MSG_COLOR]
        coors_str = client_message[MSG_COOR]# there might be two or three coors
        coors_list = [int(n) for n in coors_str.split(",")]
        if shape == LINE[SHAPE_NAME]:
            self._canvas.create_line(coors_list, fill=color,
                                             width=2)
        elif shape == RECTANGLE[SHAPE_NAME]:
            self._canvas.create_rectangle(coors_list, fill=color)
        elif shape == OVAL[SHAPE_NAME]:
            self._canvas.create_oval(coors_list, fill=color)
        elif shape == TRIANGLE[SHAPE_NAME]:
            self._canvas.create_polygon(coors_list, fill=color)

        self._canvas.create_text(coors_list[0]-TEXT_FIX,
                                 coors_list[1]-TEXT_FIX,
                                 text=user_name)

    def _reset(self):
        """
        resets the shape, the countdown, the coordinates list
        and the canvas binder attributes
        """
        self._cur_shape = DEFAULT_SHAPE
        self._coor_countdown = DEFAULT_SHAPE[SHAPE_COUNTDOWN]
        self._coor_list = []
        self._canvas_binder = False

    def _draw_canvas(self, right_frame):
        """Draws the canvas and binding it with a left mouse click
        to the _coor_appender method
        :returns: a tk canvas object"""
        canvas = tk.Canvas(right_frame, width=WIDTH_SCREEN,
                           height=HEIGHT_SCREEN,
                           highlightbackground='black', bg='white')
        canvas.pack(side=tk.BOTTOM)
        canvas.bind('<Button-1>', self._coor_appender)
        return canvas

    #################################
    #       Color Methods           #
    #################################
    def _create_colors_options(self, left_frame):
        """Creates an OptionMenu widget for selecting colors"""
        choosing_color = tk.OptionMenu(left_frame,
                                       self._cur_color,
                                       *COLOR_LIST,
                                       command=self._colors_event_handler)
        choosing_color.pack()
        self._cur_color.set(COLOR_LIST[DEFAULT_COLOR])

    def _colors_event_handler(self, color):
        """Changes the current selected color"""
        self._cur_color.set(color)

    #################################
    #       Class Client Methods    #
    #################################

    def set_client_net(self, client):
        """
        Gets client object and insert it to self.client_net
        :param client: object type
        """
        self._client_net = client

    def _send_to_client(self, data_list, coors=[]):
        """
        Calls a Client class method, which will later be sent to the server.
        the messages will deal with the client joining the
        group, drawing a shape and leaving the group.
        data_list: will contain the topic of the message
        and its details e.g.: [join, username, group]
        coors : We want to split the coordinates in the Client class
        therefor when sending a shape message the method will send
        two lists: one is data_list, and one for the coors
        """
        if type(self._client_net) is Client:

            if data_list[TOPIC] == JOIN:

                self._client_net.send_serv_msg(data_list)
            elif data_list[TOPIC] == SHAPE:
                self._client_net.send_serv_msg(data_list, coors)
            elif data_list[TOPIC] == LEAVE:
                self._client_net.send_serv_msg(data_list)

    #################################
    #   Group users list Methods    #
    #################################
    def _create_users_listbox(self, left_frame, group_name):
        """
        Creates the group's users list as a tk listbox object with
        the name of the group, and returns this object. The users
         names will be added in another method
        :param left_frame: the parent of the listbox object
        :param group_name: a string of the group name
        :return: a tk listbox object
        """
        scrollbar = tk.Scrollbar(left_frame, orient=tk.VERTICAL)
        users_list = tk.Listbox(left_frame,
                                height=30, yscrollcommand=scrollbar.set)
        scrollbar.config(command=users_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        users_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.users_list.append(group_name)
        users_list.insert(tk.END, group_name)

        return users_list

    def add_user_to_gr(self, user_name):
        """
        Adds a new user name to the user list (and listbox)
        :param user_name: string of the user name
        """
        users_list = self.users_list
        listbox_users_list = self._users_listbox
        if user_name not in users_list:
            users_list.append(user_name)
            listbox_users_list.insert(tk.END, user_name)

    def remove_user_from_group(self, user_name):
        """
        Removes a user from the users dictionary
        and the users listbox tk object
        :param user_name: string of the user name
        """
        users_list = self.users_list
        listbox_users_list = self._users_listbox
        if user_name in self.users_list:
            indx = self.users_list.index(user_name)
            listbox_users_list.delete(indx)
            del users_list[indx]

    #################################
    #        General Methods        #
    #################################

    def _window_label(self, parent, user_name, group_name):
        """
        creates a label to the client's window with the group_name
        and user_name
        :param user_name:
        :param group_name:
        """
        window_title = user_name + ' : ' + group_name
        parent.wm_title(window_title)

    def _create_help_button(self, parent):
        "Creates a help button leading to the help pop-up"
        help_button = tk.Button(parent, text=HELP_B1,
                                command=self._help_popup)
        help_button.pack()

    def _help_popup(self):
        "Called by the help button"
        help_popup = tk.Toplevel()
        help_popup.wm_title(HELP_TITLE)
        help_label = tk.Label(help_popup, text=HELP_MSG,
                              font=NORM_FONT)
        help_label.pack(side="top", fill="x", pady=10)
        ok_button = tk.Button(help_popup,
                              text=HELP_B2,
                              command=help_popup.destroy)
        ok_button.pack()

    def _joining(self, user_name):
        """Calls a  Client class method about connecting to the group
        through send_to_client method"""
        self._send_to_client([JOIN, user_name])

    def on_close(self):
        """
        Pops up a window when user is quiting.
        """
        close_popup = tk.Toplevel()
        close_popup.wm_title(CLOSE_TITLE)
        close_label = tk.Label(close_popup, text=CLOSE_MSG,
                              font=NORM_FONT)
        close_label.pack(side="top", fill="x", pady=10)
        confirm_button = tk.Button(close_popup,
                                   text=CLOSE_B_TXT,
                                   command=self._send_leaving)
        cancel_button = tk.Button(close_popup,
                                  text=CANCEL,
                                  command=close_popup.destroy)

        confirm_button.pack()
        cancel_button.pack()

    def _send_leaving(self):
        """Lets the server know the client is leaving
        and destroys the GUI"""
        self._send_to_client([LEAVE])
        self._parent.destroy()


def name_check(name):
    """
    The function checks the given name is only from letters and digits
    :param name: string
    :return: True if does otherwise - False
    """
    check_name = re.compile('[a-zA-Z0-9]+$')
    if check_name.match(name):
        return True
    else:
        return False

def main():
    if len(sys.argv) < 5:
        print(USAGE_ERR)
        return

    host, port = sys.argv[1], int(sys.argv[2])
    usr_name, group = sys.argv[3], sys.argv[4]

    if not name_check(usr_name) or not name_check(group):
        print(VALID_NAME_ERR)
        return

    root = tk.Tk()

    gui = Graphics(root, usr_name, group)
    root.protocol("WM_DELETE_WINDOW", gui.on_close)
    client = Client(host, port, usr_name, group, gui, root)
    gui.set_client_net(client)

    root.mainloop()

if __name__ == '__main__':
    main()