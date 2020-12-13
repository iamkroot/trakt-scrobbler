import json
import os
import sys
import threading
import time
import appdirs
import confuse
from configparser import ConfigParser
from pathlib import Path
from queue import Queue
from trakt_scrobbler import logger
from trakt_scrobbler.player_monitors.monitor import Monitor

if os.name == 'posix':
    import select
    import socket
elif os.name == 'nt':
    import win32file


class MPVMon(Monitor):
    name = 'mpv'
    exclude_import = True
    WATCHED_PROPS = ['pause', 'path', 'working-directory',
                     'duration', 'time-pos']
    CONFIG_TEMPLATE = {
        "ipc_path": confuse.String(default="auto-detect"),
        "poll_interval": confuse.Number(default=10),
        # seconds to wait while reading data from mpv
        "read_timeout": confuse.Number(default=2),
        # seconds to wait after one file ends to check for the next play
        # usually needed for slow mpv wrappers which may cause delay
        "restart_delay": confuse.Number(default=0.1)
    }

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.ipc_path = self.config['ipc_path']
        self.read_timeout = self.config['read_timeout']
        self.poll_interval = self.config['poll_interval']
        self.restart_delay = self.config['restart_delay']
        self.buffer = ''
        self.ipc_lock = threading.Lock()  # for IPC write queue
        self.poll_timer = None
        self.write_queue = Queue()
        self.sent_commands = {}
        self.command_counter = 1
        self.vars = {}

    @classmethod
    def read_player_cfg(cls, auto_keys=None):
        if sys.platform == "darwin":
            conf_path = Path.home() / ".config" / "mpv" / "mpv.conf"
        else:
            conf_path = (
                Path(appdirs.user_config_dir("mpv", roaming=True, appauthor=False))
                / "mpv.conf"
            )
        mpv_conf = ConfigParser(
            allow_no_value=True, strict=False, inline_comment_prefixes="#"
        )
        mpv_conf.optionxform = lambda option: option
        mpv_conf.read_string("[root]\n" + conf_path.read_text())
        return {
            "ipc_path": lambda: mpv_conf.get("root", "input-ipc-server")
        }

    def run(self):
        while True:
            if self.can_connect():
                self.update_vars()
                self.conn_loop()
                if self.vars['state'] != 0:
                    # create a 'stop' event in case the player didn't send 'end-file'
                    self.vars['state'] = 0
                    self.update_status()
                self.vars = {}
                if self.poll_timer:
                    self.poll_timer.cancel()
                time.sleep(self.restart_delay)
            else:
                logger.info('Unable to connect to MPV. Check ipc path.')
                time.sleep(self.poll_interval)

    def update_status(self):
        fpath = Path(self.vars['working-directory']) / Path(self.vars['path'])

        # Update last known position if player is stopped
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
        self.handle_status_update()

    def update_vars(self):
        """Query mpv for required properties."""
        self.updated_props_count = 0
        for prop in self.WATCHED_PROPS:
            self.send_command(['get_property', prop])
        if self.poll_timer:
            self.poll_timer.cancel()
        self.poll_timer = threading.Timer(self.poll_interval, self.update_vars)
        self.poll_timer.name = 'mpvpoll'
        self.poll_timer.start()

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

    def handle_cmd_response(self, resp):
        command = self.sent_commands[resp['request_id']]['command']
        del self.sent_commands[resp['request_id']]
        if resp['error'] != 'success':
            logger.error(f'Error with command {command!s}. Response: {resp!s}')
            return
        elif command[0] != 'get_property':
            return
        param = command[1]
        data = resp['data']
        if param == 'pause':
            self.vars['state'] = 1 if data else 2
        if param in self.WATCHED_PROPS:
            self.vars[param] = data
            self.updated_props_count += 1
        if self.updated_props_count == len(self.WATCHED_PROPS):
            self.update_status()

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
            logger.warning('Invalid JSON received. Skipping. ' + line, exc_info=True)
            return
        if 'event' in mpv_json:
            self.handle_event(mpv_json['event'])
        elif 'request_id' in mpv_json:
            self.handle_cmd_response(mpv_json)

    def send_command(self, elements):
        with self.ipc_lock:
            command = {'command': elements, 'request_id': self.command_counter}
            self.sent_commands[self.command_counter] = command
            self.command_counter += 1
            self.write_queue.put(str.encode(json.dumps(command) + '\n'))


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
        sock_list = [self.sock]
        while self.is_running:
            r, _, _ = select.select(sock_list, [], [], self.read_timeout)
            if r:  # r == [self.sock]
                # socket has data to be read
                data = self.sock.recv(4096)
                if len(data) == 0:
                    # EOF reached
                    self.is_running = False
                    break
                self.on_data(data)
            while not self.write_queue.empty():
                # block until self.sock can be written to
                select.select([], sock_list, [])
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
        return win32file.GetFileAttributes((self.ipc_path)) == \
            win32file.FILE_ATTRIBUTE_NORMAL

    def conn_loop(self):
        self.is_running = True
        self.file_handle = win32file.CreateFile(
            self.ipc_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None,
            win32file.OPEN_EXISTING,
            0, None
        )
        while self.is_running:
            try:
                while not self.write_queue.empty():
                    win32file.WriteFile(
                        self.file_handle, self.write_queue.get_nowait())
            except win32file.error as e:
                if "The pipe is being closed" not in str(e):
                    logger.debug('Exception while writing to pipe.', exc_info=True)
                self.is_running = False
                break
            size = win32file.GetFileSize(self.file_handle)
            if size > 0:
                while size > 0:
                    # pipe has data to be read
                    _, data = win32file.ReadFile(self.file_handle, 4096)
                    self.on_data(data)
                    size = win32file.GetFileSize(self.file_handle)
            else:
                time.sleep(self.read_timeout)
        win32file.CloseHandle(self.file_handle)
        logger.debug('Pipe closed.')
