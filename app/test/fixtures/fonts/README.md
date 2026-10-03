# Roboto test fixtures

These unmodified fonts are loaded by widget tests only to make text-layout
assertions reproducible across local machines and CI. They are not registered
in `pubspec.yaml` and are not bundled into the application runtime.

Source: Flutter stable 3.47.6, Flutter repository revision
`5fc346839b5d0eef006ed8404392afb4dfae428d`, tracked files under
`engine/src/flutter/txt/third_party/fonts/`:
[Roboto-Regular.ttf](https://github.com/flutter/flutter/blob/5fc346839b5d0eef006ed8404392afb4dfae428d/engine/src/flutter/txt/third_party/fonts/Roboto-Regular.ttf)
and
[Roboto-Medium.ttf](https://github.com/flutter/flutter/blob/5fc346839b5d0eef006ed8404392afb4dfae428d/engine/src/flutter/txt/third_party/fonts/Roboto-Medium.ttf).
The revision tree contains both paths. Their embedded font metadata identifies
Roboto 2.137 (2017), copyright 2011 Google Inc., and explicitly states Apache
License 2.0 with the license URL; the same full license text is supplied by the
pinned SDK as `bin/cache/artifacts/material_fonts/Roboto_LICENSE.txt` and copied
unchanged to `Roboto-LICENSE.txt` here. Thus the retained license applies to
these exact font files, not a similarly named newer font release.

| File | Bytes | SHA-256 |
|---|---:|---|
| `Roboto-Regular.ttf` | 171676 | `79e851404657dac2106b3d22ad256d47824a9a5765458edb72c9102a45816d95` |
| `Roboto-Medium.ttf` | 172064 | `f205cc511821ea56078a105557fcea6253129404d411c997e1866fbd006abb68` |
| `Roboto-LICENSE.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
