# Third-party notices

## Community Sungrow register profile

The register addresses and measurement definitions in
`addon/sungrow_sunspec/profiles/sh25t_shb.community.json` are derived from:

> Sungrow-SHx-Inverter-Modbus-Home-Assistant by mkaiser (MIT) —
> <https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant>.
> Source revision: `071f8c8c5f784198928f80de23ae168eed1acd1d`, file
> `modbus_sungrow.yaml`.

The SunSpec model 203 meter point layout follows the official SunSpec Models
repository, [`json/model_203.json`](https://github.com/SunSpec/models/blob/90b4a331dcca1d6eac69c1bead952fddcc5852e0/json/model_203.json).

The upstream project identifies the SH25T model code and contains SH*T
three-MPPT definitions. Its README/attribution document explains that many
registers are community-measured, not copied from a Sungrow datasheet. This
profile is therefore marked unverified for a specific SH25T, SHB battery, and
firmware combination. Preserve this attribution when redistributing the
derived register profile.

Copyright (c) 2025 Martin Kaiser

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
