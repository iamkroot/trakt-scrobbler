import json
import logging
import os
import threading
import time
from pathlib import Path
from queue import Queue
from player_monitors.monitor import Monitor
from utils import config

if os.name == 'posix':
    import select
    import socket

logger = logging.getLogger('trakt_scrobbler')


class MPVMon(Monitor):
    name = 'mpv'
    exclude_import = True

    def __init__(self, scrobble_queue):
        try:
            mpv_config = config['players']['mpv']
            self.ipc_path = mpv_config['ipc_path']
        except KeyError:
            logger.error('Check config for correct MPV params.')
            return
        super().__init__(scrobble_queue)
        self.buffer = ''
        self.lock = threading.Lock()
        self.write_queue = Queue()
        self.sent_commands = {}
        self.command_counter = 1
        self.watched_vars = ['pause', 'path',
                             'working-directory', 'duration', 'time-pos']
        self.vars = {}
        self.status = {}

    def update_status(self):
        fpath = Path(self.vars['working-directory']) / Path(self.vars['path'])
        pos = self.vars['time-pos']
        if self.vars['state'] == 0 and self.status['state'] == 2:
            pos += round(time.time() - self.status['time'], 3)
        self.status = {
            'state': self.vars['state'],
            'filepath': str(fpath),
            'position': pos,
            'duration': self.vars['duration'],
            'time': time.time()
        }
        self.send_to_queue()

    def update_vars(self):
        self.updated = []
        for var in self.watched_vars:
            self.send_command(['get_property', var])

    def run(self):
        while True:
            if self.can_connect():
                self.conn_loop()
                time.sleep(1)
            else:
                logger.info('Unable to connect to MPV. Check ipc path.')
                time.sleep(10)

    def on_data(self, data):
        self.buffer = self.buffer + data.decode('utf-8')
        while True:
            line_end = self.buffer.find('\n')
            if line_end == -1:
                # partial line received
                # self.on_line() is called in next data batch
                break
            else:
                self.on_line(self.buffer[:line_end])  # doesn't include \n
                self.buffer = self.buffer[line_end + 1:]  # doesn't include \n

    def on_line(self, line):
        try:
            mpv_json = json.loads(line)
        except json.JSONDecodeError:
            logger.warning('Invalid JSON received. Skipping. ' + line)
            return
        if 'event' in mpv_json:
            self.handle_event(mpv_json['event'])
        elif 'request_id' in mpv_json:
            self.handle_cmd_response(mpv_json)

    def send_command(self, elements):
        with self.lock:
            command = {'command': elements, 'request_id': self.command_counter}
            self.sent_commands[self.command_counter] = command
            self.command_counter += 1
            self.write_queue.put(str.encode(json.dumps(command) + '\n'))

    def handle_event(self, event):
        if event == 'end-file':
            self.vars['state'] = 0
            self.update_status()
        elif event == 'pause':
            self.vars['state'] = 1
            self.update_vars()
        elif event == 'unpause' or event == 'playback-restart':
            self.vars['state'] = 2
            self.update_vars()
        else:
            return

    def handle_cmd_response(self, resp):
        command = self.sent_commands[resp['request_id']]['command']
        if resp['error'] != 'success':
            logger.error(f'Error with command {command!s}. Response: {resp!s}')
            return
        elif command[0] != 'get_property':
            return
        param = command[1]
        data = resp['data']
        if param == 'pause':
            self.vars['state'] = 1 if data else 2
        if param in self.watched_vars:
            self.vars[param] = data
            self.updated.append(param)
        if len(self.updated) == len(self.watched_vars):
            self.update_status()


class MPVPosixMon(MPVMon):
    exclude_import = os.name != 'posix'

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.sock = socket.socket(socket.AF_UNIX)

    def can_connect(self):
        sock = socket.socket(socket.AF_UNIX)
        errno = sock.connect_ex(self.ipc_path)
        sock.close()
        return errno == 0

    def conn_loop(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(self.ipc_path)
        self.is_running = True
        self.update_vars()
        while self.is_running:
            r, _, e = select.select([self.sock], [], [], 0.1)
            if r == [self.sock]:
                # socket has data to read
                data = self.sock.recv(4096)
                if len(data) == 0:
                    # EOF reached
                    self.is_running = False
                self.on_data(data)
            while not self.write_queue.empty():
                # block until self.sock can be written to
                select.select([], [self.sock], [])
                try:
                    self.sock.sendall(self.write_queue.get_nowait())
                except BrokenPipeError:
                    self.is_running = False
        self.sock.close()
        logger.debug('Sock closed')


class MPVWinMon(MPVMon):
    exclude_import = os.name != 'nt'

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.file_handle = None

    def can_connect(self):
        return os.path.exists(self.ipc_path)

    def conn_loop(self):
        self.is_running = True
        self.update_vars()
        with open(self.ipc_path, 'rb+', 0) as f:
            while True:
                while not self.write_queue.empty():
                    f.write(self.write_queue.get_nowait())
                data = f.read(4096)
                if not data:
                    break
                self.on_data(data)
                time.sleep(1)
        logger.debug('Pipe closed.')
        self.is_running = False
