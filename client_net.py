
import socket
import re
import select



MAX_DATA_CHUNK = 1024
DELAY_TIME = 500

# data handle
JOIN = "join"
SHAPE = "shape"
LEAVE = "leave"
USERS = "users"
ERROR = "error"
UNK_MSG = "ERR: unknown message received from the server"
COMMA = ','

# send server message
TYPE_IND = 0
USR_IND = 1
SHAPE_IND = 2
COORS_IND = 2

NUM_WORDS_SHAPE_MSG = 5

MSG_DELIM = b'\n'
MSG_SEPER = ';'
READ_TIME = 0.1
X_COOR = 0
Y_COOR = 1
UNK_MSG_SEND = "ERR: unknown message sends to the server"


class Client:
    """
    The client object is manage the connection to the server,
    send and get messages.
    """
    def __init__(self, host, port, usr_name, group, graphic, root):
        self.host = host
        self.port = port
        self.usr_name = usr_name
        self.group = group
        self.gui = graphic
        self.root = root
        self.sock = self.server_con()


    def send_serv_msg(self, str_list, coor_list=[]):
        """
        The method get strings and concatenating them to
        valid server message from type b'data;data;...\n
        :param str_list: list of string
        :param coor_list: (optional) list of tuples represent coordinates
                        of shape
        """
        on_close = False
        serv_msg = ""
        msg_type = str_list[TYPE_IND]

        if msg_type == JOIN:
            for data in str_list:
                serv_msg += data
                serv_msg += MSG_SEPER

        elif msg_type == SHAPE:
            str_coors = ""
            # create string of coordinates from type: "coor_x, coor_y, ..."
            for coors in coor_list:
                str_coors += str(coors[X_COOR])
                str_coors += COMMA
                str_coors += str(coors[Y_COOR])
                str_coors += COMMA
            str_coors = str_coors[:-1]
            # create server message and insert the coordinates in their place
            for index, data in enumerate(str_list):
                if index == COORS_IND:
                    serv_msg += str_coors
                    serv_msg += MSG_SEPER
                serv_msg += data
                serv_msg += MSG_SEPER


        elif msg_type == LEAVE:
            serv_msg += str_list[TYPE_IND]
            serv_msg += MSG_SEPER
            on_close = True

        else:
            print(UNK_MSG_SEND)

        # remove last ';' add '\n' and encode the message
        serv_msg = serv_msg[:-1]
        encoded_msg = bytes(serv_msg,'ascii')
        encoded_msg += MSG_DELIM

        self.sock.sendall(encoded_msg)

        if on_close:
            self.sock.close()



    def server_con(self):
        """
        The method create socket and try to connect the server by host and port
        :return: socket
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host,self.port))
            self.sock = sock
            # build connect message to the server
            self.send_serv_msg([JOIN,self.usr_name,self.group])
            self.get_serv_msg()
            return sock
        except socket.error as err:
            print(str(err))
            exit()


    def get_serv_msg(self):
        """
        The method receives message from the server if there is one,
        and send it to 'data handler' for display it to the user
        """
        reg_msg = ""
        err_msg = ""
        buffer = b''
        sock = self.sock
        first_time = True

        while first_time or buffer != b'':
            first_time = False
            r,w,x= select.select([sock], [], [],READ_TIME)
            if sock in r:
                data = sock.recv(MAX_DATA_CHUNK)
                data = buffer + data
                while MSG_DELIM in data:
                    # save the message from b' to \n
                    reg_msg = data[:data.index(MSG_DELIM)]
                    self.data_handler(reg_msg)
                    data = data [data.index(MSG_DELIM)+1:]
            elif sock in x:
                data = sock.recv(MAX_DATA_CHUNK)
                data = buffer + data
                while MSG_DELIM in data:
                    err_msg = data[:data.index(MSG_DELIM)]
                    self.data_handler(err_msg)
                    data = data [data.index(MSG_DELIM)+1:]
            else:
                break
            buffer = data

        self.root.after(DELAY_TIME,self.get_serv_msg)


    def data_handler(self, server_msg ):
        """
        The method gets message from the server and display it to the user
        according to the content.
        :param server_msg:
        """
        # checks not empty message
        if server_msg == MSG_DELIM:
            return

        msg = server_msg.decode()
        words_list = msg.rsplit(MSG_SEPER)

        # checks more than one word in the message
        if len(words_list) <= 1:
            print(UNK_MSG)
            return

        # gets the msg type
        msg_type = words_list[TYPE_IND]

        if msg_type == JOIN:
            self.gui.add_user_to_gr(words_list[USR_IND])

        elif msg_type == SHAPE:
            if len(words_list) < NUM_WORDS_SHAPE_MSG:
                print(UNK_MSG)
                return
            words_list.pop(TYPE_IND)
            self.gui.add_shape(words_list)

        elif msg_type == USERS:
            words_list.pop(TYPE_IND)
            names_str = words_list[0]
            users_list = names_str.rsplit(COMMA)
            for user in users_list:
                self.gui.add_user_to_gr(user)

        elif msg_type == LEAVE:
            self.gui.remove_user_from_group(words_list[USR_IND])

        elif msg_type == ERROR:
            words_list.pop(TYPE_IND)
            print(words_list[0])

        else:
            print(UNK_MSG)

