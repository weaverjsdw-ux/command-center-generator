#!/usr/bin/env python3
"""verify.py - mechanical acceptance checks for Command Center dashboards.

Implements the checkable subset of GENERATOR_PACKAGE.md section 7, section 8
and section 6.6. Standard library only. No third-party imports. See --help.
"""
import argparse
import re
import sys
from urllib.parse import urlparse

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"

CHECKS = []


class Result:
    def __init__(self, num, name, rule, status, details=None):
        self.num = num
        self.name = name
        self.rule = rule
        self.status = status
        self.details = details or []


def check(num, name, rule):
    def deco(fn):
        CHECKS.append((num, name, rule, fn))
        return fn
    return deco


# --------------------------------------------------------------------------
# document preprocessing
# --------------------------------------------------------------------------

# One tag's attribute region, matched quote-aware: whole quoted runs are
# consumed atomically, so a literal '>' inside a quoted attribute value
# (valid HTML5 - inside an attribute value only '<', '&' and the
# enclosing quote need escaping) cannot end the tag early and hide an
# attribute that comes after it.
_ATTR_RUN = r"""(?:"[^"]*"|'[^']*'|[^>"'])*"""

# Leftmost-first document scan: an HTML comment opener, or one whole
# opening tag. Ordinary tags are matched (and then simply skipped over),
# so a "<!--" sitting inside a quoted attribute value is consumed as part
# of that tag and never mistaken for a comment opener.
_MASK_SCAN_RX = re.compile(r"<!--|<([a-zA-Z][\w-]*)\b" + _ATTR_RUN + ">")

_MASKED_ELEMENTS = ("script", "style")


def _blank_run(text):
    """Replace every character with a space except line terminators, so
    the result has the same length and the same newline offsets as the
    input. Offsets taken in the result stay valid against the original."""
    return re.sub(r"[^\n\r]", " ", text)


def _mask_non_markup(html):
    """Return a copy of html with its non-markup regions blanked out: the
    *bodies* of <script> and <style> elements, and HTML comments in full.

    Why this exists: a tag-shaped run of text inside a JS template
    literal, a JS string, a CSS rule or a commented-out example is not a
    live resource reference. A regex scan over raw document text cannot
    tell the two apart, and piling more special cases into the tag
    pattern does not fix that - it is a region problem, not a pattern
    problem. Masking first makes the distinction structural.

    The opening <script ...> / <style ...> tags themselves stay visible:
    checks legitimately inspect their attributes (src=, type=). Only what
    sits between that tag's '>' and its closing tag is blanked.

    The copy is offset-preserving - same length, same newline positions -
    so a match offset in it still yields the correct line number when
    counted against the original document.

    Returns (masked_html, regions), where regions is the ordered list of
    (start, end, kind) spans that were blanked and kind is one of
    "script", "style" or "comment". Callers use the spans to say *which*
    kind of region a reference was found in, so a masked-region hit can
    be reported for human adjudication instead of dropped silently.
    """
    pieces = []
    regions = []
    kept = 0    # next index of html not yet emitted
    scan = 0    # next index to search from
    while True:
        m = _MASK_SCAN_RX.search(html, scan)
        if m is None:
            break
        if m.group(0) == "<!--":
            end = html.find("-->", m.end())
            # An unterminated comment really does swallow the rest of the
            # document in a browser, so masking to EOF matches what the
            # page actually renders.
            stop = len(html) if end == -1 else end + 3
            blank_from, blank_to, scan = m.start(), stop, stop
            kind = "comment"
        elif m.group(1).lower() in _MASKED_ELEMENTS:
            kind = m.group(1).lower()
            close_rx = re.compile(r"</%s\s*>" % re.escape(m.group(1)), re.I)
            close = close_rx.search(html, m.end())
            if close is None:
                blank_from, blank_to, scan = m.end(), len(html), len(html)
            else:
                blank_from = m.end()
                blank_to = close.start()
                scan = close.end()
        else:
            scan = m.end()      # ordinary tag: skipped over, nothing masked
            continue
        pieces.append(html[kept:blank_from])
        pieces.append(_blank_run(html[blank_from:blank_to]))
        if blank_to > blank_from:
            regions.append((blank_from, blank_to, kind))
        kept = blank_to
    pieces.append(html[kept:])
    return "".join(pieces), regions


# A raw (unmasked) scan for one whole <script>...</script> pair. Shared by
# Ctx.js_state_at below and by check 10's _script_bodies: deliberately the
# SAME regex both places use, so "which body is offset X in" always means
# the same thing regardless of which caller is asking. Non-greedy, so it
# pairs an opening tag with the FIRST </script> found after it - this
# matches real HTML5 raw-text parsing (a browser also stops a <script>
# element at the first literal "</script" it sees, JS syntax or not), so
# a <script>...</script>-shaped string sitting inside another live
# script's own text truncates the enclosing body early. That is a real,
# accepted limitation of tag-based body extraction, not something the
# character-level JS scanner below is meant to fix.
_SCRIPT_TAG_RX = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)

# JS lexical states a character inside a <script> body can be in. Only
# "code" is live, executing JavaScript; every other state is text that
# merely LOOKS like code (a comment, a string's contents, a template
# literal's contents, a regex literal).
_JS_CODE = "code"
_JS_SQSTRING = "sqstring"
_JS_DQSTRING = "dqstring"
_JS_TEMPLATE = "template"
_JS_LINECOMMENT = "linecomment"
_JS_BLOCKCOMMENT = "blockcomment"
_JS_REGEX = "regex"

_JS_STATE_LABEL = {
    _JS_SQSTRING: "a JS string",
    _JS_DQSTRING: "a JS string",
    _JS_TEMPLATE: "a JS template literal",
    _JS_LINECOMMENT: "a JS comment",
    _JS_BLOCKCOMMENT: "a JS comment",
    _JS_REGEX: "a JS regex literal",
}


# Sentinel for last_code_char: "a value was JUST produced here" - as
# opposed to last_code_char holding an actual source character. Used for
# a closed string, template literal or regex literal, for an object
# literal's or interpolation's '}', for a call or grouping ')', and for a
# postfix '++'/'--'. A '/' right after any produced value is division
# (`"a" / 2`, `` `a` / 2 ``, `/x/ / 2`, `f() / 2`, `{a:1} / 2`,
# `i++ / 2`), exactly like a '/' right after an identifier or number.
# Never equal to any real character _scan_js_states can see, so it can't
# collide with one.
_JS_AFTER_VALUE = "\x00"

# Sentinel for last_code_char: "a statement-structure delimiter just
# closed here, and the next token is in fresh expression position" - a
# BLOCK statement's '}' (`if (x) { ... }`, `for (...) { ... }`,
# `function f(){ ... }`) or a CONTROL clause's ')' (`if (x)`,
# `while (x)`). Both are the opposite of _JS_AFTER_VALUE: no value was
# produced, so a '/' immediately after opens a REGEX LITERAL, not a
# division. Treating every '}' (and every ')') as a closed value was a
# real false-negative source - `/['"]/.test(z)` after a block close was
# read as division, leaving the quote inside it to open a runaway string
# that swallowed live code below it. Which kind of '{' or '(' is being
# closed is tracked structurally, on the frame's own brace and paren
# stacks - see _js_brace_opens_object and _scan_js_states.
_JS_AFTER_BLOCK = "\x01"


# Keywords after which a '/' is grammatically a regex literal, not
# division, even though the keyword itself ends in an identifier
# character (e.g. `return /x/.test(s)`). Checked against the WHOLE last
# completed word, never a substring - `myreturn / 2` must stay division
# - and disqualified if that word was preceded by '.', since `obj.in`
# is a property access, not the `in` operator.
_JS_REGEX_KEYWORDS = frozenset([
    "return", "typeof", "instanceof", "in", "of", "new", "delete",
    "void", "throw", "case", "do", "else", "yield", "await", "default",
])

# Keywords whose '(' opens a CONTROL clause rather than a call or a
# grouping. The difference is what a '/' immediately after the matching
# ')' means: after `if (x)` / `while (x)` / `for (...)` a regex literal
# may start (`if (a) /x/.test(b);`), but after a call or a parenthesised
# value (`f() / 2`, `(a + b) / 2`) the ')' closed a VALUE and the '/' is
# division. Resolved structurally on the frame's own paren stack, the
# same way '{' is - see _scan_js_states.
_JS_CONTROL_PAREN_KEYWORDS = frozenset([
    "if", "for", "while", "switch", "catch", "with",
])

# Characters after which a '{' opens an OBJECT LITERAL (an expression
# position) rather than a block statement. Deliberately excludes '>', so
# an arrow function body (`x => { ... }`) is read as the block it is, and
# excludes ';', ')', '}' and '{', after all of which a '{' begins a
# statement. ':' is NOT here - it is handled separately, because it means
# opposite things in the two places it appears (see
# _js_brace_opens_object). '/' is here only because the set is written as
# "operators"; `a / {` is not valid JS, so that entry is inert.
_JS_OBJECT_PREFIX = "=(,[?+-*/%&|^!~"

# Keywords after which a '{' opens an object literal (`return { ... }`).
# Note this is NOT _JS_REGEX_KEYWORDS: `do { ... }` and `else { ... }`
# take a BLOCK, even though both permit a regex literal after them.
_JS_OBJECT_KEYWORDS = frozenset([
    "return", "typeof", "instanceof", "in", "of", "new", "delete",
    "void", "throw", "case", "yield", "await",
])


def _js_brace_opens_object(prev_code_char, last_word, last_word_after_dot,
                           open_braces):
    """True if a '{' here opens an object literal (a value, so its '}'
    is followed by division), False if it opens a block statement (so its
    '}' is followed by a fresh statement, where a '/' opens a regex).

    Same shape of decision as _js_regex_may_start, and the same
    whole-word, dot-aware keyword handling, so `return {` is a value but
    `myreturn {`, `obj.return {`, `do {` and `else {` are blocks.

    ':' needs the enclosing context, which is why open_braces (the
    frame's own brace-kind stack) is passed in. A '{' after ':' is an
    object literal only when the innermost enclosing '{' is itself an
    object literal, i.e. the ':' separates a property key from its value
    (`var o = { meta: { a: 1 } }`). In statement position the same ':'
    belongs to a label or a switch case, and the '{' after it is a BLOCK
    (`lbl: { f(); }`, `switch (v) { case 1: { h(); } }`). Reading those
    as object literals made their '}' claim a value was produced, which
    made the next '/' read as division.

    This function is advisory. Nothing it returns can change a check's
    verdict - see c10's docstring - so a wrong call here costs at most an
    inaccurate note on a cited line."""
    if prev_code_char == "":
        return False
    if prev_code_char in (_JS_AFTER_VALUE, _JS_AFTER_BLOCK):
        return False
    if prev_code_char == ":":
        return bool(open_braces) and open_braces[-1]
    if prev_code_char in _JS_OBJECT_PREFIX:
        return True
    if prev_code_char.isalnum() or prev_code_char in "_$":
        return not last_word_after_dot and last_word in _JS_OBJECT_KEYWORDS
    return False


def _js_regex_span_end(text, start):
    """If the '/' at offset `start` could be a regex literal that CLOSES
    on this same physical line, return the offset just past its closing
    '/'. Return -1 if it cannot.

    This is a hard language rule, not a heuristic: a JS regex literal may
    not contain a raw newline, so a '/' with no unescaped,
    outside-a-character-class closing '/' before the end of the line is
    simply not a regex literal. Refusing to open one (rather than
    scanning an "unterminated regex" to end of line, as this scanner used
    to) means a misjudged '/' costs nothing at all instead of swallowing
    the rest of the line as non-code."""
    n = len(text)
    j = start + 1
    in_class = False
    while j < n:
        c = text[j]
        if c == "\n":
            return -1
        if c == "\\":
            if j + 1 >= n or text[j + 1] == "\n":
                return -1
            j += 2
            continue
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            return j + 1
        j += 1
    return -1


def _js_contain_span(states, text, start, end):
    """Relabel text[start:end] as live code - used by the containment
    rules below to abandon a lexical state the scanner should never have
    been in - and return the last non-whitespace character in that span
    ("" if there is none) so the caller can resynchronise last_code_char.

    Relabelling toward CODE, never away from it, is deliberate: a span
    wrongly called code costs a human one glance at a cited line, while a
    span wrongly called string/regex/comment hides a real violation and
    exits 0."""
    resync = ""
    for k in range(start, end):
        states[k] = _JS_CODE
        if not text[k].isspace():
            resync = text[k]
    return resync


def _js_regex_may_start(prev_code_char, last_word, last_word_after_dot):
    """Best-effort disambiguation of a bare '/' between "start of a regex
    literal" and "division operator".

    Primary signal is the last code-producing character seen while in
    "code" state: a '/' right after a VALUE is division, a '/' anywhere
    else can open a regex literal. Every way JS can end a value is
    accounted for, so this is a grammar rule rather than a sample of
    cases: an identifier or number (the alphanumeric branch below), a
    closing ']', a trailing '.' ending a numeric literal (`1. / 2`), a
    call or grouping ')' or an object literal's '}' (both arrive here as
    _JS_AFTER_VALUE), a closed string/template/regex literal (also
    _JS_AFTER_VALUE), and a postfix '++'/'--' (likewise). A '.' is never
    followed by a regex in valid JS - `obj. /re/` is a syntax error - so
    treating it as a value-ender is safe in both directions.

    Neither '}' nor ')' appears in the "always division" set below,
    because neither is always a value: `if (x) { f(); }` and `if (x)`
    are both followed by fresh-expression position, where
    `/['"]/.test(z)` is plain, valid JS. Calling those division left the
    quote inside the regex to open a real string that ran away and
    swallowed live code after it. _scan_js_states resolves which kind of
    '}' and ')' it saw from its own brace and paren stacks and passes the
    matching sentinel here, so this function never has to guess.

    An identifier-ending character (last_code_char alphanumeric/_/$) is
    ambiguous on its own - most identifiers ending a value mean division
    (`count / 2`), but several JS keywords also end in an identifier
    character and grammatically require what follows to be able to start
    a regex (`return /x/.test(s)`, `typeof x === "object"` followed
    later by another regex-eligible position, `case /x/.test(s):`).
    last_word (the whole last completed identifier-like token, not just
    its final character) resolves this: only a WHOLE-WORD match against
    _JS_REGEX_KEYWORDS - and only when that word was not itself a
    property access via a preceding '.' - flips an otherwise-division
    call to regex-may-open.

    This is the standard lightweight disambiguation JS syntax
    highlighters use; it is not a full parser (it does not track
    statement position or handle every ASI edge case), but it does now
    cover the keyword-lookback gap that generic identifier-ending logic
    alone cannot.

    Getting this wrong in EITHER direction is a real correctness bug, not
    a safe default: misreading a live '/' as a regex-open swallows real
    code as non-code state, which is exactly the false negative (check
    10 sees a live MAP assignment demoted to "not live" and WARNs or
    PASSes instead of FAILing) - not some inert, harmless direction.
    Misreading a regex-open as division instead leaves the regex's own
    quote/bracket characters to be interpreted as ordinary code (e.g. a
    stray quote inside the regex opening a REAL, unterminated string that
    then runs away and swallows unrelated downstream code - this is
    exactly how the keyword-lookback gap was reachable before this
    check existed: `return /['"]/.test(x)` misread as division left `['"]`
    to be read as code, and the `'` opened a real string with nothing to
    close it). There is no safe direction to round errors toward here;
    the fix is to get more cases right."""
    if prev_code_char == "":
        return True
    if prev_code_char == _JS_AFTER_BLOCK:
        return True
    if prev_code_char == _JS_AFTER_VALUE:
        return False
    if prev_code_char in "].":
        return False
    if prev_code_char.isalnum() or prev_code_char in "_$":
        return not last_word_after_dot and last_word in _JS_REGEX_KEYWORDS
    return True


