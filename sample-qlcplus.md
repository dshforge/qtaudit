# Qt migration audit: QLC+

**Prepared by:** Sun47 Microsystems  
**Date:** 2026-09-03  
**Subject:** `C:\Users\dilsh\AppData\Local\Temp\claude\d--sun47-designs\11f7fc3d-389d-464f-a387-78ae9247d809\scratchpad\qlcplus`

Phase 0 of the Sun47 migration procedure. Measured against the source tree. Figures are counts unless labelled as estimates.

---

## 1. Build system and toolchain

- Build system: **CMake** - 174 `CMakeLists.txt`
- C++ standard declared: **none declared** (Qt 6 requires C++17)
- Qt version signals: Qt6
- MSVC `/utf-8` passed: yes

## 2. Size and composition

| Type | Files | Lines |
|---|---:|---:|
| C/C++ source and headers | 1039 | 309,851 |
| QML | 251 | 64,254 |
| UI forms | 67 | 21,205 |
| **Total** | **1357** | **395,310** |

## 3. Qt modules in use

`3dcore 3dinput 3dlogic 3dquick 3dquickextras 3drender concurrent core gui linguisttools multimedia multimediawidgets network opengl printsupport qml quick script serialport svg test websockets widgets`

**Qt 5-only:** `script` - no Qt 6 equivalent.

## 4. Removed and relocated API surface

| API | Occurrences | Files | Status | Replacement |
|---|---:|---:|---|---|
| `Q_FOREACH / foreach` | 613 | 167 | deprecated | range-based for |
| `endl (unqualified)` | 52 | 6 | namespaced | Qt::endl |
| `QtScript` | 46 | 2 | removed | QJSEngine |
| `QTextStream::setCodec` | 9 | 9 | removed | setEncoding(QStringConverter::...) |
| `qrand / qsrand` | 4 | 4 | removed | QRandomGenerator |
| `QRegExp` | 4 | 2 | removed | QRegularExpression, or Qt5Compat as an interim |
| `QLayout::setMargin` | 2 | 2 | removed | setContentsMargins |
| `QVariant::type` | 1 | 1 | deprecated | typeId() / metaType() |

**Total: 731 call sites.**

> **This count is a lower bound, not a total.** The scan matches on names. An API can be reached without ever naming it - `QTextStream::setCodec` takes a `QTextCodec`, so a codebase can depend on a removed class while a search for that class returns nothing. We have hit this in our own work. Only a compile against Qt 6 produces the complete list, which is why the estimate below carries a contingency.

## 5. Source encoding risk

- Files with non-ASCII characters in string literals: **34**
- Build passes `/utf-8` to MSVC: **yes**

Non-ASCII literals present, but the build already passes `/utf-8`. Encoding behaviour should carry across unchanged. Worth one verification test regardless.

## 6. Shared library exports

- Files using `Q_DECL_EXPORT` / `__declspec(dllexport)`: **2**
- `WINDOWS_EXPORT_ALL_SYMBOLS` set: **no**

## 7. Dependencies and tests

- Third-party packages referenced: IMPORTED_TARGET, PkgConfig, alsa, fftw3, libftdi, libftdi1, libgpiodcxx, libola, libolaserver, libusb, mad, portaudio, sndfile
- Test source files: **210**
- C++ types registered into QML: **19**

Each third-party dependency needs its own Qt 6 support checked. An unmaintained dependency can cost more than the migration it blocks.

## 8. Risk register

### Red

- Qt 5-only modules in use: **script**. These have no Qt 6 equivalent and need replacing, not porting.

### Amber

- 19 C++ types registered into QML. The C++/QML boundary needs per-type review; registration macros changed in Qt 6.

## 9. Indicative sizing

- Codebase band: **large** (395,310 lines)
- Known API call sites to change: **731** (lower bound)
- Build system conversion required: **no**
- Verification base: **210 test files**

_No effort figure is given here. Effort depends on what the first compile against Qt 6 reveals, and quoting a number before that is guessing. The next step is a timeboxed trial compile, which is the smallest piece of work that turns this estimate into a plan._

---

Sun47 Microsystems LLP - office@sun47.in
