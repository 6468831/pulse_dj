(function attachRuntimeCore(global) {
  const DEFAULTS = {
    endpoint: "/api/runtime/events/",
    automaticPageViews: true,
    captureClicks: true,
    captureErrors: true,
    captureWebVitals: true,
    fingerprintLevel: "basic",
    batchSize: 20,
    flushIntervalMs: 5000,
    sessionTimeoutMs: 30 * 60 * 1000,
    storagePrefix: "runtime_core"
  }

  const state = {
    options: { ...DEFAULTS },
    queue: [],
    timer: null,
    initialized: false
  }

  function uuid() {
    if (global.crypto && global.crypto.randomUUID) {
      return global.crypto.randomUUID()
    }
    const bytes = new Uint8Array(16)
    global.crypto.getRandomValues(bytes)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    return [...bytes].map((byte, index) => {
      const value = byte.toString(16).padStart(2, "0")
      return [4, 6, 8, 10].includes(index) ? `-${value}` : value
    }).join("")
  }

  function storageKey(name) {
    return `${state.options.storagePrefix}.${name}`
  }

  function readStored(name) {
    try {
      return global.localStorage.getItem(storageKey(name))
    } catch {
      return null
    }
  }

  function writeStored(name, value) {
    try {
      global.localStorage.setItem(storageKey(name), value)
    } catch {
      document.cookie = `${storageKey(name)}=${encodeURIComponent(value)}; path=/; SameSite=Lax`
    }
  }

  function anonymousId() {
    let value = readStored("anonymous_id")
    if (!value) {
      value = uuid()
      writeStored("anonymous_id", value)
    }
    return value
  }

  function sessionId() {
    const now = Date.now()
    const lastSeen = Number(readStored("session_seen_at") || 0)
    let value = readStored("session_id")
    if (!value || now - lastSeen > state.options.sessionTimeoutMs) {
      value = uuid()
      writeStored("session_id", value)
    }
    writeStored("session_seen_at", String(now))
    return value
  }

  function campaign() {
    const params = new URLSearchParams(global.location.search)
    return {
      source: params.get("utm_source"),
      medium: params.get("utm_medium"),
      campaign: params.get("utm_campaign"),
      term: params.get("utm_term"),
      content: params.get("utm_content")
    }
  }

  function bucket(value, buckets) {
    const found = buckets.find((limit) => value <= limit)
    return found ? `<=${found}` : `>${buckets[buckets.length - 1]}`
  }

  function clientHints() {
    const uaData = navigator.userAgentData
    if (!uaData) {
      return {}
    }
    return {
      brands: uaData.brands || [],
      mobile: uaData.mobile,
      platform: uaData.platform
    }
  }

  function browserFeatures(level) {
    if (level === "disabled") {
      return {}
    }
    const features = {
      user_agent: navigator.userAgent,
      languages: navigator.languages || [navigator.language],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      screen_bucket: `${bucket(screen.width, [480, 768, 1024, 1440, 1920])}x${bucket(screen.height, [640, 900, 1080, 1440])}`,
      viewport_bucket: `${bucket(global.innerWidth, [480, 768, 1024, 1440, 1920])}x${bucket(global.innerHeight, [640, 900, 1080, 1440])}`,
      device_pixel_ratio: global.devicePixelRatio || 1,
      hardware_concurrency: navigator.hardwareConcurrency || null,
      device_memory: navigator.deviceMemory || null,
      touch: navigator.maxTouchPoints > 0,
      storage: Boolean(global.localStorage),
      client_hints: clientHints()
    }
    if (level === "extended") {
      features.webgl = webglInfo()
      features.codecs = codecInfo()
      features.capabilities = {
        service_worker: "serviceWorker" in navigator,
        bluetooth: "bluetooth" in navigator,
        credentials: "credentials" in navigator
      }
    }
    return features
  }

  function webglInfo() {
    try {
      const canvas = document.createElement("canvas")
      const gl = canvas.getContext("webgl")
      const debugInfo = gl && gl.getExtension("WEBGL_debug_renderer_info")
      if (!gl || !debugInfo) {
        return {}
      }
      return {
        vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
        renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
      }
    } catch {
      return {}
    }
  }

  function codecInfo() {
    const video = document.createElement("video")
    return {
      h264: video.canPlayType('video/mp4; codecs="avc1.42E01E"'),
      vp9: video.canPlayType('video/webm; codecs="vp9"'),
      av1: video.canPlayType('video/mp4; codecs="av01.0.05M.08"')
    }
  }

  function page() {
    return {
      url: global.location.href,
      path: global.location.pathname,
      title: document.title,
      referrer: document.referrer || null
    }
  }

  function baseEvent(eventName, properties) {
    return {
      schema_version: 1,
      event_id: uuid(),
      event_name: eventName,
      occurred_at: new Date().toISOString(),
      anonymous_id: anonymousId(),
      session_id: sessionId(),
      page: page(),
      campaign: campaign(),
      browser_features: browserFeatures(state.options.fingerprintLevel),
      properties: properties || {}
    }
  }

  function enqueue(event) {
    state.queue.push(event)
    if (state.queue.length >= state.options.batchSize) {
      flush()
    }
  }

  function flush() {
    if (!state.queue.length) {
      return
    }
    const payload = JSON.stringify({ events: state.queue.splice(0, state.options.batchSize) })
    const blob = new Blob([payload], { type: "application/json" })
    if (navigator.sendBeacon && navigator.sendBeacon(state.options.endpoint, blob)) {
      return
    }
    fetch(state.options.endpoint, {
      method: "POST",
      body: payload,
      headers: { "Content-Type": "application/json" },
      keepalive: true,
      credentials: "same-origin"
    }).catch(() => {
      state.queue.unshift(...JSON.parse(payload).events)
    })
  }

  function track(eventName, properties) {
    enqueue(baseEvent(eventName, properties))
  }

  function capturePageViews() {
    track("page_view")
    const originalPushState = history.pushState
    const originalReplaceState = history.replaceState
    function afterNavigation(fn) {
      return function wrapped() {
        const result = fn.apply(this, arguments)
        setTimeout(() => track("page_view"), 0)
        return result
      }
    }
    history.pushState = afterNavigation(originalPushState)
    history.replaceState = afterNavigation(originalReplaceState)
    global.addEventListener("popstate", () => track("page_view"))
  }

  function captureClicks() {
    document.addEventListener("click", (event) => {
      const anchor = event.target.closest && event.target.closest("a")
      if (!anchor || !anchor.href) {
        return
      }
      const url = new URL(anchor.href, global.location.href)
      const isOutbound = url.origin !== global.location.origin
      const isDownload = anchor.hasAttribute("download") || /\.(zip|pdf|csv|xlsx?|docx?)$/i.test(url.pathname)
      if (isOutbound || isDownload) {
        track(isDownload ? "download_click" : "outbound_click", {
          href: url.href,
          text: (anchor.textContent || "").trim().slice(0, 120)
        })
      }
    }, true)
  }

  function captureForms() {
    document.addEventListener("submit", (event) => {
      const form = event.target
      track("form_submitted", {
        id: form.id || null,
        name: form.getAttribute("name"),
        action_path: form.action ? new URL(form.action).pathname : null
      })
    }, true)
  }

  function captureErrors() {
    global.addEventListener("error", (event) => {
      track("javascript_error", {
        message: event.message,
        source: event.filename,
        line: event.lineno,
        column: event.colno
      })
    })
    global.addEventListener("unhandledrejection", (event) => {
      track("javascript_error", {
        message: String(event.reason && event.reason.message ? event.reason.message : event.reason)
      })
    })
  }

  function captureWebVitals() {
    if (!("PerformanceObserver" in global)) {
      return
    }
    const observers = [
      ["largest-contentful-paint", "web_vital_lcp"],
      ["layout-shift", "web_vital_cls"],
      ["event", "web_vital_inp"]
    ]
    observers.forEach(([type, name]) => {
      try {
        const observer = new PerformanceObserver((list) => {
          list.getEntries().forEach((entry) => {
            track(name, { value: entry.value || entry.startTime, rating_source: type })
          })
        })
        observer.observe({ type, buffered: true })
      } catch {
        return undefined
      }
      return undefined
    })
  }

  function init(options) {
    if (state.initialized) {
      return
    }
    state.options = { ...DEFAULTS, ...(options || {}) }
    state.initialized = true
    if (state.options.automaticPageViews) {
      capturePageViews()
    }
    if (state.options.captureClicks) {
      captureClicks()
      captureForms()
    }
    if (state.options.captureErrors) {
      captureErrors()
    }
    if (state.options.captureWebVitals) {
      captureWebVitals()
    }
    state.timer = global.setInterval(flush, state.options.flushIntervalMs)
    global.addEventListener("pagehide", flush)
  }

  global.RuntimeCore = { init, track, flush }
})(window)
