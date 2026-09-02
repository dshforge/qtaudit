#!/usr/bin/env python3
"""
qtaudit - Phase 0 migration audit for Qt codebases.

Sun47 Microsystems. Runs against a source tree and produces the written
report that opens a migration engagement.

    python qtaudit.py <path-to-source> [-o report.md] [--client "Name"]

Reads only. Never writes into the audited tree.
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import date

SOURCE_EXT = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}
QML_EXT = {".qml"}
UI_EXT = {".ui"}
SKIP_DIRS = {".git", "build", "build6", "release", "debug", "node_modules",
             ".vs", "__pycache__", "3rdparty", "third_party", "external"}

# Removed or relocated between Qt 5 and Qt 6. The comment is what we tell
# the client to do about it.
REMOVED_APIS = [
    (r"\bQRegExp\b",            "QRegExp",              "removed", "QRegularExpression, or Qt5Compat as an interim"),
    (r"\bQTextCodec\b",         "QTextCodec",           "moved",   "Qt5Compat module"),
    (r"\bsetCodec\s*\(",        "QTextStream::setCodec","removed", "setEncoding(QStringConverter::...)"),
    (r"\bQLinkedList\b",        "QLinkedList",          "removed", "std::list"),
    (r"\bQStringRef\b",         "QStringRef",           "removed", "QStringView"),
    (r"\bQDesktopWidget\b",     "QDesktopWidget",       "removed", "QScreen via QGuiApplication"),
    (r"\bQSignalMapper\b",      "QSignalMapper",        "deprecated", "lambdas connected directly"),
    (r"\binsertMulti\b",        "QHash/QMap::insertMulti", "removed", "QMultiHash / QMultiMap"),
    (r"\bqrand\b|\bqsrand\b",   "qrand / qsrand",       "removed", "QRandomGenerator"),
    (r"\btoTime_t\b|\bsetTime_t\b", "QDateTime::toTime_t", "removed", "toSecsSinceEpoch / fromSecsSinceEpoch"),
    (r"\bQScriptEngine\b|\bQScriptValue\b|\bQtScript\b", "QtScript", "removed", "QJSEngine"),
    (r"\bsetMargin\s*\(",       "QLayout::setMargin",   "removed", "setContentsMargins"),
    (r"\bQt::MidButton\b",      "Qt::MidButton",        "removed", "Qt::MiddleButton"),
    (r"\bQOpenGLWidget\b",      "QOpenGLWidget",        "moved",   "QtOpenGLWidgets module, link explicitly"),
    (r"\bQWheelEvent::delta\b|\.delta\s*\(\s*\)", "QWheelEvent::delta", "removed", "angleDelta()"),
    (r"\bQVariant::Type\b|\.type\s*\(\s*\)\s*==\s*QVariant", "QVariant::type", "deprecated", "typeId() / metaType()"),
    (r"\bQProcess::start\s*\(\s*\"", "QProcess::start(QString)", "removed", "start(program, arguments)"),
    (r"\bendl\b(?!\s*\()",      "endl (unqualified)",   "namespaced", "Qt::endl"),
    (r"\bflush\b(?=\s*;)",      "flush (unqualified)",  "namespaced", "Qt::flush"),
    (r"\bQ_FOREACH\b|\bforeach\s*\(", "Q_FOREACH / foreach", "deprecated", "range-based for"),
]

QT5_ONLY_MODULES = {"script", "scripttools", "winextras", "macextras",
                    "x11extras", "androidextras", "xmlpatterns",
                    "quick1", "webkit", "webkitwidgets"}


def walk_sources(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def read_text(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None, b""
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc), raw
        except UnicodeDecodeError:
            continue
    return None, raw


def scan(root):
    r = {
        "counts": Counter(), "lines": Counter(), "files": Counter(),
        "pro_files": [], "cmake_files": [], "qt_modules": set(),
        "api_hits": {}, "nonascii_files": [], "utf8_flag": False,
        "export_macro_files": [], "export_all_symbols": False,
        "third_party": set(), "test_files": 0, "qml_register": 0,
        "cxx_standard": None, "qt_version_hints": set(),
        "total_source_files": 0,
    }

    for path in walk_sources(root):
        rel = os.path.relpath(path, root)
        ext = os.path.splitext(path)[1].lower()
        base = os.path.basename(path).lower()

        is_build = ext in (".pro", ".pri", ".prf") or base == "cmakelists.txt" or ext == ".cmake"
        is_src = ext in SOURCE_EXT or ext in QML_EXT

        if not (is_build or is_src or ext in UI_EXT):
            continue

        text, raw = read_text(path)
        if text is None:
            continue

        nlines = text.count("\n") + 1

        if ext in SOURCE_EXT:
            r["files"]["source"] += 1; r["lines"]["source"] += nlines
            r["total_source_files"] += 1
        elif ext in QML_EXT:
            r["files"]["qml"] += 1; r["lines"]["qml"] += nlines
        elif ext in UI_EXT:
            r["files"]["ui"] += 1; r["lines"]["ui"] += nlines

        if "test" in rel.lower() and (ext in SOURCE_EXT):
            r["test_files"] += 1

        # ---- build files -------------------------------------------
        if ext in (".pro", ".pri", ".prf"):
            r["pro_files"].append(rel)
            for m in re.finditer(r"^\s*QT\s*[+*]?=\s*(.+)$", text, re.M):
                for mod in m.group(1).replace("\\", " ").split():
                    r["qt_modules"].add(mod.strip().lower())
            if "/utf-8" in text or "-finput-charset" in text:
                r["utf8_flag"] = True
            m = re.search(r"c\+\+(\d\d)", text)
            if m and not r["cxx_standard"]:
                r["cxx_standard"] = "C++" + m.group(1)

        if base == "cmakelists.txt" or ext == ".cmake":
            r["cmake_files"].append(rel)
            for m in re.finditer(r"COMPONENTS\s+([A-Za-z0-9_ \t]+)", text):
                for mod in m.group(1).split():
                    r["qt_modules"].add(mod.strip().lower())
            if re.search(r"qt_standard_project_setup", text) or "/utf-8" in text:
                r["utf8_flag"] = True     # qt_standard_project_setup adds /utf-8
            m = re.search(r"CMAKE_CXX_STANDARD\s+(\d\d)", text)
            if m:
                r["cxx_standard"] = "C++" + m.group(1)
            if "WINDOWS_EXPORT_ALL_SYMBOLS" in text:
                r["export_all_symbols"] = True
            for m in re.finditer(r"find_package\s*\(\s*([A-Za-z0-9_]+)", text):
                name = m.group(1)
                if name.lower() not in ("qt", "qt5", "qt6"):
                    r["third_party"].add(name)
            for m in re.finditer(r"pkg_check_modules\s*\(\s*[A-Za-z0-9_]+\s+([A-Za-z0-9_ ]+)", text):
                r["third_party"].update(m.group(1).split())
            if re.search(r"Qt6|find_package\s*\(\s*Qt6", text):
                r["qt_version_hints"].add("Qt6")
            if re.search(r"Qt5::|find_package\s*\(\s*Qt5", text):
                r["qt_version_hints"].add("Qt5")

        # ---- source scanning ---------------------------------------
        if is_src:
            for pattern, name, kind, fix in REMOVED_APIS:
                n = len(re.findall(pattern, text))
                if n:
                    e = r["api_hits"].setdefault(name, {"count": 0, "files": set(),
                                                        "kind": kind, "fix": fix})
                    e["count"] += n
                    e["files"].add(rel)
            if re.search(r"Q_DECL_EXPORT|Q_DECL_IMPORT|__declspec\s*\(\s*dllexport", text):
                r["export_macro_files"].append(rel)
            r["qml_register"] += len(re.findall(r"qmlRegisterType|QML_ELEMENT|QML_NAMED_ELEMENT", text))
            # non-ASCII inside string literals is the encoding risk
            for lit in re.findall(r'"(?:[^"\\n]|\.)*"', text):
                if any(ord(ch) > 127 for ch in lit):
                    r["nonascii_files"].append(rel)
                    break
    return r


def risk_rating(r):
    reds, ambers = [], []

    if r["test_files"] == 0:
        reds.append("**No automated tests found.** This is the single largest risk "
                    "item. A migration without tests cannot be verified, only hoped "
                    "for, and it changes the price.")
    elif r["test_files"] < 10:
        ambers.append(f"Only {r['test_files']} test source files. Thin coverage for a "
                      "codebase of this size.")

    qt5_mods = sorted(r["qt_modules"] & QT5_ONLY_MODULES)
    if qt5_mods:
        reds.append("Qt 5-only modules in use: **" + ", ".join(qt5_mods) +
                    "**. These have no Qt 6 equivalent and need replacing, not porting.")

    if "webengine" in r["qt_modules"] or "webkit" in r["qt_modules"]:
        reds.append("Qt WebEngine/WebKit present. Historically the most painful part "
                    "of any Qt migration; budget for it separately.")

    if r["qml_register"] > 0:
        ambers.append(f"{r['qml_register']} C++ types registered into QML. The "
                      "C++/QML boundary needs per-type review; registration macros changed in Qt 6.")

    if r["pro_files"] and not r["cmake_files"]:
        ambers.append("qmake only. Expect the build system conversion to be the "
                      "single largest phase of the work.")

    if r["nonascii_files"] and not r["utf8_flag"]:
        reds.append("**Non-ASCII characters in string literals, and the build does "
                    "not pass `/utf-8`.** Moving this build to CMake will silently "
                    "change how those literals are interpreted. See the encoding "
                    "section below - this is the defect that does not show up in any "
                    "code diff.")

    if not r["export_macro_files"] and r["pro_files"]:
        ambers.append("No export macros (`Q_DECL_EXPORT`) found. If any target here "
                      "is a shared library, check what it actually exports before "
                      "and after; a library that exports nothing still builds.")

    return reds, ambers


def report(r, root, client):
    L = []
    A = L.append
    total_lines = r["lines"]["source"] + r["lines"]["qml"] + r["lines"]["ui"]

    A(f"# Qt migration audit{': ' + client if client else ''}")
    A("")
    A(f"**Prepared by:** Sun47 Microsystems  ")
    A(f"**Date:** {date.today().isoformat()}  ")
    A(f"**Subject:** `{os.path.abspath(root)}`")
    A("")
    A("Phase 0 of the Sun47 migration procedure. Measured against the source "
      "tree. Figures are counts unless labelled as estimates.")
    A("")
    A("---")
    A("")

    # ---- 1 build system -------------------------------------------
    A("## 1. Build system and toolchain")
    A("")
    if r["pro_files"] and r["cmake_files"]:
        bs = f"**Both** - {len(r['pro_files'])} qmake files and {len(r['cmake_files'])} CMake files"
    elif r["pro_files"]:
        bs = f"**qmake** - {len(r['pro_files'])} `.pro`/`.pri` files"
    elif r["cmake_files"]:
        bs = f"**CMake** - {len(r['cmake_files'])} `CMakeLists.txt`"
    else:
        bs = "**Not detected**"
    A(f"- Build system: {bs}")
    A(f"- C++ standard declared: {r['cxx_standard'] or '**none declared** (Qt 6 requires C++17)'}")
    A(f"- Qt version signals: {', '.join(sorted(r['qt_version_hints'])) or 'none found in build files'}")
    A(f"- MSVC `/utf-8` passed: {'yes' if r['utf8_flag'] else '**no**'}")
    A("")

    # ---- 2 size ----------------------------------------------------
    A("## 2. Size and composition")
    A("")
    A("| Type | Files | Lines |")
    A("|---|---:|---:|")
    A(f"| C/C++ source and headers | {r['files']['source']} | {r['lines']['source']:,} |")
    A(f"| QML | {r['files']['qml']} | {r['lines']['qml']:,} |")
    A(f"| UI forms | {r['files']['ui']} | {r['lines']['ui']:,} |")
    A(f"| **Total** | **{sum(r['files'].values())}** | **{total_lines:,}** |")
    A("")
    return L, total_lines


def report_rest(L, r, total_lines):
    A = L.append

    # ---- 3 modules -------------------------------------------------
    A("## 3. Qt modules in use")
    A("")
    mods = sorted(r["qt_modules"])
    A("`" + " ".join(mods) + "`" if mods else "_None detected in build files._")
    A("")
    qt5_only = sorted(r["qt_modules"] & QT5_ONLY_MODULES)
    if qt5_only:
        A(f"**Qt 5-only:** `{' '.join(qt5_only)}` - no Qt 6 equivalent.")
        A("")

    # ---- 4 API surface ---------------------------------------------
    A("## 4. Removed and relocated API surface")
    A("")
    if r["api_hits"]:
        A("| API | Occurrences | Files | Status | Replacement |")
        A("|---|---:|---:|---|---|")
        for name, e in sorted(r["api_hits"].items(), key=lambda kv: -kv[1]["count"]):
            A(f"| `{name}` | {e['count']} | {len(e['files'])} | {e['kind']} | {e['fix']} |")
        total = sum(e["count"] for e in r["api_hits"].values())
        A("")
        A(f"**Total: {total} call sites.**")
    else:
        A("No removed or relocated APIs matched.")
    A("")
    A("> **This count is a lower bound, not a total.** The scan matches on names. "
      "An API can be reached without ever naming it - `QTextStream::setCodec` takes "
      "a `QTextCodec`, so a codebase can depend on a removed class while a search "
      "for that class returns nothing. We have hit this in our own work. Only a "
      "compile against Qt 6 produces the complete list, which is why the estimate "
      "below carries a contingency.")
    A("")

    # ---- 5 encoding -------------------------------------------------
    A("## 5. Source encoding risk")
    A("")
    n = len(set(r["nonascii_files"]))
    A(f"- Files with non-ASCII characters in string literals: **{n}**")
    A(f"- Build passes `/utf-8` to MSVC: **{'yes' if r['utf8_flag'] else 'no'}**")
    A("")
    if n and not r["utf8_flag"]:
        A("**This is a live defect risk, and it is the one most migrations miss.**")
        A("")
        A("Qt 6's `qt_standard_project_setup()` passes `/utf-8` to MSVC. qmake "
          "typically does not. Where the current build reads source in the system "
          "codepage, non-ASCII literals - degree symbols in unit labels, accented "
          "names, Devanagari or CJK UI text - are mangled at compile time. Moving "
          "to CMake fixes that, which means **the program's output changes with no "
          "corresponding change in the application code.**")
        A("")
        A("It is an improvement. It is also a behavioural change, and if anything "
          "downstream parses those strings or reads files written by the old build, "
          "it needs to be planned rather than discovered.")
    elif n:
        A("Non-ASCII literals present, but the build already passes `/utf-8`. "
          "Encoding behaviour should carry across unchanged. Worth one verification "
          "test regardless.")
    else:
        A("No non-ASCII string literals found. Encoding risk is low.")
    A("")

    # ---- 6 libraries -----------------------------------------------
    A("## 6. Shared library exports")
    A("")
    A(f"- Files using `Q_DECL_EXPORT` / `__declspec(dllexport)`: **{len(r['export_macro_files'])}**")
    A(f"- `WINDOWS_EXPORT_ALL_SYMBOLS` set: **{'yes' if r['export_all_symbols'] else 'no'}**")
    A("")
    if not r["export_macro_files"]:
        A("No export macros found. If any target is a shared library, verify what it "
          "exports with `dumpbin /EXPORTS` before and after. A library that exports "
          "nothing still compiles and links cleanly - we have found exactly this in "
          "a production codebase.")
        A("")

    # ---- 7 deps and tests ------------------------------------------
    A("## 7. Dependencies and tests")
    A("")
    A(f"- Third-party packages referenced: {', '.join(sorted(r['third_party'])) or 'none detected'}")
    A(f"- Test source files: **{r['test_files']}**")
    A(f"- C++ types registered into QML: **{r['qml_register']}**")
    A("")
    A("Each third-party dependency needs its own Qt 6 support checked. An "
      "unmaintained dependency can cost more than the migration it blocks.")
    A("")

    # ---- 8 risk ----------------------------------------------------
    reds, ambers = risk_rating(r)
    A("## 8. Risk register")
    A("")
    if reds:
        A("### Red")
        A("")
        for x in reds:
            A(f"- {x}")
        A("")
    if ambers:
        A("### Amber")
        A("")
        for x in ambers:
            A(f"- {x}")
        A("")
    if not reds and not ambers:
        A("No red or amber items raised by the automated scan.")
        A("")

    # ---- 9 sizing --------------------------------------------------
    A("## 9. Indicative sizing")
    A("")
    api_total = sum(e["count"] for e in r["api_hits"].values())
    band = ("small" if total_lines < 20000 else
            "medium" if total_lines < 150000 else "large")
    A(f"- Codebase band: **{band}** ({total_lines:,} lines)")
    A(f"- Known API call sites to change: **{api_total}** (lower bound)")
    A(f"- Build system conversion required: **{'yes' if r['pro_files'] and not r['cmake_files'] else 'no'}**")
    A(f"- Verification base: **{'none - price accordingly' if r['test_files']==0 else str(r['test_files']) + ' test files'}**")
    A("")
    A("_No effort figure is given here. Effort depends on what the first compile "
      "against Qt 6 reveals, and quoting a number before that is guessing. The "
      "next step is a timeboxed trial compile, which is the smallest piece of work "
      "that turns this estimate into a plan._")
    A("")
    A("---")
    A("")
    A("Sun47 Microsystems LLP - office@sun47.in")
    return L


def main():
    ap = argparse.ArgumentParser(description="Phase 0 Qt migration audit")
    ap.add_argument("path")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--client", default=None)
    a = ap.parse_args()

    if not os.path.isdir(a.path):
        sys.exit(f"not a directory: {a.path}")

    r = scan(a.path)
    L, total = report(r, a.path, a.client)
    L = report_rest(L, r, total)
    text = "\n".join(L) + "\n"

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"written: {a.out}  ({total:,} lines audited)")
    else:
        print(text)


if __name__ == "__main__":
    main()
