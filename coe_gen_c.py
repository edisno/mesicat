# -*- coding: utf-8 -*-
"""
coe_gen_c.py

Generate C code from CoE data
Created on Wed Nov 06 09:14:07 2013

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

import pystache
import os
import time
from coe_defs import *

btype_cfg_map = {
    'BOOL':'bit lbloo',
    'SINT':'byte _u',
    'USINT':'byte _u',
    'INT':'word _u',
    'UINT':'word _u',
    'DINT':'long _u',
    'UDINT':'long _u',
    'REAL':'float _uf',
}

def subindex_context(pdo):
    # Basic idea
    subs = [{
                'subindex':so.subindex,
                'hex_subindex':('%02x'%so.subindex),
                'ctype':so.ctype(),
                'subsymbol':so.symbol,
                'deftype':so.deftype(),
                'pdo_bitsize':so.pdo_bitsize(),
                'sdo_bitsize':so.sdo_bitsize(),
                'access_code_hex':so.access_code_hex(),
                'description':so.description,
                'null?':so.is_null(),
                'txpdo?':(so.access_code&0x80>0),
                'rxpdo?':(so.access_code&0x40>0),
                'default':so.default,
                'cfg_type':btype_cfg_map.get(so.btype,'//'),
            } for so in pdo.subs]    
    
    # Patch array to fit SSC code
    if pdo.is_array():
        subs = subs[0:2]
        
        ct = subs[1]['ctype']
        if ':' in ct:
            raise TypeError('Arrays of bits not supported')
        subs[1]['ctype'] = '%s aEntries[%d]' % (ct.split()[0],pdo.max_subindex())

    return subs
    
def mapped_subindex_context(coe_dict, pdo):
    if not (pdo.is_rx_pdo_map() or pdo.is_tx_pdo_map()):
        return None
    
    subs = []
    bit_index = 0
    bit_count = 0    
    # So, we want subobjects referenced by this PDO map. Thus, we take the
    # default value, lookup the referenced object, then build a sub context 
    # for each of those.
    
    for so in (find_by_map_loc(coe_dict, mso.default) for mso in pdo.subs[1:]):
        bit_count = so.pdo_bitsize()

        # padding must be explicitly advertised, or TwinCAT will not byte align
        # the PDOs 
        #if so.is_null():
        #    bit_index += bit_count
        #    continue

        obj = find_obj_by_index(coe_dict, so.index)
        symbol = '.'.join((obj.symbol,so.symbol))

        tx_pdo_code = []
        value_shift = 0
        rx_pdo_code = []
        if bit_count==1:
            # Special case bool fieds for brevity
            tx_pdo_code.append('if (%s) *data |= (1 << %d);' % (symbol, bit_index))
            tx_pdo_code.append('else *data &= ~(1 << %d);' % bit_index)

            rx_pdo_code.append('if (*data & (1 << %d)) %s = 1;' % (bit_index, symbol))
            rx_pdo_code.append('else %s = 0;' % symbol)

            bit_index += 1
            if bit_index >= 8:
                bit_index=0;
                tx_pdo_code.append('data += 1;')
                rx_pdo_code.append('data += 1;')
        elif so.btype.startswith('REAL') or so.btype.startswith('STRING'):
            # Force byte alignment
            if bit_index > 0:
                bit_index=0;
                tx_pdo_code.append('data += 1;')
                rx_pdo_code.append('data += 1;')
            # Copy data as-is. Here, we must assume bit_count mod 8 == 0
            assert bit_count&7 == 0
            # This will fail for REAL data if platform formats do not agree
            tx_pdo_code.append('memcpy(data, &%s, %d);' % (symbol, bit_count/8)) 
            tx_pdo_code.append('data += %d;' % (bit_count/8))
            rx_pdo_code.append('memcpy(&%s, data, %d);' % (symbol, bit_count/8))            
            rx_pdo_code.append('data += %d;' % (bit_count/8))
        else:
            while bit_count:
                if (bit_count >= 8) and bit_index == 0:
                    # aligned bytewise little endian copy
                    bit_count -= 8;
                    
                    if value_shift:
                        tx_pdo_code.append('*data++ = %s >> %d;'%(symbol,value_shift))
                    else:
                        tx_pdo_code.append('*data++ = %s;'%symbol)
                    
                    if value_shift:
                        rx_pdo_code.append('%s |= (*data++ << %d);'%(symbol,value_shift))
                    else:
                        rx_pdo_code.append('%s = *data++;'%symbol)
    
                    value_shift += 8
                else:
                    # odd 8 number of bits, bitwise copy
                    bit_count -= 1;
        
                    tx_pdo_code.append('if (%s & (1 << %d)) *data |= (1 << %d);' % (symbol,value_shift, bit_index))
                    tx_pdo_code.append('else *data &= ~(1 << %d);' % bit_index)
    
                    rx_pdo_code.append('if (*data & (1 << %d)) %s |= (1 << %d);' % (bit_index, symbol, value_shift))
                    rx_pdo_code.append('else %s &= ~(1 << %d);' % (symbol, value_shift))
    
                    value_shift += 1
    
                    bit_index += 1
                    if bit_index >= 8:
                        bit_index=0;
                        tx_pdo_code.append('data += 1;')
                        rx_pdo_code.append('data += 1;')
            
        subs.append({
                'tx_pdo_code':'\n            '.join(tx_pdo_code),
                'rx_pdo_code':'\n            '.join(rx_pdo_code),
                'subindex':so.subindex,
                'ctype':so.ctype(),
                'subsymbol':so.symbol,
                'deftype':so.deftype(),
                'pdo_bitsize':so.pdo_bitsize(),
                'sdo_bitsize':so.sdo_bitsize(),
                'access_code_hex':so.access_code_hex(),
                'description':so.description,
                'txpdo?':so.is_tx_pdo(),
                'rxpdo?':so.is_rx_pdo(),
                'default':so.default})

    # Force next PDO to byte boundary
    if bit_index > 0:
        fix = '\n            data += 1; // byte align to next PDO'
        subs[-1]['tx_pdo_code'] += fix
        subs[-1]['rx_pdo_code'] += fix

    return subs

def appl_context(world):
    # Convert large constants to hex, so we look more nerdy
    context = dict((k,hex(v) if isinstance(v,int) and 
        (v>9 or v<-9) else v) for k,v in world.settings.iteritems())
        
    context.update({
        'pdos':[dict(itertools.chain(pdo.properties.items(), { 
            'hex_index':pdo.hex_index(),
            'variable?':pdo.is_variable(),
            'array?':pdo.is_array(),
            'record?':pdo.is_record(),
            'max_subindex':pdo.max_subindex(),
            'subs': subindex_context(pdo),
            'dsubs': subindex_context(pdo)[1:],  # Data sub objects (less subindex count)
            'mapped_subs': mapped_subindex_context(world.coe_dict, pdo),
            'description': pdo.description,
            'symbol': pdo.symbol,
            'hex_defaults': pdo.hex_defaults(),
            'pdo_data_bitsize': pdo.pdo_data_bitsize(),
            'deftype': pdo.deftype(),
            'objflags': hex(pdo.object_code << 8 | pdo.max_subindex()),
            'tx_pdo_map?':pdo.is_tx_pdo_map(),
            'rx_pdo_map?':pdo.is_rx_pdo_map(),
        }.items())) for pdo in world.coe_dict],
        'date':time.strftime("%A, %d %B %Y"),
        'appname':'mesicat.py',
    })
    
    return context

def make(world, *args):
    context = appl_context(world)
    
    context['basename'] = os.path.basename( args[1] )
    
    #import pprint
    #pprint.pprint(world.settings)
    
    with open(args[0],'r') as infile:
        with open(args[1],'w') as out:
            context['basename'] = os.path.basename( args[1] )
            out.write(pystache.render(infile.read(), context))
        
