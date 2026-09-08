/* El Niño Atlas client script.
 *
 * Dash serves this file with the page. It carries the clientside
 * callbacks the app registers (window.dash_clientside.atlas), the URL
 * state codec that mirrors src/layout/viewstate.py, the colour-scheme
 * switch for the Plotly figures, the figure exports, and small keyboard
 * shims for the Plotly mode bar and legend. No request leaves the page.
 */
(function () {
  "use strict";

  var dc = (window.dash_clientside = window.dash_clientside || {});
  /* Graph keys, shared with the URL grammar and every control id. */
  var GRAPHS = { index: "graph-index", prices: "graph-commodities" };
  var MAP_ID = "activations-map";
  var RANGE_SUFFIX = "_range";
  var BANDS_SUFFIX = "_bands";
  var RANGE_ALL = "all";
  var SERIES_SEPARATOR = "|";
  var THEME_KEY = "theme-store";
  var STATE_ORDER = ["not_assessed", "no_alert", "alert"];
  /* Dash redraws a figure from its stored copy after the first interaction
     it reports; the redraw can undo a state applied moments earlier, so the
     applier checks its work after a short settle and applies again. */
  var SETTLE_MS = 600;
  var MAX_PASSES = 3;
  /* Each state application takes a sequence number; an application that a
     newer state has superseded stops before its next pass, so the initial
     default state never fights the state parsed from the URL. */
  var applySeq = 0;

  function keys() {
    return Object.keys(GRAPHS);
  }

  function keyForGraph(id) {
    var found = null;
    keys().forEach(function (key) {
      if (GRAPHS[key] === id) found = key;
    });
    return found;
  }

  /* ------------------------------------------------------------ codec */

  function isoDate(text) {
    var match = /^(\d{4}-\d{2}-\d{2})/.exec(String(text).trim());
    if (!match) return null;
    var parsed = new Date(match[1] + "T00:00:00Z");
    return isNaN(parsed.getTime()) ? null : match[1];
  }

  function defaultGraphState() {
    return { range: null, bands: true, series: null };
  }

  function defaultState() {
    var state = {};
    keys().forEach(function (key) {
      state[key] = defaultGraphState();
    });
    return state;
  }

  function parseRange(value) {
    if (value === RANGE_ALL) return RANGE_ALL;
    var parts = value.split(",");
    if (parts.length === 2) {
      var start = isoDate(decodeURIComponent(parts[0]));
      var end = isoDate(decodeURIComponent(parts[1]));
      if (start && end && start < end) return [start, end];
    }
    return null;
  }

  function parseSearch(search) {
    var state = defaultState();
    var query = search && search.charAt(0) === "?" ? search.slice(1) : search || "";
    query.split("&").forEach(function (pair) {
      if (!pair) return;
      var eq = pair.indexOf("=");
      var key = eq < 0 ? pair : pair.slice(0, eq);
      var value = eq < 0 ? "" : pair.slice(eq + 1);
      keys().forEach(function (graph) {
        if (key === graph + RANGE_SUFFIX) {
          state[graph].range = parseRange(value);
        } else if (key === graph + BANDS_SUFFIX) {
          state[graph].bands = value !== "off";
        } else if (key === graph) {
          /* A browser may percent-encode the separator; no series name holds one. */
          var names = value
            .replace(/%7C/gi, SERIES_SEPARATOR)
            .split(SERIES_SEPARATOR)
            .filter(Boolean)
            .map(function (n) {
              return decodeURIComponent(n);
            });
          state[graph].series = names.length ? names : null;
        }
      });
    });
    return state;
  }

  function encodeSearch(state) {
    var parts = [];
    keys().forEach(function (graph) {
      var g = (state && state[graph]) || defaultGraphState();
      if (g.range === RANGE_ALL) parts.push(graph + RANGE_SUFFIX + "=" + RANGE_ALL);
      else if (g.range) parts.push(graph + RANGE_SUFFIX + "=" + g.range[0] + "," + g.range[1]);
      if (g.bands === false) parts.push(graph + BANDS_SUFFIX + "=off");
      if (g.series && g.series.length) {
        parts.push(graph + "=" + g.series.map(encodeURIComponent).join(SERIES_SEPARATOR));
      }
    });
    return parts.length ? "?" + parts.join("&") : "";
  }

  function sameState(a, b) {
    return encodeSearch(a) === encodeSearch(b);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function graphState(state, key) {
    return (state && state[key]) || defaultGraphState();
  }

  /* ------------------------------------------------------------ graphs */

  function graphDiv(id) {
    var host = document.getElementById(id);
    if (!host) return null;
    var gd = host.classList.contains("js-plotly-plot") ? host : host.querySelector(".js-plotly-plot");
    return gd && gd._fullLayout ? gd : null;
  }

  function whenDrawn(ids, timeout) {
    var deadline = Date.now() + (timeout || 20000);
    return new Promise(function (resolve) {
      (function poll() {
        var present = ids.filter(function (id) {
          return document.getElementById(id);
        });
        var drawn = present
          .map(function (id) {
            return { id: id, gd: graphDiv(id) };
          })
          .filter(function (entry) {
            return entry.gd;
          });
        if (drawn.length === present.length || Date.now() > deadline) return resolve(drawn);
        setTimeout(poll, 120);
      })();
    });
  }

  function currentRange(gd) {
    var axis = gd._fullLayout && gd._fullLayout.xaxis;
    if (!axis || !axis.range) return null;
    var start = isoDate(axis.range[0]);
    var end = isoDate(axis.range[1]);
    return start && end ? [start, end] : null;
  }

  function isBand(shape) {
    return !!(shape && shape.type === "rect" && shape.legendgroup && /nino|nina/.test(shape.legendgroup));
  }

  function visibleSeries(gd) {
    var names = [];
    var all = true;
    (gd.data || []).forEach(function (trace) {
      if (trace.visible === false || trace.visible === "legendonly") all = false;
      else names.push(trace.name);
    });
    return all ? null : names;
  }

  /* null leaves the figure's authored window; "all" shows its whole record. */
  function applyRange(gd, range) {
    var update = {};
    if (range === RANGE_ALL) {
      if (gd._fullLayout.xaxis.autorange) return null;
      update["xaxis.autorange"] = true;
    } else if (range) {
      var now = currentRange(gd);
      if (now && now[0] === range[0] && now[1] === range[1]) return null;
      update["xaxis.range"] = [range[0], range[1]];
      update["xaxis.autorange"] = false;
    } else {
      return null;
    }
    return window.Plotly.relayout(gd, update);
  }

  function applyBands(gd, bands) {
    var shapes = (gd.layout && gd.layout.shapes) || [];
    var update = {};
    var changed = false;
    shapes.forEach(function (shape, i) {
      if (!isBand(shape)) return;
      var wanted = bands ? true : "legendonly";
      var now = shape.visible === undefined ? true : shape.visible;
      if (now !== wanted) {
        update["shapes[" + i + "].visible"] = wanted;
        changed = true;
      }
    });
    return changed ? window.Plotly.relayout(gd, update) : null;
  }

  function applySeries(gd, names) {
    var indices = [];
    var values = [];
    (gd.data || []).forEach(function (trace, i) {
      var wanted = !names || names.indexOf(trace.name) >= 0 ? true : "legendonly";
      var now = trace.visible === undefined ? true : trace.visible;
      if (now !== wanted) {
        indices.push(i);
        values.push(wanted);
      }
    });
    return indices.length ? window.Plotly.restyle(gd, { visible: values }, indices) : null;
  }

  /* Whether the drawn figure already shows its state. */
  function matches(gd, g) {
    if (g.range === RANGE_ALL) {
      if (!gd._fullLayout.xaxis.autorange) return false;
    } else if (g.range) {
      var now = currentRange(gd);
      if (!now || now[0] !== g.range[0] || now[1] !== g.range[1]) return false;
    }
    var bands = g.bands !== false;
    var bandsOk = (gd.layout.shapes || []).every(function (shape) {
      if (!isBand(shape)) return true;
      var visible = shape.visible === undefined ? true : shape.visible;
      return bands ? visible === true : visible === "legendonly";
    });
    if (!bandsOk) return false;
    return (gd.data || []).every(function (trace) {
      var wanted = !g.series || g.series.indexOf(trace.name) >= 0 ? true : "legendonly";
      var now = trace.visible === undefined ? true : trace.visible;
      return now === wanted;
    });
  }

  function applyTo(gd, g) {
    var work = [];
    var r = applyRange(gd, g.range);
    if (r) work.push(r);
    var b = applyBands(gd, g.bands !== false);
    if (b) work.push(b);
    var s = applySeries(gd, g.series || null);
    if (s) work.push(s);
    return Promise.all(work).then(function () {
      return work.length > 0;
    });
  }

  /* Dash redraws a figure from the copy in its store after a layout change
     it is told about, and that copy does not carry changes made here. Once
     a figure shows its state, the live figure is written back to the store
     so every later redraw reproduces it. */
  function pushFigure(id, gd) {
    if (!dc.set_props || !gd) return;
    dc.set_props(id, { figure: clone({ data: gd.data, layout: gd.layout }) });
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function syncControls(state) {
    keys().forEach(function (key) {
      var g = graphState(state, key);
      var select = document.getElementById("event-select-" + key);
      if (select) {
        var wanted = Array.isArray(g.range) ? g.range.join(",") : "";
        var match = Array.prototype.some.call(select.options, function (o) {
          return o.value === wanted;
        });
        select.value = match ? wanted : "";
      }
      ["range-all-", "range-30-", "range-5-"].forEach(function (prefix) {
        var button = document.getElementById(prefix + key);
        if (button) button.setAttribute("aria-pressed", "false");
      });
      if (g.range === RANGE_ALL) {
        var all = document.getElementById("range-all-" + key);
        if (all) all.setAttribute("aria-pressed", "true");
      }
    });
  }

  function lastDate(gd) {
    var last = null;
    (gd.data || []).forEach(function (trace) {
      var xs = trace.x || [];
      var end = xs[xs.length - 1];
      if (end && (!last || end > last)) last = end;
    });
    return last ? isoDate(last) : null;
  }

  function yearsBack(gd, years) {
    var last = lastDate(gd);
    if (!last) return null;
    var end = new Date(last + "T00:00:00Z");
    end.setUTCMonth(end.getUTCMonth() + 2);
    var start = new Date(end.getTime());
    start.setUTCFullYear(start.getUTCFullYear() - years);
    return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
  }

  /* ------------------------------------------------------------- theme */

  function systemScheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function effectiveScheme(stored) {
    return stored === "dark" || stored === "light" ? stored : systemScheme();
  }

  function stateScale(colours) {
    var scale = [];
    STATE_ORDER.forEach(function (state, i) {
      scale.push([i / STATE_ORDER.length, colours[state]]);
      scale.push([(i + 1) / STATE_ORDER.length, colours[state]]);
    });
    return scale;
  }

  /* The layout patch for one figure: the template, the band fills and the
     outline and threshold colours of its shapes and annotations. */
  function layoutPatch(gd, template) {
    var data = template.data;
    var patch = { template: { layout: template.layout } };
    (gd.layout.shapes || []).forEach(function (shape, i) {
      if (isBand(shape)) {
        if (data.bands[shape.legendgroup]) {
          patch["shapes[" + i + "].fillcolor"] = data.bands[shape.legendgroup];
        }
        if (shape.line && shape.line.width) patch["shapes[" + i + "].line.color"] = data.outline;
        if (shape.label) patch["shapes[" + i + "].label.font.color"] = data.outline;
      } else if (shape.name === "threshold") {
        patch["shapes[" + i + "].line.color"] = data.threshold;
      }
    });
    (gd.layout.annotations || []).forEach(function (annotation, i) {
      if (annotation.name === "threshold") {
        patch["annotations[" + i + "].font.color"] = data.threshold;
      }
    });
    return patch;
  }

  /* The restyle for one trace by its meta role, or null. */
  function traceStyle(trace, data) {
    var meta = trace.meta || {};
    if (meta.role === "index-primary") return { "line.color": data.index.primary };
    if (meta.role === "index-secondary") return { "line.color": data.index.secondary };
    if (meta.role === "series") return { "line.color": data.series[meta.rank % data.series.length] };
    if (meta.role === "choropleth") {
      return { colorscale: [stateScale(data.state)], "marker.line.color": data.map_border };
    }
    if (meta.role === "state") {
      var colour = data.state[meta.state];
      if (data.state_mark[meta.state] === "outlined") {
        return { "marker.color": data.map_border, "marker.line.color": colour };
      }
      return { "marker.color": colour, "marker.line.color": data.map_border };
    }
    return null;
  }

  function applyScheme(scheme, templates) {
    document.documentElement.setAttribute("data-theme", scheme);
    var template = templates && templates[scheme];
    if (!template || !template.layout || !template.data) return Promise.resolve();
    var ids = keys().map(function (key) {
      return GRAPHS[key];
    });
    return whenDrawn(ids.concat([MAP_ID])).then(function (drawn) {
      if (!window.Plotly) return null;
      return Promise.all(
        drawn.map(function (entry) {
          var gd = entry.gd;
          var updates = [window.Plotly.relayout(gd, layoutPatch(gd, template))];
          gd.data.forEach(function (trace, i) {
            var style = traceStyle(trace, template.data);
            if (style) updates.push(window.Plotly.restyle(gd, style, [i]));
          });
          return Promise.all(updates).then(function () {
            pushFigure(entry.id, gd);
          });
        })
      );
    });
  }

  /* ----------------------------------------------------------- exports */

  function download(dataUrl, filename) {
    var link = document.createElement("a");
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function exportFigure(gd, format, sourceLine, stem) {
    var layout = clone(gd.layout);
    var width = gd._fullLayout.width;
    var height = gd._fullLayout.height + 48;
    layout.width = width;
    layout.height = height;
    layout.margin = layout.margin || {};
    layout.margin.b = (layout.margin.b || 0) + 48;
    layout.annotations = (layout.annotations || []).concat([
      {
        text: sourceLine,
        xref: "paper",
        yref: "paper",
        x: 0,
        y: -0.24,
        xanchor: "left",
        yanchor: "top",
        showarrow: false,
        font: { size: 11 },
        align: "left",
      },
    ]);
    return window.Plotly.toImage(
      { data: gd.data, layout: layout, config: { staticPlot: true } },
      { format: format, width: width, height: height, scale: format === "png" ? 2 : 1 }
    ).then(function (url) {
      download(url, stem + "." + format);
      return stem + "." + format;
    });
  }

  /* ------------------------------------------------------- native select */

  document.addEventListener("change", function (event) {
    var target = event.target;
    if (!target || !dc.set_props || !target.id || target.id.indexOf("event-select-") !== 0) return;
    var key = target.id.slice("event-select-".length);
    dc.set_props("event-select-store-" + key, { data: { value: target.value, at: Date.now() } });
  });

  /* --------------------------------------------------- keyboard shims */

  function legendLabel(group) {
    var text = group.querySelector(".legendtext");
    return text ? text.textContent : "";
  }

  function synthesise(target, type) {
    var rect = target.getBoundingClientRect();
    target.dispatchEvent(
      new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
        button: 0,
      })
    );
  }

  function enhance(root) {
    root.querySelectorAll(".modebar-btn:not([tabindex])").forEach(function (button) {
      button.setAttribute("tabindex", "0");
      button.setAttribute("role", "button");
      var title = button.getAttribute("data-title");
      if (title) button.setAttribute("aria-label", title);
    });
    root.querySelectorAll(".legend .traces:not([tabindex])").forEach(function (group) {
      group.setAttribute("tabindex", "0");
      group.setAttribute("role", "button");
      group.setAttribute("aria-label", legendLabel(group));
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    var target = event.target;
    if (!target || !target.classList) return;
    if (target.classList.contains("modebar-btn")) {
      event.preventDefault();
      target.click();
    } else if (target.classList.contains("traces")) {
      event.preventDefault();
      var toggle = target.querySelector(".legendtoggle") || target;
      synthesise(toggle, "mousedown");
      synthesise(toggle, "mouseup");
    }
  });

  var observer = new MutationObserver(function () {
    enhance(document);
  });
  if (document.body) observer.observe(document.body, { childList: true, subtree: true });

  var sectionTick = false;

  function currentSection() {
    if (sectionTick) return;
    sectionTick = true;
    window.requestAnimationFrame(function () {
      sectionTick = false;
      markCurrentSection();
    });
  }

  function markCurrentSection() {
    var offset = 80;
    var ids = ["panel-index", "panel-commodities", "panel-activations", "sources", "cite"];
    var current = null;
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top <= offset) current = id;
    });
    document.querySelectorAll(".site-nav__link").forEach(function (link) {
      var active = current && link.getAttribute("href") === "#" + current;
      link.classList.toggle("is-current", !!active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  window.addEventListener("scroll", currentSection, { passive: true });

  /* -------------------------------------------------- dash callbacks */

  dc.atlas = {
    /* Inputs (read from the callback context by id): url.search, view-state
       and, per time-series figure present, its event-select store, band
       toggle clicks, three range buttons, relayoutData and restyleData.
       States: each band toggle's aria-pressed. Outputs: view-state,
       url.search, then each band toggle's aria-pressed in outputs_list order. */
    syncState: function () {
      var ctx = dc.callback_context;
      var inputs = ctx.inputs || {};
      var states = ctx.states || {};
      var outputs = ctx.outputs_list || [];
      var triggered = (ctx.triggered || []).map(function (t) {
        return t.prop_id;
      });
      var trigger = triggered[0] || "";
      var search = inputs["url.search"] || "";
      var state = inputs["view-state.data"] || defaultState();
      var next = clone(state);

      function toggleKeys() {
        return outputs
          .filter(function (o) {
            return o.property === "aria-pressed";
          })
          .map(function (o) {
            return String(o.id).replace("bands-toggle-", "");
          });
      }

      function pressed(newState) {
        return toggleKeys().map(function (key) {
          var wanted = graphState(newState, key).bands === false ? "false" : "true";
          var current = states["bands-toggle-" + key + ".aria-pressed"];
          return current === wanted ? dc.no_update : wanted;
        });
      }

      function result(newState, writeUrl) {
        return [newState, writeUrl ? encodeSearch(newState) : dc.no_update].concat(pressed(newState));
      }

      function nothing() {
        return [dc.no_update, dc.no_update].concat(
          toggleKeys().map(function () {
            return dc.no_update;
          })
        );
      }

      if (!trigger || trigger === "." || trigger === "url.search") {
        var parsed = parseSearch(search);
        if (sameState(parsed, state)) return [dc.no_update, dc.no_update].concat(pressed(parsed));
        return result(parsed, false);
      }
      if (trigger === "view-state.data") {
        var encoded = encodeSearch(state);
        return [dc.no_update, encoded === search ? dc.no_update : encoded].concat(
          toggleKeys().map(function () {
            return dc.no_update;
          })
        );
      }

      var id = trigger.split(".")[0];
      var prop = trigger.split(".")[1];
      var key = null;
      var match = /^(event-select-store|bands-toggle|range-all|range-30|range-5)-(.+)$/.exec(id);
      if (match) key = match[2];
      else key = keyForGraph(id);
      if (!key || !next[key]) return nothing();
      var g = next[key];
      var gd = graphDiv(GRAPHS[key]);

      if (prop === "relayoutData") {
        var payload = inputs[trigger];
        if (!payload) return nothing();
        /* The applier sets the whole "xaxis.range" array; a reader's drag
           reports the two bounds separately. The former is an echo. */
        if (Object.prototype.hasOwnProperty.call(payload, "xaxis.range")) return nothing();
        if (payload["xaxis.autorange"]) {
          g.range = RANGE_ALL;
        } else if (payload["xaxis.range[0]"] && payload["xaxis.range[1]"]) {
          var s = isoDate(payload["xaxis.range[0]"]);
          var e = isoDate(payload["xaxis.range[1]"]);
          if (s && e && s < e) g.range = [s, e];
        } else if (
          Object.keys(payload).some(function (k) {
            return /^shapes\[\d+\]\.visible$/.test(k);
          })
        ) {
          if (!gd) return nothing();
          g.bands = (gd.layout.shapes || []).some(function (shape) {
            return isBand(shape) && shape.visible !== "legendonly" && shape.visible !== false;
          });
        } else {
          return nothing();
        }
      } else if (prop === "restyleData") {
        /* A legend click reports "visible"; the scheme switch reports colours
           and is not a change of the series shown. */
        var restyle = inputs[trigger];
        var edits = restyle && restyle[0] ? Object.keys(restyle[0]) : [];
        if (!gd || edits.indexOf("visible") < 0) return nothing();
        g.series = visibleSeries(gd);
      } else if (id.indexOf("range-all-") === 0) {
        g.range = RANGE_ALL;
      } else if (id.indexOf("range-30-") === 0 || id.indexOf("range-5-") === 0) {
        if (!gd) return nothing();
        var window_ = yearsBack(gd, id.indexOf("range-30-") === 0 ? 30 : 5);
        if (!window_) return nothing();
        g.range = window_;
      } else if (id.indexOf("event-select-store-") === 0) {
        var store = inputs[trigger];
        var value = store && store.value;
        if (!value) return nothing();
        var bounds = value.split(",");
        if (bounds.length !== 2) return nothing();
        g.range = [bounds[0], bounds[1]];
      } else if (id.indexOf("bands-toggle-") === 0) {
        if (!inputs[trigger]) return nothing();
        g.bands = graphState(state, key).bands === false;
      } else {
        return nothing();
      }
      if (sameState(next, state)) return nothing();
      return result(next, true);
    },

    /* Input: view-state. Applies each figure's state, checks the result
       after a settle and applies again while a redraw undid it. */
    applyState: function (state) {
      state = state || defaultState();
      syncControls(state);
      var seq = ++applySeq;
      var ids = keys().map(function (key) {
        return GRAPHS[key];
      });
      return whenDrawn(ids).then(function (drawn) {
        var touched = {};
        function superseded() {
          return seq !== applySeq;
        }
        function pass(attempt) {
          if (superseded()) return String(Date.now());
          return Promise.all(
            drawn.map(function (entry) {
              return applyTo(entry.gd, graphState(state, keyForGraph(entry.id))).then(
                function (worked) {
                  if (worked) touched[entry.id] = true;
                }
              );
            })
          )
            .then(function () {
              return sleep(SETTLE_MS);
            })
            .then(function () {
              if (superseded()) return String(Date.now());
              var settled = drawn.every(function (entry) {
                return matches(entry.gd, graphState(state, keyForGraph(entry.id)));
              });
              if (settled || attempt + 1 >= MAX_PASSES) {
                drawn.forEach(function (entry) {
                  if (touched[entry.id]) pushFigure(entry.id, entry.gd);
                });
                return String(Date.now());
              }
              return pass(attempt + 1);
            });
        }
        return pass(0).catch(function () {
          return String(Date.now());
        });
      });
    },

    /* Input: theme-toggle clicks; State: theme-store. Output: theme-store. */
    toggleTheme: function (clicks, stored) {
      if (!clicks) return dc.no_update;
      return effectiveScheme(stored) === "dark" ? "light" : "dark";
    },

    /* Input: theme-store; State: plotly-templates. Applies the scheme. */
    applyTheme: function (stored, templates) {
      var scheme = effectiveScheme(stored);
      if (!window.__atlasSchemeListener && window.matchMedia) {
        window.__atlasSchemeListener = true;
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
          var raw = null;
          try {
            raw = JSON.parse(window.localStorage.getItem(THEME_KEY));
          } catch (err) {
            raw = null;
          }
          if (raw !== "dark" && raw !== "light") applyScheme(systemScheme(), templates);
        });
      }
      return applyScheme(scheme, templates).then(function () {
        return scheme;
      });
    },

    /* Inputs: png and svg clicks; State: {graph, source, stem}. */
    exportFigure: function (pngClicks, svgClicks, meta) {
      var ctx = dc.callback_context;
      var trigger = ((ctx.triggered || [])[0] || {}).prop_id || "";
      if (!trigger || trigger === "." || !meta) return dc.no_update;
      var format = trigger.indexOf("svg-") === 0 ? "svg" : "png";
      var gd = graphDiv(meta.graph);
      if (!gd) return dc.no_update;
      return exportFigure(gd, format, meta.source, meta.stem).then(function (name) {
        return "Saved " + name;
      });
    },

    /* Input: copy button clicks; State: the citation text. Output: status text. */
    copyCitation: function (clicks, text) {
      if (!clicks) return dc.no_update;
      if (!navigator.clipboard) return "Copy failed";
      return navigator.clipboard.writeText(text).then(
        function () {
          return "Copied";
        },
        function () {
          return "Copy failed";
        }
      );
    },
  };
})();
