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
  var GRAPHS = { index: "graph-index", prices: "graph-commodities" };
  var MAP_ID = "activations-map";
  var TIME_SERIES = [GRAPHS.index, GRAPHS.prices];
  var RANGE_KEY = "range";
  var RANGE_ALL = "all";
  var BANDS_KEY = "bands";
  var SERIES_KEYS = ["index", "prices"];
  var SERIES_SEPARATOR = "|";
  var THEME_KEY = "theme-store";
  /* Dash redraws a figure from its stored copy after the first interaction
     it reports; the redraw can undo a state applied moments earlier, so the
     applier checks its work after a short settle and applies again. */
  var SETTLE_MS = 600;
  var MAX_PASSES = 3;

  /* ------------------------------------------------------------ codec */

  function isoDate(text) {
    var match = /^(\d{4}-\d{2}-\d{2})/.exec(String(text).trim());
    if (!match) return null;
    var parsed = new Date(match[1] + "T00:00:00Z");
    return isNaN(parsed.getTime()) ? null : match[1];
  }

  function defaultState() {
    return { range: null, bands: true, series: {} };
  }

  function parseSearch(search) {
    var state = defaultState();
    var query = search && search.charAt(0) === "?" ? search.slice(1) : search || "";
    query.split("&").forEach(function (pair) {
      if (!pair) return;
      var eq = pair.indexOf("=");
      var key = eq < 0 ? pair : pair.slice(0, eq);
      var value = eq < 0 ? "" : pair.slice(eq + 1);
      if (key === RANGE_KEY) {
        var parts = value.split(",");
        if (value === RANGE_ALL) {
          state.range = RANGE_ALL;
        } else if (parts.length === 2) {
          var start = isoDate(decodeURIComponent(parts[0]));
          var end = isoDate(decodeURIComponent(parts[1]));
          if (start && end && start < end) state.range = [start, end];
        }
      } else if (key === BANDS_KEY) {
        state.bands = value !== "off";
      } else if (SERIES_KEYS.indexOf(key) >= 0) {
        /* A browser may percent-encode the separator; no series name holds one. */
        var names = value
          .replace(/%7C/gi, SERIES_SEPARATOR)
          .split(SERIES_SEPARATOR)
          .filter(Boolean)
          .map(function (n) {
            return decodeURIComponent(n);
          });
        if (names.length) state.series[key] = names;
      }
    });
    return state;
  }

  function encodeSearch(state) {
    var parts = [];
    if (state.range === RANGE_ALL) parts.push(RANGE_KEY + "=" + RANGE_ALL);
    else if (state.range) parts.push(RANGE_KEY + "=" + state.range[0] + "," + state.range[1]);
    if (state.bands === false) parts.push(BANDS_KEY + "=off");
    SERIES_KEYS.forEach(function (key) {
      var names = state.series && state.series[key];
      if (names && names.length) {
        parts.push(key + "=" + names.map(encodeURIComponent).join(SERIES_SEPARATOR));
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

  function seriesKeyFor(id) {
    return id === GRAPHS.index ? "index" : id === GRAPHS.prices ? "prices" : null;
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

  /* Whether the drawn figure already shows the state. */
  function matches(entry, state) {
    var gd = entry.gd;
    var key = seriesKeyFor(entry.id);
    if (state.range === RANGE_ALL) {
      if (!gd._fullLayout.xaxis.autorange) return false;
    } else if (state.range) {
      var now = currentRange(gd);
      if (!now || now[0] !== state.range[0] || now[1] !== state.range[1]) return false;
    }
    var bands = state.bands !== false;
    var bandsOk = (gd.layout.shapes || []).every(function (shape) {
      if (!isBand(shape)) return true;
      var visible = shape.visible === undefined ? true : shape.visible;
      return bands ? visible === true : visible === "legendonly";
    });
    if (!bandsOk) return false;
    var names = key && state.series ? state.series[key] || null : null;
    return (gd.data || []).every(function (trace) {
      var wanted = !names || names.indexOf(trace.name) >= 0 ? true : "legendonly";
      var now = trace.visible === undefined ? true : trace.visible;
      return now === wanted;
    });
  }

  function applyTo(entry, state) {
    var key = seriesKeyFor(entry.id);
    var work = [];
    var r = applyRange(entry.gd, state.range);
    if (r) work.push(r);
    var b = applyBands(entry.gd, state.bands !== false);
    if (b) work.push(b);
    var s = applySeries(entry.gd, key && state.series ? state.series[key] || null : null);
    if (s) work.push(s);
    return Promise.all(work);
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function syncControls(state) {
    var select = document.getElementById("event-select");
    if (select) {
      var wanted = Array.isArray(state.range) ? state.range.join(",") : "";
      var match = Array.prototype.some.call(select.options, function (o) {
        return o.value === wanted;
      });
      select.value = match ? wanted : "";
    }
    ["range-all", "range-30", "range-5"].forEach(function (id) {
      var button = document.getElementById(id);
      if (button) button.setAttribute("aria-pressed", "false");
    });
    if (state.range === RANGE_ALL) {
      var all = document.getElementById("range-all");
      if (all) all.setAttribute("aria-pressed", "true");
    }
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

  /* plotly.js loads after the layout renders, so the wait for drawn figures
     also waits for the library; nothing is applied until both exist. */
  function applyScheme(scheme, templateSet) {
    document.documentElement.setAttribute("data-theme", scheme);
    var template = templateSet && templateSet[scheme];
    if (!template) return Promise.resolve();
    var border = templateSet.map_border ? templateSet.map_border[scheme] : null;
    return whenDrawn(TIME_SERIES.concat([MAP_ID])).then(function (drawn) {
      if (!window.Plotly) return null;
      return Promise.all(
        drawn.map(function (entry) {
          var gd = entry.gd;
          var patch = { template: { layout: template.layout } };
          (gd.layout.shapes || []).forEach(function (shape, i) {
            if (isBand(shape) && template.bands && template.bands[shape.legendgroup]) {
              patch["shapes[" + i + "].fillcolor"] = template.bands[shape.legendgroup];
            }
          });
          var updates = [window.Plotly.relayout(gd, patch)];
          if (border) {
            gd.data.forEach(function (trace, i) {
              if (trace.type === "choropleth") {
                updates.push(window.Plotly.restyle(gd, { "marker.line.color": border }, [i]));
              } else if (trace.type === "scattergeo" && trace.marker && trace.marker.symbol === "circle") {
                updates.push(window.Plotly.restyle(gd, { "marker.line.color": border }, [i]));
              } else if (trace.type === "scattergeo" && trace.marker && trace.marker.symbol === "circle-open") {
                updates.push(window.Plotly.restyle(gd, { "marker.color": border }, [i]));
              }
            });
          }
          return Promise.all(updates);
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
    if (target && target.id === "event-select" && dc.set_props) {
      dc.set_props("event-select-store", { data: { value: target.value, at: Date.now() } });
    }
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

  var NO = function () {
    return [dc.no_update, dc.no_update, dc.no_update];
  };

  dc.atlas = {
    /* Inputs (read from the callback context by id): url.search, view-state,
       event-select-store, bands-toggle clicks, the three range buttons, and
       the relayoutData and restyleData of each time-series figure present.
       State: the band toggle's aria-pressed attribute.
       Outputs: view-state, url.search, bands-toggle aria-pressed. */
    syncState: function () {
      var ctx = dc.callback_context;
      var inputs = ctx.inputs || {};
      var states = ctx.states || {};
      var triggered = (ctx.triggered || []).map(function (t) {
        return t.prop_id;
      });
      var trigger = triggered[0] || "";
      var search = inputs["url.search"] || "";
      var state = inputs["view-state.data"] || defaultState();
      var next = clone(state);

      function pressed(newState) {
        var wanted = newState.bands === false ? "false" : "true";
        var current = states["bands-toggle.aria-pressed"];
        return current === wanted ? dc.no_update : wanted;
      }

      function result(newState, writeUrl) {
        return [newState, writeUrl ? encodeSearch(newState) : dc.no_update, pressed(newState)];
      }

      if (!trigger || trigger === "." || trigger === "url.search") {
        var parsed = parseSearch(search);
        if (sameState(parsed, state)) return [dc.no_update, dc.no_update, pressed(parsed)];
        return result(parsed, false);
      }
      if (trigger === "view-state.data") {
        var encoded = encodeSearch(state);
        return [dc.no_update, encoded === search ? dc.no_update : encoded, dc.no_update];
      }

      if (trigger.indexOf(".relayoutData") > 0) {
        var id = trigger.split(".")[0];
        var payload = inputs[trigger];
        if (!payload) return NO();
        /* The applier sets the whole "xaxis.range" array; a reader's drag
           reports the two bounds separately. The former is an echo. */
        if (Object.prototype.hasOwnProperty.call(payload, "xaxis.range")) return NO();
        if (payload["xaxis.autorange"]) {
          next.range = RANGE_ALL;
        } else if (payload["xaxis.range[0]"] && payload["xaxis.range[1]"]) {
          var s = isoDate(payload["xaxis.range[0]"]);
          var e = isoDate(payload["xaxis.range[1]"]);
          if (s && e && s < e) next.range = [s, e];
        } else if (
          Object.keys(payload).some(function (k) {
            return /^shapes\[\d+\]\.visible$/.test(k);
          })
        ) {
          var gd = graphDiv(id);
          if (!gd) return NO();
          next.bands = (gd.layout.shapes || []).some(function (shape) {
            return isBand(shape) && shape.visible !== "legendonly" && shape.visible !== false;
          });
        } else {
          return NO();
        }
      } else if (trigger.indexOf(".restyleData") > 0) {
        var rid = trigger.split(".")[0];
        var g = graphDiv(rid);
        var key = seriesKeyFor(rid);
        if (!g || !key) return NO();
        var names = visibleSeries(g);
        if (names) next.series[key] = names;
        else delete next.series[key];
      } else if (trigger === "range-all.n_clicks") {
        next.range = RANGE_ALL;
      } else if (trigger === "range-30.n_clicks" || trigger === "range-5.n_clicks") {
        var anchor = graphDiv(GRAPHS.index) || graphDiv(GRAPHS.prices);
        if (!anchor) return NO();
        var window_ = yearsBack(anchor, trigger === "range-30.n_clicks" ? 30 : 5);
        if (!window_) return NO();
        next.range = window_;
      } else if (trigger === "event-select-store.data") {
        var store = inputs[trigger];
        var value = store && store.value;
        if (!value) return NO();
        var bounds = value.split(",");
        if (bounds.length !== 2) return NO();
        next.range = [bounds[0], bounds[1]];
      } else if (trigger === "bands-toggle.n_clicks") {
        if (!inputs[trigger]) return NO();
        next.bands = state.bands === false;
      } else {
        return NO();
      }
      if (sameState(next, state)) return NO();
      return result(next, true);
    },

    /* Input: view-state. Applies the state to the drawn figures, checks the
       result after a settle and applies again while a redraw undid it. */
    applyState: function (state) {
      state = state || defaultState();
      syncControls(state);
      return whenDrawn(TIME_SERIES).then(function (drawn) {
        function pass(attempt) {
          return Promise.all(
            drawn.map(function (entry) {
              return applyTo(entry, state);
            })
          )
            .then(function () {
              return sleep(SETTLE_MS);
            })
            .then(function () {
              var settled = drawn.every(function (entry) {
                return matches(entry, state);
              });
              if (settled || attempt + 1 >= MAX_PASSES) return String(Date.now());
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
    applyTheme: function (stored, templateSet) {
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
          if (raw !== "dark" && raw !== "light") applyScheme(systemScheme(), templateSet);
        });
      }
      return applyScheme(scheme, templateSet).then(function () {
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
