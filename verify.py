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

_SCRIPT_TAG_RX = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)


def _offset_in_spans(offset, spans):
    return any(s <= offset < e for s, e in spans)


def _script_bodies(ctx):
    """[(start, end, region_kind)] for every <script>...</script> BODY
    found by a raw scan of ctx.html - deliberately unmasked, because a
    <script> tag can be found nested inside another live script's own
    text (a JS string or template literal constructing markup, the
    document.write() pattern checks 1/6/9 already treat as real) and
    that nesting is exactly what this function needs to see.

    region_kind is None when the tag's own opening '<script' sits in
    live markup - a genuinely live, executing script. Otherwise it is
    the masked-region kind ("script", "style" or "comment") that the
    tag's start offset falls in, from Ctx.region_kind_at: "script" for
    a tag built inside another script's JS string/template literal,
    "comment" for one sitting inside an HTML comment. Same idea as
    _masked_region_tags, at body-span granularity instead of per-tag.

    Caveat this function cannot resolve on its own: the body/close-tag
    pairing (like _mask_non_markup's own pairing) takes the FIRST
    </script> after an opening tag, so a <script>...</script>-shaped
    string sitting INSIDE an otherwise-live script body gets silently
    absorbed into that live body rather than split out as its own
    nested entry - the two are textually overlapping, not nested in any
    way a single open/close pairing can represent. c10 does not lean on
    region_kind alone for that case; see _looks_commented_or_quoted."""
    out = []
    for m in _SCRIPT_TAG_RX.finditer(ctx.html):
        out.append((m.start(1), m.end(1), ctx.region_kind_at(m.start())))
    return out


def _line_text_before(ctx, offset):
    """The text of offset's own physical line, from the line's start up
    to (not including) offset itself."""
    line_start = ctx.html.rfind("\n", 0, offset) + 1
    return ctx.html[line_start:offset]


def _looks_commented_or_quoted(before):
    """True if a match preceded on its own source line by this text is
    plausibly sitting inside a JS '//' line comment or a same-line
    quoted string/template literal.

    A same-line, quote-counting heuristic, not a JS parser - and
    deliberately scoped to a single line: checking only the text before
    the match on ITS OWN line means a wrong call affects just that one
    match's grading (WARN vs live), never blanks or swallows unrelated
    code elsewhere in the document the way a whole-document JS
    comment/string stripper could (a stray quote inside a regex literal,
    e.g. /['"]/text, would make a global stripper pair across everything
    that follows - this function cannot make that mistake because it
    never looks past the start of the current line)."""
    if "//" in before:
        return True
    return any(before.count(q) % 2 == 1 for q in ('"', "'", "`"))


@check(10, "exactly one MAP object assignment", "section 8.2")
def c10(ctx):
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
                soft_note(lineno, _REGION_LABEL[kind])
            elif _looks_commented_or_quoted(_line_text_before(ctx, abs_off)):
                soft_note(lineno, "a JS comment or string")
            else:
                live_hits.append((lineno, m.group(0)))
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
            # _looks_commented_or_quoted is a same-line quote-counting
            # heuristic, not a JS parser: ordinary prose in a comment
            # (an apostrophe in "don't", a URL's "//" before the real
            # declaration on the same line) can push the one genuine
            # live assignment into this bucket. Zero confirmed-live
            # hits is not the same claim as zero assignments existing
            # at all when something MAP-shaped was found; WARN and let
            # a human look, rather than FAIL a page that may be fine.
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
    10: ("second MAP object assignment",
         _inject_before("function render()", "var MAP = { assets: [] };\n"),
         {10}),
    11: ("hardcoded hex color outside :root",
         _inject_before("</style>", "h1{ color:#ff0000; }\n"),
         {11}),
})


def run_checks(ctx):
    return [fn(ctx) for _, _, _, fn in CHECKS]


_SEVERITY = {PASS: 0, SKIP: 0, WARN: 1, FAIL: 2}


def _statuses(html):
    return dict((r.num, r.status) for r in run_checks(Ctx(html, "<self-test>")))


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
    base_results = run_checks(Ctx(FIXTURE, "<self-test>"))
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
