# -*- coding: utf-8 -*-
"""
Created on Sun Dec 15 15:33:20 2013

@author: Dave Page
"""

from distutils.core import setup
setup(name='mesicat',
      version='0.1',
      description='Automate creation of supporting EtherCAT files',
      author='Dave Page',
      author_email='dave.page@gleeble.com',
      url='https://sourceforge.net/p/mesicat/',
      py_modules=['mesicat','coe_defs','coe_gen_c','coe_gen_sii','coe_gen_xml',
                  'ethercatinfo','mesi_file','mesi_settings'],
      )