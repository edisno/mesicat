"""
mesi_file.py

Parse .mesi file in to a coe dictionary

Created on Mon Nov 11 09:46:24 2013

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

import itertools
import re
import fnmatch
from pyparsing import *
from coe_defs import *

"""

------------------------------------------------------------------------------
mesi file outline:
// Comment
<define_symbol>=<value>;

make <module_name> [<arugments> ...];

record [<access>] <symbol> [@<index>] ["<description>"] {
    [<basic_type> [<access>] symbol [@<subindex>] [=<default_value>] ["<description>"];]
    ...
}

<basic_type> [<access>] <symbol> [@<index>] [=<default_value>] ["<description>"];

<basic_type> [<access>] <symbol>\[[<count>]\] [@<index>] [={<default_value>[,<default_value>]}] ["<description>"];

------------------------------------------------------------------------------

Grammar:

record_statement = 'record' access_specifier symbol (index_specifier|description_specifier)* '{' subindex_list '}' ';'
map_statement = 'map' access_specifier symbol (index_specifier|description_specifier)* '{' symbol_list '}' ';'
value_statement = basic_type access_specifier symbol (index_specifier|description_specifier)* default_specifier ';'
array_statement = basic_type access_specifier symbol '[' symbol ']' index_specifier ['=' '{'  default_value [',' default_value]* '}'] description_specifier ';'

digit = [0-9]
digits = digit | digit digits 
hex_digit = [0-9a-fA-F]
hex_digits = hex_digit | hex_digit hex_digits

integer = '0x' hex_digits | digits | symbol | '&' symbol | '$' symbol
index_specifier = '@' integer
description_specifier = '"' string '"' | ''

<access> = <access> [(readwrite|read|read_preop|read_safeop|read_op|write|write_preop|write_safeop|write_op|no_pdo_mapping|rx_pdo_mapping|tx_pdo_mapping|backup|settings|safe_inputs|safe_outputs|safe_parameter)] 
<index> = <integer>
<default_value> = <integer> | <float>

NOTES:
symbol convention: lower_case_with_underscore for internal definitions and C
symbols. UPPER_CASE for SSC defines.

Access specified at array or object level is default for all subobjects (may be overridden)

Subindex 000 is implied (automatically supplied) for array and record types

PDO mapping is supplied automatically based upon rx_pdo and tx_pdo access flags

If description is omitted, it will default to "Index 0x%04X" or "SubIndex %03d" in printf format

