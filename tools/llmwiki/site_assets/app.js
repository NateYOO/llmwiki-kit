/* llmwiki site — 검색·필터·「Codex에게 물어보기」 복사 (외부 라이브러리 없음, file://에서도 동작) */
(function () {
  "use strict";
  var ROOT = document.body.getAttribute("data-root") || "";
  var INDEX = window.LLMWIKI_INDEX || [];

  /* ---------- 알림 ---------- */
  var toastTimer;
  function toast(msg) {
    var t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, 2600);
  }

  /* ---------- 복사: clipboard API → execCommand → 선택된 상자 ---------- */
  function showBox(text) {
    var box = document.getElementById("copybox");
    if (!box) { window.prompt("Ctrl+C로 복사하세요", text); return; }
    var ta = box.querySelector("textarea");
    ta.value = text;
    box.hidden = false;
    ta.focus();
    ta.select();
  }
  function legacyCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.top = "-1000px"; ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, text.length);
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }
  function copyText(text) {
    var done = function () { toast("복사했어요 — Codex 채팅에 붙여넣으세요"); };
    var fallback = function () { if (legacyCopy(text)) done(); else showBox(text); };
    try {
      if (navigator.clipboard && window.isSecureContext !== false) {
        navigator.clipboard.writeText(text).then(done, fallback);
        return;
      }
    } catch (e) { /* 아래 대체 경로 */ }
    fallback();
  }
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("[data-ask]") : null;
    if (b) { ev.preventDefault(); copyText(b.getAttribute("data-ask")); }
    /* 나중에 서버의 POST /api/ask(로컬 codex exec)가 생기면 여기서 http:// 일 때만 호출하도록 붙인다. 지금은 복사만. */
  });
  var box = document.getElementById("copybox");
  if (box) {
    box.querySelector(".close").addEventListener("click", function () { box.hidden = true; });
    box.addEventListener("click", function (e) { if (e.target === box) box.hidden = true; });
  }

  /* ---------- 검색 ---------- */
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function mark(s, terms) {
    var out = esc(s);
    terms.forEach(function (t) {
      if (!t) return;
      var re = new RegExp("(" + esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }
  function snippet(text, terms) {
    var low = text.toLowerCase(), pos = -1;
    for (var i = 0; i < terms.length && pos < 0; i++) pos = low.indexOf(terms[i]);
    if (pos < 0) return text.slice(0, 120);
    var s = Math.max(0, pos - 50);
    return (s > 0 ? "…" : "") + text.slice(s, s + 150) + (s + 150 < text.length ? "…" : "");
  }
  function search(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    var hits = [];
    INDEX.forEach(function (d) {
      var title = (d.t || "").toLowerCase(), au = (d.a || "").toLowerCase(), body = (d.x || "").toLowerCase();
      var score = 0;
      for (var i = 0; i < terms.length; i++) {
        var t = terms[i], s = 0;
        if (title.indexOf(t) >= 0) s += 6;
        if (au.indexOf(t) >= 0) s += 4;
        if (body.indexOf(t) >= 0) s += 1 + Math.min(3, body.split(t).length - 2);
        if (!s) return;
        score += s;
      }
      if (d.k === "논문") score += 2;
      hits.push({ d: d, score: score });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    return hits.slice(0, 30).map(function (h) { return { d: h.d, terms: terms }; });
  }
  var q = document.getElementById("q"), res = document.getElementById("results"), sel = -1;
  function render() {
    var v = q.value.trim();
    if (!v) { res.hidden = true; res.innerHTML = ""; return; }
    var hits = search(v);
    if (!INDEX.length) {
      res.innerHTML = '<div class="none">검색 색인이 없어요. Codex에게 “위키 화면 새로 만들어 줘”라고 말하세요.</div>';
    } else if (!hits.length) {
      res.innerHTML = '<div class="none">“' + esc(v) + '” — 내 위키에 없음. 다른 단어(영어 원어/한국어)로 찾아보거나, 💬 Codex에게 물어보기로 넣을 논문 검색어를 받아 보세요.</div>';
    } else {
      res.innerHTML = '<div class="none">' + hits.length + '건' + (hits.length >= 30 ? " (상위 30)" : "") + "</div>" + hits.map(function (h) {
        var d = h.d;
        var sub = d.k === "논문" ? [d.y, d.a].filter(Boolean).join(" · ") + " — " + snippet(d.x || "", h.terms) : snippet(d.x || "", h.terms);
        return '<a href="' + esc(ROOT + d.u) + '"><span class="k">' + esc(d.k) + '</span><span class="t">' + mark(d.t, h.terms) +
          '</span><span class="s">' + mark(sub, h.terms) + "</span></a>";
      }).join("");
    }
    sel = -1;
    res.hidden = false;
  }
  if (q && res) {
    q.addEventListener("input", render);
    q.addEventListener("focus", render);
    q.addEventListener("keydown", function (e) {
      var items = res.querySelectorAll("a");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!items.length) return;
        sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        items.forEach(function (a, i) { a.classList.toggle("sel", i === sel); });
        items[sel].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        var a = items[sel >= 0 ? sel : 0];
        if (a) window.location.href = a.getAttribute("href");
      } else if (e.key === "Escape") { res.hidden = true; q.blur(); }
    });
    document.addEventListener("click", function (e) { if (!e.target.closest(".search")) res.hidden = true; });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== q && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); }
    });
    var m = /[?&]q=([^&]+)/.exec(window.location.search);
    if (m) { q.value = decodeURIComponent(m[1].replace(/\+/g, " ")); render(); }
  }

  /* ---------- 홈: 연도·주제 필터 ---------- */
  var fy = document.getElementById("f-year"), fg = document.getElementById("f-group"), fc = document.getElementById("f-count");
  function filter() {
    var cards = document.querySelectorAll("#paper-list .card"), shown = 0;
    cards.forEach(function (c) {
      var okY = !fy.value || c.getAttribute("data-year") === fy.value;
      var okG = !fg.value || ("|" + c.getAttribute("data-groups") + "|").indexOf("|" + fg.value + "|") >= 0;
      c.hidden = !(okY && okG);
      if (okY && okG) shown++;
    });
    if (fc) fc.textContent = cards.length + "편 중 " + shown + "편 표시";
  }
  if (fy && fg) { fy.addEventListener("change", filter); fg.addEventListener("change", filter); filter(); }
})();
