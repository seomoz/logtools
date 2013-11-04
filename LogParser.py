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

# I m p o r t s

import sys, os, time, re
import calendar

# V a r i a b e s

_MATCH_DATE = r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d,\d\d\d'

# C l a s s e s

class LogParserError(Exception):
    pass

class LogReader(object):
    '''Given a file-like object or a string, create an object that
    lets the user read logs on an entry-by-entry  basis.'''

    _NEW_RECORD = re.compile(r'\[' + _MATCH_DATE + r'\]')

    def __init__(self, based_on):
        self._look_ahead = None
        if isinstance(based_on, str) or isinstance(based_on, unicode):
            self._reader = open(based_on, 'r')
        elif self._has_callable(based_on, 'readline'):
            self._reader = based_on
        else:
            raise TypeError("Expecting string or an object with readline()")

    def _has_callable(self, obj, name):
        return hasattr(obj, name) and hasattr(getattr(obj, name), '__call__')

    def next(self):
        raw = self.raw_next()
        return None if not raw else LogEntry(raw)

    def raw_next(self):
        ret = ''
        got_first = False
        while True:
            peek = self._peekline()
            if not peek or (got_first and self._NEW_RECORD.match(peek)):
                return ret
            ret += self._nextline()
            got_first = True

    def _doread(self):
        return self._look_ahead or self._reader.readline()

    def _peekline(self):
        self._look_ahead = self._doread()
        return self._look_ahead

    def _nextline(self):
        ret = self._doread()
        self._look_ahead = None
        return ret

    def close(self):
        if self._has_callable(self._reader, 'close'):
            self._reader.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

class LogEntry(object):
    '''Represents a single entry we read in.'''

    def __init__(self, raw_entry):
        self.raw = raw_entry
        self.lines = self.raw.splitlines()
        self._first = None

    @property
    def first(self):
        if self._first is None:
            self._first = LogFields(self.lines[0])
        return self._first

class LogFields(object):
    '''Given a string that represents a log entry, parse it.'''

    # Dynamically-returned (via getattr) fields, in the order found on a line
    _FIELDS = ['raw_time', 'level', 'module', 'function', 'line_no', 'message']

    _PARSE = re.compile(r'^\[(' + _MATCH_DATE + r')\] (?:PID :\s+\d+ )?([A-Z]+) in ([^:\s]+):(\w+)@(\d+) => (.*)')

    def __init__(self, raw_line):
        self.raw = raw_line
        self._parsed = False

    def __getattr__(self, field):
        if self._parsed or field not in self._FIELDS + ['time']:
            raise AttributeError("No such attribute: '%s'" % ( field ))
        else:
            self._parsed = True
            self._doparse()
            return getattr(self, field)

    def _doparse(self):
        try:
            rfields = self._PARSE.match(self.raw).groups()
        except AttributeError:
            raise LogParserError("Unable to parse " + repr(self.raw))
        for i in range(len(self._FIELDS)):
            setattr(self, self._FIELDS[i], rfields[i])
        self.time = LogTime(self.raw_time)
        self.line_no = int(self.line_no)

class LogTime(object):
    '''Given a string that represents a date/time stamp in a log entry,
    parse it.'''

    _FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, raw_time):
        self.raw = raw_time
        self._seconds = self._millis = self._struct = None

    @property
    def struct(self):
        if self._struct is None:
            self._doparse()
        return self._struct

    @property
    def millis(self):
        if self._millis is None:
            self._doparse()
        return self._millis

    @property
    def seconds(self):
        if self._seconds is None:
            self._seconds = calendar.timegm(self.struct)
        return self._seconds

    def _doparse(self):
        i = self.raw.find(',')
        if i >= 0:
            self._millis = int(self.raw[i+1:])
            r = self.raw[:i]
        else:
            self._millis = 0
            r = self.raw
        self._struct = time.strptime(r, self._FORMAT)

