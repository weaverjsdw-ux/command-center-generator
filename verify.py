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
    """
    pieces = []
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
        elif m.group(1).lower() in _MASKED_ELEMENTS:
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
        kept = blank_to
    pieces.append(html[kept:])
    return "".join(pieces)


class Ctx:
    def __init__(self, html, path, map_text=None, reference=False, expect=None):
        self.html = html
        self.path = path
        self.lines = html.splitlines()
        self.map_text = map_text
        self.reference = reference
        self.expect = expect
        self._masked = None

    def masked_html(self):
        """self.html with non-markup regions blanked out (see
        _mask_non_markup). Computed once and cached: it is O(document) to
        build and more than one check scans it."""
        if self._masked is None:
            self._masked = _mask_non_markup(self.html)
        return self._masked

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


def _all_tags(ctx):
    """Yield (lineno, tag_name_lower, tag_text) for every opening tag in
    the document's *markup* regions.

    Two properties, each of which a previous shape of this function got
    wrong:

    - Matching runs over the whole document text, not line-by-line: a tag
      whose closing '>' lands on a physical line different from its '<'
      is ordinary, valid HTML (attribute values wrap), and a per-line
      scan would silently never see it as one tag at all.

    - Matching runs over the *masked* document, so tag-shaped text inside
      a <script> body, a <style> body or an HTML comment is not mistaken
      for a live resource reference. Line numbers are still counted
      against ctx.html, which is exact because masking is
      offset-preserving.
    """
    for m in _TAG_RX.finditer(ctx.masked_html()):
        lineno = ctx.html.count("\n", 0, m.start()) + 1
        yield lineno, m.group(1).lower(), m.group(0)


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


def _external_refs(ctx):
    """Return [(lineno, url, is_link_tag)] for every http(s) resource ref.
    Tag matching is document-wide (via _all_tags), so a <link>/<script>
    tag whose attributes wrap onto a second line is still recognized as
    one tag, and per-tag rather than per-line, so an <a href> sharing
    text with a <link>/<script>/<img> can't hide or absorb the other's
    reference."""
    out = []
    attr_rx = re.compile(r"""(?:src|href)\s*=\s*['"](https?://[^'"]+)['"]""",
                         re.I)
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        attr_m = attr_rx.search(tag_text)
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


def _fonts_links(ctx):
    return [(n, u, is_link) for n, u, is_link in _external_refs(ctx)
            if is_link and _is_font_host(u)]


@check(7, "at most one external ref, and it must be a fonts stylesheet",
       "section 7/section 6.6")
def c07(ctx):
    name = "at most one external ref, and it must be a fonts stylesheet"
    rule = "section 7/section 6.6"
    refs = _external_refs(ctx)
    fonts = _fonts_links(ctx)
    problems = []
    for n, url, _ in refs:
        if not _is_font_host(url):
            problems.append("line %d: external resource %s" % (n, url[:100]))
    if len(fonts) > 1:
        problems.append("%d fonts stylesheets; section 7 sanctions one" % len(fonts))
    if problems:
        return Result(7, name, rule, FAIL, problems)
    return Result(7, name, rule, PASS)


def _local_ref_tags(ctx):
    """Yield (lineno, tag_text) for every non-anchor tag carrying a local
    src=/href=, document-wide (via _all_tags) so a tag whose attributes
    wrap onto a second line is still recognized as one tag, and per-tag
    so an <a href> sharing text with a real local <link>/<script>/<img>
    can't hide or falsely absorb it."""
    local_attr_rx = re.compile(
        r"""(?:src|href)\s*=\s*['"](?:\./|\.\./|/)[^'"]""")
    for lineno, tag_name, tag_text in _all_tags(ctx):
        if tag_name == "a":
            continue  # anchors are navigation, not resource loads
        if local_attr_rx.search(tag_text):
            yield lineno, tag_text


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
    return fail_on_hits(8, name, rule, sorted(hits.items()))


@check(9, "every <img src=> is a data: URI", "section 7")
def c09(ctx):
    name = "every <img src=> is a data: URI"
    rule = "section 7"
    hits = []
    for i, ln in enumerate(ctx.lines):
        for m in re.finditer(r"""<img[^>]*\ssrc\s*=\s*['"]([^'"]*)['"]""",
                             ln, re.I):
            if not m.group(1).startswith("data:"):
                hits.append((i + 1, ln))
    return fail_on_hits(9, name, rule, hits)


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


def run_checks(ctx):
    return [fn(ctx) for _, _, _, fn in CHECKS]


def _tripped(html):
    ctx = Ctx(html, "<self-test>")
    return set(r.num for r in run_checks(ctx) if r.status in (FAIL, WARN))


def self_test():
    baseline = _tripped(FIXTURE)
    print("verify.py --self-test")
    print("")
    ok = True
    if baseline:
        print("BASELINE NOT CLEAN: fixture trips checks %s" % sorted(baseline))
        print("The synthetic fixture must pass every check before injection")
        print("tests mean anything. Fix the fixture or the check.")
        return 1
    print("baseline: synthetic fixture trips 0 checks")
    print("")
    registered = sorted(num for num, _, _, _ in CHECKS)
    proven = 0
    for num in registered:
        if num not in INJECTIONS:
            print("MISSING  %02d  no injection defined - check is unproven" % num)
            ok = False
            continue
        desc, transform, expected = INJECTIONS[num]
        actual = _tripped(transform(FIXTURE))
        if actual == expected:
            print("PROVEN   %02d  %s" % (num, desc))
            proven += 1
        else:
            print("BROKEN   %02d  %s" % (num, desc))
            print("             expected checks %s to trip, got %s"
                  % (sorted(expected), sorted(actual)))
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
