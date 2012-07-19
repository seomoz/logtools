#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2011 SEOmoz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys, os
import glob

# C l a s s e s

class ConcatLogReader(object):
    '''Given a set of related logs, read from them as if they were one
    big concatenated file.'''

    def __init__(self, prefix, reverse=False, read_current=False):
        dot = '' if read_current else '.'
        self.fileList = glob.glob(prefix + dot + '*')
        self.fileList.sort(reverse=not reverse)
        self._nextfile()

    def _nextfile(self):
        self.currentFile = open(self.fileList.pop()) if self.fileList else None

    def readline(self):
        # We've read all our files all the way through. EOF.
        if not self.currentFile:
            return ''

        # There's more in this file. Return it
        ret = self.currentFile.readline()
        if ret != '':
            return ret

        # No more in this file, try the next one.
        self.currentFile.close()
        self._nextfile()
        return self.readline()

class MergingLogCache(object):

    # Starting and ending positions of [yyyy-mm-dd hh:mm:ss,ccc]
    opening = 0
    closing = 24
    start = opening + 1
    minSize = closing + 1

    def __init__(self, prefix, rev, cur):
        self.reader = ConcatLogReader(prefix, reverse=rev, read_current=cur)
        self._doread()

    # Exception traces don't start with [date] and are a pain to deal
    # with, so throw 'em out.
    def _doread(self):
        while True:
            self.lookAhead = self.reader.readline()
            if self.lookAhead == '' or \
               (len(self.lookAhead) > MergingLogCache.minSize \
                and self.lookAhead[MergingLogCache.opening] == '[' \
                and self.lookAhead[MergingLogCache.closing] == ']'):
                break

    def peekline(self):
        return self.lookAhead

    def peekkey(self):
        # At EOF, return something huge so other file gets used
        if self.lookAhead == '':
            return '9999-99-99 99:99:99,999'
        return self.lookAhead[MergingLogCache.start:MergingLogCache.closing]

    def readline(self):
        ret = self.lookAhead
        if ret != '':
            self._doread()
        return ret

class MergingLogReader(object):
    '''A merging reader for attercob logs.'''

    # Note that the .1, .2, .3 files produced by logrotate are in
    # "reversed" order, but things suffixed with yyyymmdd are in
    # "normal" order.
    def __init__(self, logPrefixA, logPrefixB, reverse=False, read_current=False):
        self.aCache = MergingLogCache(logPrefixA, reverse, read_current)
        self.bCache = MergingLogCache(logPrefixB, reverse, read_current)

    def readline(self):
        if self.aCache.peekkey() < self.bCache.peekkey():
            return self.aCache.readline()
        else:
            return self.bCache.readline()

# G l o b a l s

DETAIL_HEADERS = ( 'Host', 'Instance UUID', 'Seed URL', 'Status', 'CRC', 'Octets', 'Failed', 'Always Short' )
SUMMARY_HEADERS = ( 'Host', 'Crawls', 'Short Crawls', 'Always Short' )

# M a i n   P r o g r a m

myname = os.path.basename(sys.argv[0])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.stderr.write(myname + ": expecting two log file prefixes\n")
        sys.exit(1)
    r = MergingLogReader(sys.argv[1], sys.argv[2], reverse=True, read_current=True)
    while True:
        line = r.readline()
        if line == '':
            break
        sys.stdout.write(line)

# EOF
