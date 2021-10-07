
from imp_lexer import *

import requests

class Result:
    def __init__(self, value, pos):
        self.value = value
        self.pos = pos

    def __repr__(self):
        return 'Result(%s,%d)' % (self.value, self.pos)


class Parser:
    def __call__(self,tokens,pos):
        return None

    def __add__(self,other):
        return Concat(self,other)

    def __mul__(self,other):
        return Exp(self,other)

    def __or__(self,other):
        return Alternate(self,other)

    def __xor__(self,function):
        return Process(self, function)


class Reserved(Parser):
    def __init__(self,value,tag):
        self.value = value
        self.tag = tag

    def __call__(self,tokens,pos):
        if pos < len(tokens) and \
            tokens[pos][0] == self.value and \
            tokens[pos][1] is self.tag:
             return Result(tokens[pos][0], pos + 1)
        else:
             return None

class Tag(Parser):
    def __init__(self,tag):
        self.tag = tag

    def __call__(self, tokens, pos):
        if pos < len(tokens) and tokens[pos][1] is self.tag:
            return Result(tokens[pos][0], pos + 1)
        else:
            return None
    def __repr__(self):
        return self.tag

class Concat(Parser):
    def __init__(self,left,right):
        self.left = left
        self.right = right

    def __call__(self,tokens,pos):
        left_result = self.left(tokens,pos)
        if left_result:
            right_result = self.right(tokens,left_result.pos)
            if right_result:
                combined_value = (left_result.value, right_result.value)
                return Result(combined_value, right_result.pos)
        return None

class Alternate(Parser):
    def __init__(self,left,right):
        self.left = left
        self.right = right

    def __call__(self, tokens, pos):
        left_result = self.left(tokens,pos)
        if left_result:
            return left_result
        else:
            right_result = self.right(tokens,pos)
            return right_result

class Opt(Parser):
    def __init__(self,parser):
        self.parser = parser

    def __call__(self,tokens,pos):
        result = self.parser(tokens,pos)
        if result:
            return result
        else:
            return Result(None,pos)

class Process(Parser):
    def __init__(self, parser, function):
        self.parser = parser
        self.function = function

    def __call__(self, tokens, pos):
        result = self.parser(tokens, pos)
        if result:
            result.value = self.function(result.value)
            return result

class Lazy(Parser):
    def __init__(self, parser_func):
        self.parser = None
        self.parser_func = parser_func

    def __call__(self, tokens, pos):
        if not self.parser:
            self.parser = self.parser_func()
        return self.parser(tokens, pos)

class Phrase(Parser):
    def __init__(self, parser):
        self.parser = parser

    def __call__(self, tokens, pos):
        result = self.parser(tokens, pos)
        if result and result.pos == len(tokens):
            return result
        else:
            return None

class Exp(Parser):
    def __init__(self, parser, separator):
        self.parser = parser
        self.separator = separator

    def __call__(self, tokens, pos):
        result = self.parser(tokens, pos)

        def process_next(parsed):
            return CompoundStatement(result.value, parsed)
        next_parser = self.parser ^ process_next

        next_result = result
        while next_result:
            next_result = next_parser(tokens, result.pos)
            if next_result:
                result = next_result
        return result



class Pyexp:
    def __init__(self,exp):
        self.exp = exp
    def __repr__(self):
        return self.exp

class Reqexp:
    pass

class Getexp(Reqexp):
    def __init__(self,addr, params, res):
        self.addr = addr
        self.params = params
        self.res = res
    def __repr__(self):
        return str(self.addr) + " " + str(self.params) + " " + str(self.res)
    def eval(self):
        addr = globals().get(self.addr.name, self.addr.name)
        params = globals().get(self.params.name, self.params.name)
        res = self.res.name
        globals()[res] = requests.get(addr, params=params)
        return globals()[res]
    
class Postexp(Reqexp):
    def __init__(self,addr,body, params, res):
        self.addr = addr
        self.body = body
        self.params = params
        self.res = res

class Varexp(Reqexp):
    def __init__(self,name):
        self.name = name
    def __repr__(self):
        return self.name
    def eval(self):
        return globals()[self.name]

class Jsonexp(Reqexp):
    def __init__(self,exp):
        self.exp = exp
    def __repr__(self):
        return self.exp
    def eval(self):
        return self.exp

class Statement:
    pass

class CompoundStatement(Statement):
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def __repr__(self):
        return 'CompoundStatement(%s, %s)' % (self.first, self.second)

    def eval(self):
        self.first.eval()
        self.second.eval()

class Getstat(Statement):
    def __init__(self,exp):
        self.exp = exp
    def eval(self):
        self.exp.eval()

class Poststat(Statement):
    def __init__(self,exp):
        return 0

class Pystat(Statement):
    def __init__(self,exp):
        self.exp = exp
    def eval(self):
        try:
            exec(self.exp, globals(), globals())
        except:
            print(self.exp + " failed")


def keyword(kw):
    return Reserved(kw, RESERVED)

num = Tag(INT) ^ (lambda i:int(i))
id = Tag(ID)
json = Tag(JSON)
pyexp = Tag(PYTHON_EXP)

def req_value():
    return (id^(lambda v: Varexp(v))) | (json ^ (lambda j: Jsonexp(j)))

def req_term():
    return req_value()

def get_req_exp():
    return (req_term() + req_term() + keyword('=>') + (id^(lambda v: Varexp(v))))^process_getreq

def post_req_exp():
    return (req_term() + req_term() + req_term() + keyword('=>') + (id^(lambda v: Varexp(v))))^process_postreq()

def process_getreq(parsed):
    (((a,p),_),r) = parsed
    return Getexp(a,p,r)

def process_postreq():
    return lambda addr, body, params, res : Postexp(addr,body,params, res)

def getstat():
    def proc(parsed):
        (_,gs) = parsed
        return Getstat(gs)
    return keyword('GET') + get_req_exp()^proc

def pystat():
    def proc(parsed):
        return Pystat(parsed[1:-1])
    return pyexp^proc

def stmt_list():
    separtator = keyword('\n')  ^ (lambda x: lambda l, r: CompoundStatement(l, r))
    return Exp(stmt(),separtator)

def stmt():
    return pystat() | getstat()

def parser():
    return Phrase(stmt_list())

def imp_parse(tokens):
    ast = parser()(tokens,0)
    return ast