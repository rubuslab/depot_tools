class Parser(object):
    def __init__(self, msg, fname, starting_rule='grammar', starting_pos=0):
        self.msg = msg
        self.fname = fname
        self.starting_rule = starting_rule
        self.starting_pos = starting_pos
        self.end = len(msg)
        self.val = None
        self.err = None
        self.pos = self.starting_pos
        self.errpos = self.starting_pos
        self.errset = set()
        self.builtins = ('anything', 'digit', 'letter', 'end')

    def parse(self, rule=None, start=0):
        rule = rule or self.starting_rule
        self.pos = start or self.starting_pos
        self.apply_rule(rule)
        if self.err:
            return None, self._err_str()
        return self.val, None

    def apply_rule(self, rule):
        rule_fn = getattr(self, '_' + rule + '_', None)
        if not rule_fn:
            self.err = 'unknown rule "%s"' % rule
        rule_fn()

    def _err_str(self):
        lineno, colno, begpos = self._err_offsets()
        endpos = self.msg[begpos:].index('\n')
        err_line = self.msg[begpos:endpos]
        exps = sorted(self.errset)
        if len(exps) > 2:
          expstr = "either %s, or '%s'" % (
            ', '.join("'%s'" % exp for exp in exps[:-1]), exps[-1])
        elif len(exps) == 2:
          expstr = "either '%s' or '%s'" % (exps[0], exps[1])
        else:
          expstr = "a '%s'" % exps[0]
        prefix = '%s:%d' % (self.fname, lineno)
        return "%s Expecting %s at column %d" % (prefix, expstr, colno)

    def _err_offsets(self):
        lineno = 1
        colno = 1
        i = 0
        begpos = 0
        while i < self.errpos:
            if self.msg[i] == '\n':
                lineno += 1
                colno = 1
                begpos = i
            else:
                colno += 1
            i += 1
        return lineno, colno, begpos

    def _escape(self, expr):
        return expr.replace('\r', '\\r').replace('\n', '\\n').replace(
            '\t', '\\t')

    def _expect(self, expr):
        p = self.pos
        l = len(expr)
        if (p + l <= self.end) and self.msg[p:p + l] == expr:
            self.pos += l
            self.val = expr
            self.err = False
        else:
            self.val = None
            self.err = True
            if self.pos >= self.errpos:
                if self.pos > self.errpos:
                    self.errset = set()
                self.errset.add(self._escape(expr))
                self.errpos = self.pos
        return

    def _atoi(self, s):
        return int(s)

    def _join(self, s, vs):
        return s.join(vs)

    def _anything_(self):
        if self.pos < self.end:
            self.val = self.msg[self.pos]
            self.err = None
            self.pos += 1
        else:
            self.val = None
            self.err = "anything"

    def _end_(self):
        self._anything_()
        if self.err:
            self.val = None
            self.err = None
        else:
            self.val = None
            self.err = "the end"
        return

    def _letter_(self):
        if self.pos < self.end and self.msg[self.pos].isalpha():
            self.val = self.msg[self.pos]
            self.err = None
            self.pos += 1
        else:
            self.val = None
            self.err = "a letter"
        return

    def _digit_(self):
        if self.pos < self.end and self.msg[self.pos].isdigit():
            self.val = self.msg[self.pos]
            self.err = None
            self.pos += 1
        else:
            self.val = None
            self.err = "a digit"
        return

    def _grammar_(self):
        """ gclient_file|deps_file """
        p = self.pos
        def choice_0():
            self._gclient_file_()
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._deps_file_()
        choice_1()

    def _gclient_file_(self):
        """ ws (gclient_stmt:s ws -> s)+:ss end -> ss """
        self._ws_()
        if self.err:
            return
        vs = []
        def group():
            self._gclient_stmt_()
            if not self.err:
                v_s = self.val
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self.val = v_s
            self.err = None
        group()
        if self.err:
            return
        vs.append(self.val)
        while not self.err:
            def group():
                self._gclient_stmt_()
                if not self.err:
                    v_s = self.val
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self.val = v_s
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_ss = self.val
        if self.err:
            return
        self._end_()
        if self.err:
            return
        self.val = v_ss
        self.err = None

    def _deps_file_(self):
        """ ws (deps_stmt:s ws -> s)+:ss end -> ss """
        self._ws_()
        if self.err:
            return
        vs = []
        def group():
            self._deps_stmt_()
            if not self.err:
                v_s = self.val
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self.val = v_s
            self.err = None
        group()
        if self.err:
            return
        vs.append(self.val)
        while not self.err:
            def group():
                self._deps_stmt_()
                if not self.err:
                    v_s = self.val
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self.val = v_s
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_ss = self.val
        if self.err:
            return
        self._end_()
        if self.err:
            return
        self.val = v_ss
        self.err = None

    def _ws_(self):
        """ (' '|'\t'|comment|eol)* """
        vs = []
        while not self.err:
            def group():
                p = self.pos
                def choice_0():
                    self._expect(' ')
                choice_0()
                if not self.err:
                    return

                self.err = False
                self.pos = p
                def choice_1():
                    self._expect('\t')
                choice_1()
                if not self.err:
                    return

                self.err = False
                self.pos = p
                def choice_2():
                    self._comment_()
                choice_2()
                if not self.err:
                    return

                self.err = False
                self.pos = p
                def choice_3():
                    self._eol_()
                choice_3()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None

    def _sp_(self):
        """ (' '|'\t')* """
        vs = []
        while not self.err:
            def group():
                p = self.pos
                def choice_0():
                    self._expect(' ')
                choice_0()
                if not self.err:
                    return

                self.err = False
                self.pos = p
                def choice_1():
                    self._expect('\t')
                choice_1()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None

    def _comment_(self):
        """ '#' (~(eol|end) anything)* (eol|end) """
        self._expect('#')
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                p = self.pos
                def group():
                    p = self.pos
                    def choice_0():
                        self._eol_()
                    choice_0()
                    if not self.err:
                        return

                    self.err = False
                    self.pos = p
                    def choice_1():
                        self._end_()
                    choice_1()
                group()
                self.pos = p
                if not self.err:
                     self.err = "not"
                     self.val = None
                     return
                self.err = None
                if self.err:
                    return
                self._anything_()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if self.err:
            return
        def group():
            p = self.pos
            def choice_0():
                self._eol_()
            choice_0()
            if not self.err:
                return

            self.err = False
            self.pos = p
            def choice_1():
                self._end_()
            choice_1()
        group()

    def _eol_(self):
        """ '\r'|'\n'|'\r\n' """
        p = self.pos
        def choice_0():
            self._expect('\r')
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._expect('\n')
        choice_1()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_2():
            self._expect('\r\n')
        choice_2()

    def _gclient_stmt_(self):
        """ solution|target_os """
        p = self.pos
        def choice_0():
            self._solution_()
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._target_os_()
        choice_1()

    def _deps_stmt_(self):
        """ vars|allowed_hosts|deps|deps_os|hooks|recursion|recursedeps|include_rules|skip_child_includes|specific_include_rules|target_os|use_relative_paths """
        p = self.pos
        def choice_0():
            self._vars_()
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._allowed_hosts_()
        choice_1()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_2():
            self._deps_()
        choice_2()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_3():
            self._deps_os_()
        choice_3()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_4():
            self._hooks_()
        choice_4()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_5():
            self._recursion_()
        choice_5()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_6():
            self._recursedeps_()
        choice_6()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_7():
            self._include_rules_()
        choice_7()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_8():
            self._skip_child_includes_()
        choice_8()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_9():
            self._specific_include_rules_()
        choice_9()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_10():
            self._target_os_()
        choice_10()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_11():
            self._use_relative_paths_()
        choice_11()

    def _solution_(self):
        """ 'solutions':k sp '=' sp object_list:v -> [k, v] """
        self._expect('solutions')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _object_list_(self):
        """ '[' ws (object:o ws ',' ws -> o)*:hd object?:tl ws ']' -> ['object_list', hd + tl] """
        self._expect('[')
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._object_()
                if not self.err:
                    v_o = self.val
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self._expect(',')
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self.val = v_o
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_hd = self.val
        if self.err:
            return
        self._object_()
        if self.err:
            self.val = []
            self.err = None
        else:
            self.val = [self.val]
        if not self.err:
            v_tl = self.val
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._expect(']')
        if self.err:
            return
        self.val = ['object_list', v_hd + v_tl]
        self.err = None

    def _object_(self):
        """ '{' (ws pair:kv ',' -> kv)*:hd (pair)?:tl ws '}' -> ['object', hd + tl] """
        self._expect('{')
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._ws_()
                if self.err:
                    return
                self._pair_()
                if not self.err:
                    v_kv = self.val
                if self.err:
                    return
                self._expect(',')
                if self.err:
                    return
                self.val = v_kv
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_hd = self.val
        if self.err:
            return
        def group():
            self._pair_()
        group()
        if self.err:
            self.val = []
            self.err = None
        else:
            self.val = [self.val]
        if not self.err:
            v_tl = self.val
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._expect('}')
        if self.err:
            return
        self.val = ['object', v_hd + v_tl]
        self.err = None

    def _pair_(self):
        """ str_expr:k ws ':' ws value:v -> [k, v] """
        self._str_expr_()
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._expect(':')
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._value_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _value_(self):
        """ str_expr|bool|object|str_list|'None' -> ['null', null] """
        p = self.pos
        def choice_0():
            self._str_expr_()
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._bool_()
        choice_1()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_2():
            self._object_()
        choice_2()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_3():
            self._str_list_()
        choice_3()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_4():
            self._expect('None')
            if self.err:
                return
            self.val = ['null', None]
            self.err = None
        choice_4()

    def _str_expr_(self):
        """ str_or_var:e1 (ws '+' ws str_expr:e2 -> e2)*:tl -> ['str_expr', [e1] + tl]|'(' ws str_expr:e ws ')' -> e """
        p = self.pos
        def choice_0():
            self._str_or_var_()
            if not self.err:
                v_e1 = self.val
            if self.err:
                return
            vs = []
            while not self.err:
                def group():
                    self._ws_()
                    if self.err:
                        return
                    self._expect('+')
                    if self.err:
                        return
                    self._ws_()
                    if self.err:
                        return
                    self._str_expr_()
                    if not self.err:
                        v_e2 = self.val
                    if self.err:
                        return
                    self.val = v_e2
                    self.err = None
                group()
                if not self.err:
                    vs.append(self.val)
            self.val = vs
            self.err = None
            if not self.err:
                v_tl = self.val
            if self.err:
                return
            self.val = ['str_expr', [v_e1] + v_tl]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._expect('(')
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._str_expr_()
            if not self.err:
                v_e = self.val
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._expect(')')
            if self.err:
                return
            self.val = v_e
            self.err = None
        choice_1()

    def _str_or_var_(self):
        """ str:s -> ['str', s]|'Var(' str:s ')' -> ['var', s] """
        p = self.pos
        def choice_0():
            self._str_()
            if not self.err:
                v_s = self.val
            if self.err:
                return
            self.val = ['str', v_s]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._expect('Var(')
            if self.err:
                return
            self._str_()
            if not self.err:
                v_s = self.val
            if self.err:
                return
            self._expect(')')
            if self.err:
                return
            self.val = ['var', v_s]
            self.err = None
        choice_1()

    def _str_(self):
        """ sq_str|dq_str """
        p = self.pos
        def choice_0():
            self._sq_str_()
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._dq_str_()
        choice_1()

    def _sq_str_(self):
        """ '\'' (~('\''|eol) anything)*:cs '\'' -> join('', cs) """
        self._expect('\'')
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                p = self.pos
                def group():
                    p = self.pos
                    def choice_0():
                        self._expect('\'')
                    choice_0()
                    if not self.err:
                        return

                    self.err = False
                    self.pos = p
                    def choice_1():
                        self._eol_()
                    choice_1()
                group()
                self.pos = p
                if not self.err:
                     self.err = "not"
                     self.val = None
                     return
                self.err = None
                if self.err:
                    return
                self._anything_()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_cs = self.val
        if self.err:
            return
        self._expect('\'')
        if self.err:
            return
        self.val = self._join('', v_cs)
        self.err = None

    def _dq_str_(self):
        """ '"' (~('"'|eol) anything)*:cs '"' -> join('', cs) """
        self._expect('"')
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                p = self.pos
                def group():
                    p = self.pos
                    def choice_0():
                        self._expect('"')
                    choice_0()
                    if not self.err:
                        return

                    self.err = False
                    self.pos = p
                    def choice_1():
                        self._eol_()
                    choice_1()
                group()
                self.pos = p
                if not self.err:
                     self.err = "not"
                     self.val = None
                     return
                self.err = None
                if self.err:
                    return
                self._anything_()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_cs = self.val
        if self.err:
            return
        self._expect('"')
        if self.err:
            return
        self.val = self._join('', v_cs)
        self.err = None

    def _bool_(self):
        """ 'True' -> ['bool', true]|'False' -> ['bool', false] """
        p = self.pos
        def choice_0():
            self._expect('True')
            if self.err:
                return
            self.val = ['bool', True]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._expect('False')
            if self.err:
                return
            self.val = ['bool', False]
            self.err = None
        choice_1()

    def _target_os_(self):
        """ 'target_os':k sp '=' sp str_list:v -> [k, v] """
        self._expect('target_os')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._str_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _str_list_(self):
        """ '[' ws (str_expr:s ws ',' ws -> s)*:hd str_expr?:tl ws ']' -> ['str_list', hd + tl] """
        self._expect('[')
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._str_expr_()
                if not self.err:
                    v_s = self.val
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self._expect(',')
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self.val = v_s
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_hd = self.val
        if self.err:
            return
        self._str_expr_()
        if self.err:
            self.val = []
            self.err = None
        else:
            self.val = [self.val]
        if not self.err:
            v_tl = self.val
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._expect(']')
        if self.err:
            return
        self.val = ['str_list', v_hd + v_tl]
        self.err = None

    def _vars_(self):
        """ 'vars':k sp '=' sp object:v -> [k, v] """
        self._expect('vars')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _recursion_(self):
        """ 'recursion':k sp '=' sp digit+:ds -> [k, ['num', atoi(ds)]] """
        self._expect('recursion')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        vs = []
        self._digit_()
        if self.err:
            return
        vs.append(self.val)
        while not self.err:
            self._digit_()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_ds = self.val
        if self.err:
            return
        self.val = [v_k, ['num', self._atoi(v_ds)]]
        self.err = None

    def _recursedeps_(self):
        """ 'recursedeps':k sp '=' sp rec_list:v -> [k, v] """
        self._expect('recursedeps')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._rec_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _rec_list_(self):
        """ '[' ws (rec:el ws ',' ws -> el)*:hd rec?:tl ws ']' -> ['rec_list', hd + tl] """
        self._expect('[')
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._rec_()
                if not self.err:
                    v_el = self.val
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self._expect(',')
                if self.err:
                    return
                self._ws_()
                if self.err:
                    return
                self.val = v_el
                self.err = None
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_hd = self.val
        if self.err:
            return
        self._rec_()
        if self.err:
            self.val = []
            self.err = None
        else:
            self.val = [self.val]
        if not self.err:
            v_tl = self.val
        if self.err:
            return
        self._ws_()
        if self.err:
            return
        self._expect(']')
        if self.err:
            return
        self.val = ['rec_list', v_hd + v_tl]
        self.err = None

    def _rec_(self):
        """ '(' ws str:k ws ',' ws str:v ws ')' -> [k, v]|str:k -> [k, 'DEPS'] """
        p = self.pos
        def choice_0():
            self._expect('(')
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._str_()
            if not self.err:
                v_k = self.val
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._expect(',')
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._str_()
            if not self.err:
                v_v = self.val
            if self.err:
                return
            self._ws_()
            if self.err:
                return
            self._expect(')')
            if self.err:
                return
            self.val = [v_k, v_v]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._str_()
            if not self.err:
                v_k = self.val
            if self.err:
                return
            self.val = [v_k, 'DEPS']
            self.err = None
        choice_1()

    def _allowed_hosts_(self):
        """ 'allowed_hosts':k sp '=' sp str_list:v -> [k, v] """
        self._expect('allowed_hosts')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._str_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _deps_(self):
        """ 'deps':k sp '=' sp object:v -> [k, v] """
        self._expect('deps')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _deps_os_(self):
        """ 'deps_os':k sp '=' sp object:v -> [k, v] """
        self._expect('deps_os')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _hooks_(self):
        """ 'hooks':k sp '=' sp object_list:v -> [k, v] """
        self._expect('hooks')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _include_rules_(self):
        """ 'include_rules':k sp '=' sp str_list:v -> [k, v] """
        self._expect('include_rules')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._str_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _skip_child_includes_(self):
        """ 'skip_child_includes':k sp '=' sp str_list:v -> [k, v] """
        self._expect('skip_child_includes')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._str_list_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _specific_include_rules_(self):
        """ 'specific_include_rules':k sp '=' sp object:v -> [k, v] """
        self._expect('specific_include_rules')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._object_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _use_relative_paths_(self):
        """ 'use_relative_paths':k sp '=' sp bool:v -> [k, v] """
        self._expect('use_relative_paths')
        if not self.err:
            v_k = self.val
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._expect('=')
        if self.err:
            return
        self._sp_()
        if self.err:
            return
        self._bool_()
        if not self.err:
            v_v = self.val
        if self.err:
            return
        self.val = [v_k, v_v]
        self.err = None

    def _conditional_(self):
        """ or_expr """
        self._or_expr_()

    def _or_expr_(self):
        """ and_expr:l ('||' or_expr)*:r -> ['||', l, r] """
        self._and_expr_()
        if not self.err:
            v_l = self.val
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._expect('||')
                if self.err:
                    return
                self._or_expr_()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_r = self.val
        if self.err:
            return
        self.val = ['||', v_l, v_r]
        self.err = None

    def _and_expr_(self):
        """ not_expr:l ('&&' and_expr)*:r -> ['&&', l, r] """
        self._not_expr_()
        if not self.err:
            v_l = self.val
        if self.err:
            return
        vs = []
        while not self.err:
            def group():
                self._expect('&&')
                if self.err:
                    return
                self._and_expr_()
            group()
            if not self.err:
                vs.append(self.val)
        self.val = vs
        self.err = None
        if not self.err:
            v_r = self.val
        if self.err:
            return
        self.val = ['&&', v_l, v_r]
        self.err = None

    def _not_expr_(self):
        """ '!' bool_expr:e -> ['!', e]|bool_expr """
        p = self.pos
        def choice_0():
            self._expect('!')
            if self.err:
                return
            self._bool_expr_()
            if not self.err:
                v_e = self.val
            if self.err:
                return
            self.val = ['!', v_e]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._bool_expr_()
        choice_1()

    def _bool_expr_(self):
        """ prim_expr:l sp '==' sp prim_expr:r -> ['==', l, r]|prim_expr:l sp '!=' sp prim_expr:r -> ['!=', l, r]|prim_expr:l sp 'in' sp 'target_os' -> ['in', l, 'target_os'] """
        p = self.pos
        def choice_0():
            self._prim_expr_()
            if not self.err:
                v_l = self.val
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._expect('==')
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._prim_expr_()
            if not self.err:
                v_r = self.val
            if self.err:
                return
            self.val = ['==', v_l, v_r]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._prim_expr_()
            if not self.err:
                v_l = self.val
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._expect('!=')
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._prim_expr_()
            if not self.err:
                v_r = self.val
            if self.err:
                return
            self.val = ['!=', v_l, v_r]
            self.err = None
        choice_1()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_2():
            self._prim_expr_()
            if not self.err:
                v_l = self.val
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._expect('in')
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._expect('target_os')
            if self.err:
                return
            self.val = ['in', v_l, 'target_os']
            self.err = None
        choice_2()

    def _prim_expr_(self):
        """ name:e -> ['var', e]|dq_str:e -> ['str', e]|'(' sp conditional:e sp ')' -> e """
        p = self.pos
        def choice_0():
            self._name_()
            if not self.err:
                v_e = self.val
            if self.err:
                return
            self.val = ['var', v_e]
            self.err = None
        choice_0()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_1():
            self._dq_str_()
            if not self.err:
                v_e = self.val
            if self.err:
                return
            self.val = ['str', v_e]
            self.err = None
        choice_1()
        if not self.err:
            return

        self.err = False
        self.pos = p
        def choice_2():
            self._expect('(')
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._conditional_()
            if not self.err:
                v_e = self.val
            if self.err:
                return
            self._sp_()
            if self.err:
                return
            self._expect(')')
            if self.err:
                return
            self.val = v_e
            self.err = None
        choice_2()
