/* Minimal runtime for the Claude Design ".dc" handoff format.
   Implements exactly the four directives the prototype uses:
     <sc-if value="{{ expr }}">      conditional
     <sc-for list="{{ expr }}" as="x">  repeat with scoped var
     {{ expr }}                      interpolation (text + attributes)
     onClick="{{ fn }}"              event binding
   Everything else in the template is passed through verbatim, so the
   designer's markup and inline styles render unchanged. */
(function () {
  'use strict';

  // ---- expression evaluation -------------------------------------------
  // Expressions in this template are literals or dotted paths (a, a.b.c).
  function lookup(path, scope) {
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (path === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(path)) return Number(path);
    var parts = path.split('.');
    var v = scope;
    for (var i = 0; i < parts.length; i++) {
      if (v == null) return undefined;
      v = v[parts[i]];
    }
    return v;
  }

  var RE = /\{\{([^}]*)\}\}/g;

  // Whole-value binding (e.g. onClick="{{ fn }}") returns the raw value,
  // preserving functions/booleans. Mixed strings interpolate to text.
  function evalAttr(raw, scope) {
    var m = raw.match(/^\s*\{\{([^}]*)\}\}\s*$/);
    if (m) return lookup(m[1].trim(), scope);
    return raw.replace(RE, function (_, e) {
      var v = lookup(e.trim(), scope);
      return v == null ? '' : String(v);
    });
  }

  function interpolateText(raw, scope) {
    return raw.replace(RE, function (_, e) {
      var v = lookup(e.trim(), scope);
      return v == null ? '' : String(v);
    });
  }

  // ---- rendering --------------------------------------------------------
  function renderChildren(srcNode, scope, out) {
    var kids = srcNode.childNodes;
    for (var i = 0; i < kids.length; i++) renderNode(kids[i], scope, out);
  }

  function renderNode(node, scope, out) {
    // text
    if (node.nodeType === 3) {
      var t = interpolateText(node.nodeValue, scope);
      if (t) out.appendChild(document.createTextNode(t));
      return;
    }
    if (node.nodeType !== 1) return;

    var tag = node.tagName.toLowerCase();

    if (tag === 'sc-if') {
      if (evalAttr(node.getAttribute('value') || '', scope)) {
        renderChildren(node, scope, out);
      }
      return;
    }

    if (tag === 'sc-for') {
      var list = evalAttr(node.getAttribute('list') || '', scope);
      var as = node.getAttribute('as') || 'item';
      if (Array.isArray(list)) {
        for (var i = 0; i < list.length; i++) {
          var child = Object.create(scope);
          child[as] = list[i];
          child.$index = i;
          renderChildren(node, child, out);
        }
      }
      return;
    }

    // Ordinary element. Clone rather than re-create: cloneNode preserves the
    // element's namespace, which matters for the inline <svg> pizza slices —
    // document.createElement() would produce dead HTML elements instead.
    var el = node.cloneNode(false);
    var attrs = node.attributes;
    for (var a = 0; a < attrs.length; a++) {
      var name = attrs[a].name, raw = attrs[a].value;
      var lower = name.toLowerCase();

      if (lower.indexOf('hint-placeholder') === 0) {   // design-tool hint
        el.removeAttribute(name);
        continue;
      }

      // The HTML parser lowercases attribute names, so onClick arrives as
      // onclick. Bind it as a listener and strip it, otherwise the browser
      // would try to eval "{{ goMenu }}" as inline JS.
      if (lower.length > 2 && lower.indexOf('on') === 0 && raw.indexOf('{{') !== -1) {
        el.removeAttribute(name);
        var fn = evalAttr(raw, scope);
        if (typeof fn === 'function') el.addEventListener(lower.slice(2), fn);
        continue;
      }

      var isAsset = (lower === 'src' || lower === 'href' || lower === 'data-src');
      var dynamic = raw.indexOf('{{') !== -1;
      if (!dynamic && !isAsset) continue;              // static, already cloned

      var val = dynamic ? evalAttr(raw, scope) : raw;
      if (val === false || val == null) { el.removeAttribute(name); continue; }
      val = val === true ? '' : String(val);
      // Asset paths resolve to inlined data URIs. This has to run for static
      // attributes too (e.g. the logo <img src="assets/logo-0.png">), not just
      // interpolated ones.
      if (isAsset && window.__ASSETS && window.__ASSETS[val]) {
        val = window.__ASSETS[val];
      }
      el.setAttribute(name, val);
    }
    renderChildren(node, scope, el);
    out.appendChild(el);
  }

  // ---- component base ---------------------------------------------------
  function DCLogic() {}
  DCLogic.prototype.setState = function (patch) {
    Object.assign(this.state, patch);
    this._render();
  };
  DCLogic.prototype.renderVals = function () { return {}; };
  DCLogic.prototype.componentDidMount = function () {};
  DCLogic.prototype._render = function () {
    var frag = document.createDocumentFragment();
    renderChildren(this._tpl, this.renderVals(), frag);
    this._mount.textContent = '';
    this._mount.appendChild(frag);
  };

  window.DCLogic = DCLogic;

  window.__dcBoot = function (ComponentClass, props) {
    var src = document.querySelector('x-dc');
    if (!src) return;

    // <helmet> contents belong in <head>
    var helmet = src.querySelector('helmet');
    if (helmet) {
      while (helmet.firstChild) document.head.appendChild(helmet.firstChild);
      helmet.parentNode.removeChild(helmet);
    }

    var inst = new ComponentClass();
    inst.props = props || {};
    if (!inst.state) inst.state = {};
    inst._tpl = src.cloneNode(true);          // pristine template
    var mount = document.createElement('div');
    src.parentNode.replaceChild(mount, src);
    inst._mount = mount;
    inst._render();
    inst.componentDidMount();
    window.__dc = inst;
  };
})();
