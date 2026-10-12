/**
 * Stealth Script — Injected into page context BEFORE hook-script.
 * Overrides browser APIs to match the fingerprint profile.
 *
 * This file is designed to be stringified and injected via executeJavaScript().
 * The __FINGERPRINT_PROFILE__ placeholder is replaced at injection time.
 */

export function buildStealthScript(profileJson: string): string {
  // Defensive escaping: ensure JSON can be safely embedded in a JS literal
  const safeJson = profileJson
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
    .replace(/<\/script/gi, '<\\/script');
  return `(function() {
  'use strict';
  if (window.__stealth_applied__) return;
  window.__stealth_applied__ = true;

  const profile = ${safeJson};

  // === Utility: make overridden functions look native ===
  function makeNative(fn, name) {
    const nativeToString = function() { return 'function ' + name + '() { [native code] }'; };
    Object.defineProperty(nativeToString, 'name', { value: 'toString' });
    fn.toString = nativeToString;
    return fn;
  }

  function overrideGetter(obj, prop, value) {
    try {
      const desc = Object.getOwnPropertyDescriptor(obj, prop) ||
                   Object.getOwnPropertyDescriptor(Object.getPrototypeOf(obj), prop);
      if (desc && desc.get) {
        const newGet = makeNative(function() { return value; }, 'get ' + prop);
        Object.defineProperty(obj, prop, { get: newGet, configurable: true });
      } else {
        Object.defineProperty(obj, prop, { value: value, writable: false, configurable: true });
      }
    } catch(e) {}
  }

  // Seeded PRNG (mulberry32) — top-level so all noise sections can use it
  function mulberry32(seed) {
    return function() {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  // ========== Layer 2: Navigator / Screen Overrides ==========

  // navigator.webdriver
  try {
    Object.defineProperty(navigator, 'webdriver', {
      get: makeNative(function() { return false; }, 'get webdriver'),
      configurable: true,
    });
  } catch(e) {}

  // navigator.platform
  overrideGetter(navigator, 'platform', profile.platform);

  // navigator.languages
  overrideGetter(navigator, 'languages', Object.freeze([...profile.languages]));
  overrideGetter(navigator, 'language', profile.languages[0]);

  // navigator.hardwareConcurrency
  overrideGetter(navigator, 'hardwareConcurrency', profile.hardwareConcurrency);

  // navigator.deviceMemory
  overrideGetter(navigator, 'deviceMemory', profile.deviceMemory);

  // navigator.plugins — fake PluginArray
  try {
    const fakePlugins = [
      { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
      { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
      { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
    ];
    const pluginArr = Object.create(PluginArray.prototype);
    fakePlugins.forEach((p, i) => {
      const plugin = Object.create(Plugin.prototype);
      Object.defineProperty(plugin, 'name', { value: p.name });
      Object.defineProperty(plugin, 'filename', { value: p.filename });
      Object.defineProperty(plugin, 'description', { value: p.description });
      Object.defineProperty(plugin, 'length', { value: 0 });
      pluginArr[i] = plugin;
    });
    Object.defineProperty(pluginArr, 'length', { value: fakePlugins.length });
    pluginArr.item = makeNative(function(i) { return pluginArr[i] || null; }, 'item');
    pluginArr.namedItem = makeNative(function(name) {
      for (let i = 0; i < pluginArr.length; i++) { if (pluginArr[i].name === name) return pluginArr[i]; }
      return null;
    }, 'namedItem');
    pluginArr.refresh = makeNative(function() {}, 'refresh');
    overrideGetter(navigator, 'plugins', pluginArr);
  } catch(e) {}

  // screen properties
  overrideGetter(screen, 'width', profile.screenWidth);
  overrideGetter(screen, 'height', profile.screenHeight);
  overrideGetter(screen, 'availWidth', profile.screenWidth);
  overrideGetter(screen, 'availHeight', profile.screenHeight - 40); // taskbar offset
  overrideGetter(screen, 'colorDepth', profile.colorDepth);
  overrideGetter(screen, 'pixelDepth', profile.colorDepth);

  // window.devicePixelRatio
  overrideGetter(window, 'devicePixelRatio', profile.devicePixelRatio);

  // window.chrome — polyfill for non-headless detection
  try {
    if (!window.chrome) {
      window.chrome = {};
    }
    if (!window.chrome.runtime) {
      window.chrome.runtime = {
        connect: makeNative(function() {}, 'connect'),
        sendMessage: makeNative(function() {}, 'sendMessage'),
      };
    }
  } catch(e) {}

  // Timezone spoofing
  try {
    const origDTF = Intl.DateTimeFormat;
    const newDTF = makeNative(function(...args) {
      const instance = new origDTF(...args);
      const origResolved = instance.resolvedOptions.bind(instance);
      instance.resolvedOptions = makeNative(function() {
        const opts = origResolved();
        opts.timeZone = profile.timezone;
        return opts;
      }, 'resolvedOptions');
      return instance;
    }, 'DateTimeFormat');
    newDTF.prototype = origDTF.prototype;
    newDTF.supportedLocalesOf = origDTF.supportedLocalesOf;
    Intl.DateTimeFormat = newDTF;
  } catch(e) {}

  try {
    Date.prototype.getTimezoneOffset = makeNative(function() {
      return profile.timezoneOffset;
    }, 'getTimezoneOffset');
  } catch(e) {}

  // Permissions.query
  try {
    const origQuery = Permissions.prototype.query;
    Permissions.prototype.query = makeNative(function(desc) {
      if (desc && desc.name === 'notifications') {
        return Promise.resolve({ state: 'prompt', onchange: null });
      }
      return origQuery.call(this, desc);
    }, 'query');
  } catch(e) {}

  // ========== Layer 3: Canvas / WebGL / Audio / WebRTC Noise ==========

  // --- Canvas fingerprint noise ---
  try {
    const canvasRng = mulberry32(profile.canvasNoise);

    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = makeNative(function(...args) {
      try {
        const ctx = this.getContext('2d');
        if (ctx) {
          const imageData = ctx.getImageData(0, 0, this.width, this.height);
          const data = imageData.data;
          // Apply subtle pixel noise
          for (let i = 0; i < data.length; i += 4) {
            data[i] = data[i] + Math.floor((canvasRng() - 0.5) * 2);     // R
            data[i+1] = data[i+1] + Math.floor((canvasRng() - 0.5) * 2); // G
          }
          ctx.putImageData(imageData, 0, 0);
        }
      } catch(e) {}
      return origToDataURL.apply(this, args);
    }, 'toDataURL');

    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = makeNative(function(...args) {
      try {
        const ctx = this.getContext('2d');
        if (ctx) {
          const imageData = ctx.getImageData(0, 0, this.width, this.height);
          const data = imageData.data;
          for (let i = 0; i < data.length; i += 4) {
            data[i] = data[i] + Math.floor((canvasRng() - 0.5) * 2);
          }
          ctx.putImageData(imageData, 0, 0);
        }
      } catch(e) {}
      return origToBlob.apply(this, args);
    }, 'toBlob');
  } catch(e) {}

  // --- WebGL fingerprint ---
  try {
    const origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = makeNative(function(pname) {
      const UNMASKED_VENDOR = 0x9245;
      const UNMASKED_RENDERER = 0x9246;
      if (pname === UNMASKED_VENDOR) return profile.webglVendor;
      if (pname === UNMASKED_RENDERER) return profile.webglRenderer;
      return origGetParam.call(this, pname);
    }, 'getParameter');

    if (typeof WebGL2RenderingContext !== 'undefined') {
      const origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
      WebGL2RenderingContext.prototype.getParameter = makeNative(function(pname) {
        const UNMASKED_VENDOR = 0x9245;
        const UNMASKED_RENDERER = 0x9246;
        if (pname === UNMASKED_VENDOR) return profile.webglVendor;
        if (pname === UNMASKED_RENDERER) return profile.webglRenderer;
        return origGetParam2.call(this, pname);
      }, 'getParameter');
    }
  } catch(e) {}

  // --- AudioContext fingerprint noise ---
  try {
    const audioRng = mulberry32(profile.audioNoise);
    const origCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = makeNative(function() {
      const osc = origCreateOscillator.call(this);
      const origConnect = osc.connect.bind(osc);
      osc.connect = makeNative(function(dest, ...args) {
        if (dest instanceof AnalyserNode) {
          // Inject a gain node with tiny noise
          const gainNode = osc.context.createGain();
          gainNode.gain.value = 1 + (audioRng() - 0.5) * 0.0001;
          origConnect(gainNode);
          gainNode.connect(dest);
          return dest;
        }
        return origConnect(dest, ...args);
      }, 'connect');
      return osc;
    }, 'createOscillator');
  } catch(e) {}

  // --- WebRTC protection ---
  try {
    if (profile.webrtcPolicy === 'block') {
      window.RTCPeerConnection = makeNative(function() {
        throw new DOMException('WebRTC is disabled', 'NotAllowedError');
      }, 'RTCPeerConnection');
      window.webkitRTCPeerConnection = window.RTCPeerConnection;
      if (window.RTCSessionDescription) {
        window.RTCSessionDescription = makeNative(function() {
          throw new DOMException('WebRTC is disabled', 'NotAllowedError');
        }, 'RTCSessionDescription');
      }
    }
  } catch(e) {}

  // ========== iframe sync ==========
  try {
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.tagName === 'IFRAME') {
            injectIntoIframe(node);
          }
        });
      });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    function injectIntoIframe(iframe) {
      const tryInject = function(attempt) {
        try {
          const win = iframe.contentWindow;
          if (!win || win.__stealth_applied__) return;
          // Re-apply critical overrides in iframe context
          Object.defineProperty(win.navigator, 'webdriver', {
            get: function() { return false; },
            configurable: true,
          });
          win.__stealth_applied__ = true;
        } catch(e) {
          // Cross-origin iframe — cannot access, skip silently
          if (attempt < 3) {
            requestAnimationFrame(function() { tryInject(attempt + 1); });
          }
        }
      };
      iframe.addEventListener('load', function() { tryInject(0); });
      tryInject(0);
    }

    // Process existing iframes
    document.querySelectorAll('iframe').forEach(injectIntoIframe);
  } catch(e) {}

})();`;
}
