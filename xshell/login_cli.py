#! python3
import winreg
import re
import os
from glob import glob
import subprocess as sp

'''
这个脚本是win下xshell6版本的脚本, 目的是能够自动链接剪贴板里的ip地址.
'''

class PowerShell:
    # from scapy
    def __init__(self, coding, ):
        cmd = [self._where('PowerShell.exe'),
               "-NoLogo", "-NonInteractive",  # Do not print headers
               "-Command", "-"]  # Listen commands from stdin
        startupinfo = sp.STARTUPINFO()
        startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
        self.popen = sp.Popen(cmd, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT, startupinfo=startupinfo)
        self.coding = coding

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.popen.kill()

    def run(self, cmd, timeout=15):
        b_cmd = cmd.encode(encoding=self.coding)
        try:
            b_outs, errs = self.popen.communicate(b_cmd, timeout=timeout)
        except sp.TimeoutExpired:
            self.popen.kill()
            b_outs, errs = self.popen.communicate()
        outs = b_outs.decode(encoding=self.coding)
        return outs, errs

    @staticmethod
    def _where(filename, dirs=None, env="PATH"):
        """Find file in current dir, in deep_lookup cache or in system path"""
        if dirs is None:
            dirs = []
        if not isinstance(dirs, list):
            dirs = [dirs]
        if glob(filename):
            return filename
        paths = [os.curdir] + os.environ[env].split(os.path.pathsep) + dirs
        try:
            return next(os.path.normpath(match)
                        for path in paths
                        for match in glob(os.path.join(path, filename))
                        if match)
        except (StopIteration, RuntimeError):
            raise IOError("File not found: %s" % filename)

def documentsPath():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    path = winreg.QueryValueEx(key, r"Personal")[0]
    return path


def removePub(ip, port=22):
    doc_path = documentsPath()
    pub_paths = [os.path.join(doc_path, r"NetSarang Computer\6\SECSH\HostKeys", "key_{0}_{1}.pub".format(ip, port)),
                 os.path.join(doc_path, r"NetSarang Computer\7\SECSH\HostKeys", "key_{0}_{1}.pub".format(ip, port))]

    for pub_path in pub_paths:
        if os.path.exists(pub_path):
            os.remove(pub_path)


def Main():
    # if xsh.Session.RemoteAddress or xsh.Session.Connected:
    if xsh.Session.Connected:
        xsh.Dialog.MsgBox("请新开本地选项卡后再试(Shift+Alt+N)")
        return
    xsh.Screen.Synchronous = True
    with PowerShell('GBK') as ps:
        outs, errs = ps.run('Get-Clipboard')
    iplist = re.findall(r"\b[012]?\d{1,2}(?:\.[012]?\d{1,2}){3}\b", outs)
    if not iplist:
        return
    for ip in iplist:
        removePub(ip)
    xsh.Screen.Send("ssh " + "; ".join(iplist) + "\r")
