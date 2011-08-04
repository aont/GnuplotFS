#!/usr/bin/env python

import os, stat, errno

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

class ImageList:
    def __init__(self):
        self.image_list = []

    def get_image(self, num):
        for gpimage in self.image_list:
            if gpimage.num == num:
                return gpimage
        gpimage = GPImage(num)
        self.image_list.append(gpimage)
        return gpimage

    def del_image(self, num):
        for gpimage in self.image_list:
            if gpimage.num == num:
                self.image_list.remove(gpimage)
                return

image_list = ImageList()

class GPImage:
    def __init__(self, num):
        self.num = num
        gp = subprocess.Popen("gnuplot", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        gp.stdin.write("set terminal png\n")
        gp.stdin.write("plot sin(x+%s)\n" % (num*0.1))
        gp.stdin.write("exit\n")
        self.data = gp.stdout.read()
    
class GnuplotFS(Fuse):
    import re
    fn_re = re.compile("/image_(\d+)\.png")

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        
        
    def getattr(self, path):
        print "getattr:\t%s" % path        
        fn_match = self.__class__.fn_re.match(path)
        st = fuse.Stat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 2
        elif not fn_match == None:
            image_num = int(fn_match.group(1))
            if image_num > 315:
                return -errno.ENOENT

            st.st_mode = stat.S_IFREG | 0444
            st.st_nlink = 1

            #gpimage = GPImage(image_num)
            st.st_size = 1024*1024*1024 # len(gpimage.data)
            #del gpimage

        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        print "readdir:\t%s" % path
        for r in  '.', '..', "image_0.png", "image_1.png", "image_2.png":
            yield fuse.Direntry(r)

    def open(self, path, flags):
        print "open:\t%s" % path
        fn_match = self.__class__.fn_re.match(path)
        if fn_match == None:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

        ffi = fuse.FuseFileInfo()
        ffi.direct_io = True
        return ffi

    def read(self, path, size, offset):
        print "read:\t%s" % path
        fn_match = self.__class__.fn_re.match(path)
        if fn_match == None:
            return -errno.ENOENT

        image_num = int(fn_match.group(1))
        gpimage = image_list.get_image(image_num)        
        slen = len(gpimage.data)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = gpimage.data[offset:offset+size]
        else:
            buf = ''
        return buf
    
    def release(self, path, flags):
        print "release:\t%s" % path
        fn_match = self.__class__.fn_re.match(path)
        if fn_match == None:
            return -errno.ENOSYS
        else:
            image_num = int(fn_match.group(1))
            image_list.del_image(image_num)
            return -errno.ENOSYS

def main():
    server = GnuplotFS(version="gnuplotfs " + fuse.__version__)
    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
