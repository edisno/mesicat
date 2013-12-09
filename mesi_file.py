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
    
    #PARENT_ACCESS = ACCESS.copy().setParseAction(parent_eval_access)
    #CHILD_ACCESS = ACCESS.copy().setParseAction(child_eval_access)
    
    #MAP = Keyword("map")
    RECORD = Keyword("record")
    
    NAME = Word(alphas+"_", alphanums+"_.")
    WILDNAME = Word(alphas+"_", alphanums+"_.*")
    integer = Regex(r"[+-]?\d+").setParseAction(lambda tok: int(tok[0]))
    hex_integer = Regex(r"0x[0-9a-zA-Z]+").setParseAction(lambda tok: int(tok[0],16))
    
    def find_wildname_list(symbol):
        pat = re.compile(fnmatch.translate(symbol))
        return [coe_vars[k] for k in coe_vars.keys() if pat.match(k)]
    
    #expr = Forward()
    #operand = NAME | integer | char | string_
    #expr << (operatorPrecedence(operand, 
    #    [
    #    (oneOf('! - *'), 1, opAssoc.RIGHT),
    #    (oneOf('++ --'), 1, opAssoc.RIGHT),
    #    (oneOf('++ --'), 1, opAssoc.LEFT),
    #    (oneOf('* / %'), 2, opAssoc.LEFT),
    #    (oneOf('+ -'), 2, opAssoc.LEFT),
    #    (oneOf('< == > <= >= !='), 2, opAssoc.LEFT),
    #    (Regex(r'=[^=]'), 2, opAssoc.LEFT),
    #    ]) + 
    #    Optional( LBRACK + expr + RBRACK | 
    #              LPAR + Group(Optional(delimitedList(expr))) + RPAR )
    #    )
    
    expr = MatchFirst([hex_integer, integer, "&" + NAME, "$" + NAME, NAME])
    class expr_eval():
        def __init__(self, tok):
            self.values = tok
        def eval(self, parent):
            t = self.values
            if isinstance(t[0],int):
                return t[0]
                
            if t[0]=='$':
                f = lambda x: x.index
                t = t[1:]
            elif t[0]=='&':
                f = lambda x: x.coe_reference()
                t = t[1:]
            else:
                f = lambda x: x.default
            return f( coe_dict(t) )
    expr.setParseAction(expr_eval)
    expr = Group( expr )
    
    list_expr = delimitedList(MatchFirst([hex_integer, integer, Combine("&" + WILDNAME), Combine("$" + WILDNAME), WILDNAME]))
    class list_expr_eval():
        def __init__(self, tok):
            self.values = tok
        def eval(self, parent):
            vals = []
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
    DESCRIPTION = (dblQuotedString.copy().setParseAction(removeQuotes))("description")
    STRING_LITERAL = dblQuotedString.copy().setParseAction(removeQuotes)
    DEFAULT = EQUAL + expr("default")
    PROPERTY = Suppress('.') + NAME("property") + EQUAL + expr("value") #+ LPAR + expr("value") + RPAR
    
    #expr.setDebug()
    #map_expr.setDebug()
    #INDEX.setDebug()
    
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
    
    assign_stmt = NAME('symbol') + '=' + (expr | STRING_LITERAL)('default') + SEMI
    class eval_assign():
        def __init__(self, tok):
            self.values = tok
        def eval(self,parent):
            statement_parms = self.values.asDict()

            symbol = statement_parms['symbol']

            default = statement_parms['default']
            if not isinstance(default, basestring):
                default = default[0].eval(self)
            
            obj = assign_object(symbol, default)
            coe_vars[symbol] = obj

            return None
    assign_stmt.setParseAction(eval_assign)    
    
    variable_statement = TYPE("btype") + ACCESS("access") + NAME("symbol") + ZeroOrMore(INDEX | DEFAULT | DESCRIPTION) + SEMI;
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
    
    record_statement = RECORD + ACCESS("access") + NAME("symbol") + ZeroOrMore(INDEX | DESCRIPTION) + Group(LBRACE + OneOrMore(subindex_statement) + RBRACE)("subindex") + SEMI
    class eval_record():
        def __init__(self, tok):
            self.values = tok
            self.default_access = 0
        def eval(self,parent):
            # parent is some object with .last_index
            statement_parms = self.values.asDict()
            
            if 'index' in statement_parms:
                index = statement_parms['index'][0].eval(self)
            else:
                index = parent.last_index+1
            parent.last_index = index
            symbol = statement_parms['symbol']
            description = statement_parms.get('description', 'Index %#04x'%index) 

            obj = coe_object(coe_object.oc_record, index, symbol, description)
            obj.default_access = statement_parms.get('access',0)
            coe_vars[symbol] = obj
            # Add nothing -- gets us a subindex 0 and padding
            obj.add()
            
            for sis in statement_parms['subindex']:
                obj.subs.append( sis.eval(obj) )
            
            return obj
    record_statement.setParseAction(eval_record)    

    array_statement = TYPE("btype") + ACCESS("access") + NAME("symbol") + LBRACK + Optional(expr("size")) + RBRACK + ZeroOrMore(INDEX | DESCRIPTION) + Optional(EQUAL + LBRACE + list_expr("values") + RBRACE) + SEMI
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
                    result.coe_dict.append(obj)
    body.ignore(cppStyleComment).setParseAction(eval_body)

    class result_object():
        def __init__(self):
            self.last_index = 0
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