def _scan_js_states(text):
    """Walk JS source text ONCE, left to right, tracking real lexical
    state - live code, a '...' string, a "..." string, a `...` template
    literal (with ${...} interpolation switching back to live code,
    properly nested), a // line comment, a /* */ block comment, or a
    best-effort regex literal - honouring backslash escapes. Returns a
    list of per-character state labels, the same length as text, so the
    state at a given offset within this body is states[offset - start].

    This replaces an earlier same-line, quote-parity heuristic that was
    provably unsound: counting quote characters before a match on its own
    line cannot tell "inside a string" from "an odd number of unrelated
    quotes happen to precede it" (an apostrophe in ordinary prose inside
    an unrelated, already-closed string). This scanner is genuinely
    stateful across the WHOLE body, so a properly closed string earlier
    in the text can never bleed into a later, unrelated line - the
    apostrophe in `someFunc("don't")` stays inside that double-quoted
    string and never affects anything that follows it.

    THIS SCANNER IS ADVISORY. Its output annotates findings; it may not
    suppress or downgrade one. Callers must not use it to drop a match
    from a count - see c10's docstring for the five review rounds that
    established this rule the expensive way. No hand-written lexer inside
    a single-file checker resolves JS regex-vs-division for every input,
    so any design that lets this function veto a finding converts a lexer
    bug into a false PASS on a real violation. Given it cannot veto, its
    remaining job is to be RIGHT AS OFTEN AS POSSIBLE so its notes are
    worth reading - which is what everything below is for.

    Includes keyword lookback for the regex/division rule (`return
    /x/.test(s)` vs `count / 2`) and a structural block-vs-object-literal
    distinction for '}' - see _js_regex_may_start, _js_brace_opens_object
    and last_word below.

    Because no context-free scanner resolves regex-vs-division for every
    input, note quality here does NOT rest on that disambiguation being
    complete. It rests on four CONTAINMENT rules, each a hard JavaScript
    language rule rather than a heuristic, that bound how far a miscall
    can spread:

      1. A '...' or "..." string may not contain a raw newline. Reaching
         one means this scanner mis-entered that state, so the span is
         abandoned and RELABELLED AS LIVE CODE at the newline (see
         _js_contain_span). A backslash immediately before the newline is
         a legal line continuation and is honoured, so real multi-line
         strings still work.
      2. A regex literal may not contain a raw newline either, so a '/'
         with no closing '/' on its own line never opens one at all (see
         _js_regex_span_end) - it is just an ordinary code character.
      3. Inside a span where a '/' was judged DIVISION but could
         grammatically have been a regex literal, a '`' or a '/*' is not
         allowed to open a template literal or block comment. Those are
         the only two states that legitimately cross a line boundary,
         i.e. the only two a misjudged division could use to escape rules
         1 and 2. Strings and line comments are deliberately NOT
         suppressed there: rule 1 already bounds them, and suppressing
         them would wrongly relabel real string and comment text as live.
      4. Any string, template literal, block comment or ${} interpolation
         still open at the end of the body is a syntax error in real JS,
         so it too is relabelled as live code rather than allowed to
         swallow the tail of the script.

    Together these mostly keep the scanner resynchronised at line
    boundaries, so a regex/division miscall usually costs at most part of
    one line and what it costs is relabelled toward "live" rather than
    away from it.

    These rules are NOT airtight, and no claim here should be read as
    saying they are. Rule 3 only arms when a same-line closing '/' exists
    and only guards '`' and '/*', so a quote inside a misjudged span can
    still pair with another quote MID-LINE - which rule 1, firing only at
    a newline, never sees. Rule 3's span also stops one character short of
    the candidate closing '/', so a '/*' formed at that boundary is
    unguarded. Both were demonstrated against real, executing JavaScript
    after four rounds of fixes here. They remain because the fix for them
    is not a fifth round of lexing: it is that no caller may act on this
    scanner's opinion as a verdict.

    Automatic-semicolon-insertion also remains out of scope.

    last_code_char and last_word are updated on every code character AND
    at every point a string, template literal, regex literal or brace
    closes (via the _JS_AFTER_VALUE / _JS_AFTER_BLOCK sentinels), so a
    '/' immediately following a closed literal is read as division, not
    judged against whatever token preceded that literal's OPENING
    quote."""
    n = len(text)
    states = [_JS_CODE] * n
    # Every frame has the same six fields, so every push and pop site
    # reads the same shape:
    #   [0] state
    #   [1] brace kinds - for a "code" frame, one entry per currently open
    #       '{' (True = object literal, False = block statement), so a '}'
    #       knows which kind it closes; None for a non-code frame, which
    #       never tracks braces. A code frame entered via ${ inside a
    #       template literal also uses "no braces left open" to recognise
    #       the '}' that ends the interpolation.
    #   [2][3][4] saved last_code_char / last_word / last_word_after_dot -
    #       only used by a ${ } interpolation frame: an interpolation is a
    #       fresh expression context, so its OWN last_code_char/last_word
    #       start clean (regex may open; no preceding word) rather than
    #       inheriting whatever code token/word preceded the ${ OR leaking
    #       in from an earlier, already-closed sibling interpolation in
    #       the same template - see the push/pop sites below.
    #   [5] the offset this frame's state started at, used by the
    #       containment rules to relabel an abandoned span as live code.
    #   [6] paren kinds - for a "code" frame, one entry per currently open
    #       '(' (True = a control clause's paren, as in `if (x)`, False =
    #       a call or grouping paren, as in `f(x)` or `(a + b)`), so a ')'
    #       knows whether it closed a value; None for a non-code frame.
    stack = [[_JS_CODE, [], "", "", False, 0, []]]
    last_code_char = ""
    # Exclusive end offset of the most recent span in which a '/' was
    # judged DIVISION even though a same-line closing '/' exists, i.e. a
    # span that could grammatically have been a regex literal instead.
    # Inside such a span a '`' or a '/*' may not open a template literal
    # or block comment (containment rule 3 in the docstring): those two
    # states are the only ones that legitimately cross a line boundary, so
    # they are the only way a misjudged division could escape the
    # line-level containment the other rules give. Positional and
    # monotonic, so it needs no reset and cannot go stale.
    suspect_until = -1
    # last_word: the last COMPLETE identifier-like token seen in code
    # state (letters/digits/_/$), used only for the regex/division
    # keyword check above. cur_word accumulates the token currently being
    # read; it is "finalized" into last_word the moment a non-identifier
    # character ends it (including a '/' itself: `return/2` has no space
    # but "return" must still finalize before that '/' is judged).
    # *_after_dot records whether the token was a property access
    # (`obj.in`) rather than a real keyword - checked at the moment the
    # token STARTS, against whatever character came immediately before.
    last_word = ""
    last_word_after_dot = False
    cur_word = ""
    cur_word_after_dot = False
    i = 0
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        top = stack[-1]
        state = top[0]
        if state == _JS_CODE:
            # Word tracking for the keyword-lookback regex/division rule
            # (see _js_regex_may_start): extend the in-progress token on
            # an identifier character, or finalize it the moment a non-
            # identifier character ends it - INCLUDING a '/' itself
            # (`return/2` has no space, but "return" must still finalize
            # before that '/' is judged). Runs before the branch dispatch
            # below so last_word is current by the time a '/' on THIS
            # character needs it.
            if ch.isalnum() or ch in "_$":
                if not cur_word:
                    cur_word_after_dot = (last_code_char == ".")
                cur_word += ch
            elif cur_word:
                last_word = cur_word
                last_word_after_dot = cur_word_after_dot
                cur_word = ""
            if ch == "/" and nxt == "/":
                stack.append([_JS_LINECOMMENT, None, "", "", False, i, None])
                states[i] = _JS_LINECOMMENT
                i += 1
                continue
            if ch == "/" and nxt == "*" and i >= suspect_until:
                stack.append([_JS_BLOCKCOMMENT, None, "", "", False, i, None])
                states[i] = _JS_BLOCKCOMMENT
                i += 1
                continue
            if ch == "'":
                stack.append([_JS_SQSTRING, None, "", "", False, i, None])
                states[i] = _JS_SQSTRING
                i += 1
                continue
            if ch == '"':
                stack.append([_JS_DQSTRING, None, "", "", False, i, None])
                states[i] = _JS_DQSTRING
                i += 1
                continue
            if ch == "`" and i >= suspect_until:
                stack.append([_JS_TEMPLATE, None, "", "", False, i, None])
                states[i] = _JS_TEMPLATE
                i += 1
                continue
            if ch == "/" and i >= suspect_until:
                # Containment rule 2: a regex literal cannot contain a raw
                # newline, so unless a closing '/' exists on THIS line
                # there is no regex literal here at all and the '/' falls
                # through as an ordinary code character. The scanner used
                # to run an unterminated regex to end of line, which
                # relabelled the rest of a live line as non-code for free.
                span_end = _js_regex_span_end(text, i)
                if span_end >= 0:
                    if _js_regex_may_start(last_code_char, last_word,
                                           last_word_after_dot):
                        for k in range(i, span_end):
                            states[k] = _JS_REGEX
                        i = span_end
                        last_code_char = _JS_AFTER_VALUE
                        last_word = ""
                        last_word_after_dot = False
                        continue
                    # Division was the call - but a regex literal was
                    # grammatically possible here, so this span is exactly
                    # where a wrong call does its damage. Containment rule
                    # 3: no '`' and no '/*' may open a state inside it.
                    # The span stops one character SHORT of the candidate
                    # closing '/', so that '/' can still start a comment:
                    # `a / b; /* note */` is ordinary code whose comment
                    # must not be swallowed, and if the earlier '/' really
                    # was division then a '/*' at the span's far end
                    # really is a comment.
                    suspect_until = span_end - 1
            states[i] = _JS_CODE
            if ch == "(":
                top[6].append(not last_word_after_dot
                              and last_word in _JS_CONTROL_PAREN_KEYWORDS)
                last_word = ""
                last_word_after_dot = False
            elif ch == ")":
                # closes a '(' this frame opened: a call or grouping paren
                # produced a value (so a following '/' is division), a
                # control clause's paren did not (so a following '/' opens
                # a regex literal - `if (a) /['"]/.test(b);`). An
                # unbalanced ')' is read as a call close, its overwhelming
                # meaning in real JS.
                last_code_char = _JS_AFTER_BLOCK if (
                    top[6] and top[6].pop()) else _JS_AFTER_VALUE
                last_word = ""
                last_word_after_dot = False
                i += 1
                continue
            elif ch == "{":
                top[1].append(_js_brace_opens_object(
                    last_code_char, last_word, last_word_after_dot, top[1]))
                last_word = ""
                last_word_after_dot = False
            elif ch == "}":
                if top[1]:
                    # closes a '{' this frame opened: an object literal
                    # produces a value (so a following '/' is division), a
                    # block statement does not (so a following '/' opens a
                    # regex literal).
                    last_code_char = _JS_AFTER_VALUE if top[1].pop() \
                        else _JS_AFTER_BLOCK
                    last_word = ""
                    last_word_after_dot = False
                    i += 1
                    continue
                if len(stack) > 1:
                    # no '{' open in this frame, so this '}' ends the
                    # ${ ... } interpolation that pushed it. Restore the
                    # OUTER expression's last_code_char/last_word - not
                    # whatever this interpolation's own code last looked
                    # at. A second, later ${...} in the same template must
                    # start fresh (see the push site), never see the
                    # previous interpolation's leftover values - that
                    # stale-value leak, for last_code_char alone, is
                    # exactly what let a regex-shaped token like /['"]/
                    # inside a SECOND interpolation be misread as
                    # division, opening a real string that ran away and
                    # swallowed live code after it.
                    last_code_char = top[2]
                    last_word = top[3]
                    last_word_after_dot = top[4]
                    stack.pop()
                    i += 1
                    continue
                # An unbalanced '}' at the top level of the body: real JS
                # would not have one, so the brace stack has most likely
                # lost a '{' to a span the containment rules relabelled
                # (they do not re-tokenise what they hand back). Read it
                # as a block close, the far commoner meaning of a bare '}'
                # in statement text, and keep scanning. Note the
                # len(stack) > 1 guard above: the base frame is never
                # popped, so this cannot underflow the stack.
                last_code_char = _JS_AFTER_BLOCK
                last_word = ""
                last_word_after_dot = False
                i += 1
                continue
            if not ch.isspace():
                # A postfix (or prefix) '++'/'--' produces a value, so a
                # '/' after it is division - `i++ / 2` is not a regex
                # open, even though a bare '+' or '-' before a '/' is.
                # Recorded as the value sentinel rather than as '+'/'-'
                # so _js_regex_may_start needs no second-to-last
                # character.
                last_code_char = _JS_AFTER_VALUE \
                    if (ch in "+-" and last_code_char == ch) else ch
            i += 1
            continue
        if state == _JS_LINECOMMENT:
            states[i] = state
            if ch == "\n":
                stack.pop()
            i += 1
            continue
        if state == _JS_BLOCKCOMMENT:
            states[i] = state
            if ch == "*" and nxt == "/":
                states[i + 1] = state
                i += 2
                stack.pop()
                continue
            i += 1
            continue
        if state in (_JS_SQSTRING, _JS_DQSTRING):
            quote = "'" if state == _JS_SQSTRING else '"'
            if ch == "\\":
                # A backslash escapes the next character - and immediately
                # before a newline it is a LINE CONTINUATION, the one way
                # a '...' or "..." string may legally cross a line
                # boundary. Handled before the newline rule below so a
                # continued string keeps running, exactly as real JS does.
                states[i] = state
                if i + 1 < n:
                    states[i + 1] = state
                i += 2
                continue
            if ch == "\n":
                # Containment rule 1: JS forbids a raw newline inside a
                # '...' or "..." string, so this state cannot be real -
                # far more likely the scanner mis-entered it (a quote
                # inside a misjudged regex literal is how every known
                # instance of this bug started). Abandon it, relabel the
                # whole span as LIVE CODE, and resynchronise at the
                # newline. This is what stops a phantom string from
                # running to a distant quote and swallowing a genuine
                # second `var MAP =` on the way.
                last_code_char = _js_contain_span(states, text, top[5], i)
                states[i] = _JS_CODE
                last_word = ""
                last_word_after_dot = False
                cur_word = ""
                cur_word_after_dot = False
                stack.pop()
                i += 1
                continue
            states[i] = state
            if ch == quote:
                i += 1
                stack.pop()
                last_code_char = _JS_AFTER_VALUE
                last_word = ""
                last_word_after_dot = False
                continue
            i += 1
            continue
        if state == _JS_TEMPLATE:
            states[i] = state
            if ch == "\\":
                if i + 1 < n:
                    states[i + 1] = state
                i += 2
                continue
            if ch == "`":
                i += 1
                stack.pop()
                last_code_char = _JS_AFTER_VALUE
                continue
            if ch == "$" and nxt == "{":
                states[i] = state
                states[i + 1] = state
                i += 2
                # A ${...} interpolation is a fresh expression context:
                # save the outer last_code_char/last_word (restored when
                # this frame's matching '}' pops, above) and reset the
                # active values so a '/' as this interpolation's OWN
                # first token is judged on its own terms - never against
                # whatever code token/word happened to precede this ${,
                # and never against a stale value left over from an
                # earlier, already-closed sibling interpolation in the
                # same template (that stale-value bug is exactly what let
                # a regex-shaped token like /['"]/ inside a SECOND
                # interpolation be misread as division, opening a real
                # string that ran away and swallowed live code after it).
                stack.append([_JS_CODE, [], last_code_char,
                              last_word, last_word_after_dot, i, []])
                last_code_char = ""
                last_word = ""
                last_word_after_dot = False
                cur_word = ""
                cur_word_after_dot = False
                continue
            i += 1
            continue
    # Containment rule 4: a string, template literal, block comment or
    # ${ } interpolation still open at the end of the body is a syntax
    # error in real JS, so it is much more likely a state this scanner
    # mis-entered than genuinely unterminated source. Relabel every
    # still-open span as live code instead of letting it swallow the tail
    # of the script - this is the "runs away to EOF" half of the failure
    # class, closed structurally. Frames are popped from the top down and
    # each relabels through the end of the body, so an outer frame's
    # earlier start offset wins, which is what we want. A // line comment
    # running to EOF is legal JS and is deliberately left alone.
    while len(stack) > 1:
        frame = stack.pop()
        if frame[0] in (_JS_SQSTRING, _JS_DQSTRING, _JS_TEMPLATE,
                        _JS_BLOCKCOMMENT):
            _js_contain_span(states, text, frame[5], n)
    return states


