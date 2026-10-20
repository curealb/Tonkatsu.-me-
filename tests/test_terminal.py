from __future__ import annotations
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import unittest
from tonkatsu.timeline import ROOT


@unittest.skipUnless(os.name=='posix','PTY integration is POSIX-only')
class TerminalTests(unittest.TestCase):
    def exercise(self,terminate=False):
        import pty
        import termios
        import fcntl
        import struct
        master,slave=pty.openpty()
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
        original=termios.tcgetattr(slave)
        proc=subprocess.Popen([sys.executable,str(ROOT/'player.py'),'--demo','--autoplay'],
                              stdin=slave,stdout=slave,stderr=slave,cwd=ROOT)
        output=bytearray()
        try:
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and b'Tonkatsu.(me)' not in output:
                if select.select([master],[],[],.1)[0]: output.extend(os.read(master,65536))
            self.assertIn(b'Tonkatsu.(me)',output)
            if terminate:
                proc.send_signal(signal.SIGTERM)
            else:
                os.write(master,b' m\x1b[Crq')
            while proc.poll() is None and time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]: output.extend(os.read(master,65536))
            self.assertEqual(proc.wait(timeout=2),0)
            while select.select([master],[],[],.05)[0]: output.extend(os.read(master,65536))
            self.assertEqual(termios.tcgetattr(slave),original)
            self.assertIn(b'\x1b[?1049l',output)
        finally:
            if proc.poll() is None: proc.kill();proc.wait(timeout=2)
            os.close(master);os.close(slave)

    def test_transport_keys_and_quit_restore_terminal(self): self.exercise()
    def test_sigterm_restores_terminal(self): self.exercise(terminate=True)