test = r"""
// g5im.mesi -- Meta ESI file for G5 Instrument Module project

// RxPDO Definitions
record read rx_pdo_mapping pdo_dig_outputs @ 0x7100 "Digital Outputs" {
    BOOL j101_7 =1 "J101-7";
    BOOL j101_8 "J101-8" =1;
    BOOL j101_9 "J101-9";
    BOOL j101_10 "J101-10";
    BOOL j102_a "J102-A";
    BOOL j102_b "J102-B";
    BOOL j103_a "J103-A";
    BOOL j103_b "J103-B";
    BOOL j104_a "J104-A";
    BOOL j104_b "J104-B";
    BOOL j105_a "J105-A";
    BOOL j105_b "J105-B";
    PAD4 reserved;
};

record read rx_pdo_mapping rx_pdo_dac_0 @0x7200 "Control (DAC) RxPDO-0" {
    USINT servo_mode "Servo control mode select";
    REAL data0 "Data 0"; // (various data depending on mode)
    REAL data1 "Data 1";
    BOOL dig_out "Digital Output";
    BOOL rst_integ "Servo Integrator reset";
    PAD6 reserved;
};

record read rx_pdo_mapping rx_pdo_dac_1 "Control (DAC) RxPDO-1" @ 0x7300  {
    USINT servo_mode "Servo control mode select";
    REAL data0 "Data 0"; // (various data depending on mode)
    REAL data1 "Data 1";
    BOOL dig_out "Digital Output";
    BOOL rst_integ "Servo Integrator reset";
    PAD6 reserved;
};

record read rx_pdo_mapping rx_pdo_dac_2 @0x7400 "Control (DAC) RxPDO-2" {
    USINT servo_mode "Servo control mode select";
    REAL data0 "Data 0"; // (various data depending on mode)
    REAL data1 "Data 1";
    BOOL dig_out "Digital Output";
    BOOL rst_integ "Servo Integrator reset";
    PAD6 reserved;
};

record read rx_pdo_mapping rx_pdo_dac_3 @0x7500 "Control (DAC) RxPDO-3" {
    USINT servo_mode "Servo control mode select";
    REAL data0 "Data 0"; // (various data depending on mode)
    REAL data1 "Data 1";
    BOOL dig_out "Digital Output";
    BOOL rst_integ "Servo Integrator reset";
    PAD6 reserved;
};

record read rx_pdo_mapping pdo_can_out @0x7600 "CAN Bus Transmit Data" {
    USINT tx_cnt "Transmit data counter"; // Increments for every new message
    USINT reserved "Reserved"; 		// All the following registers in SJA1000 format
    USINT id_high "ID (10..3)";
    USINT id_low "ID (2..0) RTR DLC";
    USINT data_1 "Data 1";
    USINT data_2 "Data 2";
    USINT data_3 "Data 3";
    USINT data_4 "Data 4";
    USINT data_5 "Data 5";
    USINT data_6 "Data 6";
    USINT data_7 "Data 7";
    USINT data_8 "Data 8"; 
};

// TxPDO Definitions
record read tx_pdo_mapping pdo_super @0x6000 "Supervisory TxPDO" {
    UDINT time_low "Low 32 bits of system time at sample 0";
    BOOL teds_det1 "TEDS presence detect 1";
    BOOL teds_det2 "TEDS presence detect 2";
    BOOL teds_det3 "TEDS presence detect 3";
    BOOL teds_det4 "TEDS presence detect 4";
    PAD4 reserved;
};

record read tx_pdo_mapping pdo_dig_inputs @0x6100 "Digital Inputs" {
    BOOL j101_7 "J101-7";
    BOOL j101_8 "J101-8";
    BOOL j101_9 "J101-9";
    BOOL j101_10 "J101-10";
    BOOL j102_a "J102-A";
    BOOL j102_b "J102-B";
    BOOL j103_a "J103-A";
    BOOL j103_b "J103-B";
    BOOL j104_a "J104-A";
    BOOL j104_b "J104-B";
    BOOL j105_a "J105-A";
    BOOL j105_b "J105-B";
    PAD4 reserved;
};

record read tx_pdo_mapping pdo_measure_0 @0x6200 "Measurement (ADC) TxPDO-0" {
    REAL data0 "Sample 0"; 
    REAL data1 "Sample 1";
    REAL data2 "Sample 2";
    REAL data3 "Sample 3";
    REAL data4 "Sample 4";
    BOOL dig_in "Digital Input";
    BOOL config_valid "Configuration valid and measurement active";
    BOOL measurement "Measurement toggle";
    BOOL low_limit_ind "Low limit";
    BOOL hi_limit_ind "High limit";
    BOOL excitation_err_ind "Excitation error";
    BOOL sync_err_ind "Synchronization error";
    BOOL pga_err_ind "PGA Error";
};

record read tx_pdo_mapping pdo_measure_1 @0x6300 "Measurement (ADC) TxPDO-1" {
    REAL data0 "Sample 0"; 
    REAL data1 "Sample 1";
    REAL data2 "Sample 2";
    REAL data3 "Sample 3";
    REAL data4 "Sample 4";
    BOOL dig_in "Digital Input";
    BOOL config_valid "Configuration valid and measurement active";
    BOOL measurement "Measurement toggle";
    BOOL low_limit_ind "Low limit";
    BOOL hi_limit_ind "High limit";
    BOOL excitation_err_ind "Excitation error";
    BOOL sync_err_ind "Synchronization error";
    BOOL pga_err_ind "PGA Error";
};

record read tx_pdo_mapping pdo_measure_2 @0x6400 "Measurement (ADC) TxPDO-2" {
    REAL data0 "Sample 0"; 
    REAL data1 "Sample 1";
    REAL data2 "Sample 2";
    REAL data3 "Sample 3";
    REAL data4 "Sample 4";
    BOOL dig_in "Digital Input";
    BOOL config_valid "Configuration valid and measurement active";
    BOOL measurement "Measurement toggle";
    BOOL low_limit_ind "Low limit";
    BOOL hi_limit_ind "High limit";
    BOOL excitation_err_ind "Excitation error";
    BOOL sync_err_ind "Synchronization error";
    BOOL pga_err_ind "PGA Error";
};

record read tx_pdo_mapping pdo_measure_3 @0x6500 "Measurement (ADC) TxPDO-3" {
    REAL data0 "Sample 0"; 
    REAL data1 "Sample 1";
    REAL data2 "Sample 2";
    REAL data3 "Sample 3"; 
    REAL data4 "Sample 4";
    BOOL dig_in "Digital Input";
    BOOL config_valid "Configuration valid and measurement active";
    BOOL measurement "Measurement toggle";
    BOOL low_limit_ind "Low limit";
    BOOL hi_limit_ind "High limit";
    BOOL excitation_err_ind "Excitation error";
    BOOL sync_err_ind "Synchronization error";
    BOOL pga_err_ind "PGA Error";
};

record read tx_pdo_mapping pdo_can_in @0x6600 "CAN Bus Receive Data" {
    USINT rx_cnt "Receive data counter"; // Increments for every new message
    USINT status "Status"; // All the following registers in SJA1000 format
    USINT id_high "ID (10..3)";
    USINT id_low "ID (2..0) RTR DLC";
    USINT data_1 "Data 1";
    USINT data_2 "Data 2";
    USINT data_3 "Data 3";
    USINT data_4 "Data 4";
    USINT data_5 "Data 5";
    USINT data_6 "Data 6";
    USINT data_7 "Data 7";
    USINT data_8 "Data 8"; 
};

// PDO Mappings
UDINT read rx_pdo_map_dig_outputs[1] @0x1600 = { &pdo_dig_outputs.* };
UDINT read rx_pdo_map_dac_0[1] = { &rx_pdo_dac_0.* , &rx_pdo_dac_1.* };
UDINT read rx_pdo_map_dac_1[1] = { &rx_pdo_dac_1.* };
UDINT read rx_pdo_map_dac_2[1] = { &rx_pdo_dac_2.* };
UDINT read rx_pdo_map_dac_3[1] = { &rx_pdo_dac_3.* };
UDINT read rx_pdo_map_can_out[1] = { &pdo_can_out.* };

UDINT read tx_pdo_map_super[] @0x1a00 = { &pdo_super.* };
UDINT read tx_pdo_map_dig_inputs[] = { &pdo_dig_inputs.* };
UDINT read tx_pdo_map_measure_0[] = { &pdo_measure_0.* };
UDINT read tx_pdo_map_measure_1[] = { &pdo_measure_1.* };
UDINT read tx_pdo_map_measure_2[] = { &pdo_measure_2.* };
UDINT read tx_pdo_map_measure_3[] = { &pdo_measure_3.* };
UDINT read tx_pdo_map_can_in[] = { &pdo_can_in.* };

// PDO Assigns
UINT read sRxPDOassign[6] @0x1c12 = { $rx_pdo_map_* };  
UINT read sTxPDOassign[6] @0x1c13 = { $tx_pdo_map_* };
"""

if __name__ == "__main__":
    #try:
    ast = parse(test)
    import pprint
    pprint.pprint(ast)
    #except SemanticException, err:
    #    print err
    #    exit(3)
    #except ParseException as err:    
    #    print 'Error :{e.lineno} [col {e.col}]: {e.line}'.format(e=err)
        #exit(3)



#def parse(filename):
#    with open(filename, 'r') as in:
        