<symbol> returns the default value for the symbol. 
&<symbol> returns the CoE index,subindex,size code (as uint32_t)
$<symbol> returns the CoE index (as uint16_t)
If the default specifier list for an array declaration is larger than the
defined size of the array, the process will fail with an error.
"""

LPAR,RPAR,LBRACK,RBRACK,LBRACE,RBRACE,SEMI,COMMA,EQUAL = map(Suppress, "()[]{};,=")

# make keywords for CoE access modes
access_bits = {
    'readwrite':0x3f,
    'read':0x7,
    'read_preop':0x1,
    'read_safeop':0x2,
    'read_op':0x4,
    'write':0x38,
    'write_preop':0x8,
    'write_safeop':0x10,
    'write_op':0x20,
    'no_pdo_mapping':-0xc0,
    'rx_pdo_mapping':0x40,
    'tx_pdo_mapping':0x80,
    'backup':0x100,
    'settings':0x200,
    'safe_inputs':0x400,
    'safe_outputs':0x800,
    'safe_parameter':0x1000
}

def parse(string):
    coe_vars = {}
    
    # make keywords for CoE basic types
    type_keywords = []
    for ct in coe_types.keys():
        kw = Keyword(ct).setName(ct)
        vars()[ct] = kw
        type_keywords.append(kw)
        
    access_keywords = []
    for k,v in access_bits.iteritems():
        kw = Keyword(k) #.setName(k.upper())
        vars()[k.upper()] = kw
        access_keywords.append(kw)
    
    TYPE = MatchFirst(type_keywords)
    
    ACCESS = Group( ZeroOrMore( MatchFirst(access_keywords) ) )
    def eval_access(tok):
        field = 0
        for t in tok[0]:
            bits = access_bits[t]
            if bits >= 0:
                field |= bits
        #return {'mask':mask,'field':field}
        return field
    ACCESS.setParseAction(eval_access)
    
    RECORD = Keyword("record")
    
    NAME = Word(alphas+"_", alphanums+"_.")
    WILDNAME = Word(alphas+"_", alphanums+"_.*")
    integer = Regex(r"[+-]?\d+").setParseAction(lambda tok: int(tok[0]))
    hex_integer = Regex(r"0x[0-9a-zA-Z]+").setParseAction(lambda tok: int(tok[0],16))
    
    def find_wildname_list(symbol):
        pat = re.compile(fnmatch.translate(symbol))
        lst = [coe_vars[k] for k in coe_vars.keys() if pat.match(k)]
        print 'find_wildname_list(',symbol,') => ',lst
        return lst
    
    expr = MatchFirst([hex_integer, integer, "&" + NAME, "$" + NAME, NAME, dblQuotedString])
    class expr_eval():
        def __init__(self, tok):
            self.values = tok
        def eval(self, parent):
            t = self.values
            
            if isinstance(t[0],int):
                return t[0]
                
            if t[0][0]=='"':
                return t[0][1:-1]
            elif t[0]=='$':
                f = lambda x: x.index
                t = t[1:]
            elif t[0]=='&':
                f = lambda x: x.coe_reference()
                t = t[1:]
            else:
                f = lambda x: x.default
            return f( coe_vars[t] )
    expr.setParseAction(expr_eval)
    expr = Group( expr )
    
    list_expr = delimitedList(MatchFirst([hex_integer, integer, Combine("&" + WILDNAME), Combine("$" + WILDNAME), WILDNAME]))
    class list_expr_eval():
        def __init__(self, tok):
            self.values = tok
        def eval(self, parent):
            vals = []
            print 'processing',self.values
            for t in self.values:
                if isinstance(t,int):
                    vals.append(t)
                    continue

                if t[0]=='$':
                    f = lambda x: x.index
                    t = t[1:]
                elif t[0]=='&':
                    f = lambda x: x.coe_reference()
                    t = t[1:]
                else:
                    f = lambda x: x.default
                vals += sorted(f(x) for x in find_wildname_list(t))
            return vals
    list_expr.setParseAction(list_expr_eval)
    list_expr = Group( list_expr )
    
    INDEX = Suppress('@') + expr("index")
    DESCRIPTION = Suppress(':') + (dblQuotedString.copy().setParseAction(removeQuotes))("description")
    STRING_LITERAL = dblQuotedString.copy().setParseAction(removeQuotes)
    DEFAULT = EQUAL + expr("default")
    PROPERTY = ZeroOrMore(Group(Suppress('.') + NAME("key") + EQUAL + expr("value")))("property")
    
    #expr.setDebug()
    #map_expr.setDebug()
    #INDEX.setDebug()
    #DESCRIPTION.setDebug()
    
    class make_object():
        """Simple object to hold a make statement"""
        def __init__(self, symbol, value):
            # The name default is used so this can be read like a coe_sub_object
            self.index = 0
            self.symbol = symbol
            self.default = value
        def __repr__(self):
            return "make_object(symbol='%s', default='%s')" % (self.symbol, self.default)
    
    MAKE_ARGS = ZeroOrMore( Word(alphanums+":!@#$%^()=+[]{}<>_./\\-") )
    make_stmt = 'make' + NAME('module') + MAKE_ARGS('args') + SEMI;
    class eval_make():
        def __init__(self, tok):
            self.values = tok
        def eval(self,parent):
            statement_parms = self.values.asDict()
           
            parent.make_list.append( 
                (statement_parms['module'], 
                 statement_parms['args'].asList() if 'args' in statement_parms else [])
            )

            return None
    make_stmt.setParseAction(eval_make)

    class assign_object():
        """Simple object to hold an assigned value"""
        def __init__(self, symbol, value):
            # The name default is used so this can be read like a coe_sub_object
            self.index = 0
            self.symbol = symbol
            self.default = value
        def __repr__(self):
            return "assign_object(symbol='%s', default='%s')" % (self.symbol, self.default)
        def coe_reference(self):
            raise TypeError("Error: assign_object %s cannot be referenced" % self.symbol)
    def add_coe_literal(symbol, value):    
        obj = assign_object(symbol, value)
        coe_vars[symbol] = obj
        
    assign_stmt = NAME('symbol') + '=' + expr('default') + SEMI
    class eval_assign():
        def __init__(self, tok):
            self.values = tok
        def eval(self,parent):
            statement_parms = self.values.asDict()

            symbol = statement_parms['symbol']

            default = statement_parms['default']
            if not isinstance(default, basestring):
                default = default[0].eval(self)
            
            add_coe_literal(symbol, default)

            return None
    assign_stmt.setParseAction(eval_assign)    
    
    variable_statement = TYPE("btype") + ACCESS("access") + NAME("symbol") + ZeroOrMore(INDEX | DEFAULT | DESCRIPTION) + PROPERTY + SEMI;
    subindex_statement = variable_statement.copy()
    class eval_variable():
        def __init__(self, tok):
            self.values = tok
            self.parameters = { 'default':0, 'index':0, 'description':None }            
        def eval(self,parent):
            # parent is object with .last_index
            statement_parms = self.values.asDict()

            if 'index' in statement_parms:
                index = statement_parms['index'][0].eval(self)
            else:
                index = parent.last_index+1
            parent.last_index = index
            access = statement_parms.get('access',0)
            btype = statement_parms['btype']
            symbol = statement_parms['symbol']
            if 'default' in statement_parms:
                default = statement_parms['default'][0].eval(self)
            else:
                default = 0
            description = statement_parms.get('description', 'Index %#04x'%index) 

            obj = coe_object(coe_object.oc_variable, index, symbol, description)
            obj.default = default
            
            obj.add(default,access=access,index=index,subindex=0,btype=btype,symbol=symbol,description=description)
            coe_vars[symbol] = obj

            obj.properties = {}            
            if 'property' in statement_parms:
                for prop in statement_parms['property']:
                    key = prop['key']
                    value = prop['value'][0].eval(self)
                    obj.properties[key] = value
                    add_coe_literal('.'.join((symbol,key)), value)

            return obj
    variable_statement.setParseAction(eval_variable)    

    class eval_subindex():
        def __init__(self, tok):
            self.values = tok
        def eval(self,parent):
            # parent is coe_object
            statement_parms = self.values.asDict()

            index = parent.index
            if 'index' in statement_parms:
                subindex = statement_parms['index'][0].eval(self)
            else:
                subindex = parent.max_subindex()+1
            access = statement_parms.get('access',0) | parent.default_access
            btype = statement_parms['btype']
            symbol = statement_parms['symbol']
            if 'default' in statement_parms:
                default = statement_parms['default'][0].eval(self)
            else:
                default = 0
            description = statement_parms.get('description') 

            so = coe_sub_object(index, subindex, access, btype, symbol, default, description)
            coe_vars[parent.symbol+'.'+symbol] = so
            return so
    subindex_statement.setParseAction(eval_subindex)    
    
    SPECIFICATION = delimitedList(Group(OneOrMore(INDEX | DESCRIPTION)))("specification")
    #SPECIFICATION.setDebug()
    
    record_statement = RECORD + ACCESS("access") + NAME("symbol") + ((LPAR + SPECIFICATION + RPAR) | ZeroOrMore(INDEX | DESCRIPTION)) + PROPERTY + Group(LBRACE + OneOrMore(subindex_statement) + RBRACE)("subindex") + SEMI
    class eval_record():
        def __init__(self, tok):
            self.values = tok
            self.default_access = 0
            
        def make_obj(self, symbol, parms, spec):
            if 'index' in spec:
                index = spec['index'][0].eval(self)
            else:
                index = self.parent.last_index+1
            self.parent.last_index = index
            
            description = spec.get('description', 'Index %#04x'%index) 

            obj = coe_object(coe_object.oc_record, index, symbol, description)
            obj.default_access = self.default_access
            obj.properties = self.properties
            for key,value in self.properties.iteritems():
                add_coe_literal('.'.join((symbol,key)), value)
            
            coe_vars[symbol] = obj
            # Add nothing -- gets us a subindex 0 and padding
            obj.add()
        
            for sis in parms['subindex']:
                obj.subs.append( sis.eval(obj) )
            obj.subs[0].default = obj.max_subindex()
            
            return obj
            
        def eval(self,parent):
            self.parent = parent
            # parent is some object with .last_index
            statement_parms = self.values.asDict()
            
            self.default_access = statement_parms.get('access',0)

            base_symbol = statement_parms['symbol']

            self.properties = {}            
            if 'property' in statement_parms:
                for prop in statement_parms['property']:
                    key = prop['key']
                    value = prop['value'][0].eval(self)
                    self.properties[key] = value

            if 'specification' in statement_parms:
                print '!@#',statement_parms
                objs = []     
                typedef_len = len(statement_parms['specification'])
                for i in xrange(typedef_len):
                    spec = statement_parms['specification'][i].asDict()
                    print '*&^',i, spec
                    symbol = '%s_%d' % (base_symbol, i)
                    obj = self.make_obj(symbol, statement_parms, spec)
                    obj.typedef = typedef_specification(base_symbol, typedef_len, i)
                    objs.append(obj)
                return objs
            else:
                return self.make_obj(base_symbol, statement_parms, statement_parms)
                
    record_statement.setParseAction(eval_record)    

    array_statement = TYPE("btype") + ACCESS("access") + NAME("symbol") + LBRACK + Optional(expr("size")) + RBRACK + ZeroOrMore(INDEX | DESCRIPTION) + PROPERTY + Optional(EQUAL + LBRACE + list_expr("values") + RBRACE) + SEMI
    class eval_array():
        def __init__(self, tok):
            self.values = tok
            self.parameters = {}
        def eval(self,parent):
            # parent is some object with .last_index
            statement_parms = self.values.asDict()
            
            btype = statement_parms['btype']
            access = statement_parms.get('access',0)
            if 'index' in statement_parms:
                index = statement_parms['index'][0].eval(self)
            else:
                index = parent.last_index+1
            parent.last_index = index
            symbol = statement_parms['symbol']
            if 'size' in statement_parms:
                size = statement_parms['size'][0].eval(self)
            else:
                size = 0
            description = statement_parms.get('description', 'Index %#04x'%index) 

            obj = coe_object(coe_object.oc_array, index, symbol, description)
            obj.default_access = statement_parms.get('access',0)
            coe_vars[symbol] = obj
            
            default_values = []
            for sis in statement_parms['values']:
                default_values += sis.eval(obj)
            
            if size > len(default_values):
                default_values += [0]*(size-len(default_values))
            
            obj.add(*default_values,access=access,index=index,btype=btype)
            
            obj.properties = {}            
            if 'property' in statement_parms:
                for prop in statement_parms['property']:
                    key = prop['key']
                    value = prop['value'][0].eval(self)
                    obj.properties[key] = value
                    add_coe_literal('.'.join((symbol,key)), value)

            return obj
    array_statement.setParseAction(eval_array)    
    
    statement = Group( make_stmt | assign_stmt | variable_statement | 
        record_statement | array_statement )
    
    body = ZeroOrMore(statement)
    class eval_body():
        def __init__(self, tok):
            self.values = tok
            self.access = 0
        def eval(self, result):
            for s in self.values:
                obj = s[0].eval(result)
                if obj:
                    try:
                        result.coe_dict.extend(obj)
                    except TypeError:
                        result.coe_dict.append(obj)
    body.ignore(cppStyleComment).setParseAction(eval_body)

    class result_object():
        def __init__(self):
            self.last_index = 0x6000
            self.coe_dict = []
            self.make_list = []
            self.settings = {}
            
    result = result_object()
    
    # set parser element names
    for vname in ("make_stmt assign_stmt variable_statement record_statement "
                  "array_statement statement body".split()):
        v = vars()[vname]
        v.setName(vname)
        #v.setDebug()
    
    #~ for vname in "fundecl stmt".split():
        #~ v = vars()[vname]
        #~ v.setDebug()
    body.parseString(string,parseAll=True)[0].eval(result)
    result.settings = dict((k,getattr(coe_vars[k],'default',0)) for k in coe_vars.keys())    
    
    return result
