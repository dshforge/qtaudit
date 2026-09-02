# Qt migration audit: QSimpleScada (baseline)

**Prepared by:** Sun47 Microsystems  
**Date:** 2026-09-03  
**Subject:** `d:\sun47\designs\qt-migration-portfolio\baseline-qt5`

Phase 0 of the Sun47 migration procedure. Measured against the source tree. Figures are counts unless labelled as estimates.

---

## 1. Build system and toolchain

- Build system: **qmake** - 2 `.pro`/`.pri` files
- C++ standard declared: **none declared** (Qt 6 requires C++17)
- Qt version signals: none found in build files
- MSVC `/utf-8` passed: **no**

## 2. Size and composition

| Type | Files | Lines |
|---|---:|---:|
| C/C++ source and headers | 24 | 3,092 |
| QML | 0 | 0 |
| UI forms | 2 | 444 |
| **Total** | **26** | **3,536** |

## 3. Qt modules in use

`network qml quick quickwidgets widgets`

## 4. Removed and relocated API surface

| API | Occurrences | Files | Status | Replacement |
|---|---:|---:|---|---|
| `QTextStream::setCodec` | 2 | 1 | removed | setEncoding(QStringConverter::...) |

**Total: 2 call sites.**

> **This count is a lower bound, not a total.** The scan matches on names. An API can be reached without ever naming it - `QTextStream::setCodec` takes a `QTextCodec`, so a codebase can depend on a removed class while a search for that class returns nothing. We have hit this in our own work. Only a compile against Qt 6 produces the complete list, which is why the estimate below carries a contingency.

## 5. Source encoding risk

- Files with non-ASCII characters in string literals: **0**
- Build passes `/utf-8` to MSVC: **no**

No non-ASCII string literals found. Encoding risk is low.

## 6. Shared library exports

- Files using `Q_DECL_EXPORT` / `__declspec(dllexport)`: **0**
- `WINDOWS_EXPORT_ALL_SYMBOLS` set: **no**

No export macros found. If any target is a shared library, verify what it exports with `dumpbin /EXPORTS` before and after. A library that exports nothing still compiles and links cleanly - we have found exactly this in a production codebase.

## 7. Dependencies and tests

- Third-party packages referenced: none detected
- Test source files: **0**
- C++ types registered into QML: **0**

Each third-party dependency needs its own Qt 6 support checked. An unmaintained dependency can cost more than the migration it blocks.

## 8. Risk register

### Red

- **No automated tests found.** This is the single largest risk item. A migration without tests cannot be verified, only hoped for, and it changes the price.

### Amber

- qmake only. Expect the build system conversion to be the single largest phase of the work.
- No export macros (`Q_DECL_EXPORT`) found. If any target here is a shared library, check what it actually exports before and after; a library that exports nothing still builds.

## 9. Indicative sizing

- Codebase band: **small** (3,536 lines)
- Known API call sites to change: **2** (lower bound)
- Build system conversion required: **yes**
- Verification base: **none - price accordingly**

_No effort figure is given here. Effort depends on what the first compile against Qt 6 reveals, and quoting a number before that is guessing. The next step is a timeboxed trial compile, which is the smallest piece of work that turns this estimate into a plan._

---

Sun47 Microsystems LLP - office@sun47.in
