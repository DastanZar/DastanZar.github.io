(() => {
  const root = document.documentElement;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const staticMode = new URLSearchParams(window.location.search).has("static") || reduceMotion;

  if (staticMode) {
    root.classList.add("static");
  }

  // Open the curtain after a frame so the hero lines can animate in.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => root.classList.add("is-ready"));
  });

  // Scroll progress + masthead state.
  const progress = document.querySelector(".progress i");
  const masthead = document.querySelector(".masthead");
  let scrollQueued = false;

  const updateScrollUI = () => {
    const max = root.scrollHeight - window.innerHeight;
    if (progress) {
      progress.style.width = `${max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 0}%`;
    }
    if (masthead) {
      masthead.classList.toggle("is-scrolled", window.scrollY > 8);
    }
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

  // Scroll reveals.
  if (!staticMode && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -6% 0px" }
    );

    document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));

    document.querySelectorAll(".ship-row").forEach((row, index) => {
      row.style.transitionDelay = `${Math.min(index * 0.045, 0.27)}s`;
    });
    document.querySelectorAll(".method-step").forEach((step, index) => {
      step.style.transitionDelay = `${index * 0.09}s`;
    });
  } else {
    document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-in"));
  }

  // Receipt viewer ---------------------------------------------------------
  const receipts = window.RECEIPTS || {};
  const order = window.RECEIPT_ORDER || Object.keys(receipts);
  const tabList = document.querySelector(".tabs");
  const pre = document.getElementById("receiptJson");
  const fileLabel = document.getElementById("receiptFile");
  const projectLabel = document.getElementById("receiptProject");
  const rawLink = document.getElementById("receiptRaw");
  const meta = document.getElementById("receiptMeta");
  const lines = document.getElementById("receiptLines");

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

  const activateReceipt = (slug) => {
    const entry = receipts[slug];
    if (!entry || !pre) return;

    document.querySelectorAll(".tab").forEach((tab) => {
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

  // Floating evidence preview for the shipping index -----------------------
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
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

    document.querySelectorAll(".ship-row[data-preview]").forEach((row) => {
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
})();
