
import lexer

RESERVED = 'RESERVED'
INT      = 'INT'
ID       = 'ID'
STR_CONST= 'STR_CONST'
JSON     = 'JSON'
PYTHON_EXP = 'PYTHON_EXP'

token_exprs = [
    (r'[ \n\t]+',                  None),
    (r'#[^\n]*',                   None),
    (r'GET' ,                  RESERVED),
    (r'POST' ,                 RESERVED),
    (r'\|.*\|',              PYTHON_EXP),                                                 
    (r'\{.*\}',                    JSON),
    (r'\[.*\]',                    JSON),
    (r'=>' ,                   RESERVED),
    (r'".*"',                 STR_CONST),
    (r'[0-9]+',                     INT),
    (r'[A-Za-z][A-Za-z0-9_]*',       ID),
]

def imp_lex(characters):
    return lexer.lex(characters, token_exprs)