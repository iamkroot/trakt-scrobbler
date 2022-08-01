import logging
import queue
import time

from clikit.api.io.output import VERBOSE

from .command import Command


class TestCommand(Command):
    """
    Test player-monitor connection.

    test
        {player : Name of the monitor}
    """
    def get_monitor(self, name):
        import confuse
        from trakt_scrobbler import config
        from trakt_scrobbler.player_monitors import collect_monitors
        all_monitors = collect_monitors()
        monitors = {Mon.name: Mon for Mon in all_monitors if isinstance(Mon.name, str)}

        try:
            Mon = monitors[name]
        except KeyError:
            names = ", ".join(sorted(map(str, monitors)))
            self.line(f"Unknown monitor '{name}'. Should be one of {names}", "error")
            raise SystemExit(1)

        templ = confuse.StrSeq(default=[])
        allowed_monitors = config['players']['monitored'].get(templ)
        if name not in allowed_monitors:
            names = ", ".join(sorted(allowed_monitors))
            self.line(f"{name} is not in list of allowed_monitors ({names})", "comment")
            cmd = f"trakts config set --add players.monitored {name}"
            self.line(f"Hint: Use <info>{cmd}</> to monitor it.")

        return Mon

    def add_log_handler(self):
        """Output the log messages to stdout too"""
        from trakt_scrobbler import logger
        h = logging.StreamHandler()
        if self.io.is_debug():
            level = logging.DEBUG
        elif self.io.is_verbose():
            level = logging.INFO
        else:
            level = logging.WARNING
        h.setLevel(level)
        logger.addHandler(h)

    def init_monitor(self, Mon, queue):
        mon = Mon(queue)
        if not mon or not mon._initialized:
            self.line(f"Could not start monitor for {Mon.name}", "error")
            raise SystemExit(1)
        mon.setDaemon(True)
        return mon

    def wait_for_connection(self, mon):
        pi = self.progress_indicator()
        pi.start("Trying to connect")
        for _ in range(600):  # wait for a minute
            if mon.can_connect():
                pi.finish("Connected", reset_indicator=True)
                break
            pi.advance()
            time.sleep(0.1)
        else:
            pi.finish("Timed out", reset_indicator=True)
            raise SystemExit(1)

    def pretty_print_status(self, status):
        _, data = status
        media_info = data['media_info']
        progress = data['progress']
        self.write("Playing ")
        self.write(media_info['title'], "info")
        if media_info['type'] == 'episode':
            self.write(" S{season:02}E{episode:02}".format(**media_info), "info")
        self.line(f" at {progress:.2f}%")

    def _handle(self):
        name = self.argument("player")
        Mon = self.get_monitor(name)

        self.add_log_handler()

        self.comment(f"Testing connection with {name}.")
        self.line(f"Please ensure that {name} is playing some media.")

        dummy_queue = queue.Queue()
        mon = self.init_monitor(Mon, dummy_queue)
        self.wait_for_connection(mon)

        self.line("Starting monitor", "info", verbosity=VERBOSE)
        mon.start()

        try:
            with self.spin("Waiting for events", "Got info"):
                status = dummy_queue.get(block=True, timeout=15)
        except queue.Empty:
            self.line("Timed out fetching events from player", "error")
            raise SystemExit(1)
        else:
            self.pretty_print_status(status)

    def handle(self):
        try:
            return self._handle()
        except SystemExit as e:
            if not self.io.is_debug():
                self.line("<info>Hint:</> Try re-running <comment>trakts test</> with"
                          " '<comment>-vvv</>' to enable more debug logging.")
            return e.code
