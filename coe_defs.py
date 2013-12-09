# -*- coding: utf-8 -*-
"""
coe_defs.py

Definitions of CoE datastructures to support generate_coe.py

Created on Wed Nov 06 09:09:07 2013

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

import struct
import itertools

class coe_type:
    def __init__(self, pdo_bitsize, sdo_bitsize, cdef, coetype, ctype, pyformat):
        self.pdo_bitsize = pdo_bitsize
        self.sdo_bitsize = sdo_bitsize
        self.cdef = cdef
        self.coetype = coetype
        self.ctype = ctype
        self.pyformat = pyformat

# Valid Basic Data types for this application. 
# See ETG.2000 section 7 table 7
# See ETG.1000.6 5.6.7.3
# The fake type BECKHOFF816 works around a subindex 0 issue in the SSC.
# The SI0 max subindex is advertised in the CoE dictionary as an 8 bit
# unsigned, but is allocated in the in-memory CoE object as
# 16 bit unsigned. This has no impact on the PDO transfer, as SI0 is 
# not included, and the data is copied explicitly. For the SDO bulk 
# transfer, however, the in-memory layout is controlling, so the 
# SDO bit offset of the subsequent SDOn data (n>0) must take into account the
# 16 bits allocated for SI0. As such, we must double book the PDO and SDO
# bit size, so the correct dictionary type/size is reported, and the correct
# SDO offsets are determined. 
# The SSC should eventually be fixed such that SI0 can be USINT as per spec
coe_types = {
    'BECKHOFF816':  coe_type(8,16, 'UNSIGNED8',      5, 'uint16_t %s',    'B'),
    'PAD1':         coe_type(1,1,  'NULL',           0, 'unsigned %s:1',  'B'),
    'PAD2':         coe_type(2,2,  'NULL',           0, 'unsigned %s:2',  'B'),
    'PAD3':         coe_type(3,3,  'NULL',           0, 'unsigned %s:3',  'B'),
    'PAD4':         coe_type(4,4,  'NULL',           0, 'unsigned %s:4',  'B'),
    'PAD5':         coe_type(5,5,  'NULL',           0, 'unsigned %s:5',  'B'),
    'PAD6':         coe_type(6,6,  'NULL',           0, 'unsigned %s:6',  'B'),
    'PAD7':         coe_type(7,7,  'NULL',           0, 'unsigned %s:7',  'B'),
    'PAD8':         coe_type(8,8,  'NULL',           0, 'unsigned %s:8',  'B'),
    'BOOL':         coe_type(1,1,  'BOOLEAN',        1, 'unsigned %s:1',  'B'),
    'BIT2':         coe_type(2,2,  'BIT2',        0x31, 'unsigned %s:2',  'B'),
    'BIT3':         coe_type(3,3,  'BIT3',        0x32, 'unsigned %s:3',  'B'),
    'SINT':         coe_type(8,8,  'INTEGER8',       2, 'int8_t %s',      'b'),
    'USINT':        coe_type(8,8,  'UNSIGNED8',      5, 'uint8_t %s',     'B'),
    'INT':          coe_type(16,16,'INTEGER16',      3, 'int16_t %s',     'h'),
    'UINT':         coe_type(16,16,'UNSIGNED16',     6, 'uint16_t %s',    'H'),
    'DINT':         coe_type(32,32,'INTEGER32',      4, 'int32_t %s',     'l'),
    'UDINT':        coe_type(32,32,'UNSIGNED32',     7, 'uint32_t %s',    'L'),
    'REAL':         coe_type(32,32,'REAL32',         8, 'float %s',       'f'),
    'STRING(5)':    coe_type(40,40,'VISIBLESTRING',  9, 'char *%s',      '5s'),
    'STRING(8)':    coe_type(64,64,'VISIBLESTRING',  9, 'char *%s',      '8s'),
    'STRING(10)':   coe_type(80,80,'VISIBLESTRING',  9, 'char *%s',      '10s')
}

class coe_sub_object:
    """A representation of CoE dictionary sub-objects. A sub object always has 
    a parent dictionary object. Sub objects are referenced by their parent 
    object's 16 bit index and a sub object 8 bit index of the form XXXXX:XX 
    (e.g. 7000:10)"""
    def __init__(self, index, subindex, access='r-r-r-', btype='BOOL', symbol='undefined', default=0, description=None):
        self.index = index
        self.subindex = subindex
        self.set_access(access)
        self.btype = btype
        self.symbol = symbol
        self.default = default
        if description:
            self.description = description
        else:
            self.description = 'SubIndex %03d' % subindex
        
    #0x1c00:00, r-r-r-, usint, 8 bit, "SubIndex 000"
    def __str__(self):
        return ('0x%04x:%02x, %s, %s, %d bit, %s [%#x]' % 
            (self.index, self.subindex, self.access(), self.btype, 
             self.pdo_bitsize(), self.description, self.default))
    
    def __repr__(self):
        return ("coe_sub_object(index=0x%04x, subindex=0x%02x, access=%#x, btype='%s', symbol='%s', default=%r, description='%s')" %
            (self.index, self.subindex, self.access_code, self.btype, self.symbol, self.default, self.description))

    def xml_index(self):
        "Index in EtherCATInfo XML hex format"
        return '#x%04X' % self.index

    def coe_reference(self):
        return self.index << 16 | self.subindex << 8 | self.pdo_bitsize()

    def deftype(self):
        "Beckhoff Slave Stack Code CoE type defines"
        return 'DEFTYPE_'+coe_types[self.btype].cdef
        
    def ctype(self):
        "Type used in C language declarations"
        return coe_types[self.btype].ctype % self.symbol
        
    def pdo_bitsize(self):
        "PDO Size of type in bits"
        return coe_types[self.btype].pdo_bitsize
    
    def sdo_bitsize(self):
        "SDO Size of type in bits"
        return coe_types[self.btype].sdo_bitsize

    def is_null(self):
        "True if CoE type is NULL (padding)"
        return coe_types[self.btype].coetype == 0
        
    # Access permissions: PREOP SAFEOP OP   PDO
    #                     rw    rw     rw   TR
    def access(self):
        """A string representation of access permissions for user display"""
        s = list("rwrwrwRT")
        for i,b in enumerate((1,8,2,16,4,32,64,128)):
            if self.access_code & b == 0:
                s[i] = '-'
        return ''.join(s)
    
    def set_access(self, access):
        """Set permissions as a code (int) or as a permissions string"""
        if isinstance(access, int):
            self.access_code = access
        else:
            s = access.ljust(8,'-')
            a = 0
            for i,b in enumerate((1,8,2,16,4,32,64,128)):
                if s[i]!='-':
                    a |= b
            self.access_code = a
    
    def set_pdo_access(self, tr):
        """Set access bits for TxPdo (tr='T') or RxPDO (tr='R') access"""
        if tr=='T':
            self.access_code |= 0x80
        elif tr=='R':
            self.access_code |= 0x40
    
    def is_tx_pdo(self):
        """Return true if TX PDO access bit is set"""
        return (self.access_code & 0x80)>0
    
    def is_rx_pdo(self):
        """Return true if TX PDO access bit is set"""
        return (self.access_code & 0x40)>0
    
    def access_code_hex(self):
        """Return the access permissions code as a hex string"""
        return '%#x' % self.access_code
        
    def hexbinary_default(self):
        """Return a xs:hexBinary representation of the default value"""
        # Note EtherCAT is a CANOpen derivative, and thus little endian. 
        return ''.join('%02x' % x for x in 
            bytearray(struct.pack('<'+coe_types[self.btype].pyformat, self.default)))
     
    def hexdec_default(self):
        """Return a HexDecValue representation of the default value"""
        return '#x%x' % max(0,self.default)
     
class coe_object:
    """A representation of CoE objects. An object can be an array, variable, or
    record. In any event, the object always aggregates one or more subobjects
    where data is actually stored. In the case of a variable, only one subobject
    (:00) is present. For arrays, an i bit subobject :00 holds the array size, 
    and the N elements are stored in N subobjects all of the same type. A record
    can hold N subobjects of any basic type (where N < 256); subobject 0 holds the 
    subobject count (N)."""
    # Object codes
    oc_variable = 7
    oc_array = 8
    oc_record = 9   
    
    oc_names_ = {7:'variable',8:'array',9:'record'}
    
    def __init__(self, object_code=0, index=0, symbol=None, description=None):
        self.object_code = object_code
        self.index = index
        self.symbol = symbol
        self.description = description
        
        # Sub objects
        self.subs = []
        
        # Arbitrary configuration properties
        self.properties = {}
        
    def is_variable(self):
        """True if this object is of CoE VARIABLE type"""
        return self.object_code == coe_object.oc_variable
    def is_array(self):
        """True if this object is of CoE ARRAY type"""
        return self.object_code == coe_object.oc_array
    def is_record(self):
        """True if this object is of CoE RECORD type"""
        return self.object_code == coe_object.oc_record
        
    def is_rx_pdo_map(self):
        """Return true if object is a RxPDO mapping"""
        return (self.index>>8) == 0x16
    
    def is_tx_pdo_map(self):
        """Return true if object is a TxPDO mapping"""
        return (self.index>>8) == 0x1a

    def add(self,*args, **kwargs):
        """Add (replace, actually) the argument list as sub objects to this 
        object. The argument list consists of tuples of:
        (access, btype, symbol, default, description)
        because we're properly lazy, and we don't like to repeat ourselves,
        we can supply keyword arguments which remove the corresponding
        element from the tuple and replace with the given contant value. 
        For example:
        add('a','b','c',access='r-r-r-',bytpe='USINT',default=0,description=None)
        """
        if self.is_record():
            self.subs = [
                coe_sub_object(self.index, 0, 'r-r-r-', 'BECKHOFF816', 
                               'u16SubIndex0', len(args), 'Subindex 000' ),
            ]
            for i,atuple in enumerate(args):
                a = list(atuple)
                so = coe_sub_object(self.index,i+1,'------','BOOL','unknown',0,'')
                if 'access' in kwargs:
                    so.set_access(kwargs['access'])
                else:
                    so.set_access(a.pop(0))
                if 'btype' in kwargs:
                    so.btype = kwargs['btype']
                else:
                    so.btype = a.pop(0)
                if 'symbol' in kwargs:
                    so.symbol = kwargs['symbol']
                else:
                    so.symbol = a.pop(0)
                if 'default' in kwargs:
                    so.default = kwargs['default']
                else:
                    so.default = a.pop(0)
                if 'description' in kwargs:
                    so.description = kwargs['description']
                else:
                    so.description = a.pop(0)
                self.subs.append(so)
            # update subindex 0: max subindex             
            self.subs[0].default = self.max_subindex()
        elif self.is_array():
            if 'size' in kwargs:
                self.array_size = max(size, len(args))
            else:
                self.array_size = len(args)
                
            self.subs = [
                coe_sub_object(self.index, 0, 'r-r-r-', 'BECKHOFF816', 
                               'u16SubIndex0', self.array_size, 'Subindex 000' ),
            ]
            
            for i,value in enumerate(args):
                so = coe_sub_object(self.index,i+1,'------','USINT','unknown',0,'')
                if 'access' in kwargs:
                    so.set_access(kwargs['access'])
                else:
                    so.set_access('------')
                if 'btype' in kwargs:
                    so.btype = kwargs['btype']
                else:
                    so.btype = 'USINT'
                if 'symbol' in kwargs:
                    so.symbol = kwargs['symbol']
                else:
                    so.symbol = 'data_%d'%i
                if 'default' in kwargs:
                    so.default = kwargs['default']
                else:
                    so.default = value
                if 'description' in kwargs:
                    so.description = kwargs['description']
                else:
                    so.description = 'SubIndex %03d' % (i+1)
                self.subs.append(so)
        elif self.is_variable():       
            self.subs = [
                coe_sub_object(self.index, 0, '------', 'USINT', 
                               'data', 0, 'Subindex 000' ),
            ]
            so = self.subs[0]
            if 'access' in kwargs:
                so.set_access(kwargs['access'])
            if 'btype' in kwargs:
                so.btype = kwargs['btype']
            if 'symbol' in kwargs:
                so.symbol = kwargs['symbol']
            if 'default' in kwargs:
                so.default = kwargs['default']
            else:
                so.default = args[0]
            if 'description' in kwargs:
                so.description = kwargs['description']
            
    def hex_index(self):
        """Return the object index in hex"""
        return '%04X' % self.index  
    
    def xml_index(self):
        "Index in EtherCATInfo XML hex format"
        return '#x%04X' % self.index
    
    def max_subindex(self):
        """Return the maximum configured sub index"""
        return max(itertools.chain((0,), (x.subindex for x in self.subs)))
    
    def hex_defaults(self):
        """Return a comma delimited list of hex default values suitable for
        use in a C-style initializer statement
        """
        return ','.join('%#x'%so.default for so in self.subs)
        
    def pdo_data_bitsize(self):
        "Return size of PDO data (excluding subindex 0)"
        return sum(so.pdo_bitsize() for so in self.subs if so.subindex>0)
        
    def sdo_bitsize(self):
        """
        Return the total SDO size in bits including all padding and workarounds
        """
        return sum(so.sdo_bitsize() for so in self.subs)        

    def sdo_bitoffset(self, subindex):
        """
        Return the offset in bits within the SDO memory object of the 
        specified sub object
        """
        return sum(x.sdo_bitsize() for x in self.subs if x.subindex<subindex)
        
    def deftype(self):
        """Return a string containing the cdef type symbol (e.g. 'UNSIGNED8')
        of this object"""
        if self.is_variable():
            return self.subs[0].deftype()
        elif self.is_array():
            return self.subs[1].deftype()
        elif self.is_rx_pdo_map() or self.is_tx_pdo_map():
            return 'DEFTYPE_PDOMAPPING'
        else:
            return 'DEFTYPE_RECORD'
            
        #SDO 0x1c00, "Sync manager type"
    def __str__(self):
        return ('SDO 0x%04x, "%s"\n' % (self.index, self.description)) + '\n'.join('\t'+str(x) for x in self.subs)

    def __repr__(self):
        return ("coe_object(%s,index=0x%04x, symbol='%s', description='%s').subs=[%s]" %         
            (coe_object.oc_names_[self.object_code],self.index, 
             self.symbol, self.description, ','.join(repr(x) for x in self.subs)))

def insert_subindex_count(pobj):
    idx = pobj[0][0]
    pobj.insert(0, (idx, 0, 'r-r-r-', 'USINT', len(pobj), 'Subindex count' ))

def make_pdo_map(index,pdo):
    pmap = coe_object(index, pdo.symbol+'_map', 'PDO Map:'+pdo.description)
    mapz = []
    if index < 0x1a00:
        tr = 'R'
    else:
        tr = 'T'

    # loop over PDO data (skip subindex 0 and its padding)
    for so in pdo.subs[2:]:
        so.set_pdo_access(tr)
        mapz.append((so.symbol, so.coe_reference(), so.description))
    pmap.add(*mapz, access='r-r-r-', btype='UDINT')
    return pmap

def find_obj_by_index(coe_dict, index):
    return next((obj for obj in coe_dict if obj.index==index), None)

def find_by_map_loc(coe_dict, map_loc):
    so = next((so for so in find_obj_by_index(coe_dict, map_loc>>16).subs if so.subindex==((map_loc>>8) & 0xff)), None)
    #print 'find by map',so.symbol,so.bitsize()
    return so
    