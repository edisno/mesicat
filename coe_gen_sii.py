# -*- coding: utf-8 -*-
"""
coe_gen_sii.py

Generate SII EEPROM data from CoE data
Created on Wed Nov 20 

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
import string
import itertools
from coe_defs import *

sii_area_layout = [ # symbol, default, py struct format (all LE)
    ('pdi_control',         0x0080, 'H'),
    ('pdi_config',          0x00e0, 'H'),
    ('sync_impulse_len',    0x03e8, 'H'),
    ('pdi_config2',         0x0000, 'H'),
    ('sta_alias',           0x0000, 'H'),
    ('sii.reserved_05',     0x0000, '4x'),
    ('sii.checksum',        0x0000, 'H'), # low byte only
    ('VENDOR_ID',       0xffffffff, 'I'),
    ('PRODUCT_CODE',    0xffffffff, 'I'),
    ('REVISION_NUMBER',          1, 'I'),
    ('SERIAL_NUMBER',            0, 'I'),
    ('sii.reserved_10',          0, '8x'),
    ('bs_mbx_rx_off',       0x1000, 'H'),
    ('bs_mbx_rx_size',      0x0080, 'H'),
    ('bs_mbx_tx_off',       0x1400, 'H'),
    ('bs_mbx_tx_size',      0x0080, 'H'),
    ('std_mbx_rx_off',      0x1000, 'H'),
    ('std_mbx_rx_size',     0x0080, 'H'),
    ('std_mbx_tx_off',      0x1400, 'H'),
    ('std_mbx_tx_size',     0x0080, 'H'),
    ('mbx_protocol',        0x0000, 'H'),
    ('sii.zero_land',            0, '66x'),
    ('sii.size',            0x000f, 'H'),
    ('sii.version',         0x0001, 'H'),
]

sii_general_layout = [
    ('GROUP_IDX',       0, 'B'),
    ('IMG_IDX',         0, 'B'),
    ('ORDER_NO_IDX',    0, 'B'),
    ('DEVICE_IDX',      0, 'B'), # Spec says NameIdx: "Device Name Information"
    ('sii.gen_rsvd',    0, 'x'),
    ('coe_details',     0, 'B'),
    ('foe_details',     0, 'B'),
    ('eoe_details',     0, 'B'),
    ('soe_channels',    0, 'B'),
    ('ds402_channels',  0, 'B'),
    ('sysman_class',    0, 'B'),
    ('general_flags',   0, 'B'),
    ('current_on_ebus', 0, 'h'),
    ('sii.gen_pad1',    0, '2x'),
    ('sii.phys_port',   0, 'H'),
    ('sii.gen_pad2',    0, '14x'),
]

sii_sm_layout = [
    ('start_addr',      0, 'H'),
    ('size',            0, 'H'),
    ('control',         0, 'B'),
    ('status',          0, 'B'), 
    ('enable',          0, 'B'),
    ('type',            0, 'B'),
]

# From: http://code.google.com/p/atrias/wiki/EtherCAT_SII_File
sii_dc_layout = [
    ('sync0_cycle',         0, 'I'),
    ('sync0_shift',         0, 'i'),
    ('sync1_shift',         0, 'i'),
    ('sync1_cycle_factor',  0, 'h'), 
    ('assign_activate',     0, 'H'),
    ('sync0_cycle_factor',  0, 'h'),
    ('name_idx',            0, 'B'),  # Index to Name string
    ('unknown',             0, '5x'),
]

def crc(data):
    """
    CRC polynomial x^8 + x^2 + x^1 + x^0 initialized with 0xff
    as per ETG1000.6 table 16
    """
    rem = 0xff
    for octet in data:
        rem ^= octet
        for i in xrange(8):
            if rem & 0x80:
                rem = (rem << 1) ^ 0x07
            else:
                rem <<= 1
            rem &= 0xff
    return rem

def hexdump(data, label=''):
    print label
    count = len(data)
    hexapad = itertools.chain(('%02X'%d for d in data),itertools.repeat(
        '~~',((count+15)/16)*16-count))
    print '\n'.join('%03X0: '%a+' '.join(l) for a,l in 
        enumerate(zip(*[iter(hexapad)]*16)))

def cdump(data):
    count = len(data)
    hexapad = itertools.chain(('%#04x'%ord(d) for d in data),itertools.repeat('0',((count+15)/16)*16-count))
    return '    '+',\n    '.join( ', '.join(l) for l in zip(*[iter(hexapad)]*16))

def pack_cat_layout(settings_dict, layout, prefix=''):
    fmt = '<'+''.join(v[2] for v in layout)  
    pargs = [settings_dict.get(prefix+v[0],v[1]) for v in layout if 'x' not in v[2]]
    bytes =  bytearray(struct.pack(fmt, *pargs))
    #print fmt, pargs, len(bytes)
    return bytes

def head_n_pad(sctype, data):
    if len(data)&1:
        data.append(0)
    bad=bytearray(itertools.chain(struct.pack('<HH',sctype,len(data)/2), data))
    #hexdump(bad, 'head_n_pad '+str(sctype))
    return bad
    
def pack_cat_strings(*args):
    """
    Pack string arguments into SII Structure Category String 
    IAW ETG.6000.6 Table 20
    """
    return head_n_pad(10, bytearray(chr(len(args))+''.join(struct.pack('<%dp'%(len(s)+1),s) for s in args)))

def pack_cat_general(settings_dict):
    """
    Pack SII Structure Category General
    IAW ETG.6000.6 Table 21
    """
    return head_n_pad(30, pack_cat_layout(settings_dict, sii_general_layout))

def pack_cat_fmmu(settings_dict):
    """
    Pack SII Structure Category FMMU
    IAW ETG.6000.6 Table 22
    """
    d = b''.join(chr(settings_dict.get('fmmu%d.mode'%i, 0xff)) for i in xrange(8))

    # strip unused modes
    d = bytearray( string.rstrip(d, '\xff') )    
    
    # pad to even number of bytes
    while len(d)==0 or len(d)&1:
        d.append(0xff)
    
    return head_n_pad(40, d)

def pack_cat_sm(settings_dict):
    """
    Pack SII Structure Category SM
    IAW ETG.6000.6 Table 23
    """
    sm_count = max(i+1 if settings_dict.get('sm%d.enable' % i,0) else 0 for i in xrange(8))
    
    sm_bin = bytearray()

    if sm_count == 0:
        return sm_bin

    for i in xrange(sm_count):
        sm_bin += pack_cat_layout(settings_dict, sii_sm_layout, 'sm%d.'%i)
        
    return head_n_pad(41, sm_bin)

def pack_cat_dc(settings_dict):
    """
    Pack SII Structure Category DC
    No reference to standard available
    Ref: http://code.google.com/p/atrias/wiki/EtherCAT_SII_File
    """
    dc_bin = bytearray()
    
    if not settings_dict['DC_SUPPORTED']:
        return dc_bin
        
    for i in xrange(8):
        if settings_dict.get('dc%d.name' % i):
            dc_bin += pack_cat_layout(settings_dict, sii_dc_layout, 'dc%d.'%i)
    
    # Return an empty bytearray if we find no DC settings.
    if not dc_bin:
        return dc_bin

    return head_n_pad(60, dc_bin)

def make(world, *args):
    # Essentially, many of the settings are inspired by the ecat_def header file
    settings = world.settings

    # Build ConfigData
    config_data = pack_cat_layout(settings, sii_area_layout[0:6])
    
    # Record config data for XML file
    settings['config_data'] = ''.join('%02X' % d for d in config_data)
    
    # Compute checksum and save
    settings['sii.checksum'] = crc(config_data)

    # Pack SII area data
    eeprom = pack_cat_layout(settings, sii_area_layout)
    
    # Record mailbox bootstrap settings
    settings['bootstrap'] = ''.join('%02X' % d for d in eeprom[0x28:0x30])

    # String setup
    my_strings = []
    for base in ('TYPE', 'GROUP', 'IMG', 'ORDER_NO', 'DEVICE'):
        name_key = base + '_NAME'
        index_key = base+'_IDX'
        if name_key in settings:
            my_strings.append( settings[name_key] )
            settings[index_key] = len(my_strings) # one-based index
        else:
            settings[index_key] = 0 # zero means no string present
    
    # Prepare DC strings if required
    if settings['DC_SUPPORTED']:
        for i in xrange(8):
            k = 'dc%d.name' % i
            if k in settings:
                my_strings.append(settings[k])
                settings[k+'_idx'] = len(my_strings)                
        
    # Add strings to EEPROM
    if len(my_strings):
        eeprom += pack_cat_strings(*my_strings)
        
    # Add Structure General 
    eeprom += pack_cat_general(settings)
    
    # Add FMMU
    eeprom += pack_cat_fmmu(settings)

    # Add SM
    eeprom += pack_cat_sm(settings)
    
    # Add distributed clock
    eeprom += pack_cat_dc(settings)
    #hexdump(eeprom, 'Add DC')
    
    # Pad to size with FF (also, makes terminating FFFF category type)
    eeprom = string.ljust(str(eeprom), settings['ESC_EEPROM_SIZE'], '\xff')    
    
    # Sling to disk
    with open('eeprom.bin','w') as out:
        out.write( eeprom )
    
    # Make an initializer dump for C code generation
    settings['sii_eeprom_initializer'] = cdump(eeprom)
    
if __name__ == "__main__":
    dat = (0x80, 0x00, 0xe0, 0x00, 0xe8, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
    
    cs = crc(dat)
    
    print 'Expect 0x3c, got',hex(cs)
    
    