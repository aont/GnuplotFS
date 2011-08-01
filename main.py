#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import os, stat, errno
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse

import subprocess

if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

def get_image(num):
    gp = subprocess.Popen("/opt/local/bin/gnuplot", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    gp.stdin.write("set terminal png\n")
    gp.stdin.write("plot sin(x+%s)\n" % (num*0.1))
    gp.stdin.write("exit\n")
    return gp.stdout.read()

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


import re
fn_re = re.compile("/image_(\d+)\.png")


class HelloFS(Fuse):
    def getattr(self, path):
        fn_match = fn_re.match(path)
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 2
        elif not fn_match == None:
            st.st_mode = stat.S_IFREG | 0444
            st.st_nlink = 1
            image_num = int(fn_match.group(1))
            image = get_image(image_num)
            st.st_size = len(image)
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', "image_0.png":
            yield fuse.Direntry(r)

    def open(self, path, flags):
        print "open:\t%s" % path
        fn_match = fn_re.match(path)
        if fn_match == None:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        fn_match = fn_re.match(path)
        if fn_match == None:
            return -errno.ENOENT

        image_num = int(fn_match.group(1))
        image = get_image(image_num)        
        slen = len(image)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = image[offset:offset+size]
        else:
            buf = ''
        return buf

def main():
    usage="""
processfs usage

""" + Fuse.fusage
    server = HelloFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