class Ctx:
    def __init__(self, html, path, map_text=None, reference=False, expect=None):
        self.html = html
        self.path = path
        self.lines = html.splitlines()
        self.map_text = map_text
        self.reference = reference
        self.expect = expect
        self._masked = None
        self._regions = None
        self._js_states = None

    def masked_html(self):
        """self.html with non-markup regions blanked out (see
        _mask_non_markup). Computed once and cached: it is O(document) to
        build and more than one check scans it."""
        if self._masked is None:
            self._masked, self._regions = _mask_non_markup(self.html)
        return self._masked

    def region_kind_at(self, offset):
        """Which kind of non-markup region ("script", "style", "comment")
        contains this document offset, or None if the offset is in live
        markup."""
        self.masked_html()
        for start, end, kind in self._regions:
            if start <= offset < end:
                return kind
        return None

    def lineno_at(self, offset):
        """1-based physical line number of a document offset."""
        return self.html.count("\n", 0, offset) + 1

    def js_state_at(self, offset):
        """The real JS lexical state at a document offset that falls
        inside a <script>...</script> body - _JS_CODE (live, executing),
        _JS_SQSTRING/_JS_DQSTRING/_JS_TEMPLATE (a string's contents),
        _JS_LINECOMMENT/_JS_BLOCKCOMMENT (a comment's contents), or
        _JS_REGEX (a regex literal's contents). None if offset is not
        inside any <script> body found by a raw scan of self.html (see
        _SCRIPT_TAG_RX).

        ADVISORY ONLY. Use this to explain a finding, never to drop one.
        A caller that lets a non-_JS_CODE answer remove a match from a
        count converts any lexer bug into a false PASS on a real
        violation - which happened five times in five review rounds
        before c10 was rewritten to strip this function of that power.
        See c10 and _scan_js_states for the full reasoning.

        Backed by _scan_js_states, a real per-body character-level
        tokenizer - not a per-line heuristic - so a match's
        classification cannot be changed by unrelated text elsewhere on
        the same line the way counting quote characters could. Computed
        lazily and cached once per body: more than one check needs this
        (check 10's advisory notes here; Task 5's reference-word checks
        are expected to reuse it rather than re-deriving their own
        JS-awareness - on the same advisory-only terms)."""
        if self._js_states is None:
            self._js_states = {}
        for m in _SCRIPT_TAG_RX.finditer(self.html):
            start, end = m.start(1), m.end(1)
            if start <= offset < end:
                if start not in self._js_states:
                    self._js_states[start] = _scan_js_states(
                        self.html[start:end])
                return self._js_states[start][offset - start]
        return None

    def find(self, pattern, flags=0):
        rx = re.compile(pattern, flags)
        return [(i + 1, ln) for i, ln in enumerate(self.lines) if rx.search(ln)]

    def script_text(self):
        return "\n".join(re.findall(
            r"<script\b[^>]*>(.*?)</script\s*>", self.html, re.S | re.I))

    def style_text(self):
        return "\n".join(re.findall(
            r"<style\b[^>]*>(.*?)</style\s*>", self.html, re.S | re.I))

    def root_tokens(self):
        tokens = {}
        for body in re.findall(r":root\s*\{(.*?)\}", self.style_text(), re.S):
            for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", body):
                tokens[name] = value.strip()
        return tokens


def line_details(hits, limit=10):
    out = ["line %d: %s" % (n, ln.strip()[:120]) for n, ln in hits[:limit]]
    if len(hits) > limit:
        out.append("... and %d more" % (len(hits) - limit))
    return out


def fail_on_hits(num, name, rule, hits, status=FAIL):
    if hits:
        return Result(num, name, rule, status, line_details(hits))
    return Result(num, name, rule, PASS)


NOT_CHECKED = [
    ("whether the page renders at all (the blank-page bug)", "section 8.1"),
    ("root render fires after its dependencies", "section 8.1"),
    ("banner/panels non-removable and present on all tabs", "section 8.4"),
    ("every number traces to the map", "section 8.5"),
    ("parked assets actually render gray", "section 8.6(a)"),
    ("DAG hub / fan-out correctness", "section 8.9"),
    ('"no restated asset literals"', "section 8.2"),
    ("messy-input handling wired (truncation, dup-rank, orphan-row)", "section 8.8"),
]


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

# Matches one whole opening tag at a time, respecting quoted attribute
# values (see _ATTR_RUN for why naive "[^>]*" tag matching is wrong).
_TAG_RX = re.compile(r"<([a-zA-Z][\w-]*)\b" + _ATTR_RUN + ">")


def _tags_in(text):
    """Yield (start_offset, tag_name_lower, tag_text) for every opening
    tag in text. Matching runs over the whole text, not line-by-line: a
    tag whose closing '>' lands on a different physical line from its
    '<' is ordinary, valid HTML (attribute values wrap), and a per-line
    scan would never see it as one tag at all."""
    for m in _TAG_RX.finditer(text):
        yield m.start(), m.group(1).lower(), m.group(0)


def _all_tags(ctx):
    """Yield (lineno, tag_name_lower, tag_text) for every opening tag in
    the document's *live markup*.

    Matching runs over the masked document, so tag-shaped text inside a
    <script> body, a <style> body or an HTML comment is not mistaken for
    a live resource reference. Line numbers are still counted against
    ctx.html, which is exact because masking is offset-preserving."""
    for start, name, text in _tags_in(ctx.masked_html()):
        yield ctx.lineno_at(start), name, text


def _masked_region_tags(ctx):
    """Yield (start_offset, tag_name_lower, tag_text, region_kind) for
    tag-shaped text that exists ONLY in a non-markup region.

    These are not live markup and must not FAIL - but they are not
    nothing either. A dashboard that builds its DOM in template literals
    keeps most of its real markup here, so a genuine CDN reference can
    live in this set. Callers report these at WARN for human
    adjudication rather than dropping them.

    Offsets, not line numbers, are yielded: scanning raw text produces
    matches that can span many lines of JavaScript, so callers cite the
    line of the *attribute they matched* rather than the line the bogus
    match happened to start on."""
    live = set(start for start, _, _ in _tags_in(ctx.masked_html()))
    for start, name, text in _tags_in(ctx.html):
        if start in live:
            continue
        kind = ctx.region_kind_at(start)
        if kind is None:
            continue
        yield start, name, text, kind


_REGION_LABEL = {
    "script": "a <script> body",
    "style": "a <style> body",
    "comment": "an HTML comment",
}

_ADJUDICATE = ("may be constructed markup or documentation; "
               "needs human adjudication")


def _cap(items, limit=10):
    if len(items) <= limit:
        return items
    return items[:limit] + ["... and %d more" % (len(items) - limit)]


def _merge_hits(*hit_lists):
    """Merge several (lineno, text) hit lists into one, deduplicated by
    line number, so a violation two independent detection paths both
    caught is reported once, not twice."""
    merged = {}
    for hits in hit_lists:
        for lineno, text in hits:
            merged.setdefault(lineno, text)
    return sorted(merged.items())


def _flatten(text):
    return re.sub(r"\s+", " ", text).strip()


@check(1, 'no <script type="module">', "section 7/section 8.1")
def c01(ctx):
    name = 'no <script type="module">'
    rule = "section 7/section 8.1"
    type_module_rx = re.compile(r"""type\s*=\s*['"]module['"]""", re.I)
    tag_hits = [(lineno, _flatten(tag_text))
                for lineno, tag_name, tag_text in _all_tags(ctx)
                if tag_name == "script" and type_module_rx.search(tag_text)]
    # Union with a direct search over the RAW (unmasked) lines: for this
    # file://-breaker check the costs are asymmetric. A miss ships a
    # blank page; a false flag costs a human one glance at a cited line
    # to see it's inside a string literal. Deliberately over-report -
    # this is also what keeps document.write('<script ...>') caught now
    # that script bodies are masked out of the tag scan. Do not
    # generalise this union to checks whose false positives land on
    # ordinary content (see check 2).
    direct_hits = ctx.find(r"""<script[^>]*type\s*=\s*['"]module['"]""", re.I)
    hits = _merge_hits(tag_hits, direct_hits)
    return fail_on_hits(1, name, rule, hits)


def _script_body_lines(ctx):
    """Yield (lineno, text) for every physical line inside a <script>...
    </script> body, using real document line numbers. Scanning is scoped
    to script content only so ordinary page markup (e.g. an "Export Data"
    button label) can never be mistaken for an ES import/export statement.
    """
    for m in re.finditer(r"<script\b[^>]*>(.*?)</script\s*>", ctx.html,
                         re.S | re.I):
        start_line = ctx.html.count("\n", 0, m.start(1)) + 1
        for j, body_ln in enumerate(m.group(1).split("\n")):
            yield start_line + j, body_ln


@check(2, "no ES import/export statements", "section 7")
def c02(ctx):
    name = "no ES import/export statements"
    rule = "section 7"
    hits = []
    for lineno, ln in _script_body_lines(ctx):
        if re.search(r"^\s*(?:import|export)\s+", ln):
            hits.append((lineno, ln))
    return fail_on_hits(2, name, rule, hits)


@check(3, "no dynamic import()", "section 7")
def c03(ctx):
    name = "no dynamic import()"
    rule = "section 7"
    return fail_on_hits(3, name, rule, ctx.find(r"\bimport\s*\("))


@check(4, "no fetch() or XMLHttpRequest", "section 7")
def c04(ctx):
    name = "no fetch() or XMLHttpRequest"
    rule = "section 7"
    return fail_on_hits(
        4, name, rule, ctx.find(r"\bfetch\s*\(|\bXMLHttpRequest\b"))


@check(5, "await occurrences (top-level detection is heuristic)", "section 7")
def c05(ctx):
    name = "await occurrences (top-level detection is heuristic)"
    rule = "section 7"
    # WARN, never FAIL: reliably distinguishing top-level await from awaits
    # inside async functions needs brace-depth analysis that is not robust
    # against unusual or minified formatting. Report and let a human judge.
    return fail_on_hits(5, name, rule, ctx.find(r"\bawait\b"), status=WARN)


@check(6, "no <script src=> at all", "section 7 all executable code inlined")
def c06(ctx):
    name = "no <script src=> at all"
    rule = "section 7 all executable code inlined"
    src_rx = re.compile(r"\ssrc\s*=", re.I)
    tag_hits = [(lineno, _flatten(tag_text))
                for lineno, tag_name, tag_text in _all_tags(ctx)
                if tag_name == "script" and src_rx.search(tag_text)]
    # Union with a direct search over the RAW (unmasked) lines - same
    # asymmetric-cost reasoning as check 1 above. This is the path that
    # catches document.write('<script src=...>'), whose tag text lives
    # inside a JS string and so is masked out of the tag scan.
    direct_hits = ctx.find(r"<script[^>]*\ssrc\s*=", re.I)
    hits = _merge_hits(tag_hits, direct_hits)
    return fail_on_hits(6, name, rule, hits)


FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def _is_font_host(url):
    """True only if url's actual host is a known fonts CDN host - not
    merely a URL that contains the host name as a substring somewhere
    (e.g. in a query string), which would defeat the whole check."""
    host = (urlparse(url).hostname or "").lower()
    return host in FONT_HOSTS


_REF_ATTR_RX = re.compile(
    r"""(?:src|href)\s*=\s*['"](https?://[^'"]+)['"]""", re.I)


def _external_refs(ctx):
    """Return [(lineno, url, is_link_tag)] for every http(s) resource ref
    in LIVE markup. Tag matching is document-wide (via _all_tags), so a
    <link>/<script> tag whose attributes wrap onto a second line is still
    recognized as one tag, and per-tag rather than per-line, so an
    <a href> sharing text with a <link>/<script>/<img> can't hide or
    absorb the other's reference."""
    out = []
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        attr_m = _REF_ATTR_RX.search(tag_text)
        if attr_m:
            out.append((lineno, attr_m.group(1), tag_name == "link"))
    # The CSS url() scan stays on RAW lines on purpose. Its two live
    # homes are exactly the regions the mask blanks: a <style> body, and
    # a script assigning el.style.background = "url(...)". Masking here
    # would turn real violations into false passes.
    for i, ln in enumerate(ctx.lines):
        for m in re.finditer(r"url\(\s*['\"]?(https?://[^'\")]+)", ln, re.I):
            out.append((i + 1, m.group(1), False))
    return out


def _masked_region_external_refs(ctx):
    """Return [(lineno, url, region_kind)] for http(s) resource refs that
    exist only inside a script body, a style body or an HTML comment.

    Every match in the tag is reported, not just the first: a raw-text
    match can span several template-literal tags at once, and the point
    of this path is that nothing is dropped silently. The cited line is
    the line of the URL itself, so the citation always names a line that
    actually contains it."""
    out = []
    for start, tag_name, tag_text, kind in _masked_region_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        for m in _REF_ATTR_RX.finditer(tag_text):
            out.append((ctx.lineno_at(start + m.start(1)), m.group(1), kind))
    return out


def _fonts_links(ctx):
    return [(n, u, is_link) for n, u, is_link in _external_refs(ctx)
            if is_link and _is_font_host(u)]


@check(7, "at most one external ref, and it must be a fonts stylesheet",
       "section 7/section 6.6")
