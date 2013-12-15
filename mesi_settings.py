# -*- coding: utf-8 -*-
"""
mesi_settings.py

Set up missing defaults. Implement design rules and
best practices. Write out ecat_def.h

Created on Wed Nov 21

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


sane_defaults = (
    # Identification
    ('VENDOR_ID',       0xffffffff),
    ('PRODUCT_CODE',    0xffffffff),
    ('REVISION_NUMBER',          0),
    ('SERIAL_NUMBER',            0),

    ('DEVICE_PROFILE_TYPE', 0x00001389),  # Slave device type (Object 0x1000)
    ('DEVICE_NAME', 'Undefined'), # Name of the slave device (Object 0x1008)
    ('DEVICE_HW_VERSION', '0.00'),
    ('DEVICE_SW_VERSION', '0.00'),

    # Generic
    ('EXPLICIT_DEVICE_ID',0), # If this switch is set Explicit device ID requests are handled
    ('ESC_SM_WD_SUPPORTED',0), # Set if the SyncManger watchdog provided by the ESC should be used
    ('STATIC_OBJECT_DIC',0), # If this switch is set, the object dictionary is "build" static
    ('ESC_EEPROM_ACCESS_SUPPORT',0), # If this switch is set the slave stack provides functions to access the EEPROM.
    
    # Hardware					
    ('MCI_HW',0),
    ('HW_ACCESS_FILE','#include "tieschw.h"'),
    ('ESC_16BIT_ACCESS', 0), # 0 for AM335x
    ('ESC_32BIT_ACCESS', 0), # 0 for AM335x
    ('CONTROLLER_16BIT', 0),
    ('CONTROLLER_32BIT', 0),
    ('MBX_16BIT_ACCESS', 0), 	
    ('BIG_ENDIAN_16BIT', 0),
    ('BIG_ENDIAN_FORMAT', 0),
    ('EXT_DEBUGER_INTERFACE', 0),
    ('UC_SET_ECAT_LED', 0),  	
    ('ESC_SUPPORT_ECAT_LED', 0),  	
    ('ESC_EEPROM_EMULATION', 0),  	
    ('CREATE_EEPROM_CONTENT', 0), 	
    ('ESC_EEPROM_SIZE', 0x800), # Specify the EEPROM size in Bytes of the connected EEPROM 
    ('EEPROM_READ_SIZE', 8), # If EEPROM emulation is active, the number of bytes which will be read per operation.
    ('EEPROM_WRITE_SIZE', 2),
    ('MAKE_PTR_TO_ESC',''), # Should be defined to the initialize the pointer to the ESC
    					
    # EtherCAT State Machine
    ('BOOTSTRAPMODE_SUPPORTED',0),
    ('OP_PD_REQUIRED',1), 
    ('PREOPTIMEOUT', 0x7D0), 
    ('SAFEOP2OPTIMEOUT', 0x2328), 
    					
    # Synchronization					
    ('AL_EVENT_ENABLED',1), # 1 for synchronous mode supported
    ('DC_SUPPORTED',1), # DC Supported
    ('ECAT_TIMER_INT',0), 
    ('MIN_PD_CYCLE_TIME', 0x186A0), # 100usec cycle time
    ('MAX_PD_CYCLE_TIME', 0xC3500000),
    ('PD_OUTPUT_DELAY_TIME', 0x0),
    ('PD_OUTPUT_CALC_AND_COPY_TIME', 0x0),
    ('PD_INPUT_CALC_AND_COPY_TIME', 0x0),
    ('PD_INPUT_DELAY_TIME', 0x0),
    					
    # Application					
    ('CiA402_DEVICE',0),
    ('SAMPLE_APPLICATION',0),
    ('SAMPLE_APPLICATION_INTERFACE',0),
    ('APPLICATION_FILE','#include "tiescappl.h"'),
    ('USE_DEFAULT_MAIN',1), 
    					
    # Process Data					
    ('MIN_PD_WRITE_ADDRESS', 0x1000 ), 
    ('DEF_PD_WRITE_ADDRESS', 0x1800 ), 
    ('MAX_PD_WRITE_ADDRESS', 0x3000 ), 
    ('MIN_PD_READ_ADDRESS', 0x1000 ), 
    ('DEF_PD_READ_ADDRESS', 0x1C00 ), 
    ('MAX_PD_READ_ADDRESS', 0x3000 ), 
    					
    # Mailbox					
    ('MAILBOX_QUEUE',1), 
    ('AOE_SUPPORTED',0), 
    ('COE_SUPPORTED',1), 
    ('COMPLETE_ACCESS_SUPPORTED',1), 
    ('SEGMENTED_SDO_SUPPORTED',1), 
    ('SDO_RES_INTERFACE',1), 
    ('USE_SINGLE_PDO_MAPPING_ENTRY_DESCR',0), 
    ('BACKUP_PARAMETER_SUPPORTED',0), # Support load and store backup parameter
    ('STORE_BACKUP_PARAMETER_IMMEDIATELY',0), # Object values will be stored when they are written
    ('DIAGNOSIS_SUPPORTED',0), # If this define is set the slave stack supports diagnosis messages (Object 0x10F3). 
    ('MAX_DIAG_MSG', 0x14), 
    ('EMERGENCY_SUPPORTED',0),
    ('MAX_EMERGENCIES',1),
    ('VOE_SUPPORTED',0),
    ('SOE_SUPPORTED',0),
    ('EOE_SUPPORTED',0),
    ('STATIC_ETHERNET_BUFFER',0),
    ('FOE_SUPPORTED',0),
    ('FOE_SAVE_FILES',0),
    ('MAX_FILE_SIZE', 0x500),
    ('MIN_MBX_SIZE', 0x0022),
    ('MAX_MBX_SIZE', 0x0100),
    ('MIN_MBX_WRITE_ADDRESS', 0x1000),
    ('DEF_MBX_WRITE_ADDRESS', 0x1000),
    ('MAX_MBX_WRITE_ADDRESS', 0x3000),
    ('MIN_MBX_READ_ADDRESS', 0x1000),
    ('DEF_MBX_READ_ADDRESS', 0x1400),
    ('MAX_MBX_READ_ADDRESS', 0x3000),

    # Random junk which should not be set in ecat_def.h but rather in the 
    # build  environment
    ('EL9800_HW',0,),
    ('EL9800_APPLICATION',0),
    ('FC1100_HW',0,),
    ('TIESC_HW',0,),
    ('_PIC18',0,),
    ('_PIC24',0,),
    ('TEST_APPLICATION',0),
    ('TIESC_APPLICATION', 0),

    ('physics','YY'),
)

def set_default_val(settings, dest, val):
    if dest not in settings:
        settings[dest] = val

def set_default(settings, dest, src):
    if dest not in settings:
        settings[dest] = settings[src]

def get_mapped_subobjects(coe_dict, map_addr):
    subs = []
    for pdo_map_entry in (obj for obj in coe_dict if (obj.index&0xff00)==map_addr):
        for mso in pdo_map_entry.subs[1:]:
            subs.append(find_by_map_loc(coe_dict,mso.default))
    return subs

def make(world, *args):
    # Essentially, many of the settings are stolen from the ecat_def header 
    # file. Additional lowercase symbols are added for C and internal
    # data
    settings = world.settings
    
    # Fill in sane defaults, where missing
    for d in sane_defaults:
        set_default_val(settings, d[0], d[1])

    ### Prepare SII configuration
    # Obtain size of SII EEPROM in bytes
    eeprom_size = settings.get('ESC_EEPROM_SIZE',2048)
    
    # In the EEPROM, the size is specified as kibibits-1
    set_default_val(settings, 'sii.size', (eeprom_size*8/1024)-1)
    
    # Convert physical port string to SII bitfield
    phys_port = 0
    for index,port in enumerate(settings['physics']):
        shift = index*4
        if port=='Y':
            phys_port |= 1 << shift
        elif port=='K':
            phys_port |= 3 << shift
#        elif port=='H':
#            phys_port |= 2 << shift
    set_default_val(settings, 'sii.phys_port', phys_port)

    # Work out mailbox protocol flags IAW ETG.1000.6 Table 18
    mbx_protocol = settings.get('mbx_protocol',0)
    if settings.get('AOE_SUPPORTED',0):
        mbx_protocol |= 1
    if settings.get('EOE_SUPPORTED',0):
        mbx_protocol |= 2
    if settings.get('COE_SUPPORTED',0):
        mbx_protocol |= 4 
    if settings.get('FOE_SUPPORTED',0):
        mbx_protocol |= 8
    if settings.get('SOE_SUPPORTED',0):
        mbx_protocol |= 16
    if settings.get('VOE_SUPPORTED',0):
        mbx_protocol |= 32
    settings['mbx_protocol'] = mbx_protocol

    set_default_val(settings, 'MAILBOX_SUPPORTED', 1 if mbx_protocol else 0)

    # Structure Category General 
    set_default_val(settings, 'coe_details', 0)
    if settings['COE_SUPPORTED']:
        settings['coe_details'] |= 3 
    if settings['COMPLETE_ACCESS_SUPPORTED']:
        settings['coe_details'] |= 0x20

    set_default_val(settings, 'foe_details', 1 if settings['FOE_SUPPORTED'] else 0)
    set_default_val(settings, 'eoe_details', 1 if settings['EOE_SUPPORTED'] else 0)
    
    set_default(settings, 'bs_mbx_rx_off', 'DEF_MBX_WRITE_ADDRESS')
    set_default_val(settings, 'bs_mbx_rx_size', 128)
    set_default(settings, 'bs_mbx_tx_off', 'DEF_MBX_READ_ADDRESS')
    set_default_val(settings, 'bs_mbx_tx_size', 128)
    
    set_default(settings, 'std_mbx_rx_off', 'DEF_MBX_WRITE_ADDRESS')
    set_default_val(settings, 'std_mbx_rx_size', 128)
    set_default(settings, 'std_mbx_tx_off', 'DEF_MBX_READ_ADDRESS')
    set_default_val(settings, 'std_mbx_tx_size', 128)

    set_default_val(settings,'DEVICE_NAME_LEN',len(settings['DEVICE_NAME']))
    set_default_val(settings,'DEVICE_HW_VERSION_LEN',len(settings['DEVICE_HW_VERSION']))
    set_default_val(settings,'DEVICE_SW_VERSION_LEN',len(settings['DEVICE_SW_VERSION']))
    
    rx_pdos = get_mapped_subobjects(world.coe_dict, 0x1600)
    tx_pdos = get_mapped_subobjects(world.coe_dict, 0x1a00)
    
    rx_pdo_bytes = (sum(so.pdo_bitsize() for so in rx_pdos)+7)/8   
    tx_pdo_bytes = (sum(so.pdo_bitsize() for so in tx_pdos)+7)/8   
    
    set_default_val(settings,'MAX_PD_OUTPUT_SIZE',rx_pdo_bytes)
    set_default_val(settings,'MAX_PD_INPUT_SIZE',tx_pdo_bytes)
    
    set_default_val(settings, 'INTERRUPTS_SUPPORTED', 1 if 
        settings['DC_SUPPORTED'] or settings['AL_EVENT_ENABLED'] or 
        settings['ECAT_TIMER_INT'] else 0)
  
    
    