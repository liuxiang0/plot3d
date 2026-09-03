#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mathparse.py — 数学表达式解析层（第二阶段）

功能:
  1. LaTeX 兼容: \\frac{}{} \\sqrt{} \\sqrt[n]{} ^{} \\sin \\pi \\cdot \\left\\right … → 普通表达式
  2. 安全求值: AST 白名单（数字 / +-*/** / 白名单函数），builtins 全部禁用
  3. 自动分类: 显式 y=f(x) / 隐式 f(x,y)=g(x,y) / 曲面 z=f(x,y) / 参数式 x(t),y(t),z(t)
  4. 定义域后缀: ; x=-3..3, y=-2..2, t=0..2pi
约定: ln=自然对数, lg=常用对数, log(x)=ln, log(a,x)=以a为底; 不支持科学计数法(用 10^k)
"""
import ast
import math
import re


class ParseError(Exception):
    """表达式解析/编译错误"""


FUNCS = {
    'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
    'arcsin': math.asin, 'arccos': math.acos, 'arctan': math.atan,
    'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
    'exp': math.exp, 'ln': math.log, 'lg': math.log10,
    'log': math.log, 'sqrt': math.sqrt, 'abs': abs,
    'floor': math.floor, 'ceil': math.ceil,
    'sgn': lambda x: (x > 0) - (x < 0),
    'atan2': math.atan2, 'pow': pow, 'mod': lambda a, b: a % b,
    'min': min, 'max': max,
}
CONSTS = {'pi': math.pi, 'e': math.e, 'tau': math.tau}
SAFE_GLOBALS = {'__builtins__': {}}
SAFE_GLOBALS.update(FUNCS)
SAFE_GLOBALS.update(CONSTS)
_MULTI_ARG = {'log', 'atan2', 'pow', 'mod'}
_BAD_NODES = (ast.Attribute, ast.Subscript, ast.List, ast.Tuple, ast.Set,
              ast.Dict, ast.Lambda, ast.IfExp, ast.Compare, ast.BoolOp,
              ast.JoinedStr, ast.FormattedValue, ast.comprehension,
              ast.ListComp, ast.GeneratorExp, ast.Starred)
_TEX_FUNCS = (('\\arcsin', 'asin'), ('\\arccos', 'acos'), ('\\arctan', 'atan'),
              ('\\sinh', 'sinh'), ('\\cosh', 'cosh'), ('\\tanh', 'tanh'),
              ('\\sin', 'sin'), ('\\cos', 'cos'), ('\\tan', 'tan'),
              ('\\ln', 'ln'), ('\\lg', 'lg'), ('\\log', 'log'), ('\\exp', 'exp'))
_PI = '3.14159265358979323846'


# ====================== LaTeX → 普通表达式 ======================

def _match(s: str, i: int) -> int:
    """s[i] 为 '{'，返回配对 '}' 的下标"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return j
    raise ParseError('花括号不配对')


def latex_to_plain(s: str) -> str:
    s = re.sub(r'^\$+|\$+$', '', s.strip())          # 去 $...$ / $$...$$
    s = s.replace('\\left', '').replace('\\right', '')
    s = (s.replace('\\leq', '<=').replace('\\le', '<=').replace('\\geq', '>=')
          .replace('\\ge', '>=').replace('\\lt', '<').replace('\\gt', '>'))
    s = re.sub(r'\\[,;! ]', '', s)                   # 间距命令
    s = s.replace('\\dfrac', '\\frac').replace('\\tfrac', '\\frac')
    for k, v in _TEX_FUNCS:
        s = s.replace(k, v)
    s = (s.replace('\\pi', 'pi').replace('\\cdot', '*')
          .replace('\\times', '*').replace('\\div', '/'))
    while '\\sqrt' in s:                             # \sqrt[n]{...} / \sqrt{...}
        i = s.index('\\sqrt')
        j = i + 5
        m = re.match(r'\s*\[([^\]]*)\]', s[j:])
        idx, j2 = (m.group(1), j + m.end()) if m else (None, j)
        while j2 < len(s) and s[j2] == ' ':
            j2 += 1
        if j2 >= len(s) or s[j2] != '{':
            raise ParseError('\\sqrt 需要花括号: \\sqrt{...}')
        k = _match(s, j2)
        body = s[j2 + 1:k]
        rep = f'sqrt({body})' if idx is None else f'(({body})**(1/({idx})))'
        s = s[:i] + rep + s[k + 1:]
    while '\\frac' in s:                             # \frac{a}{b} → ((a)/(b))
        i = s.index('\\frac')
        j = i + 5
        while j < len(s) and s[j] == ' ':
            j += 1
        if j >= len(s) or s[j] != '{':
            raise ParseError('\\frac 缺少分子花括号')
        k1 = _match(s, j)
        j2 = k1 + 1
        while j2 < len(s) and s[j2] == ' ':
            j2 += 1
        if j2 >= len(s) or s[j2] != '{':
            raise ParseError('\\frac 缺少分母花括号')
        k2 = _match(s, j2)
        a, b = s[j + 1:k1], s[j2 + 1:k2]
        s = s[:i] + f'(({a})/({b}))' + s[k2 + 1:]
    if '\\' in s:
        m = re.search(r'\\[A-Za-z]+', s)
        raise ParseError(f'不支持的 LaTeX 命令: {m.group(0) if m else s}')
    return s


# ====================== 规范化（两种输入共用） ======================

def insert_implicit_mul(s: str) -> str:
    """隐式乘法: 2x→2*x · )(→)*( · x(→x*(（函数名豁免）"""
    out, i, n = [], 0, len(s)
    prev = None
    last_name = ''
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        j = i + 1
        if ch.isdigit() or (ch == '.' and i + 1 < n and s[i + 1].isdigit()):
            while j < n and (s[j].isdigit() or s[j] == '.'):
                j += 1
            tok, cur, last_name = s[i:j], 'num', ''
        elif ch.isalpha() or ch == '_':
            while j < n and (s[j].isalnum() or s[j] == '_'):
                j += 1
            tok, cur, last_name = s[i:j], 'name', s[i:j]
        elif ch == '(':
            if prev in ('num', 'rparen') or (prev == 'name' and last_name not in FUNCS):
                out.append('*')
            tok, cur, last_name = '(', 'lparen', ''
        elif ch == ')':
            tok, cur, last_name = ')', 'rparen', ''
        else:
            tok, cur, last_name = ch, 'other', ''
        if cur in ('num', 'name') and prev in ('num', 'name', 'rparen'):
            out.append('*')
        out.append(tok)
        prev = cur
        i = j
    return ''.join(out)


def normalize_expr(s: str) -> str:
    s = (s.replace('−', '-').replace('×', '*').replace('÷', '/')
          .replace('·', '*').replace('π', 'pi'))
    s = re.sub(r'_\{[^{}]*\}', '', s)                # 下标视为标注, 删除
    s = re.sub(r'_[A-Za-z0-9]', '', s)
    prev = None
    while prev != s:                                 # ^{...} → **(...)（支持嵌套）
        prev = s
        s = re.sub(r'\^\{([^{}]*)\}', r'**(\1)', s)
    s = re.sub(r'\^([+-]?[A-Za-z0-9.]+)', r'**(\1)', s)
    s = s.replace('{', '(').replace('}', ')')        # 剩余花括号 → 圆括号
    s = re.sub(r'\b(' + '|'.join(sorted(FUNCS, key=len, reverse=True)) +
               r')\s+([A-Za-z]\w*|\d+(?:\.\d+)?)', r'\1(\2)', s)   # sin x → sin(x)
    return insert_implicit_mul(s)


# ====================== AST 白名单编译 ======================

def compile_expr(plain: str):
    """校验 + 编译; 返回 (code, 自由变量集合)"""
    try:
        tree = ast.parse(plain, mode='eval')
    except (SyntaxError, ValueError) as e:
        raise ParseError(f'语法错误: {e}')
    free = set()
    for node in ast.walk(tree):
        if isinstance(node, _BAD_NODES):
            raise ParseError(f'不支持的语法: {type(node).__name__}')
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ParseError(f'非法常量: {node.value!r}')
        elif isinstance(node, ast.Name):
            if node.id not in FUNCS and node.id not in CONSTS:
                free.add(node.id)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
                raise ParseError('仅允许调用白名单数学函数')
            if node.keywords:
                raise ParseError('不支持关键字参数')
            nm, na = node.func.id, len(node.args)
            if nm in ('min', 'max'):
                if na < 1:
                    raise ParseError(f'{nm} 至少需要 1 个参数')
            elif nm in _MULTI_ARG:
                if not 1 <= na <= 2:
                    raise ParseError(f'{nm} 接受 1-2 个参数')
            elif na != 1:
                raise ParseError(f'{nm} 只接受 1 个参数')
    return compile(tree, '<expr>', 'eval'), free


def make_func(code, varnames, params=None):
    """编译产物 → 数值函数; 定义域外/异常统一返回 nan（供采样器跳过）"""
    p = params or {}
    def f(*vals):
        env = dict(zip(varnames, vals))
        env.update(p)
        try:
            v = eval(code, SAFE_GLOBALS, env)
        except Exception:
            return math.nan
        return float(v) if isinstance(v, (int, float)) else math.nan
    return f


def _auto_params(free, vars_, params):
    """未知自由名 → 自动参数（默认 1.0, 可用 ; 名=值 指定）; 返回自动新增名单"""
    extra = sorted(free - vars_ - set(params))
    for nm in extra:
        params[nm] = 1.0
    return extra


# ====================== 定义域与顶层切分 ======================

def _parse_bound(tok: str) -> float:
    """解析定义域边界: 支持 pi/π/PI、四则运算与括号, 如 -pi, 2pi, pi/2, 3*pi/4"""
    t = tok.replace('π', 'pi').replace(' ', '').lower()
    t = re.sub(r'(\d)pi', r'\1*pi', t)
    t = t.replace('pi', '(' + _PI + ')')
    if not t or not re.fullmatch(r'[-+0-9.*/()eE]+', t):
        raise ParseError(f'无法解析定义域边界: {tok}')
    try:
        v = float(eval(t, {'__builtins__': {}}, {}))
    except Exception:
        raise ParseError(f'无法解析定义域边界: {tok}')
    if not math.isfinite(v):
        raise ParseError(f'定义域边界须为有限数: {tok}')
    return v


