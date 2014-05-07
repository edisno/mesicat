# -*- coding: utf-8 -*-
"""
Meta ESI script for EtherCAT

This script parses a meta ESI file (mesi) to a CoE dictionary datastructure.
The data is then formatted to EtherCATInfo XML and/or C header+source file
definitions for the Slave Stack Code.

Created on Fri Nov 01 17:12:36 2013

@author: Dave Page, Dynamic Systems Inc.

@copyright MIT License
Copyright (C) 2013 Dynamic Systems Inc.
Permission is hereby granted, free of charge, to any person obtaining 
a copy of this software and associated documentation files (the 
"Software"), to deal in the Software without restriction, including 
without limitation the rights to use, copy, modify, merge, publish, 
distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to 
the following conditions:
The above copyright notice and this permission notice shall be included 
in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS 
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR 
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR 
OTHER DEALINGS IN THE SOFTWARE.
"""
import sys
import getopt
import importlib
import mesi_file

def usage():
    print sys.argv[0], "[-v] file.mesi"

def main():
    verbose = False
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v")
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
        
    if len(args) != 1:
        usage()
        sys.exit(1)

    for o, a in opts:
        if o == "-v":
            verbose = True
        else:
            assert False, "unhandled option"

    with open(args[0],'r') as infile:
        world = mesi_file.parse(infile.read())
    
    # Handy dump of defined objects
    if verbose:
        for obj in world.coe_dict:
            print obj
        
    for activity, args in world.make_list:
        print 'Make %s(%s):' % (activity, ','.join(args))
        mod = importlib.import_module(activity)
        mod.make(world, *args)
  
if __name__ == '__main__':
    main()