def c07(ctx):
    name = "at most one external ref, and it must be a fonts stylesheet"
    rule = "section 7/section 6.6"
    fonts = _fonts_links(ctx)
    problems = []
    reported = set()
    for n, url, _ in _external_refs(ctx):
        if not _is_font_host(url):
            problems.append("line %d: external resource %s" % (n, url[:100]))
            reported.add((n, url))
    if len(fonts) > 1:
        problems.append("%d fonts stylesheets; section 7 sanctions one" % len(fonts))
    # Refs found only in a script/style body or an HTML comment are not
    # live markup, so they cannot be a FAIL. They are not nothing either:
    # a dashboard that builds its DOM in template literals keeps most of
    # its real markup there, so a genuine CDN reference can hide in this
    # set alongside documentation. Report at WARN and let a human decide.
    # Fonts hosts are NOT exempted here: the live path already counts
    # sanctioned fonts links, and exempting them here would silently
    # swallow a second one injected at runtime.
    soft = []
    for n, url, kind in _masked_region_external_refs(ctx):
        if (n, url) in reported:
            continue        # same reference already reported as a FAIL
        reported.add((n, url))
        soft.append("line %d: external resource %s (inside %s - %s)"
                    % (n, url[:100], _REGION_LABEL[kind], _ADJUDICATE))
    soft = _cap(soft)
    if problems:
        return Result(7, name, rule, FAIL, problems + soft)
    if soft:
        return Result(7, name, rule, WARN, soft)
    return Result(7, name, rule, PASS)


_LOCAL_ATTR_RX = re.compile(r"""(?:src|href)\s*=\s*['"](?:\./|\.\./|/)[^'"]""")

# Same rule as _LOCAL_ATTR_RX but capturing the whole quoted value, so a
# masked-region WARN can cite the reference itself rather than a
# raw-text tag match that may span many lines of JavaScript.
_LOCAL_REF_RX = re.compile(
    r"""(?:src|href)\s*=\s*['"]((?:\./|\.\./|/)[^'"]*)['"]""")


def _local_ref_tags(ctx):
    """Yield (lineno, tag_text) for every non-anchor LIVE tag carrying a
    local src=/href=, document-wide (via _all_tags) so a tag whose
    attributes wrap onto a second line is still recognized as one tag,
    and per-tag so an <a href> sharing text with a real local
    <link>/<script>/<img> can't hide or falsely absorb it."""
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        if _LOCAL_ATTR_RX.search(tag_text):
            yield lineno, tag_text


def _masked_region_local_refs(ctx):
    """Return [(lineno, ref_value, region_kind)] for local src=/href=
    references that exist only inside a script body, a style body or an
    HTML comment. Cited at the line of the reference itself - see
    _masked_region_external_refs for why."""
    out = []
    for start, tag_name, tag_text, kind in _masked_region_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        for m in _LOCAL_REF_RX.finditer(tag_text):
            out.append((ctx.lineno_at(start + m.start(1)), m.group(1), kind))
    return out


@check(8, "no local file references", "section 7 zero external local files")
def c08(ctx):
    name = "no local file references"
    rule = "section 7 zero external local files"
    hits = {}
    for lineno, tag_text in _local_ref_tags(ctx):
        hits[lineno] = _flatten(tag_text)
    # RAW lines here, deliberately - see the note in _external_refs.
    for i, ln in enumerate(ctx.lines):
        if re.search(r"url\(\s*['\"]?(?!data:|https?:|#)[^)'\"]+\.[a-z0-9]{2,5}",
                     ln, re.I):
            hits.setdefault(i + 1, ln)
    problems = line_details(sorted(hits.items()))
    # Masked-region references: WARN, never FAIL - same reasoning as
    # check 7 above.
    soft = []
    seen = set()
    for lineno, ref, kind in _masked_region_local_refs(ctx):
        if lineno in hits or (lineno, ref) in seen:
            continue        # same reference already reported as a FAIL
        seen.add((lineno, ref))
        soft.append("line %d: local reference %s (inside %s - %s)"
                    % (lineno, ref[:100], _REGION_LABEL[kind], _ADJUDICATE))
    soft = _cap(soft)
    if problems:
        return Result(8, name, rule, FAIL, problems + soft)
    if soft:
        return Result(8, name, rule, WARN, soft)
    return Result(8, name, rule, PASS)


_IMG_SRC_RX = re.compile(r"""\ssrc\s*=\s*['"]([^'"]*)['"]""", re.I)


@check(9, "every <img src=> is a data: URI", "section 7")
def c09(ctx):
    name = "every <img src=> is a data: URI"
    rule = "section 7"
    # Region-graded exactly like checks 7 and 8: an <img> in live markup
    # is a violation; one that exists only inside a script body, a style
    # body or an HTML comment is constructed markup or documentation and
    # gets a WARN for human adjudication rather than a FAIL. Routing this
    # through _all_tags also gives check 9 the quote-aware, multi-line
    # tag matching the other tag-based checks already had - its old
    # per-line "<img[^>]*" scan could see neither.
    hits = []
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name != "img":
            continue
        m = _IMG_SRC_RX.search(tag_text)
        if m and not m.group(1).startswith("data:"):
            hits.append((lineno, _flatten(tag_text)))
    soft = []
    seen = set()
    for start, tag_name, tag_text, kind in _masked_region_tags(ctx):
        if tag_name != "img":
            continue
        for m in _IMG_SRC_RX.finditer(tag_text):
            if m.group(1).startswith("data:"):
                continue
            lineno = ctx.lineno_at(start + m.start(1))
            if (lineno, m.group(1)) in seen:
                continue
            seen.add((lineno, m.group(1)))
            soft.append("line %d: img src %s (inside %s - %s)"
                        % (lineno, m.group(1)[:100],
                           _REGION_LABEL[kind], _ADJUDICATE))
    soft = _cap(soft)
    problems = line_details(hits)
    if problems:
        return Result(9, name, rule, FAIL, problems + soft)
    if soft:
        return Result(9, name, rule, WARN, soft)
    return Result(9, name, rule, PASS)


# --------------------------------------------------------------------------
# checks 10-11: section 8.2 (single source of truth for data) and
# section 8.3 (single source of truth for style)
# --------------------------------------------------------------------------

NAMED_COLORS = (
    "aqua black blue fuchsia gray green lime maroon navy olive purple red "
    "silver teal white yellow orange crimson coral gold indigo ivory khaki "
    "lavender magenta salmon tan tomato turquoise violet wheat").split()

_MAP_ASSIGN_RX = re.compile(
    r"\b(?:const|let|var)\s+MAP\s*=|\bwindow\.MAP\s*=")


def _offset_in_spans(offset, spans):
    return any(s <= offset < e for s, e in spans)


def _script_bodies(ctx):
    """[(start, end, region_kind)] for every <script>...</script> BODY
    found by a raw scan of ctx.html (see _SCRIPT_TAG_RX) - deliberately
    unmasked, because a <script> tag can be found nested inside another
    live script's own text (a JS string or template literal constructing
    markup, the document.write() pattern checks 1/6/9 already treat as
    real) and that nesting is exactly what this function needs to see.

    region_kind is None when the tag's own opening '<script' sits in
    live markup - a genuinely live, executing script. Otherwise it is
    the masked-region kind ("script", "style" or "comment") that the
    tag's start offset falls in, from Ctx.region_kind_at: "script" for
    a tag built inside another script's JS string/template literal,
    "comment" for one sitting inside an HTML comment. Same idea as
    _masked_region_tags, at body-span granularity instead of per-tag.

    This says nothing about what happens WITHIN a body that region_kind
    reports as live - text inside it can still be a JS comment, string or
    template literal rather than executing code. c10 answers that with
    Ctx.js_state_at, a real per-character JS tokenizer, not with anything
    computed here."""
    out = []
    for m in _SCRIPT_TAG_RX.finditer(ctx.html):
        out.append((m.start(1), m.end(1), ctx.region_kind_at(m.start())))
    return out


@check(10, "exactly one MAP object assignment", "section 8.2")
def c10(ctx):
    """section 8.2: exactly one MAP object literal.

    THE JS LEXER IS ADVISORY HERE AND HAS NO VETO. Two or more MAP
    assignments inside live <script> bodies is always a FAIL, whatever
    Ctx.js_state_at thinks of them; the lexer's opinion is appended to
    each cited line as a note the reader can act on.

    This is deliberate and was paid for. An earlier version let
    js_state_at DOWNGRADE a finding - a match it called "inside a JS
    string/comment/regex" was dropped from the count - to avoid
    false-FAILing on a `MAP =` written inside a comment. Five separate
    lexer defects, over five review rounds, each turned a real second
    assignment into "not live" and shipped WARN with exit 0: a false PASS
    on the exact violation this check exists to catch. Each fix was
    correct and the next reviewer found the same failure through a new
    mechanism, because no hand-written lexer inside a single-file checker
    resolves JS regex-vs-division for every input.

    Removing the veto removes the failure class by construction rather
    than by another round of disambiguation: a lexer error can now only
    make a note wrong, never make a verdict wrong. The cost is a false
    FAIL when a page really does carry a commented-out `MAP =` beside
    the live one - one glance at a cited line that already says which
    line and why. That is the cheap direction; a shipped violation with
    exit 0 is not.

    The REGION-masking layer (_mask_non_markup, via _script_bodies and
    region_kind_at) keeps its veto and is unchanged. A `MAP =` inside an
    HTML comment, or inside a <script> tag that itself only exists in a
    comment or a JS string, still reports at WARN. That layer is
    markup-level, has been stable across every round of this task, and is
    not implicated in any of the defects above."""
    name = "exactly one MAP object assignment"
    rule = "section 8.2"
    bodies = _script_bodies(ctx)
    live_hits = []
    soft = []

    def soft_note(lineno, label):
        soft.append("line %d: MAP assignment-like text (inside %s - %s)"
                    % (lineno, label, _ADJUDICATE))

    for start, end, kind in bodies:
        for m in _MAP_ASSIGN_RX.finditer(ctx.html[start:end]):
            abs_off = start + m.start()
            lineno = ctx.lineno_at(abs_off)
            if kind is not None:
                # masked-region veto: retained, see the docstring
                soft_note(lineno, _REGION_LABEL[kind])
                continue
            # Live <script> body. The match counts. js_state_at may only
            # annotate it.
            js_state = ctx.js_state_at(abs_off)
            label = _JS_STATE_LABEL.get(js_state)
            text = m.group(0)
            if label is not None:
                # Advisory only. Kept short deliberately: line_details
                # truncates at 120 characters, and a note that gets cut
                # off is worse than a terse one.
                text = "%s (note: lexer reads this as inside %s - " \
                    "advisory, not a verdict)" % (text, label)
            live_hits.append((lineno, text))
    # a bare "MAP =" mention sitting directly inside an HTML comment,
    # with no enclosing <script> tag at all
    body_spans = [(s, e) for s, e, _ in bodies]
    for m in _MAP_ASSIGN_RX.finditer(ctx.html):
        if ctx.region_kind_at(m.start()) != "comment":
            continue
        if _offset_in_spans(m.start(), body_spans):
            continue
        soft_note(ctx.lineno_at(m.start()), _REGION_LABEL["comment"])
    soft = _cap(soft)
    if len(live_hits) == 1:
        return Result(10, name, rule, WARN, soft) if soft \
            else Result(10, name, rule, PASS)
    if not live_hits:
        if soft:
            # Every MAP-shaped match was vetoed by the MARKUP-region
            # layer, not by the JS lexer. "Nothing live found alongside
            # something MAP-shaped in a comment" is not the same claim as
            # "no assignment exists"; WARN and let a human look.
            return Result(10, name, rule, WARN, soft)
        return Result(10, name, rule, FAIL,
                      ["no MAP object assignment found"])
    return Result(10, name, rule, FAIL,
                  ["%d MAP assignments; section 8.2 requires exactly one"
                   % len(live_hits)] + line_details(live_hits) + soft)


_STYLE_TAG_RX = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
_ROOT_BLOCK_RX = re.compile(r":root\s*\{.*?\}", re.S)
_CSS_COMMENT_RX = re.compile(r"/\*.*?\*/", re.S)
_CSS_DECL_RX = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]*)")


def _has_color_literal(text):
    return bool(re.search(r"#[0-9a-fA-F]{3,8}\b", text)
                or re.search(r"\b(?:rgba?|hsla?)\s*\(", text)
                or any(re.search(r"\b%s\b" % c, text) for c in NAMED_COLORS))


def _style_bodies(ctx):
    """[(start, end, region_kind)] for every <style>...</style> BODY,
    same shape and same reasoning as _script_bodies above: region_kind
    is None for a genuinely live stylesheet, else the masked-region kind
    the tag's own start offset falls in."""
    out = []
    for m in _STYLE_TAG_RX.finditer(ctx.html):
        out.append((m.start(1), m.end(1), ctx.region_kind_at(m.start())))
    return out


def _non_root_declarations(ctx):
    """(lineno, property, value) for every CSS declaration outside a
    :root block, in every genuinely live <style> body.

    Offset-based throughout: line numbers come from Ctx.lineno_at
    against the declaration's own match offset, never from a fuzzy
    per-line substring search - so an empty or unusual value (color:;)
    can never crash the lookup, by construction rather than by guard.
    Declarations that exist only inside a CSS comment, or only inside a
    non-live <style> body (nested in a JS string or an HTML comment),
    are excluded here; check 11 reports those separately, at WARN."""
    bodies = _style_bodies(ctx)
    nested = [(s, e) for s, e, kind in bodies if kind is not None]
    out = []
    for start, end, kind in bodies:
        if kind is not None:
            continue
        body = ctx.html[start:end]
        masked = _ROOT_BLOCK_RX.sub(lambda m: _blank_run(m.group(0)), body)
        masked = _CSS_COMMENT_RX.sub(lambda m: _blank_run(m.group(0)), masked)
        for m in _CSS_DECL_RX.finditer(masked):
            abs_off = start + m.start()
            if _offset_in_spans(abs_off, nested):
                continue
            prop, value = m.group(1).strip(), m.group(2).strip()
            out.append((ctx.lineno_at(abs_off), prop, value))
    return out


def _soft_color_literals(ctx):
    """[(note)] strings for color-literal-shaped text that is not a live
    style rule: inside a CSS comment in a live <style> body, inside a
    <style> body that only exists in a masked region (a JS string,
    nested inside another <style>/<script> body, or an HTML comment), or
    sitting directly inside an HTML comment with no enclosing <style>
    body at all. Check 11 reports these at WARN with the adjudication
    note, rather than FAIL - same reasoning as checks 7-9's soft bucket."""
    bodies = _style_bodies(ctx)
    seen = set()
    out = []

    def add(lineno, snippet, label):
        if lineno in seen:
            return
        seen.add(lineno)
        out.append("line %d: %s (inside %s - %s)"
                    % (lineno, snippet[:80], label, _ADJUDICATE))

    for start, end, kind in bodies:
        body = ctx.html[start:end]
        if kind is not None:
            for m in _CSS_DECL_RX.finditer(body):
                value = m.group(2).strip()
                if _has_color_literal(value):
                    add(ctx.lineno_at(start + m.start()),
                        "%s: %s" % (m.group(1).strip(), value),
                        _REGION_LABEL[kind])
            continue
        for cm in _CSS_COMMENT_RX.finditer(body):
            if _has_color_literal(cm.group(0)):
                add(ctx.lineno_at(start + cm.start()),
                    cm.group(0).strip(), "a CSS comment")
    body_spans = [(s, e) for s, e, _ in bodies]
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\s*\(",
                         ctx.html):
        if ctx.region_kind_at(m.start()) != "comment":
            continue
        if _offset_in_spans(m.start(), body_spans):
            continue
        lineno = ctx.lineno_at(m.start())
        add(lineno, ctx.lines[lineno - 1].strip(), _REGION_LABEL["comment"])
    return _cap(out)


