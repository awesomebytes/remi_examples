#!/usr/bin/env python

import subprocess
import tempfile
import os
import signal
import time
from threading import Thread

import remi.gui as gui
from remi import start, App


# Threaded function snippet
def threaded(fn):
    """To use as decorator to make a function call threaded.
    Needs import
    from threading import Thread"""
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


class ShellCmd:
    """Helpful class to spawn commands and keep track of them"""

    def __init__(self, cmd):
        self.retcode = None
        self.outf = tempfile.NamedTemporaryFile(mode="w")
        self.errf = tempfile.NamedTemporaryFile(mode="w")
        self.inf = tempfile.NamedTemporaryFile(mode="r")
        self.process = subprocess.Popen(cmd, shell=True, stdin=self.inf,
                                        stdout=self.outf, stderr=self.errf,
                                        preexec_fn=os.setsid, close_fds=True)

    def __del__(self):
        if not self.is_done():
            self.kill()
        self.outf.close()
        self.errf.close()
        self.inf.close()

    def get_stdout(self):
        with open(self.outf.name, "r") as f:
            return f.read()

    def get_stderr(self):
        with open(self.errf.name, "r") as f:
            return f.read()

    def get_retcode(self):
        """Get retcode or None if still running"""
        if self.retcode is None:
            self.retcode = self.process.poll()
        return self.retcode

    def is_done(self):
        return self.get_retcode() is not None

    def is_succeeded(self):
        """Check if the process ended with success state (retcode 0)
        If the process hasn't finished yet this will be False."""
        return self.get_retcode() == 0

    def kill(self):
        self.retcode = -1
        os.killpg(self.process.pid, signal.SIGTERM)
        self.process.wait()


class MyApp(App):
    def __init__(self, *args):
        super(MyApp, self).__init__(*args)

    def main(self):
        container = gui.VBox()
        self.hor_box = gui.HBox()
        self.hor_box2 = gui.HBox()

        self.execute_bt = gui.Button('Execute')
        self.cancel_bt = gui.Button('Cancel')
        self.cancel_bt.set_enabled(False)
        self.txt = gui.TextInput(width=300, hint='command...')
        self.txt.set_on_enter_listener(self.on_execute_pressed)
        self.stdout_label = gui.Label("Output:")
        self.cmd_stdout_label = gui.Label("",
                                          width=500, height=300,
                                          single_line=False)
        self.cmd_stdout_label.style['border'] = '1px solid'
        self.stderr_label = gui.Label("Error: ")
        self.cmd_stderr_label = gui.Label("",
                                          width=500, height=300,
                                          single_line=False)
        self.cmd_stderr_label.style['border'] = '1px solid'

        # setting the listener for the onclick event of the button
        self.execute_bt.set_on_click_listener(self.on_execute_pressed)
        self.cancel_bt.set_on_click_listener(self.on_cancel_pressed)

        self.hor_box.append(self.txt)
        self.hor_box.append(self.execute_bt)
        self.hor_box.append(self.cancel_bt)

        self.hor_box2.append(self.stdout_label)
        self.hor_box2.append(self.cmd_stdout_label)
        self.hor_box2.append(self.stderr_label)
        self.hor_box2.append(self.cmd_stderr_label)

        # appending a widget to another, the first argument is a string key
        container.append(self.hor_box)
        container.append(self.hor_box2)
        container.append(self.hor_box3)

        self.cmd = None

        # returning the root widget
        return container

    # listener function
    def on_execute_pressed(self, widget, *args, **kwargs):
        print("Executing command: " + self.txt.get_text())
        self.execute_bt.set_enabled(False)
        self.cancel_bt.set_enabled(True)
        self.execute_and_track_command()

    @threaded
    def execute_and_track_command(self):
        self.cmd = ShellCmd(self.txt.get_text())
        while self.cmd is not None and not self.cmd.is_done():
            self.cmd_stdout_label.set_text(self.cmd.get_stdout())
            self.cmd_stderr_label.set_text(self.cmd.get_stderr())
            time.sleep(0.1)

        print("Command done.")
        self.cmd = None
        self.cancel_bt.set_enabled(False)
        self.execute_bt.set_enabled(True)

    def on_cancel_pressed(self, widget):
        print("Canceled command.")
        if self.cmd is not None:
            self.cmd.kill()
            self.cmd = None
        self.cancel_bt.set_enabled(False)
        self.execute_bt.set_enabled(True)


if __name__ == '__main__':
    # starts the webserver
    start(MyApp)
