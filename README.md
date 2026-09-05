# qtaudit

Phase 0 migration audit for Qt codebases. Sun47 Microsystems.

Point it at a source tree, get the written report that opens a
migration engagement. Read-only; it never writes into the audited tree.

```
python qtaudit.py /path/to/their/source --client "Acme GmbH" -o acme-audit.md
```

Python 3, standard library only. No install, nothing to build. Runs on
the prospect's machine if they will not let the source leave the
building - which industrial clients often will not, and being able to
say "then run it yourself, it is 400 lines and you can read it" is
worth more than the report.

## What it reports

1. Build system, C++ standard, Qt version signals, `/utf-8` flag
2. Size and composition
3. Qt modules, with Qt 5-only modules called out
4. Removed and relocated API surface, per call site
5. **Source encoding risk**
6. **Shared library export check**
7. Third-party dependencies, tests, C++/QML boundary
8. Risk register, red and amber
9. Indicative sizing, with no hours attached

## The two checks nobody else runs

**Encoding.** Qt 6's `qt_standard_project_setup()` passes `/utf-8` to
MSVC; qmake usually does not. Where a codebase has non-ASCII string
literals and the current build lacks that flag, moving to CMake changes
how those literals are interpreted, so the program's output changes with
no corresponding change in application code. It shows up on a byte
comparison and nowhere in an API diff.

**Exports.** A shared library with no export macros compiles, links, and
exports nothing, and every stage of the build says it is fine. The tool
flags the library so it is checked with `dumpbin /EXPORTS` before and after.

## The API count is a floor

An API can be reached without ever being named. `QTextStream::setCodec`
takes a `QTextCodec`, so a codebase can depend on a removed class while a
search for that class comes back empty: zero hits from grep, two from the
compiler.

Which is why every report labels its count a floor, and why the number
that matters comes from a compile against Qt 6.

## Sizing, not guesswork

Section 9 sizes the job against what the first Qt 6 compile turns up,
and asks for a timeboxed trial compile to get it. That is the smallest
piece of work that turns an estimate into a plan.

## Validated against

| Codebase | Lines | Result |
|---|---:|---|
| QSimpleScada (Qt 5, qmake) | 3,536 | Found `setCodec` x2 in 1 file - matches what the compiler found |
| QLC+ (dual Qt5/Qt6, CMake) | 395,310 | Flagged `script` as Qt 5-only (red), 19 QML registrations (amber), correctly found the test suite |

Sample outputs: [`sample-qsimplescada.md`](sample-qsimplescada.md),
[`sample-qlcplus.md`](sample-qlcplus.md)