@check(11, "no hardcoded colors outside :root", "section 8.3")
def c11(ctx):
    name = "no hardcoded colors outside :root"
    rule = "section 8.3"
    problems = []
    for lineno, prop, value in _non_root_declarations(ctx):
        if _has_color_literal(value):
            problems.append("line %d: %s: %s" % (lineno, prop, value[:80]))
    soft = _soft_color_literals(ctx)
    if problems:
        return Result(11, name, rule, FAIL, _cap(problems) + soft)
    if soft:
        return Result(11, name, rule, WARN, soft)
    return Result(11, name, rule, PASS)


# --------------------------------------------------------------------------
# checks 12-13: section 8.6(c) (no CTA verbs outside quoted blocks) and
# section 8.7 (no reference-example vocabulary absent from the map)
# --------------------------------------------------------------------------

# Stems, not whole words: real copy inflects them ("Launching", "Published",
# "Shipping"), so each stem is followed by \w* to absorb the inflection.
# Leading \b keeps this from firing mid-word ("relationship" does not
# contain a word-boundary immediately before "ship" - the character before
# it, "n", is itself a word character, so \bship never matches there).
CTA_PATTERN = r"\b(?:launch|ship|shipping|shipped|publish|buy|buys|buying|subscrib)\w*\b"

# section 8.7's reference (homelab) example vocabulary. This is a
# PROVENANCE list, not a ban list: ordinary English words on it ("backup",
# "restore", "monitoring") are legitimate in a research dashboard that
# happens to discuss backups. c13 only flags a hit that is BOTH absent
# from the current map AND not otherwise explained - see c13.
REFERENCE_VOCAB = ["homelab", "provisioning", "backup", "restore", "dotfiles",
                   "monitoring", "showcase", "adoption-reality", "community pull"]


# One attribute: NAME, optionally followed by ='...' / ="..." / =bare-value.
# Quote-aware in the same shape _ATTR_RUN already uses elsewhere in this
# file, so a quoted VALUE is captured whole rather than scanned as raw
# text - see _tag_is_quoted_marked for why that distinction matters here.
_ATTR_PARSE_RX = re.compile(
    r"""([^\s"'=<>`/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")


def _tag_is_quoted_marked(tag_text):
    """True if tag_text - one WHOLE opening tag, already matched via the
    quote-aware _TAG_RX/_ATTR_RUN shape - genuinely carries the
    quoted-region marking: the WINNING class attribute's value contains
    "quoted" as one of its whitespace-delimited TOKENS (not merely as a
    substring - "quoted-tag" and "unquoted" must not count), or a
    WINNING attribute literally NAMED data-quoted exists (its value, if
    any, is irrelevant - a bare boolean-style data-quoted with no '='
    still counts).

    "Winning" matters because HTML5 duplicate-attribute parsing keeps
    only the FIRST occurrence of a given attribute name; every later
    occurrence of that same name is a parse-time no-op a real browser
    never applies. `<div class="foo" class="quoted">` renders with
    class="foo" - the second, "quoted"-carrying occurrence is dead text
    as far as any browser is concerned. An earlier revision of this
    function tested EVERY class/data-quoted occurrence it found via
    _ATTR_PARSE_RX.finditer and returned True on the first one that
    happened to carry the token, regardless of position - so
    `class="foo" class="quoted">Buy now` was wrongly treated as quoted
    and _strip_quoted blanked the whole element, silently dropping the
    CTA verb. The fix: collapse the tag's attributes to a first-occurrence
    map first (skipping every later duplicate of an already-seen name),
    then test only the winning class/data-quoted from that map - never
    a later occurrence, however it reads.

    Attribute NAMES are case-insensitive in HTML (CLASS="quoted" and
    DATA-QUOTED both count), handled by lower-casing the name before it
    is used as the map key. Class TOKEN VALUES are NOT case-insensitive:
    a CSS ".quoted" selector does not match class="Quoted" in standards
    mode, so a browser does not treat that element as quoted, and this
    function must not either. An earlier revision lower-cased the class
    value before splitting it into tokens (`class_value.lower().split()`),
    conflating attribute-name case-insensitivity with token-value
    case-sensitivity - `<div class="Quoted">Buy now</div>` was wrongly
    treated as genuinely quoted and silently stripped. The token compare
    below is case-sensitive against the exact string "quoted"; only the
    attribute NAME lookups (winners.get("class"), "data-quoted" in
    winners) stay case-insensitive, because those really are names, not
    values.

    This replaces an earlier, defective detector that scanned raw tag
    text with `[^>]*` for the SUBSTRING "class=...quoted..." or
    "data-quoted" anywhere in the tag - which does not distinguish an
    actual attribute from an unrelated attribute's VALUE that merely
    contains that text. `<div title="data-quoted">` and
    `<div title="use class='quoted' for this">` both matched the old
    detector, so _strip_quoted blanked the whole element and silently
    dropped any live CTA verb inside it - the same "tool goes quiet"
    failure class the EOF-fallback fix addressed, reached through a
    different path in the same check. Because tag_text was already
    parsed quote-aware by the caller, an attribute VALUE containing
    those substrings is correctly seen as just a value, never mistaken
    for markup, by iterating actual name/value pairs instead of
    substring-matching the raw tag text."""
    winners = {}
    for m in _ATTR_PARSE_RX.finditer(tag_text):
        name = m.group(1).lower()
        if name in winners:
            continue  # HTML5: first occurrence wins; later ones are no-ops
        value = m.group(2)
        if value is None:
            value = m.group(3)
        if value is None:
            value = m.group(4)
        winners[name] = value
    if "data-quoted" in winners:
        return True
    class_value = winners.get("class")
    if class_value and "quoted" in class_value.split():
        return True
    return False


# Detects the spec's REAL quoted-region convention as well as the static
# attribute this file can actually resolve. GENERATOR_PACKAGE.md section 3
# rule 5 marks a quoted region with a visible "[quoted]" bracket token, not
# a class="quoted" attribute - see demo_dashboard.html's qtag(), which
# builds `<span class="chip quoted-tag">[quoted]</span>` at RUNTIME via
# `el("span","chip quoted-tag","[quoted]")` (a DOM API call, not literal
# markup text). The search below runs over the WHOLE raw document,
# including inside <script> bodies, on purpose: this is used only to
# decide what NOTE to attach (see c12), never a verdict, so there is no
# false-FAIL risk in over-detecting it, and restricting the search to live
# markup would make it blind to exactly the JS-rendered case it exists to
# name.
_QUOTED_TOKEN_RX = re.compile(r"""class\s*=\s*['"][^'"]*\bquoted\b|data-quoted|\[quoted\]""",
                              re.I)


def _quoted_convention_seen(html):
    return bool(_QUOTED_TOKEN_RX.search(html))


def _find_matching_close(html, tag_name, search_from):
    """Return the offset just past the CLOSING tag that matches the
    opening tag whose body starts at search_from, tracking nesting depth
    for same-named tags rather than stopping at the first closing tag of
    that name.

    A non-greedy `.*?</tag>` (the literal starter code's approach) closes
    on the FIRST same-tag closing tag it finds, which is wrong the moment
    a quoted element contains a NESTED element of the same tag name
    (`<div class="quoted"><div class="icon"></div>real quoted text</div>`)
    - the inner </div> ends the match early and leaves "real quoted text"
    outside the stripped region, undetected and unexcused. Depth-tracking
    finds the true matching close instead: every same-name opening tag
    seen before the next same-name closing tag increments depth; every
    closing tag decrements it; the match ends when depth returns to 0.

    Returns search_from - i.e. NOTHING beyond the opening tag itself gets
    treated as resolved - if no matching close exists anywhere in the
    rest of the document (an unterminated quoted element). This is NOT
    the same fallback _mask_non_markup uses for an unterminated <script>/
    <style>/comment (blank to end of document), and an earlier revision
    of this function wrongly copied that behavior by analogy. The
    analogy does not hold: <script> and <style> are HTML5 raw-text
    elements, so an unterminated one genuinely does consume the rest of
    the document in a browser. A <div>, or any other generic tag a
    quoted-region marker can appear on, is not a raw-text element - unclosed
    markup still renders its siblings and everything after it as normal,
    visible DOM. Blanking to end-of-document on a single missing closing
    tag silently dropped every real CTA-verb hit after it from the
    report - exactly the "tool goes quiet" failure this project exists
    to prevent, worse than the false-FAIL it would have been reporting
    instead of hiding. An unresolvable quoted region must fail toward
    REPORTING the hit, never toward hiding it, so the correct fallback is
    the same one the base non-greedy regex already had: no matching close
    found -> strip nothing beyond the opening tag, and let downstream
    text stand as live, reportable content."""
    open_rx = re.compile(r"<%s\b%s>" % (re.escape(tag_name), _ATTR_RUN), re.I)
    close_rx = re.compile(r"</%s\s*>" % re.escape(tag_name), re.I)
    depth = 1
    pos = search_from
    while depth > 0:
        next_close = close_rx.search(html, pos)
        if next_close is None:
            return search_from
        next_open = open_rx.search(html, pos, next_close.start())
        if next_open is not None:
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    return pos


def _strip_quoted(html):
    """Remove elements genuinely, attribute-wise marked as quoted
    (a class attribute carrying "quoted" as a whitespace-delimited
    token, or an attribute literally named data-quoted). Returns
    (text, static_markup_found).

    Blanking is offset-preserving - the same idiom _mask_non_markup uses
    via _blank_run - so a matched quoted element's characters (including
    its own opening/closing tags) become spaces rather than being deleted.
    A naive re.sub(..., " ") that COLLAPSES a multi-line quoted block to a
    single space character would shift every offset and line number after
    it in the returned text, which would make region_kind_at and
    lineno_at (both called against these offsets by c12) silently
    misattribute region and cite the wrong line for anything downstream of
    a multi-line quoted block.

    Candidate opening tags come from _TAG_RX - the SAME quote-aware,
    document-wide tag matcher checks 6-9 already use - not a bespoke
    substring scan. Each candidate is then tested by
    _tag_is_quoted_marked, which parses its actual attribute name/value
    pairs rather than substring-matching the tag's raw text. An earlier
    revision matched `class\\s*=...quoted...|data-quoted` as a raw
    substring anywhere in `[^>]*` tag text, which cannot distinguish a
    real attribute from an unrelated attribute's VALUE that merely
    contains that text - `<div title="data-quoted">` or
    `<div title="use class='quoted' for this">` both satisfied it,
    causing _strip_quoted to blank the whole element and silently drop
    any live CTA verb inside - a hit-loss bug, not merely an
    over-broad one, since check 12 is WARN-only and a dropped hit never
    surfaces at all. Every ambiguous or unparseable case must resolve
    toward NOT stripping (so the text stays live and gets reported),
    never toward stripping on a guess - the same governing principle
    _find_matching_close's EOF fallback already applies.

    Nesting-aware via _find_matching_close - see its docstring for why a
    non-greedy same-tag regex is wrong the moment a quoted element
    contains a same-named child element.

    This only ever REMOVES text it can prove is quoted; it never proves
    the converse. See c12 for why "nothing static found here" stopped
    being treated as "nothing is quoted" - static_markup_found is kept
    only as a minor, best-effort signal, not a verdict input."""
    pieces = []
    kept = 0
    scan = 0
    found_any = False
    # No "already inside a previously-stripped span" guard is needed here:
    # scan and kept are always advanced together to the same close_end
    # (or to m.end() for a candidate that turns out not to be genuinely
    # quoted-marked), so each search starts exactly where the previous
    # decision left off, and re.search(html, scan) cannot return a match
    # starting before scan. A nested quoted-marked element inside an
    # already-stripped outer span (e.g. <div class="quoted"><span
    # class="quoted">...) is therefore never independently found at all -
    # it is already behind the search cursor, consumed as part of the
    # outer element's own depth-tracked strip - so there is nothing left
    # to double-process.
    for m in iter(lambda: _TAG_RX.search(html, scan), None):
        if not _tag_is_quoted_marked(m.group(0)):
            scan = m.end()
            continue
        found_any = True
        close_end = _find_matching_close(html, m.group(1), m.end())
        pieces.append(html[kept:m.start()])
        pieces.append(_blank_run(html[m.start():close_end]))
        kept = close_end
        scan = close_end
    if not found_any:
        return html, False
    pieces.append(html[kept:])
    return "".join(pieces), True


@check(12, "no call-to-action verbs outside quoted blocks", "section 8.6(c)")
def c12(ctx):
    """section 8.6(c): no launch/ship/publish/buy/subscribe verb outside a
    quoted block.

    WARN-ONLY BY DESIGN - THIS CHECK NEVER FAILS. An earlier revision
    FAILed once static class="quoted"/data-quoted markup existed anywhere
    in the file, reasoning that a document proven able to mark quoted
    regions could have every remaining stem hit treated as unexcused.
    Two problems made that unsupportable, and both are permanent
    properties of what this tool can see from static text - not
    implementation bugs to patch away:

    1. The reference dashboard's OWN quoted-region convention, per
       GENERATOR_PACKAGE.md section 3 rule 5, is a visible "[quoted]"
       bracket annotation - not a class="quoted" attribute. demo_
       dashboard.html implements it correctly, via `qtag()`:
       `el("span","chip quoted-tag","[quoted]")` - a DOM API call that
       BUILDS the marked span at runtime. No static regex over document
       text can know which rendered text a runtime-constructed element
       ends up wrapping. So "no static quoted markup found" never proved
       "nothing here is quoted" - it only ever proved "not marked in a
       way this tool can resolve," and the FAIL branch could fire on a
       spec-compliant, correctly-quoted dashboard whose actual quoting
       mechanism is simply invisible to a text-level check.
    2. CTA_PATTERN is a stem grep - section 8.6(c) specifies exactly this
       - and stems overmatch ordinary English ("ships", "publishable",
       "buyer") that is not a call to action. Escalating that kind of hit
       to FAIL the instant ANY quoted markup exists anywhere in the file,
       even markup nowhere near the hit, produced a confirmed false FAIL
       on ordinary honest-assessment prose.

    So every CTA-verb hit is still found and still cited, every time -
    nothing is dropped. What changed is that the check stopped asserting
    a verdict (quoted vs. not) it cannot actually determine from static
    text alone. A dashboard full of real, live calls to action still gets
    every one of them reported, at WARN, for a human to read and act on -
    exactly the same adjudication an unmarked file already required
    before this change, just without ever risking exit 1 on a false
    positive it cannot tell apart from a real one.

    Two independent notes travel with a live hit:
      - _quoted_convention_seen: whether the file shows ANY evidence of
        the spec's real "[quoted]" convention (static or, far more
        likely, JS-rendered) - if so, the note says so explicitly rather
        than implying no quoting exists at all.
      - region-graded exactly like checks 7-9, on a SEPARATE axis: a hit
        that exists only inside a <script> body, a <style> body or an
        HTML comment is not live user-facing content at all, and gets its
        own WARN note rather than being folded into the live-hit note."""
    name = "no call-to-action verbs outside quoted blocks"
    rule = "section 8.6(c)"
    text, _static_marked = _strip_quoted(ctx.html)
    convention_seen = _quoted_convention_seen(ctx.html)
    cta_rx = re.compile(CTA_PATTERN, re.I)
    live_hits = []
    soft = []
    seen_live = set()
    seen_soft = set()
    for m in cta_rx.finditer(text):
        lineno = ctx.lineno_at(m.start())
        kind = ctx.region_kind_at(m.start())
        if kind is not None:
            if lineno in seen_soft:
                continue
            seen_soft.add(lineno)
            soft.append("line %d: %s (inside %s - %s)"
                        % (lineno, ctx.lines[lineno - 1].strip()[:120],
                           _REGION_LABEL[kind], _ADJUDICATE))
            continue
        if lineno in seen_live:
            continue
        seen_live.add(lineno)
        live_hits.append((lineno, ctx.lines[lineno - 1]))
    soft = _cap(soft)
    if not live_hits and not soft:
        return Result(12, name, rule, PASS)
    details = []
    if live_hits:
        if convention_seen:
            details.append(
                "this file marks quoted regions (a \"[quoted]\" token or "
                "a quoted-bearing class name was found), but quoted "
                "regions may be constructed at runtime and cannot be "
                "resolved statically; hits below need human adjudication")
        else:
            details.append(
                "no quoted-region marking found (class=\"quoted\", "
                "data-quoted, or a literal \"[quoted]\" token); hits "
                "below need human adjudication")
        details.extend(line_details(live_hits))
    details.extend(soft)
    return Result(12, name, rule, WARN, details)


@check(13, "no reference-example vocabulary absent from the source map",
       "section 8.7")
def c13(ctx):
    """section 8.7: no reference-example (homelab) vocabulary except where
    present in THIS map.

    This is a PROVENANCE test, not a wordlist ban - see REFERENCE_VOCAB.
    A word's every occurrence is suppressed silently, in every region,
    the moment it is found anywhere in --map's text: at that point it is
    this map's own vocabulary, not a leaked reference-example word, and
    section 8.7 has nothing to say about it.

    For whatever survives that suppression, region-grading applies first
    (a hit that exists only inside a <script> body, a <style> body or an
    HTML comment is not live content - WARN, same as checks 7-9), and
    only then does the live/no-map-given distinction from the docstring
    below decide FAIL vs WARN. --map turns "this word may be legitimate
    English" into a checkable fact; without it the check cannot tell
    leakage from legitimate usage and always WARNs instead of guessing.

    Word-boundary note: several list entries ("backup", "restore",
    "monitoring") can sit inside a hyphenated CSS custom-property token
    such as --backup-tint, where \\b still matches on either side of the
    hyphen (Task 4's `\\bred\\b` inside `--banner-red` bug). A :root token
    declaration lives inside a <style> body by construction, so the
    region grading above already demotes that hit to WARN rather than
    letting it FAIL - the fix is the existing region layer, not a new
    hyphen-aware pattern. Verified empirically in the report, not just
    reasoned about."""
    name = "no reference-example vocabulary absent from the source map"
    rule = "section 8.7"
    if ctx.reference:
        return Result(13, name, rule, SKIP,
                      ["--reference: this file IS the reference example"])
    live_hits = []
    soft = []
    seen_live = set()
    seen_soft = set()
    for word in REFERENCE_VOCAB:
        rx = re.compile(r"\b%s\b" % re.escape(word), re.I)
        if ctx.map_text and rx.search(ctx.map_text):
            continue  # present in THIS map, so not leakage (section 8.7)
        for m in rx.finditer(ctx.html):
            lineno = ctx.lineno_at(m.start())
            kind = ctx.region_kind_at(m.start())
            if kind is not None:
                key = (lineno, word)
                if key in seen_soft:
                    continue
                seen_soft.add(key)
                soft.append("line %d: %r (inside %s - %s)"
                            % (lineno, word, _REGION_LABEL[kind], _ADJUDICATE))
                continue
            key = (lineno, word)
            if key in seen_live:
                continue
            seen_live.add(key)
            live_hits.append(
                (lineno, "%r  %s" % (word, ctx.lines[lineno - 1].strip())))
    soft = _cap(soft)
    if not live_hits and not soft:
        return Result(13, name, rule, PASS)
    if live_hits:
        if ctx.map_text:
            return Result(13, name, rule, FAIL, line_details(live_hits) + soft)
        return Result(13, name, rule, WARN,
                      ["no --map given, so leakage cannot be told from "
                       "legitimate vocabulary; hits below need human "
                       "adjudication"] + line_details(live_hits) + soft)
    # only masked-region hits survive: not live user-facing content
    return Result(13, name, rule, WARN, soft)


# --------------------------------------------------------------------------
# checks 14-15: section 6.6 (fonts: fallback stack, non-blocking load)
# --------------------------------------------------------------------------

GENERIC_FAMILIES = ("monospace", "sans-serif", "serif", "system-ui",
                    "ui-monospace", "ui-sans-serif", "ui-serif",
                    "cursive", "fantasy")

_VAR_REF_RX = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)")


