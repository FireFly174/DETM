# DETM Book (EN v2, draft)

This folder contains the English v2 draft of the DETM book.

Status:
- Draft translation/adaptation.
- Terminology aligned with canonical docs (`docs/eng/*`, `docs/rus/ROADMAP.md`).
- Designed for fast reading and practical navigation.

Important:
- `_compiled_v2*.md`, `_compiled_v2*.html`, `_compiled_v2*.pdf` are generated artifacts.
- Do not edit compiled files directly; edit source chapters/manifests and rebuild.
- Shared build notes: `docs/book/README_BUILD.md`.

Build:
- Full: `tools\\compile_book_en_v2.cmd`
- Quick: `tools\\compile_book_en_v2.cmd draft quick`
- Print-oriented markdown: `tools\\compile_book_en_v2.cmd print`
- Render HTML/PDF from compiled markdown: `tools\\render_book_en_v2.cmd print`
- Full export (compile + render): `tools\\export_book_en_v2.cmd print`

Outputs:
- `docs/book/en_v2/_compiled_v2.md`
- `docs/book/en_v2/_compiled_v2_quick.md`
- print variants with `_print` suffix
