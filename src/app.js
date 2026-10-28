(() => {
  const root = document.documentElement;
  const params = new URLSearchParams(window.location.search);
  const staticQuery = params.has("static");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const staticMode = staticQuery || reduceMotion;
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  if (staticMode) root.classList.add("static");
  if (reduceMotion) root.classList.add("reduce-motion");

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

  // Open the curtain after a frame so the hero lines can animate in.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => root.classList.add("is-ready"));
  });

  // -----------------------------------------------------------------------
  // Scroll progress + masthead
  // -----------------------------------------------------------------------
  const progress = $(".progress i");
  const masthead = $(".masthead");
  let scrollQueued = false;

  const updateScrollUI = () => {
    const max = root.scrollHeight - window.innerHeight;
    const raw = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    if (progress) progress.style.width = `${raw * 100}%`;
    root.style.setProperty("--scroll-rot", `${raw * 12}deg`);
    if (masthead) masthead.classList.toggle("is-scrolled", window.scrollY > 8);
    scrollQueued = false;
  };

  window.addEventListener(
    "scroll",
    () => {
      if (!scrollQueued) {
        scrollQueued = true;
        requestAnimationFrame(updateScrollUI);
      }
    },
    { passive: true }
  );
  updateScrollUI();

  // -----------------------------------------------------------------------
  // Split display type into tracks. Word-level, not opacity stacks.
  // -----------------------------------------------------------------------
  const splitWords = () => {
    $$("[data-split]").forEach((element) => {
      let wordIndex = 0;

      const walk = (node) => {
        [...node.childNodes].forEach((child) => {
          if (child.nodeType === Node.TEXT_NODE) {
            const text = child.textContent;
            if (!text.trim()) return;
            const fragment = document.createDocumentFragment();
            text.split(/(\s+)/).forEach((part) => {
              if (!part) return;
              if (/^\s+$/.test(part)) {
                fragment.appendChild(document.createTextNode(part));
                return;
              }
              const word = document.createElement("span");
              word.className = "word";
              word.style.setProperty("--word-i", String(wordIndex++));
              const inner = document.createElement("span");
              inner.textContent = part;
              word.appendChild(inner);
              fragment.appendChild(word);
            });
            child.replaceWith(fragment);
            return;
          }
          if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== "BR") {
            walk(child);
          }
        });
      };

      walk(element);
      element.classList.add("is-split");
    });
  };

  splitWords();

  // -----------------------------------------------------------------------
  // Typewriter headings (Doto). Characters stay in the document and only
  // their opacity animates, so nothing reflows while it types and the
  // heading still reads correctly without JavaScript.
  // -----------------------------------------------------------------------
  const twElements = $$("[data-tw]");

  if (twElements.length && !staticMode) {
    const twSplit = (element) => {
      const chars = [];
      const walk = (node) => {
        [...node.childNodes].forEach((child) => {
          if (child.nodeType === Node.TEXT_NODE) {
            const text = child.textContent;
            if (!text) return;
            const fragment = document.createDocumentFragment();
            for (const character of text) {
              if (/\s/.test(character)) {
                fragment.appendChild(document.createTextNode(character));
                continue;
              }
              const span = document.createElement("span");
              span.className = "tw-c";
              span.textContent = character;
              fragment.appendChild(span);
              chars.push(span);
            }
            child.replaceWith(fragment);
            return;
          }
          if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== "BR") walk(child);
        });
      };
      walk(element);
      return chars;
    };

    const twState = twElements.map((element) => {
      const label = element.textContent.replace(/\s+/g, " ").trim();
      const chars = twSplit(element);
      if (chars.length) element.setAttribute("aria-label", label);
      return { element, chars, timer: 0, once: Boolean(element.closest(".hero")), done: false };
    });

    root.classList.add("tw");

    const twType = (state) => {
      const { chars } = state;
      if (!chars.length) return;
      window.clearTimeout(state.timer);
      chars.forEach((char) => char.classList.remove("is-on", "is-cursor"));
      // keep every heading between roughly 0.9s and 1.6s, long or short
      const per = Math.max(16, Math.min(52, Math.round(1300 / chars.length)));
      let index = 0;
      const step = () => {
        if (index > 0) chars[index - 1].classList.remove("is-cursor");
        if (index >= chars.length) return;
        chars[index].classList.add("is-on", "is-cursor");
        index += 1;
        state.timer = window.setTimeout(step, per);
      };
      step();
    };

    const twClear = (state) => {
      window.clearTimeout(state.timer);
      state.chars.forEach((char) => char.classList.remove("is-on", "is-cursor"));
    };

    if ("IntersectionObserver" in window) {
      const twObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            const state = twState.find((item) => item.element === entry.target);
            if (!state) return;
            if (entry.isIntersecting) {
              if (state.done) return;
              twType(state);
              if (state.once) {
                state.done = true;
                twObserver.unobserve(entry.target);
              }
            } else if (!state.once) {
              twClear(state);
            }
          });
        },
        { threshold: 0.3 }
      );

      twState.forEach((state) => {
        if (state.once) {
          const rect = state.element.getBoundingClientRect();
          if (rect.top < window.innerHeight && rect.bottom > 0) {
            twType(state);
            state.done = true;
            return;
          }
        }
        twObserver.observe(state.element);
      });
    }
  }

  // -----------------------------------------------------------------------
  // Theme switcher: surface + signal, remembered per browser.
  // -----------------------------------------------------------------------
  const THEMES = [
    ["light", "Light", "#f2efe5", "#141511"],
    ["espresso", "Espresso", "#1a1512", "#f3ece1"],
    ["graphite", "Graphite", "#201f1a", "#f4f1e8"],
    ["forest", "Forest", "#101710", "#e9f0e4"],
    ["navy", "Navy", "#0f1520", "#e8eef7"],
    ["plum", "Plum", "#17121b", "#efe8f2"],
    ["slate", "Slate", "#17191c", "#eceef0"],
    ["night", "Night", "#000000", "#ffffff"],
    ["olive", "Olive", "#191a12", "#f0efe0"],
    ["amber", "Amber", "#0b0b09", "#ded9c6"],
  ];
  const ACCENTS = [
    ["auto", "Auto", null],
    ["signal", "Signal", "#e9491b"],
    ["coral", "Coral", "#ff6a3d"],
    ["amber", "Amber", "#ffb000"],
    ["lime", "Lime", "#b6e05a"],
    ["cyan", "Cyan", "#5ad1e0"],
    ["magenta", "Magenta", "#ff5f9e"],
    ["sage", "Sage", "#aab6a0"],
    ["red", "Red", "#ff4d4d"],
  ];

  const themeToggle = $("[data-theme-toggle]");
  const themePanel = $("[data-theme-panel]");
  const baseHost = $("[data-theme-bases]");
  const accentHost = $("[data-theme-accents]");
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  if (themeToggle && themePanel && baseHost && accentHost) {
    const prefs = {
      theme: root.getAttribute("data-theme") || "light",
      accent: root.getAttribute("data-accent") || "auto",
    };
    const baseSwatches = new Map();
    const accentSwatches = new Map();
    const themeGround = (id) => (THEMES.find((t) => t[0] === id) || THEMES[0])[2];

    const syncPressed = () => {
      baseSwatches.forEach((button, id) => {
        button.setAttribute("aria-pressed", String(prefs.theme === id));
        button.classList.toggle("is-on", prefs.theme === id);
      });
      accentSwatches.forEach((button, id) => {
        button.setAttribute("aria-pressed", String(prefs.accent === id));
        button.classList.toggle("is-on", prefs.accent === id);
      });
    };

    const apply = () => {
      root.setAttribute("data-theme", prefs.theme);
      root.setAttribute("data-accent", prefs.accent);
      if (themeMeta) themeMeta.setAttribute("content", themeGround(prefs.theme));
      syncPressed();
      try {
        localStorage.setItem("mlsys.theme.v1", JSON.stringify(prefs));
      } catch (error) {}
    };

    THEMES.forEach(([id, name, bg, ink]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "theme-swatch";
      button.setAttribute("aria-pressed", "false");
      const chip = document.createElement("span");
      chip.className = "theme-chip";
      chip.style.background = bg;
      chip.style.boxShadow = `inset 0 0 0 1px ${ink}`;
      const text = document.createElement("span");
      text.textContent = name;
      button.append(chip, text);
      button.addEventListener("click", () => {
        prefs.theme = id;
        apply();
      });
      baseSwatches.set(id, button);
      baseHost.appendChild(button);
    });

    ACCENTS.forEach(([id, name, value]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "theme-swatch is-accents";
      button.setAttribute("aria-pressed", "false");
      button.title = id === "auto" ? "Use the surface's own signal colour" : name;
      button.setAttribute("aria-label", name);
      const chip = document.createElement("span");
      chip.className = "theme-chip";
      chip.style.background =
        id === "auto"
          ? "conic-gradient(from 30deg, #e9491b, #ffb000, #b6e05a, #5ad1e0, #ff5f9e, #e9491b)"
          : value;
      button.appendChild(chip);
      button.addEventListener("click", () => {
        prefs.accent = id;
        apply();
      });
      accentSwatches.set(id, button);
      accentHost.appendChild(button);
    });

    const closePanel = () => {
      themePanel.hidden = true;
      themeToggle.setAttribute("aria-expanded", "false");
    };

    themeToggle.addEventListener("click", () => {
      const opening = themePanel.hidden;
      themePanel.hidden = !opening;
      themeToggle.setAttribute("aria-expanded", String(opening));
    });

    document.addEventListener("click", (event) => {
      if (themePanel.hidden) return;
      if (!event.target.closest("[data-theme-widget]")) closePanel();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !themePanel.hidden) {
        closePanel();
        themeToggle.focus();
      }
    });

    syncPressed();
  }

  // -----------------------------------------------------------------------
  // Reveals + section rules + chart print
  // -----------------------------------------------------------------------
  const revealElements = $$(".reveal");
  const sectionElements = $$(".section");
  const splitElements = $$("[data-split]");
  const vizElements = $$(".mini-viz");
  const headElements = $$(".section-head");

  const addState = (elements, className) => {
    elements.forEach((element) => element.classList.add(className));
  };

  if (staticMode || !("IntersectionObserver" in window)) {
    addState(revealElements, "is-in");
    addState(sectionElements, "is-section-in");
    addState(splitElements, "is-in");
    addState(vizElements, "is-in");
    addState(headElements, "is-in");
    $$(".ship-row").forEach((row) => row.classList.add("is-in"));
  } else {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-in");
          if (entry.target.classList.contains("section")) {
            entry.target.classList.add("is-section-in");
          }
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -4% 0px" }
    );

    [...revealElements, ...sectionElements, ...splitElements, ...vizElements, ...headElements].forEach((element) =>
      observer.observe(element)
    );

    const staggerGroups = [
      $$(".case-duo .case-mini"),
      $$(".ship-list .ship-row"),
      $$(".inventory-theme"),
      $$(".method-grid .method-step"),
    ];
    staggerGroups.forEach((group) =>
      group.forEach((element, index) => element.style.setProperty("--reveal-i", String(index % 6)))
    );
  }

  // -----------------------------------------------------------------------
  // Count-ups: tabular numbers, final state for static/reduced motion
  // -----------------------------------------------------------------------
  const counters = $$("[data-count]");
  const counterValue = (element, value) => {
    const decimals = Number(element.dataset.decimals || 0);
    const suffix = element.dataset.suffix || "";
    return `${value.toFixed(decimals)}${suffix}`;
  };

  const finishCounter = (element) => {
    const target = Number(element.dataset.count);
    element.textContent = counterValue(element, target);
    element.dataset.counted = "true";
  };

  const runCounter = (element) => {
    if (element.dataset.counted === "true") return;
    element.dataset.counted = "true";
    if (staticMode) {
      finishCounter(element);
      return;
    }
    const target = Number(element.dataset.count);
    const duration = 920;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = counterValue(element, target * eased);
      if (progress < 1) requestAnimationFrame(tick);
      else element.textContent = counterValue(element, target);
    };
    requestAnimationFrame(tick);
  };

  if (counters.length) {
    if (!staticMode) counters.forEach((element) => (element.textContent = counterValue(element, 0)));
    if (staticMode || !("IntersectionObserver" in window)) {
      counters.forEach(finishCounter);
    } else {
      const counterObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            runCounter(entry.target);
            counterObserver.unobserve(entry.target);
          });
        },
        { threshold: 0.45 }
      );
      counters.forEach((element) => counterObserver.observe(element));
      window.setTimeout(() => $$(".proof [data-count]").forEach(runCounter), 900);
    }
  }

  // -----------------------------------------------------------------------
  // Active section in the masthead
  // -----------------------------------------------------------------------
  const navLinks = $$(".nav-links a");
  const sectionTargets = navLinks
    .map((link) => {
      const id = link.getAttribute("href");
      return id && id.startsWith("#") ? $(id) : null;
    })
    .filter(Boolean);

  if (sectionTargets.length && "IntersectionObserver" in window && !staticMode) {
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          navLinks.forEach((link) => {
            const active = link.getAttribute("href") === `#${entry.target.id}`;
            link.classList.toggle("is-active", active);
            if (active) link.setAttribute("aria-current", "location");
            else link.removeAttribute("aria-current");
          });
        });
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: 0 }
    );
    sectionTargets.forEach((section) => sectionObserver.observe(section));
  }

  // -----------------------------------------------------------------------
  // Receipt console
  // -----------------------------------------------------------------------
  const receipts = window.RECEIPTS || {};
  const order = window.RECEIPT_ORDER || Object.keys(receipts);
  const tabList = $(".tabs");
  const pre = $("#receiptJson");
  const fileLabel = $("#receiptFile");
  const projectLabel = $("#receiptProject");
  const rawLink = $("#receiptRaw");
  const meta = $("#receiptMeta");
  const lines = $("#receiptLines");
  const consoleEl = $(".console");

  const escapeHtml = (value) =>
    value.replace(/[&<>"']/g, (char) => {
      switch (char) {
        case "&":
          return "&amp;";
        case "<":
          return "&lt;";
        case ">":
          return "&gt;";
        case '"':
          return "&quot;";
        case "'":
          return "&#39;";
        default:
          return char;
      }
    });

  const highlightJson = (json) =>
    json.replace(
      /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let className = "tok-num";
        if (/^"/.test(match)) {
          className = /:\s*$/.test(match) ? "tok-key" : "tok-str";
        } else if (/true|false/.test(match)) {
          className = "tok-bool";
        } else if (/null/.test(match)) {
          className = "tok-null";
        }
        return `<span class="${className}">${escapeHtml(match)}</span>`;
      }
    );

  const printConsole = () => {
    if (!consoleEl || staticMode) return;
    consoleEl.classList.remove("is-printing");
    void consoleEl.offsetWidth;
    consoleEl.classList.add("is-printing");
    window.setTimeout(() => consoleEl.classList.remove("is-printing"), 620);
  };

  const activateReceipt = (slug) => {
    const entry = receipts[slug];
    if (!entry || !pre) return;

    $$(".tab").forEach((tab) => {
      tab.setAttribute("aria-selected", String(tab.dataset.receipt === slug));
    });

    const json = JSON.stringify(entry.data, null, 2);
    const code = pre.querySelector("code") || pre;
    code.innerHTML = highlightJson(json);
    pre.scrollTop = 0;

    if (fileLabel) fileLabel.textContent = entry.label;
    if (projectLabel) projectLabel.textContent = entry.project || slug;
    if (rawLink) rawLink.href = entry.source;
    if (meta) meta.textContent = `source: ${entry.project || slug} / receipts/${entry.label}`;
    if (lines) {
      const lineCount = json.split("\n").length.toLocaleString("en-US");
      const byteCount = new Blob([json]).size.toLocaleString("en-US");
      lines.textContent = `${lineCount} lines / ${byteCount} bytes`;
    }
    printConsole();
  };

  if (tabList && pre) {
    tabList.querySelectorAll(".tab").forEach((tab) => {
      tab.setAttribute("aria-controls", "receiptJson");
      tab.addEventListener("click", () => activateReceipt(tab.dataset.receipt));
    });

    tabList.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      const tabs = [...tabList.querySelectorAll(".tab")];
      const active = tabs.findIndex((tab) => tab.getAttribute("aria-selected") === "true");
      const next = event.key === "ArrowRight" ? (active + 1) % tabs.length : (active - 1 + tabs.length) % tabs.length;
      tabs[next].focus();
      tabs[next].click();
      event.preventDefault();
    });

    const first = tabList.querySelector(".tab");
    if (first) activateReceipt(first.dataset.receipt);
  } else if (pre) {
    pre.querySelector("code").textContent = "No receipts were embedded in this build.";
  }

  // -----------------------------------------------------------------------
  // Ink: the one living object
  // -----------------------------------------------------------------------
  const figure = $("[data-ink-figure]");
  const bubble = $("[data-ink-bubble]");
  const tab = $("[data-ink-tab]");
  const tabBubble = $("[data-ink-tab-bubble]");
  const stage = $("[data-ink-stage]");
  const trickButtons = $$("[data-ink-trick]");
  let bubbleTimer = 0;
  let sayHoldTimer = 0;
  let trickTimer = 0;
  let pointTimer = 0;
  let tabSayTimer = 0;

  const say = (text, hold = 2900) => {
    if (!bubble || !text) return;
    window.clearTimeout(bubbleTimer);
    window.clearTimeout(sayHoldTimer);
    bubble.classList.add("is-swapping");
    bubbleTimer = window.setTimeout(() => {
      bubble.textContent = text;
      bubble.classList.remove("is-swapping");
    }, 110);
    sayHoldTimer = window.setTimeout(() => {
      if (!bubble) return;
      const idleLine = bubble.dataset.idle || "I count the calls.";
      bubble.classList.add("is-swapping");
      window.setTimeout(() => {
        bubble.textContent = idleLine;
        bubble.classList.remove("is-swapping");
      }, 110);
    }, hold);
  };

  const sayTab = (text, hold = 2800) => {
    if (!tab || !tabBubble || !text) return;
    window.clearTimeout(tabSayTimer);
    tabBubble.textContent = text;
    tabBubble.classList.add("is-on");
    tabSayTimer = window.setTimeout(() => tabBubble.classList.remove("is-on"), hold);
  };

  const randomLine = (lines) => lines[Math.floor(Math.random() * lines.length)];

  const endTrick = (delay = 0) => {
    window.clearTimeout(trickTimer);
    trickTimer = window.setTimeout(() => {
      if (!figure) return;
      figure.classList.remove(
        "is-hopping",
        "is-swirling",
        "is-pointing",
        "point-left",
        "point-right",
        "is-stamping",
        "is-happy",
        "is-startled"
      );
      figure.style.removeProperty("--point-head-tilt");
      figure.style.removeProperty("--point-lean");
      figure.style.removeProperty("--point-lean-rotate");
    }, delay);
  };

  const playTrick = (name, targetDirection) => {
    if (!figure || staticMode) return;
    const classes = [
      "is-hopping",
      "is-swirling",
      "is-pointing",
      "point-left",
      "point-right",
      "is-stamping",
      "is-happy",
      "is-startled",
    ];
    figure.classList.remove(...classes);
    void figure.offsetWidth;

    if (name === "point") {
      const direction = targetDirection || "left";
      figure.classList.add("is-pointing", `point-${direction}`);
      figure.style.setProperty("--point-head-tilt", direction === "left" ? "4deg" : "-4deg");
      figure.style.setProperty("--point-lean", direction === "left" ? "-3px" : "3px");
      figure.style.setProperty("--point-lean-rotate", direction === "left" ? "1deg" : "-1deg");
      say("that one has a receipt.");
      endTrick(1080);
      return;
    }

    const clss = { hop: "is-hopping", swirl: "is-swirling", stamp: "is-stamping", happy: "is-happy" }[name];
    if (!clss) return;
    figure.classList.add(clss);
    if (name === "hop") say("receipts first. vibes second.");
    if (name === "swirl") say("six tentacles. zero GPU claims.");
    if (name === "stamp") say("audited. still true.");
    if (name === "happy") say(randomLine(["mrrp.", "I checked it twice.", "the ledger is warm."]));
    endTrick(name === "swirl" ? 1080 : name === "stamp" ? 1520 : 960);
  };

  const setGaze = (event) => {
    if (!figure || !canHover || staticMode) return;
    const rect = figure.getBoundingClientRect();
    if (!rect.width) return;
    const x = Math.max(-1, Math.min(1, (event.clientX - (rect.left + rect.width / 2)) / (rect.width * 0.55)));
    const y = Math.max(-1, Math.min(1, (event.clientY - (rect.top + rect.height * 0.47)) / (rect.height * 0.45)));
    figure.style.setProperty("--ink-look-x", `${(x * 2.8).toFixed(2)}px`);
    figure.style.setProperty("--ink-look-y", `${(y * 2.2).toFixed(2)}px`);
    figure.style.setProperty("--ink-head-tilt", `${(x * 2.4).toFixed(2)}deg`);
  };

  const resetGaze = () => {
    if (!figure) return;
    figure.style.setProperty("--ink-look-x", "0px");
    figure.style.setProperty("--ink-look-y", "0px");
    figure.style.setProperty("--ink-head-tilt", "0deg");
  };

  if (figure && stage) {
    bubble.dataset.idle = "I count the calls.";

    figure.addEventListener("click", () => playTrick("happy"));
    trickButtons.forEach((button) => {
      button.addEventListener("click", () => playTrick(button.dataset.inkTrick));
    });

    if (reduceMotion) {
      trickButtons.forEach((button) => {
        button.disabled = true;
        button.title = "Ink is sitting still, in honour of reduced motion.";
      });
    }

    if (canHover && !staticMode) {
      stage.addEventListener("pointermove", setGaze, { passive: true });
      stage.addEventListener("pointerleave", resetGaze, { passive: true });
    }

    const pointTargets = $$("[data-ink-point]");
    pointTargets.forEach((target) => {
      target.addEventListener("pointerenter", () => {
        if (staticMode || !canHover) return;
        const targetRect = target.getBoundingClientRect();
        const figureRect = figure.getBoundingClientRect();
        const direction = targetRect.left + targetRect.width / 2 < figureRect.left + figureRect.width / 2 ? "left" : "right";
        window.clearTimeout(pointTimer);
        figure.classList.remove(
          "is-pointing",
          "point-left",
          "point-right",
          "is-hopping",
          "is-swirling",
          "is-stamping",
          "is-happy",
          "is-startled"
        );
        figure.classList.add("is-pointing", `point-${direction}`);
        figure.style.setProperty("--point-head-tilt", direction === "left" ? "4deg" : "-4deg");
        figure.style.setProperty("--point-lean", direction === "left" ? "-3px" : "3px");
        figure.style.setProperty("--point-lean-rotate", direction === "left" ? "1deg" : "-1deg");
        if (target.dataset.inkSay) say(target.dataset.inkSay, 2400);
        pointTimer = window.setTimeout(() => {
          figure.classList.remove("is-pointing", "point-left", "point-right");
        }, 1100);
      });
    });

    if (!staticMode) {
      window.setTimeout(() => {
        if (document.visibilityState !== "visible") return;
        playTrick("hop");
      }, 1180);
    }
  }

  // The margin companion: same character, smaller chair.
  if (tab) {
    tab.addEventListener("click", () => {
      if (staticMode) return;
      const tricks = ["is-hopping", "is-swirling", "is-pointing"];
      tab.classList.remove(...tricks);
      void tab.offsetWidth;
      const trick = randomLine(tricks);
      tab.classList.add(trick);
      window.setTimeout(() => tab.classList.remove(trick), 1000);
      sayTab(randomLine(["mrrp.", "still counting.", "the receipts are fine."]), 2200);
    });

    if (stage && "IntersectionObserver" in window && !staticMode) {
      let tabVisible = false;
      const stageObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            const next = !entry.isIntersecting;
            if (next === tabVisible) return;
            tabVisible = next;
            tab.classList.toggle("is-visible", next);
          });
        },
        { threshold: 0.08 }
      );
      stageObserver.observe(stage);
    }
  }

  // -----------------------------------------------------------------------
  // Pointer ink: card wash + registration square
  // -----------------------------------------------------------------------
  if (canHover && !staticMode) {
    const washTargets = ".case-mini, .proof-item, .method-step, .receipt-point, .inventory-card";
    let washQueued = false;
    let lastPointer = null;

    document.addEventListener(
      "pointermove",
      (event) => {
        lastPointer = event;
        if (washQueued) return;
        washQueued = true;
        requestAnimationFrame(() => {
          washQueued = false;
          if (!lastPointer) return;
          const target = lastPointer.target.closest(washTargets);
          if (!target) return;
          const rect = target.getBoundingClientRect();
          target.style.setProperty("--mx", `${lastPointer.clientX - rect.left}px`);
          target.style.setProperty("--my", `${lastPointer.clientY - rect.top}px`);
        });
      },
      { passive: true }
    );

    const reg = document.createElement("div");
    reg.className = "reg-cursor";
    reg.setAttribute("aria-hidden", "true");
    document.body.appendChild(reg);
    let cursorQueued = false;
    let cursorEvent = null;

    const moveReg = () => {
      cursorQueued = false;
      if (!cursorEvent) return;
      reg.style.left = `${cursorEvent.clientX}px`;
      reg.style.top = `${cursorEvent.clientY}px`;
      const interactive = cursorEvent.target.closest("a, button, .case-mini, .ship-row, .proof-item, .method-step, .receipt-point, .inventory-card");
      reg.classList.toggle("is-on", Boolean(interactive));
    };

    window.addEventListener(
      "pointermove",
      (event) => {
        cursorEvent = event;
        if (cursorQueued) return;
        cursorQueued = true;
        requestAnimationFrame(moveReg);
      },
      { passive: true }
    );

    window.addEventListener("pointerdown", () => reg.classList.add("is-press"), { passive: true });
    window.addEventListener("pointerup", () => reg.classList.remove("is-press"), { passive: true });
  }

  // Floating evidence preview for the shipping index -----------------------
  if (!staticMode && canHover) {
    const preview = document.createElement("div");
    preview.className = "cursor-preview";
    preview.setAttribute("aria-hidden", "true");
    preview.innerHTML =
      '<div class="preview-head"><span>receipt</span><b></b></div><img alt="" src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="><div class="preview-foot"><strong></strong><span></span></div>';
    document.body.appendChild(preview);

    const previewImage = preview.querySelector("img");
    const previewProject = preview.querySelector(".preview-head b");
    const previewMetric = preview.querySelector(".preview-foot strong");
    const previewLabel = preview.querySelector(".preview-foot span");

    const movePreview = (event) => {
      const width = preview.offsetWidth || 300;
      const height = preview.offsetHeight || 230;
      let x = event.clientX + 22;
      let y = event.clientY + 18;
      if (x + width > window.innerWidth - 16) x = event.clientX - width - 22;
      if (y + height > window.innerHeight - 16) y = event.clientY - height - 18;
      if (y < 80) y = 80;
      preview.style.left = `${Math.max(10, x)}px`;
      preview.style.top = `${Math.max(10, y)}px`;
    };

    $$(".ship-row[data-preview]").forEach((row) => {
      row.addEventListener("mouseenter", () => {
        previewImage.src = row.dataset.preview;
        previewProject.textContent = row.dataset.previewProject || "";
        previewMetric.textContent = row.dataset.previewMetric || "";
        previewLabel.textContent = row.dataset.previewLabel || "";
        preview.classList.add("is-visible");
      });
      row.addEventListener("mousemove", movePreview);
      row.addEventListener("mouseleave", () => preview.classList.remove("is-visible"));
      row.addEventListener("focus", () => preview.classList.remove("is-visible"));
    });

    window.addEventListener("scroll", () => preview.classList.remove("is-visible"), { passive: true });
  }

  // Keyboard shortcuts for Ink, only when the stage is focused.
  if (stage && !staticMode) {
    stage.addEventListener("keydown", (event) => {
      if (event.target.matches("button") && event.key !== "h" && event.key !== "s" && event.key !== "p" && event.key !== "t") return;
      const key = event.key.toLowerCase();
      const map = { h: "hop", s: "swirl", p: "point", t: "stamp" };
      if (!map[key]) return;
      event.preventDefault();
      playTrick(map[key]);
    });
  }

  // Avoid a stale hover state when leaving the window.
  window.addEventListener("blur", () => {
    if (figure) {
      figure.classList.remove("is-pointing", "point-left", "point-right");
      figure.style.removeProperty("--point-head-tilt");
    }
    if (tabBubble) tabBubble.classList.remove("is-on");
  });
})();