def _resolve_font_value(value, tokens):
    """Substitute var(--x) / var(--x, inline-fallback) references
    against tokens (Ctx.root_tokens()), repeatedly, so a token that
    itself references another token still resolves
    (--heading-font:var(--font-mono)). Bounded iteration guards a
    cyclic token definition (--a:var(--b); --b:var(--a);) without
    hanging; a var() whose name is not in tokens AND carries no inline
    fallback argument is left unresolved on purpose - "var(" surviving
    in the return value is the caller's signal to treat this as
    UNCERTAINTY (WARN), never as proof of a missing fallback (FAIL).
    See the c14 docstring for why that direction matters."""
    resolved = value
    for _ in range(6):
        m = _VAR_REF_RX.search(resolved)
        if not m:
            break
        if m.group(1) in tokens:
            replacement = tokens[m.group(1)]
        elif m.group(2) is not None:
            replacement = m.group(2).strip()
        else:
            break
        resolved = resolved[:m.start()] + replacement + resolved[m.end():]
    return resolved


_FONT_FACE_BLOCK_RX = re.compile(r"@font-face\s*\{[^{}]*\}", re.I | re.S)


def _live_style_font_declarations(ctx):
    """(lineno, value) for every font-family declaration in a live
    <style> body. Mirrors _non_root_declarations exactly (same body
    scan, same :root/CSS-comment masking via _blank_run so offsets stay
    valid), with one addition: @font-face{...} blocks are ALSO masked
    out before the declaration regex runs, not filtered out afterward.

    An @font-face rule's own font-family declaration NAMES the family
    being defined (`@font-face{font-family:'Custom Font';
    src:local('X')}`) - it is not a font-family STACK, so section 6.6's
    fallback-tail requirement does not apply to it, unlike an ordinary
    rule's font-family declaration. @media/@supports/@keyframes are
    deliberately NOT given this treatment: they nest real declarations
    that do need checking.

    This function exists because a LINE-based version of the same
    exemption (blank the physical lines an @font-face block spans, then
    filter _non_root_declarations's line-numbered output against that
    set) was tried first and broken by this task's own break-it
    testing: a minified single physical line holding both an
    @font-face block and a separate, real, live font-family violation
    exempted the real violation too, purely because it shared a line
    number with the @font-face block - a false PASS on a genuine
    violation. Masking by OFFSET, at the exact character span, the same
    way _non_root_declarations already masks :root, cannot make that
    mistake: nothing outside the @font-face block's own span is ever
    touched, however many other rules share its physical line."""
    bodies = _style_bodies(ctx)
    nested = [(s, e) for s, e, kind in bodies if kind is not None]
    out = []
    for start, end, kind in bodies:
        if kind is not None:
            continue
        body = ctx.html[start:end]
        masked = _ROOT_BLOCK_RX.sub(lambda m: _blank_run(m.group(0)), body)
        masked = _CSS_COMMENT_RX.sub(lambda m: _blank_run(m.group(0)), masked)
        masked = _FONT_FACE_BLOCK_RX.sub(lambda m: _blank_run(m.group(0)), masked)
        for m in _CSS_DECL_RX.finditer(masked):
            if m.group(1).strip().lower() != "font-family":
                continue
            abs_off = start + m.start()
            if _offset_in_spans(abs_off, nested):
                continue
            out.append((ctx.lineno_at(abs_off), m.group(2).strip()))
    return out


def _looks_like_font_stack_value(value):
    """True if value has the SHAPE of a CSS font-family value: a
    comma-separated fallback list, a single quoted family name (the
    exact single-font-no-fallback shape this check exists to catch), or
    a bare generic family word on its own. False for a bare number,
    keyword or unquoted single word - those are never a font-family
    value, whatever the token's NAME suggests."""
    v = value.strip()
    if not v:
        return False
    if "," in v:
        return True
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return True
    return v.strip("'\"").lower() in GENERIC_FAMILIES


def _is_font_family_token(token_name, value):
    """True if a :root custom property plausibly holds a font-family
    STACK, so section 6.6's fallback-tail requirement applies to its
    own definition too - see the c14 docstring for why a token-based
    design's :root tokens are checked as well as live declarations
    ("check both sites").

    Two gates, both required, deliberately conservative toward NOT
    flagging:

    - NAME must contain "font" (matches this project's own convention -
      --font-mono/--font-sans/--font-serif in examples/*.html). This is
      a literal-word substring check, never a check for a
      GENERIC_FAMILIES word (serif/monospace/...) appearing in the
      NAME - that is exactly the hyphen/word-boundary trap that
      produced 40 false findings in checks 11/13 (a generic family word
      sits inside plenty of token names, e.g. --serif-heading-color,
      that hold a color, not a font stack).
    - VALUE must look like a font-family value (see
      _looks_like_font_stack_value). This excludes the many other
      legitimate "font-*"-named design tokens that are not stacks at
      all - --font-base:16px, --font-scale:1.25, --font-weight:600,
      --font-leading:1.5 - which a name-only filter would wrongly flag:
      a bare number or keyword is never a font-family value.

    Known, accepted limitation: a font-role token holding a single BARE
    (unquoted, no comma) non-generic family name and nothing else -
    --font-primary:Arial, with no fallback at all - fails the shape
    gate and is not examined here. That specific violation still gets
    caught if the token is referenced anywhere by a live font-family:
    declaration (resolved and judged at the point of use, by the main
    declaration loop in c14) - it escapes ONLY when the bad token is
    defined but never referenced, i.e. dead CSS that cannot affect the
    rendered page."""
    if "font" not in token_name.lower():
        return False
    return _looks_like_font_stack_value(value)