def _split_top(s: str, sep: str = ','):
    """按顶层分隔符切分（括号内的分隔符忽略）"""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append(''.join(cur))
    return [p.strip() for p in parts if p.strip()]


COMP_RE = re.compile(r'<=|>=|<|>')


def _split_comparison(s):
    """拆分单个不等式 → (code左, code右, 算子, 自由变量集)"""
    m = COMP_RE.search(s)
    if not m:
        raise ParseError('不是不等式')
    lhs, rhs = s[:m.start()].strip(), s[m.end():].strip()
    if not lhs or not rhs:
        raise ParseError('不等式左右两侧不能为空')
    if COMP_RE.search(lhs) or COMP_RE.search(rhs):
        raise ParseError('仅支持单个不等式（链式如 0<x<1 请用逗号拆为不等式组 x>0, x<1）')
    code_l, free_l = compile_expr(lhs)
    code_r, free_r = compile_expr(rhs)
    return code_l, code_r, m.group(), free_l | free_r


# ====================== 总入口: 自动识别与分类 ======================

def parse_input(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        raise ParseError('表达式为空')
    is_latex = ('\\' in raw) or ('$' in raw)
    s = latex_to_plain(raw) if is_latex else raw
    for a, b in (('（', '('), ('）', ')'), ('，', ','), ('；', ';'),
                 ('≤', '<='), ('≥', '>='), ('²', '^2'), ('³', '^3')):
        s = s.replace(a, b)
    domains, params = {}, {}
    if ';' in s:                                     # 定义域后缀 + 参数赋值
        main, _, dom = s.partition(';')
        dom = dom.replace(' ', '')
        pat = re.compile(r'(x|y|z|t|u|v)\s*(?:∈|in|=)\s*\[?\s*([^\s,]+?)\s*(?:\.\.|,)\s*([^\s,\]]+)\s*\]?')
        for m in pat.finditer(dom):
            lo, hi = _parse_bound(m.group(2)), _parse_bound(m.group(3))
            if lo >= hi:
                raise ParseError(f'定义域下界须小于上界: {m.group(1)}')
            domains[m.group(1)] = (lo, hi)
        dom2 = pat.sub(lambda m: ' ' * len(m.group(0)), dom)
        for m in re.finditer(r'([A-Za-z]\w*)\s*=\s*([^\s,]+)', dom2):
            nm, val = m.group(1), m.group(2)
            if nm in ('x', 'y', 'z', 't', 'u', 'v'):
                raise ParseError(f'{nm} 是坐标变量, 定义域请写 {nm}=a..b')
            if '..' in val:
                raise ParseError(f'参数 {nm} 为单值赋值如 {nm}=2（区间仅坐标变量可用）')
            params[nm] = _parse_bound(val)
        s = main
    s = normalize_expr(s.strip())
    xr = domains.get('x', (-5.0, 5.0))
    yr = domains.get('y', (-5.0, 5.0))
    zr = domains.get('z', (-5.0, 5.0))
    base = {'latex': is_latex, 'plain': s, 'params': params}

    # 1) 多表达式（顶层逗号）: 不等式组 或 参数式
    parts = _split_top(s)
    if len(parts) > 1:
        has_comp = [bool(COMP_RE.search(p)) for p in parts]
        if all(has_comp):                            # 不等式组（取交集, 仅 2D）
            infos, allfree = [], set()
            for p in parts:
                code_l, code_r, op, free = _split_comparison(p)
                infos.append((code_l, code_r, op))
                allfree |= free
            if 'z' in allfree:
                raise ParseError('不等式组暂仅支持 x,y 两变量（三维请写单个不等式）')
            auto = _auto_params(allfree, {'x', 'y'}, params)
            conds = []
            for code_l, code_r, op in infos:
                fl = make_func(code_l, ('x', 'y'), params)
                fr = make_func(code_r, ('x', 'y'), params)
                conds.append((lambda x, y, _fl=fl, _fr=fr: _fl(x, y) - _fr(x, y),
                              op in ('>', '>=')))
            base.update(kind='inequality2d', conds=conds, auto_params=auto,
                        x_range=xr, y_range=yr)
            return base
        if any(has_comp):
            raise ParseError('不等式不能与参数式/方程混用')
        comps_info = {}                              # lhs -> (code, free)
        for p in parts:
            if '=' not in p:
                raise ParseError('多表达式须为参数式 x=f(t),y=g(t),z=h(t) 或 r(u,v) 形式')
            lhs, rhs = [t.strip() for t in p.split('=', 1)]
            if lhs in ('t', 'u', 'v') and '..' in rhs:   # 内嵌定义域 t/u/v=0..2pi
                lo, _, hi = rhs.partition('..')
                if not lo.strip() or not hi.strip():
                    raise ParseError(f'{lhs} 定义域格式错误: {p}')
                blo, bhi = _parse_bound(lo), _parse_bound(hi)
                if blo >= bhi:
                    raise ParseError(f'{lhs} 定义域下界须小于上界')
                domains[lhs] = (blo, bhi)
                continue
            if lhs not in ('x', 'y', 'z'):
                raise ParseError(f'参数式左侧须为 x/y/z，得到 "{lhs}"')
            code, free = compile_expr(rhs)
            comps_info[lhs] = (code, free)
        if not comps_info:
            raise ParseError('未找到参数分量 x/y/z=...')
        allfree = set().union(*(f for _, f in comps_info.values()))
        if 't' in allfree and (allfree & {'u', 'v'}):
            raise ParseError('同一式不能混用 t 与 u,v')
        if 't' in allfree:                           # 参数曲线
            auto = _auto_params(allfree, {'t'}, params)
            comps = {lhs: make_func(code, ('t',), params)
                     for lhs, (code, _) in comps_info.items()}
            base.update(kind='parametric', comps=comps, auto_params=auto,
                        t_range=domains.get('t', (0.0, 2 * math.pi)))
            return base
        if allfree & {'u', 'v'}:                     # 参数曲面 r(u,v)
            auto = _auto_params(allfree, {'u', 'v'}, params)
            comps = {lhs: make_func(code, ('u', 'v'), params)
                     for lhs, (code, _) in comps_info.items()}
            base.update(kind='param_surface', comps=comps, auto_params=auto,
                        u_range=domains.get('u', (0.0, 2 * math.pi)),
                        v_range=domains.get('v', (0.0, 2 * math.pi)))
            return base
        raise ParseError('参数分量须含 t 或 u,v（如仅 z=0 为退化式）')

    # 2) 单个不等式: F(x,y)<0 区域 / F(x,y,z)<0 不等式体
    if COMP_RE.search(s):
        code_l, code_r, op, free = _split_comparison(s)
        pos = op in ('>', '>=')
        if 'z' in free:
            auto = _auto_params(free, {'x', 'y', 'z'}, params)
            fl = make_func(code_l, ('x', 'y', 'z'), params)
            fr = make_func(code_r, ('x', 'y', 'z'), params)
            F = lambda x, y, z, _fl=fl, _fr=fr: _fl(x, y, z) - _fr(x, y, z)
            base.update(kind='inequality3d', conds=[(F, pos)], auto_params=auto,
                        x_range=xr, y_range=yr, z_range=zr)
            return base
        if not (free & {'x', 'y'}):
            raise ParseError('不等式需包含变量 x 或 y')
        auto = _auto_params(free, {'x', 'y'}, params)
        fl = make_func(code_l, ('x', 'y'), params)
        fr = make_func(code_r, ('x', 'y'), params)
        F = lambda x, y, _fl=fl, _fr=fr: _fl(x, y) - _fr(x, y)
        base.update(kind='inequality2d', conds=[(F, pos)], auto_params=auto,
                    x_range=xr, y_range=yr)
        return base

    # 3) 单方程
    if '=' in s:
        lhs, rhs = [t.strip() for t in s.split('=', 1)]
    else:
        lhs, rhs = None, s

    if lhs in ('x', 'y', 'z'):                       # 显式
        code, free = compile_expr(rhs)
        if lhs in free:
            raise ParseError(f'右侧不能含左侧变量 {lhs} 本身')
        if lhs == 'y':
            auto = _auto_params(free, {'x'}, params)
            base.update(kind='explicit2d', var='x', f=make_func(code, ('x',), params),
                        auto_params=auto, x_range=xr)
            return base
        if lhs == 'x':
            auto = _auto_params(free, {'y'}, params)
            base.update(kind='explicit2d', var='y', f=make_func(code, ('y',), params),
                        auto_params=auto, y_range=yr)
            return base
        auto = _auto_params(free, {'x', 'y'}, params)
        base.update(kind='surface', f=make_func(code, ('x', 'y'), params),
                    auto_params=auto, x_range=xr, y_range=yr)
        return base

    # 4) 隐式: F(x,y)=0 曲线 / F(x,y,z)=0 曲面（裸表达式: 仅含 x 视为 y=f(x)）
    code_r, free_r = compile_expr(rhs)
    if lhs is None:
        if free_r - set(params) <= {'x'}:
            auto = _auto_params(free_r, {'x'}, params)
            base.update(kind='explicit2d', var='x', f=make_func(code_r, ('x',), params),
                        auto_params=auto, x_range=xr)
            return base
        code_l, free_l = None, set()
    else:
        code_l, free_l = compile_expr(lhs)
    free = free_l | free_r
    if 'z' in free:                                   # 隐式曲面
        auto = _auto_params(free, {'x', 'y', 'z'}, params)
        fl3 = (make_func(code_l, ('x', 'y', 'z'), params) if code_l is not None
               else (lambda x, y, z: 0.0))
        fr3 = make_func(code_r, ('x', 'y', 'z'), params)
        base.update(kind='implicit3d', auto_params=auto,
                    F=lambda x, y, z, _fl=fl3, _fr=fr3: _fl(x, y, z) - _fr(x, y, z),
                    x_range=xr, y_range=yr, z_range=zr)
        return base
    if not (free & {'x', 'y'}):
        raise ParseError('表达式需包含变量 x 或 y')
    auto = _auto_params(free, {'x', 'y'}, params)
    fl = (make_func(code_l, ('x', 'y'), params) if code_l is not None
          else (lambda x, y: 0.0))
    fr = make_func(code_r, ('x', 'y'), params)
    base.update(kind='implicit2d', auto_params=auto,
                F=lambda x, y, _fl=fl, _fr=fr: _fl(x, y) - _fr(x, y),
                x_range=xr, y_range=yr)
    return base
