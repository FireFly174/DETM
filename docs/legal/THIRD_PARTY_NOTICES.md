# Third-Party Notices

This project depends on third-party packages with their own licenses.

Core package dependencies in `pyproject.toml`:

- `numpy` (BSD-style, see package metadata)
- `msgpack` (Apache-2.0)

Additional runtime/UI and analysis dependencies in `requirements.txt`:

- `torch` (BSD-style, see package metadata)
- `napari` (BSD-style, see package metadata)
- `qtpy` (BSD-style, see package metadata)
- `pyside6` (LGPL/commercial dual model by Qt, see package metadata and Qt terms)
- `PyYAML` (MIT-style, see package metadata)
- `matplotlib` (PSF-based matplotlib license, see package metadata)

Optional dependency group in `pyproject.toml`:

- `torch` (BSD-style, see package metadata)

Notes:

- This list describes direct dependencies declared by the project.
- Transitive dependencies are not fully enumerated in this file.
- For redistribution/commercial packaging, verify exact license texts for the
  resolved dependency set in your lock/build environment.

You are responsible for compliance with third-party license terms in your distribution and deployment model.
