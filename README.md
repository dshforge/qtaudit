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
9. Indicative sizing - deliberately with no effort figure

## The two checks nobody else runs

**Encoding.** Qt 6's `qt_standard_project_setup()` passes `/utf-8` to
MSVC; qmake usually does not. Where a codebase has non-ASCII string
literals and the current build lacks that flag, moving to CMake changes
how those literals are interpreted - the program's output changes with
no corresponding change in application code. We found this in our own
migration, by measuring, and it does not appear in any API diff.

**Exports.** A shared library with no export macros compiles, links, and
exports nothing. We found exactly that in a real project. The tool
flags it so it is checked with `dumpbin /EXPORTS` before and after.

## The honesty rule built into the output

Every report states that the API count is a **lower bound, not a
total**, and says why: an API can be reached without ever naming it.
`QTextStream::setCodec` takes a `QTextCodec`, so a codebase can depend
on a removed class while a search for that class returns nothing. We hit
this ourselves - grep found zero, the compiler found two.

An audit that implies its number is complete is the inflated precision
that costs credibility with industrial clients. This one says what it
cannot see.

## No effort estimate, on purpose

Section 9 sizes the job but gives no hours. Effort depends on what the
first compile against Qt 6 reveals, and quoting before that is guessing.
The recommended next step is a timeboxed trial compile - the smallest
piece of work that turns the estimate into a plan, and the natural first
paid engagement.

## Validated against

| Codebase | Lines | Result |
|---|---:|---|
| QSimpleScada (Qt 5, qmake) | 3,536 | Found `setCodec` x2 in 1 file - matches what the compiler found |
| QLC+ (dual Qt5/Qt6, CMake) | 395,310 | Flagged `script` as Qt 5-only (red), 19 QML registrations (amber), correctly found the test suite |

Sample outputs: [`sample-qsimplescada.md`](sample-qsimplescada.md),
[`sample-qlcplus.md`](sample-qlcplus.md)
