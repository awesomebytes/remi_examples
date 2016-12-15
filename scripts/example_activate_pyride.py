#!/usr/bin/env python

# For ShellCmd, from https://gist.github.com/awesomebytes/fd1dba778c3569d09702
import subprocess
import tempfile
import os
import signal

# For PyRIDECommander, from
# https://gist.github.com/awesomebytes/a852e34cd6965173244247ea5ce069ff
import telnetlib
from ast import literal_eval

# For REMI, https://github.com/dddomodossola/remi
# or my ROS wrapper, https://github.com/awesomebytes/remi_ros
import remi.gui as gui
from remi import start, App

"""
Example web interface to start and use
some software in the robot.
Access http://robot-ip:8111 from any device in the network.

Author: Sammy Pfeiffer <Sammy.Pfeiffer at student.uts.edu.au>
"""


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


class PyRIDECommander(object):
    prompt = '>>> '

    def __init__(self, hostname="pr2", port=27005):
        self.tn = telnetlib.Telnet(hostname, port)
        # So we clean up
        self.tn.read_until(self.prompt)
        self.last_output = None

    def send_command(self, command):
        """
        Send command, at \r\n if needed.

        :param str command: text command
        """
        # Fix needed \r\n in the end
        if not command.endswith('\r\n'):
            command += '\r\n'
        self.last_command = command[:-2]
        self.tn.write(command)
        tmp_output = self.tn.read_until(self.prompt)

        if len(tmp_output) > (len(command) + len(self.prompt)):
            self.last_output = tmp_output[len(command):-len(self.prompt)]
        else:
            self.last_output = None

        if self.last_output is not None:
            try:
                self.last_output = literal_eval(self.last_output)
            except SyntaxError:
                pass
        return self.last_output

    def get_last_output(self):
        return self.last_output

    def get_last_command(self):
        return self.last_command

    def close(self):
        self.tn.close()

    def __del__(self):
        try:
            self.tn.close()
        except Exception as e:
            print("Exception on __del__: " + str(e))


class MyApp(App):
    def __init__(self, *args):
        super(MyApp, self).__init__(*args)

    def main(self):
        container = gui.VBox()

        horizontal_container_buttons = gui.HBox()

        self.launch_bt = gui.Button('Launch PyRIDE PR2')
        self.launch_bt.set_on_click_listener(self.on_launch_bt_pressed)
        self.stop_bt = gui.Button('Stop PyRIDE PR2')
        self.stop_bt.set_on_click_listener(self.on_stop_bt_pressed)
        horizontal_container_buttons.append(self.launch_bt)
        horizontal_container_buttons.append(self.stop_bt)
        container.append(horizontal_container_buttons)

        horizontal_container = gui.HBox()
        self.say_input = gui.TextInput(width=300, hint='say...')
        self.say_input.set_on_enter_listener(self.on_say)
        self.say_button = gui.Button('Say')
        self.say_button.set_on_click_listener(self.on_say)
        horizontal_container.append(self.say_input)
        horizontal_container.append(self.say_button)

        container.append(horizontal_container)

        # returning the root widget
        return container

    def on_launch_bt_pressed(self, widget):
        self.cmd = ShellCmd("roslaunch pyride_pr2 pyride.launch")

    def on_stop_bt_pressed(self, widget):
        # Big command that:
        #                           checks all processes
        #                                        only the ones that have pyride.launch
        #                                                           not the grep itself
        #                                                                          second column is the PID
        #                      kill all those PIDS
        self.cmd_kill = ShellCmd("kill `ps aux | grep pyride.launch | grep -v grep | awk '{print $2}'`")

    def on_say(self, widget, *args, **kwargs):
        self.prc = PyRIDECommander()
        text = self.say_input.get_text()
        self.prc.send_command('PyPR2.say("' + text + '")')


if __name__ == '__main__':
    # starts the webserver
    start(MyApp,
          address='0.0.0.0',
          port=8111,
          websocket_port=8082,
          host_name='138.25.61.21')
    # host_name can be pr2 if no phones are accessing