# Quote-matched alternation, like _ATTR_PARSE_RX elsewhere in this file -
# never r"""['"]([^'"]*)['"]""", which accepts a MISMATCHED closing quote
# (opens on the outer double quote, closes on the first embedded single
# quote) and truncates the value. A real, confirmed defect during this
# task's own break-it testing: style="font-family:'Weird Font'" has a
# single quote inside a double-quoted attribute value - exactly the shape
# a font-family value with a quoted family name always has - and the
# mismatched-quote pattern silently truncated the captured value to just
# "font-family:", dropping the font name and its (missing) fallback
# entirely. That is a hidden hit: a live, FAIL-worthy inline style=
# declaration would have gone unexamined and the check would PASS a real
# violation.
_STYLE_ATTR_RX = re.compile(r"""\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


def _inline_style_font_values(ctx):
    """(lineno, value) for every font-family declaration inside a LIVE
    inline style="" attribute. Offset-based against the declaration's
    own position within the attribute value (not the tag's start), so a
    tag whose attributes wrap onto a later physical line still cites
    the line the declaration actually sits on - same reasoning
    _masked_region_external_refs already documents for other checks.
    _non_root_declarations only ever looks at <style> body text;
    section 6.6's fallback-stack requirement binds a live inline
    style= rule exactly the same way, so c14 must look here too."""
    out = []
    for start, tag_name, tag_text in _tags_in(ctx.masked_html()):
        attr_m = _STYLE_ATTR_RX.search(tag_text)
        if not attr_m:
            continue
        group_idx = 1 if attr_m.group(1) is not None else 2
        value_text = attr_m.group(group_idx)
        base = start + attr_m.start(group_idx)
        for m in _CSS_DECL_RX.finditer(value_text):
            if m.group(1).strip().lower() != "font-family":
                continue
            out.append((ctx.lineno_at(base + m.start()), m.group(2).strip()))
    return out


_FONT_FAMILY_TEXT_RX = re.compile(r"font-family\s*:\s*[^;{}\n]*", re.I)


def _soft_font_declarations(ctx):
    """[note] strings for font-family-shaped text that is NOT a live
    style rule: inside a CSS comment in a live <style> body, inside a
    <style> body that only exists in a masked region (nested in a JS
    string/template literal or an HTML comment), or sitting directly
    inside a live <script> body (a JS string constructing markup or
    CSS) or an HTML comment with no enclosing <style> tag at all.
    Region-graded and reported at WARN with the adjudication note,
    never dropped and never FAIL - same reasoning as checks 7-9's and
    c11's soft buckets.

    Unlike c11's soft-color-literal scan, the final raw-text pass below
    is not narrowed to the "comment" region kind. A bare color-literal
    pattern (#fff, rgba(...)) is common in ordinary JS unrelated to CSS,
    so c11 narrows its pass to avoid noise; "font-family:" is a far more
    specific textual shape that essentially only appears where CSS or
    CSS-shaped text is being constructed, so including the "script"
    region kind here is low-noise and, per this task's resolved
    ambiguity, required: a font-family mention inside a JS string must
    still surface, not vanish."""
    bodies = _style_bodies(ctx)
    seen = set()
    out = []

    def add(lineno, snippet, label):
        if lineno in seen:
            return
        seen.add(lineno)
        out.append("line %d: %s (inside %s - %s)"
                    % (lineno, snippet[:80], label, _ADJUDICATE))

    for start, end, kind in bodies:
        body = ctx.html[start:end]
        if kind is not None:
            for m in _FONT_FAMILY_TEXT_RX.finditer(body):
                add(ctx.lineno_at(start + m.start()), m.group(0).strip(),
                    _REGION_LABEL[kind])
            continue
        for cm in _CSS_COMMENT_RX.finditer(body):
            for m in _FONT_FAMILY_TEXT_RX.finditer(cm.group(0)):
                add(ctx.lineno_at(start + cm.start() + m.start()),
                    m.group(0).strip(), "a CSS comment")
    body_spans = [(s, e) for s, e, _ in bodies]
    for m in _FONT_FAMILY_TEXT_RX.finditer(ctx.html):
        kind = ctx.region_kind_at(m.start())
        if kind is None:
            continue
        if _offset_in_spans(m.start(), body_spans):
            continue
        add(ctx.lineno_at(m.start()), m.group(0).strip(), _REGION_LABEL[kind])
    return _cap(out)


@check(14, "every font-family ends in a generic family", "section 6.6")
def c14(ctx):
    """section 6.6: every font-family declaration must terminate in a
    generic family, so the page stays legible with zero network.

    var() IS resolved against Ctx.root_tokens() before judging (a
    dashboard commonly writes font-family:var(--mono) with the real
    stack living in :root). An UNRESOLVABLE var() - the custom property
    is not defined anywhere root_tokens() can see - is NOT proof of a
    missing fallback: it is reported at WARN, never FAIL. Uncertainty
    must never invent a defect; see _resolve_font_value.

    Three sites are checked, because section 6.6's requirement binds
    wherever a font-family value actually lives: a live <style> body's
    declarations (_live_style_font_declarations - the same body scan
    and :root/comment masking _non_root_declarations uses, plus an
    @font-face exemption its own font-family does not need), a live
    inline style= attribute (_inline_style_font_values - not covered by
    _non_root_declarations at all), and :root token DEFINITIONS
    themselves for a token-based design (_is_font_family_token) - a
    badly-defined token still needs catching even where nothing in this
    document happens to reference it via var().

    Region-graded like checks 7-13: a font-family mention that exists
    only inside a CSS comment, a nested/non-live <style> body, a live
    <script> body's JS text, or an HTML comment is not a live style
    rule and cannot FAIL - _soft_font_declarations reports it at WARN
    instead of dropping it.

    Known limitations, tested and disclosed rather than silently
    assumed away (see the task report): Ctx.root_tokens() is
    region-blind (built in Task 2, out of scope here) - a :root block
    that exists only inside an HTML comment or a JS string still feeds
    the token map, so a bad font token defined ONLY there can produce a
    false FAIL via the root-token loop, and conversely a live
    font-family:var(--x) whose --x is defined ONLY in such a commented-
    out :root resolves and PASSes when the rendered page would actually
    see --x as undefined. A font-role root token holding a single bare,
    unquoted, non-generic family name with no comma and no quotes
    (--font-primary:Arial) is not examined by the root-token loop at
    all unless referenced elsewhere (see _is_font_family_token)."""
    name = "every font-family ends in a generic family"
    rule = "section 6.6"
    tokens = ctx.root_tokens()
    problems = []
    warns = []

    def audit(value, cite):
        resolved = _resolve_font_value(value, tokens)
        if not resolved.strip():
            return  # empty value: not a missing-fallback violation
        if "var(" in resolved:
            warns.append("%s: unresolvable var() in stack: %s"
                        % (cite, value[:60]))
            return
        last = resolved.split(",")[-1].strip().strip("'\"").lower()
        if last not in GENERIC_FAMILIES:
            problems.append("%s: stack ends in %r, not a generic family"
                            % (cite, last[:40]))

    for lineno, value in _live_style_font_declarations(ctx):
        audit(value, "line %d" % lineno)

    for lineno, value in _inline_style_font_values(ctx):
        audit(value, "line %d (inline style attribute)" % lineno)

    for token, value in tokens.items():
        if not _is_font_family_token(token, value):
            continue
        audit(value, "%s (root token)" % token)

    warns.extend(_soft_font_declarations(ctx))
    problems = _cap(problems)
    warns = _cap(warns)
    if problems:
        return Result(14, name, rule, FAIL, problems + warns)
    if warns:
        return Result(14, name, rule, WARN, warns)
    return Result(14, name, rule, PASS)


def _fonts_link_tags(ctx):
    """(lineno, url, tag_text) for every LIVE <link> tag whose href
    points at a known fonts host - the FULL tag text, not just the
    source line the href happens to render on. A real <link> commonly
    wraps media=/onload= onto a later physical line (see
    examples/research_dashboard.html); judging render-blocking
    behaviour from a single source line, as ctx.lines[lineno-1] alone
    would, misses attributes that live elsewhere in the same tag and
    false-FAILs a compliant tag."""
    out = []
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name != "link":
            continue
        m = _REF_ATTR_RX.search(tag_text)
        if m and _is_font_host(m.group(1)):
            out.append((lineno, m.group(1), tag_text))
    return out


def _soft_fonts_links(ctx):
    """(lineno, url, region_kind) for a fonts-host reference that
    exists only inside a masked region. Not live markup, so it cannot
    make check 15 FAIL - section 6.6's render-blocking requirement is
    about what a browser actually loads - but per this project's
    standing rule a hit is never silently dropped either."""
    return [(n, u, kind) for n, u, kind in _masked_region_external_refs(ctx)
            if _is_font_host(u)]


def _link_attr_winners(tag_text):
    """First-occurrence-wins attribute name/value map for one whole
    <link ...> tag - the same parsing _tag_is_quoted_marked already
    uses for class/data-quoted, applied here to media/onload/rel.
    Never a substring search over raw tag text: that cannot distinguish
    a real media=/onload= attribute from an unrelated attribute's VALUE
    that merely CONTAINS that text - e.g.
    title="media='print' onload='x'" - which is exactly the bug class
    _tag_is_quoted_marked's own docstring documents
    (title="data-quoted"), reached here through a decoy title/alt/
    aria-label instead of a decoy class. A checker that can be told
    "this is non-blocking" by an attribute that ISN'T media= or onload=
    would let a genuinely render-blocking fonts link ship at exit 0 -
    the worse of the two failure directions this task warns about."""
    winners = {}
    for m in _ATTR_PARSE_RX.finditer(tag_text):
        attr_name = m.group(1).lower()
        if attr_name in winners:
            continue
        value = m.group(2)
        if value is None:
            value = m.group(3)
        if value is None:
            value = m.group(4)
        winners[attr_name] = value
    return winners


def _fonts_link_is_nonblocking(tag_text):
    """True if a <link> tag's own REAL attributes (via
    _link_attr_winners, not a raw-text substring search) show the
    non-blocking swap pattern section 6.6 requires: media="print"
    paired with an onload= handler (the standard print-media async-CSS
    trick), or rel="preload" - checked as a whitespace-delimited TOKEN
    of the rel attribute's value, not a substring, so
    rel="stylesheet-preload-notice" cannot be mistaken for the real
    preload keyword (the same fix checks 7/13 made for class/vocabulary
    tokens)."""
    winners = _link_attr_winners(tag_text)
    media = (winners.get("media") or "").strip().lower()
    has_onload = "onload" in winners
    rel_tokens = (winners.get("rel") or "").split()
    return (media == "print" and has_onload) or ("preload" in rel_tokens)


@check(15, "fonts stylesheet does not block render", "section 6.6")
def c15(ctx):
    """section 6.6: a fonts stylesheet must not block render. Scope is
    deliberately narrow (this check has nothing to say about anything
    but a genuine fonts <link>'s own loading behaviour): no external
    fonts stylesheet at all is PASS with a note that nothing can block;
    a live fonts <link> FAILs only for missing the non-blocking swap
    pattern (see _fonts_link_is_nonblocking); a fonts reference found
    only in a masked region cannot FAIL (not live markup) but is still
    surfaced at WARN rather than dropped, per this project's standing
    rule."""
    name = "fonts stylesheet does not block render"
    rule = "section 6.6"
    live = _fonts_link_tags(ctx)
    soft_raw = _soft_fonts_links(ctx)
    if not live and not soft_raw:
        return Result(15, name, rule, PASS,
                      ["no external fonts stylesheet; nothing can block"])
    problems = []
    for lineno, url, tag_text in live:
        if not _fonts_link_is_nonblocking(tag_text):
            problems.append(
                "line %d: %s loads render-blocking; section 6.6 requires "
                'media="print"+onload swap or rel="preload"'
                % (lineno, url[:70]))
    soft = _cap([
        "line %d: fonts stylesheet %s (inside %s - %s); render-blocking "
        "status cannot be determined for non-live markup"
        % (n, u[:70], _REGION_LABEL[kind], _ADJUDICATE)
        for n, u, kind in soft_raw])
    if problems:
        return Result(15, name, rule, FAIL, problems + soft)
    if soft:
        return Result(15, name, rule, WARN, soft)
    return Result(15, name, rule, PASS)


@check(16, "output hygiene: DOCTYPE first, </html> last, no prose", "section 8.10")
def c16(ctx):
    problems = []
    text = ctx.html.strip()
    if "```" in text:
        problems.append("markdown code fence present in output")
    # a single leading HTML comment is permitted: the prompt's documented
    # missing-delimiter behavior emits one
    lead = re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.S)
    if not lead.lstrip().lower().startswith("<!doctype html"):
        problems.append("does not begin with <!DOCTYPE html> "
                        "(one leading HTML comment is allowed)")
    if not text.rstrip().lower().endswith("</html>"):
        problems.append("does not end with </html>")
    if problems:
        return Result(16, "output hygiene: DOCTYPE first, </html> last, no prose",
                      "section 8.10", FAIL, problems)
    return Result(16, "output hygiene: DOCTYPE first, </html> last, no prose",
                  "section 8.10", PASS)


# --------------------------------------------------------------------------
# check 17: per-example data-faithfulness fixtures (section 8.4/8.5, partial)
# --------------------------------------------------------------------------

# Per-fixture expected data, keyed by the --expect name. Only what is
# mechanically checkable: the asset codes that must appear in MAP, the
# rank each code must be recorded at, and the source map's own
# binding-constraint sentence, verbatim. 'selftest' backs the self-test
# harness (see _statuses) so this check is actually exercisable instead
# of permanently SKIPping for lack of --expect; its values match the
# FIXTURE's MAP literal exactly, one asset, no banner requirement.
# 'research' is given by the task spec, matched against
# examples/research_portfolio_map.md and examples/research_dashboard.html.
# 'demo' is derived from examples/demo_source_map.md: asset codes and
# ranks from its "Setup readiness x community pull" ranked table, and
# the banner from its "Honesty constraint (binding, every entry)"
# sentence's bolded never-clause (trailing period omitted, same
# convention as 'research', so the substring check does not depend on
# whatever punctuation happens to follow it in the rendered markup).
EXPECTATIONS = {
    "selftest": {
        "codes": ["AAA-1"],
        "ranks": {"AAA-1": 1},
        "banner": "",
    },
    "research": {
        "codes": ["MEM-1", "MEM-2", "MEM-3", "TOOL-1", "TOOL-2", "TOOL-3"],
        "ranks": {"MEM-3": 1, "TOOL-2": 2, "MEM-1": 3,
                  "TOOL-1": 4, "MEM-2": 5, "TOOL-3": 6},
        "banner": "never validated findings, never recommendations, "
                  "never a causal claim",
    },
    "demo": {
        "codes": ["INF-1", "INF-2", "INF-3", "PUB-1", "PUB-2", "PUB-3"],
        "ranks": {"INF-2": 1, "INF-1": 2, "PUB-1": 3,
                  "INF-3": 4, "PUB-3": 5, "PUB-2": 6},
        "banner": "never production-ready software, never a security "
                  "guarantee, never a maintained product promise",
    },
}


def _skip_noncode(text, i):
    """If text[i] opens a quoted string ('...', "...", `...`, backslash
    escapes honoured) or a comment (// to end of line, /* to */), return
    the offset just past its close. Otherwise return None.

    Shared by _map_body and _map_entries so both scans agree on what
    counts as live structure: a brace, a comma or a quote character
    sitting INSIDE a string value (`code: "A{B"`) or a comment can never
    be mistaken for JS structure by either one. An unterminated string
    or comment is treated as running to end of text rather than
    resynchronising mid-scan and risking a wrong brace-depth count in
    either direction - the same fail-safe choice _mask_non_markup makes
    for an unterminated comment or <script> body elsewhere in this
    file."""
    n = len(text)
    c = text[i]
    if c in ("'", '"', "`"):
        j = i + 1
        while j < n:
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == c:
                return j + 1
            j += 1
        return n
    if c == "/" and i + 1 < n and text[i + 1] == "/":
        nl = text.find("\n", i)
        return n if nl == -1 else nl + 1
    if c == "/" and i + 1 < n and text[i + 1] == "*":
        close = text.find("*/", i + 2)
        return n if close == -1 else close + 2
    return None


def _map_body(html):
    """Text of the MAP object literal (its outer braces included), or
    None if it cannot be located.

    Brace depth is counted only over characters _skip_noncode says are
    live code - never inside a quoted string or a comment. A naive,
    string-blind counter that scans every '{'/'}' character regardless
    of context is wrong in two distinct, opposite ways, and an
    unescaped brace inside a string value (`title_first: "Home{lab"`,
    or a stray '}' the same way) can trigger either one depending on
    which brace it is:

    - a spurious '}' inside a string reads as MAP's own closing brace
      and stops the scan too EARLY, truncating the returned body before
      the real end. That shrinks what check 17 can inspect - codes and
      ranks that exist further down are reported missing - which is a
      false FAIL on faithful data, not a false PASS: fewer characters to
      search can only ever ADD "not found" problems, never remove one
      that should be there.
    - a spurious '{' inside a string inflates the depth count by one, so
      the real closing brace only brings depth to 1, not 0, and the scan
      runs too LATE, past MAP's true end into unrelated document text.
      That is the more dangerous direction: the over-captured tail is
      text check 17 was never meant to search, and if it happens to
      contain something code:/rank:-shaped it can manufacture either a
      false PASS (an accidental match papering over a real absence) or,
      under c17's own-field-uniqueness rule, a false FAIL (a second,
      unrelated "owner" of a code that was faithfully recorded once).

    _skip_noncode removes both failure modes by construction: every
    character this function counts as '{' or '}' is one _skip_noncode
    agrees is live code, so neither a stray '{' nor a stray '}' sitting
    inside a string or comment can register as either kind of brace.
    Verified empirically, not just reasoned about - see this task's
    break-it notes for the discriminating test (an UNBALANCED brace
    inside a string on each side; a balanced pair like `"A{B}C"` does
    not exercise this scanner at all, since naive counting also nets
    zero on it)."""
    m = re.search(r"(?:const|let|var)\s+MAP\s*=\s*", html)
    if not m:
        return None
    start = html.find("{", m.end())
    if start == -1:
        return None
    depth = 0
    i = start
    n = len(html)
    while i < n:
        skip = _skip_noncode(html, i)
        if skip is not None:
            i = skip
            continue
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
        i += 1
    return None


def _map_entries(body):
    """[(start, end)] offsets, into `body`, of every object literal
    nested exactly one brace level inside MAP's own outer object - one
    span per asset entry in `assets: [ {...}, {...} ]`, plus any other
    single-object field MAP happens to carry (e.g. `honesty: {...}`,
    `axes: {...}`). The extra spans are harmless: c17 only ever asks
    whether an asset CODE and its RANK co-occur in the same span, and no
    non-asset field carries either shape of text.

    This replaces a naive `re.split(r"}\\s*,", body)` chunker. That
    approach also breaks a single asset entry into fragments at any
    nested array's own '},' (`missing:[{x:...},{x:...}]` appears inside
    every entry in both example dashboards) - harmless ONLY because both
    real examples happen to write `code` and `rank` next to each other
    before any nested field. A dashboard that instead wrote a nested
    array field before `rank:` in one entry's own field order would have
    its rank split into a different fragment than its code, and the
    naive check would FAIL a genuinely faithful dashboard. Depth is
    tracked with the same _skip_noncode logic _map_body uses, so a
    string or comment inside an entry can't shift the count either.

    depth 1 is MAP's own outer object and is deliberately never
    captured as a span: doing so would make every code/rank pair
    trivially co-occur in "the whole document," defeating the pairing
    check entirely."""
    spans = []
    n = len(body)
    i = 0
    depth = 0
    entry_start = None
    while i < n:
        skip = _skip_noncode(body, i)
        if skip is not None:
            i = skip
            continue
        c = body[i]
        if c == "{":
            depth += 1
            if depth == 2:
                entry_start = i
        elif c == "}":
            if depth == 2 and entry_start is not None:
                spans.append((entry_start, i + 1))
                entry_start = None
            depth -= 1
        i += 1
    return spans


@check(17, "expected asset codes, ranks, and banner text present", "section 8.4/section 8.5")
def c17(ctx):
    """section 8.4/8.5 (partial): per-example data faithfulness, gated
    behind --expect.

    This is the one check in the file that asserts a dashboard carries
    SPECIFIC data rather than checking a structural or hygiene property
    every dashboard must share - so it only runs when the caller names
    which fixture to check against (EXPECTATIONS), and SKIPs otherwise
    rather than silently comparing against nothing.

    Ctx.js_state_at is not used here at all - it classifies JS lexical
    state for advisory notes on OTHER checks' findings, and has no
    bearing on locating or reading a data literal's own text. Nothing in
    this check may let it downgrade or suppress a finding; it is simply
    not part of this check's reasoning to begin with.

    Failure-direction discipline: an unknown --expect name is a FAIL
    naming the known fixtures (never a silent SKIP - a typo in the
    fixture name must not look like "nothing wrong here"); an
    unlocatable MAP is a FAIL with an explicit reason (never a PASS -
    inability to check is not evidence of correctness); a missing code,
    a code owning zero or more than one code: field, a wrong rank, or
    absent banner text are each their own FAIL line, capped at 10 like
    every other check in this file. The rank check requires the code's
    OWN code: field, in exactly one MAP entry, to carry the right rank -
    not just "the code and the rank both appear somewhere in one chunk"
    - because a decoy object anywhere else in MAP (a bogus assets[]
    entry, or an unrelated field) can otherwise vouch for a wrong real
    entry's rank; see _map_entries and this task's break-it notes."""
    name = "expected asset codes, ranks, and banner text present"
    rule = "section 8.4/section 8.5"
    if not ctx.expect:
        return Result(17, name, rule, SKIP, ["no --expect fixture given"])
    exp = EXPECTATIONS.get(ctx.expect)
    if exp is None:
        return Result(17, name, rule, FAIL,
                      ["unknown fixture %r; known: %s"
                       % (ctx.expect, ", ".join(sorted(EXPECTATIONS)))])
    body = _map_body(ctx.html)
    if body is None:
        return Result(17, name, rule, FAIL,
                      ["could not locate the MAP object literal to inspect"])
    problems = []
    for code in exp["codes"]:
        if code not in body:
            problems.append("asset code %s absent from MAP" % code)
    entries = [body[s:e] for s, e in _map_entries(body)]
    for code, rank in exp["ranks"].items():
        # A code must own its own `code:"X"` field in EXACTLY one entry -
        # not merely appear as a substring somewhere inside a chunk that
        # also happens to contain the right rank number. Checking for
        # co-occurrence alone (code in chunk AND rank pattern in chunk)
        # is fooled by a decoy: a second, unrelated object anywhere in
        # MAP that pairs the right code with the right rank (e.g. a
        # bogus extra `assets[]` entry, or an unrelated field elsewhere
        # in the object) makes that co-occurrence true even while the
        # REAL asset entry for that code carries a wrong rank -
        # confirmed empirically during this task's own break-it testing
        # (a genuinely unfaithful dashboard passed under the earlier,
        # co-occurrence-only version of this loop). Requiring the code's
        # OWN field, and requiring it to own exactly one, closes that:
        # zero owners is "code not found", more than one is itself a
        # faithfulness problem (a duplicated or decoy entry) and must
        # not be trusted for its rank either way.
        # Quote-matched alternation, like _STYLE_ATTR_RX elsewhere in this
        # file - never r'code\s*:\s*[\'"]%s[\'"]', which accepts a
        # MISMATCHED closing quote and would also match a single-quoted
        # code: field that happens to be followed by an unrelated double
        # quote later on the line. Both real examples write double
        # quotes, but nothing about being a faithful dashboard requires
        # that specific style, so a single-quoted code: field must still
        # count as this code's one true owner, not zero.
        esc = re.escape(code)
        code_rx = re.compile(r'code\s*:\s*(?:"%s"|\'%s\')' % (esc, esc))
        owners = [e for e in entries if code_rx.search(e)]
        if not owners:
            problems.append("%s is not recorded at rank %d" % (code, rank))
        elif len(owners) > 1:
            problems.append(
                "%s has its own code: field in %d MAP entries "
                "(expected exactly 1); its rank cannot be trusted"
                % (code, len(owners)))
        elif not re.search(r"rank\W+%d\b" % rank, owners[0]):
            problems.append("%s is not recorded at rank %d" % (code, rank))
    if exp["banner"] and exp["banner"] not in ctx.html:
        problems.append("binding-constraint text absent verbatim: %r"
                        % exp["banner"][:60])
    if problems:
        return Result(17, name, rule, FAIL, problems[:10])
    return Result(17, name, rule, PASS)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

# The fixture carries two deliberate false-positive traps: a multi-line
# tag inside a JS template literal, and a multi-line HTML comment holding
# lookalike markup. Neither is a live resource reference, so the
# "baseline trips 0 checks" assertion below is a standing regression test
# against a check that scans raw text with no idea which regions are
# actually markup. INJECTIONS only ever proves violations are caught;
# this is what proves legitimate content is not flagged.
FIXTURE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Self-Test Fixture</title>
<style>
:root{ --bg:#0d1117; --ink:#e6edf3; --mono:'IBM Plex Mono', ui-monospace, monospace; }
body{ background:var(--bg); color:var(--ink); font-family:var(--mono); }
</style>
</head>
<body>
<div id="app"></div>
<!--
reference only, not live:
<link href="https://cdn.example.com/also-documentation.css"
>
-->
<script>
var MAP = { assets: [ { code: "AAA-1", rank: 1 } ] };
function render(){ document.getElementById('app').textContent = MAP.assets[0].code; }
render();
const exampleEmbed = `<link
  href="https://cdn.example.com/documentation-only.css">`;
</script>
</body>
</html>
"""


def _inject_before(marker, snippet):
    def fn(html):
        return html.replace(marker, snippet + marker, 1)
    return fn


INJECTIONS = {
    16: ("markdown fence prepended",
         lambda html: "```html\n" + html,
         {16}),
}

INJECTIONS.update({
    1: ("script tag given type=module",
        lambda html: html.replace("<script>", '<script type="module">', 1),
        {1}),
    2: ("ES import statement in script body",
        _inject_before("var MAP =", 'import x from "./y.js";\n'),
        {2}),
    3: ("dynamic import() call",
        _inject_before("var MAP =", 'import("./y.js");\n'),
        {3}),
    4: ("fetch() call",
        _inject_before("var MAP =", 'fetch("/data.json");\n'),
        {4}),
    5: ("await expression",
        _inject_before("var MAP =", "await ready;\n"),
        {5}),
    6: ("external CDN script src",
        _inject_before("</head>",
                       '<script src="https://cdn.example.com/x.js"></script>\n'),
        {6, 7}),
    7: ("external non-fonts stylesheet, tag carries an unescaped '>' "
        "in an attribute before href (regression guard)",
        _inject_before("</head>",
                       '<link title="a>b" rel="stylesheet" '
                       'href="https://cdn.example.com/a.css">\n'),
        {7}),
    8: ("local relative stylesheet reference, tag carries an unescaped "
        "'>' in an attribute before href (regression guard)",
        _inject_before("</head>",
                       '<link title="a>b" rel="stylesheet" '
                       'href="./local.css">\n'),
        {8}),
    9: ("img src that is not a data: URI",
        _inject_before("</body>", '<img src="#" alt="x">\n'),
        {9}),
})

INJECTIONS.update({
    # Multi-line payload combining FOUR shapes that have each, in turn,
    # defeated an earlier version of check 10's live/not-live
    # disambiguation:
    #  1. a closed string immediately followed by a bare '/' (an earlier
    #     scanner bug misread this as opening a regex literal, which ran
    #     away and swallowed the assignment as non-code state);
    #  2. an apostrophe-bearing string before the assignment (defeated
    #     the original same-line quote-parity heuristic);
    #  3. a template literal with a SECOND ${...} interpolation whose
    #     leading token is regex-shaped ('${a} ${/['"]/.test(x)}') - the
    #     second interpolation's '/' inherited a stale last_code_char
    #     from the FIRST interpolation and was misread as division, so
    #     its own '[\'"]' opened a real string that ran away and
    #     swallowed a live assignment after it;
    #  4. a 'return' keyword immediately before a regex-shaped, quote-
    #     containing token ('return /['"]/.test(x);') - before keyword
    #     lookback existed, the identifier-ending 'n' in "return" made
    #     the '/' read as division, leaving '[\'"]' to be read as code
    #     and its own quote to open a real, unterminated string;
    #  5. a BLOCK statement's closing '}' immediately before a regex-
    #     shaped, quote-containing token on the next line ('if (true) {
    #     ... }' then '/['"]/.test(z);') - every '}' used to be read as
    #     "a value just closed," so that '/' was called division and the
    #     quote inside it opened a real string that ran away past the
    #     assignment below it.
    # This strengthens the input so a future regression in any of the
    # five mechanisms trips the self-test; it does not change what the
    # injection is supposed to prove, so the expected set stays {10}.
    #
    # Since check 10's lexer became advisory (see c10), the duplicate
    # assignment below trips the check on the RAW COUNT, and would do so
    # even if all five shapes above were mis-lexed. That is the point -
    # the payload is now a regression guard on the accuracy of the
    # advisory notes rather than on whether the violation is caught at
    # all, and it is deliberately kept for that. The expected set is
    # still {10}, and the self-test grades by severity worsening against
    # the baseline (_tripped), so this injection's PASS -> FAIL counts as
    # a trip exactly as its earlier PASS -> WARN -> FAIL did.
    10: ("second MAP object assignment, on lines combining a "
         "string-then-division token, an apostrophe-bearing string, "
         "a nested-template-interpolation regex literal, a "
         "keyword-preceding regex literal, and a block-close-then-regex "
         "literal (regression guard)",
         _inject_before(
             "function render()",
             "var ratio = \"a\" / 2; someFunc(\"don't\");\n"
             "var t = `${a} ${/['\"]/.test(x)} `;\n"
             "function ok(x){ return /['\"]/.test(x); }\n"
             "if (true) { someFunc(); }\n"
             "/['\"]/.test(z);\n"
             "var MAP = { assets: [] };\n"),
         {10}),
    11: ("hardcoded hex color outside :root",
         _inject_before("</style>", "h1{ color:#ff0000; }\n"),
         {11}),
})

INJECTIONS.update({
    12: ("call-to-action verb in body copy",
         _inject_before("</body>", "<p>Buy now and subscribe today.</p>\n"),
         {12}),
    13: ("reference-example vocabulary leak",
         _inject_before("</body>", "<p>homelab provisioning notes</p>\n"),
         {13}),
})

INJECTIONS.update({
    14: ("font-family with no generic fallback",
         _inject_before("</style>", "h2{ font-family:'Weird Font'; }\n"),
         {14}),
    15: ("render-blocking fonts stylesheet",
         _inject_before("</head>",
                        '<link rel="stylesheet" '
                        'href="https://fonts.googleapis.com/css2?family=X">\n'),
         {15}),
})

INJECTIONS.update({
    17: ("expected asset code removed from MAP",
         lambda html: html.replace('"AAA-1"', '"ZZZ-9"'),
         {17}),
})


def run_checks(ctx):
    return [fn(ctx) for _, _, _, fn in CHECKS]


_SEVERITY = {PASS: 0, SKIP: 0, WARN: 1, FAIL: 2}


def _statuses(html):
    # expect="selftest" is required so check 17 (gated on --expect) is
    # actually exercised by the self-test harness instead of permanently
    # SKIPping - see EXPECTATIONS['selftest'] and the c17 docstring.
    return dict((r.num, r.status)
                for r in run_checks(Ctx(html, "<self-test>", expect="selftest")))


def _tripped(html, baseline=None):
    """Check numbers whose status is worse on this document than on the
    baseline.

    The fixture is deliberately no longer all-PASS: it carries
    false-positive traps (a tag inside a JS template literal, a tag
    inside an HTML comment) that checks 7/8 are supposed to report at
    WARN. Grading an injection by the raw set of non-PASS checks would
    make every injection inherit those baseline WARNs, and no expected
    set could stay exact. Grading by what an injection makes *worse*
    keeps every expected set exact and, unlike widening each expected set
    by the baseline, still proves the WARN -> FAIL transition on the very
    checks this matters for."""
    base = baseline or {}
    worse = set()
    for num, status in _statuses(html).items():
        if _SEVERITY[status] > _SEVERITY.get(base.get(num, PASS), 0):
            worse.add(num)
    return worse


def self_test():
    print("verify.py --self-test")
    print("")
    ok = True
    base_results = run_checks(Ctx(FIXTURE, "<self-test>", expect="selftest"))
    base_fail = [r for r in base_results if r.status == FAIL]
    base_warn = [r for r in base_results if r.status == WARN]
    if base_fail:
        print("BASELINE NOT CLEAN: fixture FAILs checks %s"
              % sorted(r.num for r in base_fail))
        for r in base_fail:
            for d in r.details:
                print("    %s" % d)
        print("The synthetic fixture must produce no FAIL before injection")
        print("tests mean anything. Fix the fixture or the check.")
        return 1
    print("baseline: synthetic fixture produces 0 FAIL")
    if base_warn:
        print("")
        print("baseline WARN, expected: the fixture carries deliberate")
        print("false-positive traps - a tag inside a JS template literal and")
        print("a tag inside an HTML comment. Neither is live markup, so")
        print("neither may FAIL; both must stay visible rather than vanish.")
        for r in base_warn:
            print("  WARN %02d  %s" % (r.num, r.name))
            for d in r.details:
                print("           %s" % d)
    print("")
    baseline = dict((r.num, r.status) for r in base_results)
    registered = sorted(num for num, _, _, _ in CHECKS)
    proven = 0
    for num in registered:
        if num not in INJECTIONS:
            print("MISSING  %02d  no injection defined - check is unproven" % num)
            ok = False
            continue
        desc, transform, expected = INJECTIONS[num]
        actual = _tripped(transform(FIXTURE), baseline)
        if actual == expected:
            print("PROVEN   %02d  %s" % (num, desc))
            proven += 1
        else:
            print("BROKEN   %02d  %s" % (num, desc))
            print("             expected checks %s to worsen against the "
                  "baseline, got %s" % (sorted(expected), sorted(actual)))
            ok = False
    print("")
    print("%d/%d checks provably detect their violation"
          % (proven, len(registered)))
    return 0 if ok else 1


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def report(results, path):
    print("verify.py - %s" % path)
    print("")
    for r in sorted(results, key=lambda r: r.num):
        print("%-4s %02d  %s" % (r.status, r.num, r.name))
        for d in r.details:
            print("          %s" % d)
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print("")
    print("%d pass, %d fail, %d warn, %d skip" % (
        counts.get(PASS, 0), counts.get(FAIL, 0),
        counts.get(WARN, 0), counts.get(SKIP, 0)))
    print("")
    print("NOT CHECKED (needs a browser or human judgment):")
    for desc, rule in NOT_CHECKED:
        print("  - %-52s %s" % (desc, rule))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Mechanical acceptance checks for Command Center dashboards.")
    p.add_argument("dashboard", nargs="?", help="path to the generated HTML file")
    p.add_argument("--map", dest="map_path",
                   help="source map the dashboard was generated from; "
                        "enables check 13 to tell leakage from legitimate usage")
    p.add_argument("--reference", action="store_true",
                   help="suppress check 13; for examples/demo_dashboard.html, "
                        "which IS the reference example")
    p.add_argument("--expect", help="apply a named per-example fixture (check 17)")
    p.add_argument("--prompt", action="store_true",
                   help="emit a paste-ready model repair instruction instead of a report")
    p.add_argument("--self-test", dest="self_test", action="store_true",
                   help="prove each check detects its violation, then exit")
    args = p.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.dashboard:
        p.error("dashboard path is required unless --self-test is given")

    with open(args.dashboard, "r", encoding="utf-8") as fh:
        html = fh.read()
    map_text = None
    if args.map_path:
        with open(args.map_path, "r", encoding="utf-8") as fh:
            map_text = fh.read()

    ctx = Ctx(html, args.dashboard, map_text, args.reference, args.expect)
    results = run_checks(ctx)
    report(results, args.dashboard)
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
