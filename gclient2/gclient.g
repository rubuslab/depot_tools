grammar = gclient_file | deps_file,

gclient_file = ws (gclient_stmt:s ws -> s)+:ss end          -> ss,

deps_file = ws (deps_stmt:s ws -> s)+:ss end                -> ss,

ws = (' ' | '\t' | comment | eol)*,

sp = (' ' | '\t')*,

// Comments extend to the end of the line (or the end of the file if the
// file doesn't end in a newline).
comment = '#' (~(eol|end) anything)* (eol|end),

eol = '\r' | '\n' | '\r\n',

gclient_stmt = solution | target_os,

// The last two statement types are ignored by gclient but used by
// checkdeps.py.
deps_stmt = vars
    | allowed_hosts
    | deps
    | deps_os
    | hooks
    | recursion 
    | recursedeps
    | include_rules
    | skip_child_includes
    | specific_include_rules
    | target_os
    | use_relative_paths,

solution = 'solutions':k sp '=' sp object_list:v           -> [k, v],

object_list = '[' ws (object:o ws ',' ws -> o)*:hd object?:tl ws ']'
                                                           -> ['object_list',
                                                               hd + tl],

// We don't use actual dicts for objects so that we can do further evaluation
// of the keys and values.
object = '{' (ws pair:kv ',' -> kv)*:hd (pair)?:tl ws '}'  -> ['object',
                                                               hd + tl],

pair  = str_expr:k ws ':' ws value:v                       -> [k, v],

value = str_expr
    | bool
    | object
    | str_list
    | 'None'                                               -> ['null', null],

str_expr = str_or_var:e1 (ws '+' ws str_expr:e2 -> e2)*:tl -> ['str_expr', 
                                                               [e1] + tl]
    | '(' ws str_expr:e ws ')'                             -> e,

str_or_var = str:s                                         -> ['str', s] 
    | 'Var(' str:s ')'                                     -> ['var', s],

str = sq_str | dq_str,

sq_str = '\'' (~('\'' | eol) anything)*:cs '\''            -> join('', cs),

dq_str = '"' (~('"' | eol) anything)*:cs '"'               -> join('', cs),

bool = 'True'                                              -> ['bool', true]
    | 'False'                                              -> ['bool', false],

target_os = 'target_os':k sp '=' sp str_list:v             -> [k, v],

str_list = '[' ws (str_expr:s ws ',' ws -> s)*:hd str_expr?:tl ws ']' -> ['str_list', 
                                                                          hd + tl],

// The vars object is a dict mapping variable names (strs) to
// strings or dicts mapping conditions to strings.
vars = 'vars':k sp '=' sp object:v                         -> [k, v],

// recursion is deprecated and we might be able to omit it.
recursion = 'recursion':k sp '=' sp digit+:ds              -> [k, ['num', 
                                                                   atoi(ds)]],

// recursedeps is a list of either dependencies or pairs of (dep, filename)
// where the filename specifies what file in the dependency to use instead
// of DEPS.
recursedeps = 'recursedeps':k sp '=' sp rec_list:v         -> [k, v],

// TODO: come up with better names for these two rules :).
rec_list = '[' ws (rec:el ws ',' ws -> el)*:hd rec?:tl ws ']' -> ['rec_list',
                                                                  hd + tl],

rec  = '(' ws str:k ws ',' ws str:v ws ')'                 -> [k, v]
     | str:k                                               -> [k, 'DEPS'],

// Each member of the list must be a valid domain name.
allowed_hosts = 'allowed_hosts':k sp '=' sp str_list:v     -> [k, v],

// The object is a map of str to str_exprs. The str_expr must
// evaluate to a valid URL.
deps = 'deps':k sp '=' sp object:v                         -> [k, v],

// The object is a map of strs to (maps of strs to str_exprs).
deps_os = 'deps_os':k sp '=' sp object:v                   -> [k, v],

// Each object in the list is a map containing:
//   { 'name': str, 'pattern': str, 'action': str_list }
hooks = 'hooks':k sp '=' sp object_list:v                  -> [k, v],

include_rules = 'include_rules':k sp '=' sp str_list:v     -> [k, v],

skip_child_includes = 'skip_child_includes':k sp '=' sp str_list:v
                                                           -> [k, v],

// This is a map of str -> str_exprs.
specific_include_rules = 'specific_include_rules':k sp '=' sp object:v
                                                           -> [k, v],

use_relative_paths = 'use_relative_paths':k sp '=' sp bool:v -> [k, v],

// Some strings may contain conditional expressions in the following format.
// Conditionals are GN-like (i.e., C-like), not Python-like.
conditional = or_expr,

// The associativity of these next two are "wrong" -- (a && b && c) will parse
// as (a && (b && c)) -- but that doesn't effect the computation since the
// operators are associative and short-circuiting will still work right.
// TODO: replace these with left-recursive expressions when that works in glop.
or_expr  = and_expr:l ('||' or_expr)*:r                    -> ['||', l, r],

and_expr = not_expr:l ('&&' and_expr)*:r                   -> ['&&', l, r],

not_expr = '!' bool_expr:e                                 -> ['!', e]
    | bool_expr,

// The 'in' operator only works against target_os and is only intended for
// backwards compatibility.
bool_expr = prim_expr:l sp '==' sp prim_expr:r             -> ['==', l, r]
    | prim_expr:l sp '!=' sp prim_expr:r                   -> ['!=', l, r]
    | prim_expr:l sp 'in' sp 'target_os'                   -> ['in', l,
                                                               'target_os'],

prim_expr = name:e                                         -> ['var', e]                 
    | dq_str:e                                             -> ['str', e]
    | '(' sp conditional:e sp ')'                          -> e,

name = (letter | '_'):hd (letter | digit | '_')*:tl        -> hd + join('',tl)

