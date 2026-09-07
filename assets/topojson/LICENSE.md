# Topojson licence

`world_50m.json` is the world geometry at 50 m resolution that plotly.js
fetches for geo figures. The page serves it from this folder, through
the `topojsonURL` figure configuration, so that the activation map makes
no request to `cdn.plot.ly`.

| Field | Value |
|---|---|
| File | `world_50m.json`, 1,100,027 bytes |
| Retrieved from | https://cdn.plot.ly/world_50m.json on 7 September 2026 |
| sha256 | `8aca84b4376b3ad809cd6284bfec947434e57e61c565c525570f0639964c96bf` |
| Publisher | Plotly Technologies Inc., as part of plotly.js (`dist/topojson`), built from Natural Earth data |
| Licence | MIT (plotly.js); the underlying Natural Earth data are in the public domain |
| Bundled plotly.js | 4.0.0, as shipped in the `plotly` 7.0.0 Python package the app serves |

The file is byte-identical to the one the page fetched from the CDN
before this folder existed, so the map geometry is unchanged.

## plotly.js LICENSE

```
MIT License

Copyright (c) 2016-2024 Plotly Technologies Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```
