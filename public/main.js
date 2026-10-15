// «Кварта»: живой календарь обжарки, источник заявки (UTM) и форма.
document.documentElement.classList.add("js");

const MONTHS = ["январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"];
const MONTHS_GEN = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
const DAYS = ["пн","вт","ср","чт","пт","сб","вс"];
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- календарь: считаем по минскому времени ---------- */
function minskToday() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Minsk", year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(new Date());
  const get = (t) => Number(parts.find((p) => p.type === t).value);
  return new Date(get("year"), get("month") - 1, get("day"));
}
const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
const weekday = (d) => (d.getDay() + 6) % 7; // пн = 0 … вс = 6
const nbsp = (s) => s.replace(/ /g, " ");
const dayMonth = (d) => nbsp(`${d.getDate()} ${MONTHS_GEN[d.getMonth()]}`);

function renderCalendar() {
  const today = minskToday();
  const wd = weekday(today);
  const roast = addDays(today, (3 - wd + 7) % 7); // ближайший четверг (сегодня, если четверг)
  const friday = addDays(roast, 1);
  const monday = addDays(roast, -3);

  let note;
  if (wd <= 1) note = `Закажите до конца среды, и в пятницу, ${dayMonth(friday)}, кофе будет у вас.`;
  else if (wd === 2) note = `Сегодня последний день, чтобы успеть к пятнице, ${dayMonth(friday)}.`;
  else if (wd === 3) note = `Сегодня жарим. Новые заказы привезём в пятницу, ${dayMonth(addDays(friday, 7))}.`;
  else if (wd === 4) note = `Сегодня развозим свежую партию. Закажите до конца среды, и в пятницу, ${dayMonth(friday)}, привезём вам.`;
  else note = `Закажите до конца среды, и в пятницу, ${dayMonth(friday)}, кофе будет у вас.`;

  // С пятницы по воскресенье листок уже показывает следующую неделю — так и подписываем.
  document.getElementById("cal-month").textContent = wd >= 4
    ? `След. неделя · ${MONTHS[roast.getMonth()]}`
    : `${MONTHS[roast.getMonth()]} ${roast.getFullYear()}`;
  document.getElementById("cal-num").textContent = roast.getDate();
  document.getElementById("cal-title").innerHTML =
    `<span class="visually-hidden">${dayMonth(roast)}, </span>` + (wd === 3 ? "сегодня&nbsp;—<br>жарим" : "четверг&nbsp;—<br>жарим");
  document.getElementById("cal-note").textContent = note;

  const week = document.getElementById("cal-week");
  week.innerHTML = "";
  for (let i = 0; i < 7; i++) {
    const d = addDays(monday, i);
    const li = document.createElement("li");
    const isToday = d.getTime() === today.getTime();
    const label = isToday ? "сегодня" : i === 3 ? "обжарка" : i === 4 ? "доставка" : String(d.getDate());
    li.innerHTML = `${DAYS[i]}<small>${label}</small>`;
    if (i === 3 || i === 4) li.classList.add("is-roast");
    if (isToday) { li.classList.add("is-today"); li.setAttribute("aria-current", "date"); }
    week.append(li);
  }
  if (!reduceMotion) document.getElementById("cal-page").classList.add("is-flipping");
}
renderCalendar();

/* ---------- появление блоков при скролле ---------- */
const reveals = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window && !reduceMotion) {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }, { rootMargin: "0px 0px -8% 0px" });
  reveals.forEach((el) => io.observe(el));
} else {
  reveals.forEach((el) => el.classList.add("is-in"));
}

/* ---------- откуда пришёл человек ----------
   Модель «последний рекламный переход»: если в адресе есть UTM или click id —
   запоминаем их (перезаписывая старые). Если человек вернулся напрямую —
   оставляем последний рекламный источник. Храним 30 дней. */
const ATTR_KEY = "kvarta_attribution";
const AD_PARAMS = ["utm_source","utm_medium","utm_campaign","utm_content","utm_term","yclid","gclid","fbclid"];

function readAttribution() {
  try {
    const saved = JSON.parse(localStorage.getItem(ATTR_KEY) || "null");
    if (saved && Date.now() - saved.ts < 30 * 864e5) return saved;
  } catch { /* приватный режим или битые данные */ }
  return null;
}

function captureAttribution() {
  const params = new URLSearchParams(location.search);
  const fromAd = AD_PARAMS.some((k) => params.get(k));
  if (!fromAd && readAttribution()) return;
  const external = document.referrer && !document.referrer.startsWith(location.origin);
  const data = { ts: Date.now(), landing_page: location.href.slice(0, 500), referrer: external ? document.referrer.slice(0, 500) : null };
  for (const k of AD_PARAMS) data[k] = params.get(k)?.slice(0, 200) || null;
  try { localStorage.setItem(ATTR_KEY, JSON.stringify(data)); } catch { /* не страшно */ }
  sessionAttribution = data;
}
let sessionAttribution = null;
captureAttribution();

function attributionPayload() {
  const a = readAttribution() || sessionAttribution || {};
  const out = { page_url: location.href.slice(0, 500) };
  for (const k of [...AD_PARAMS, "landing_page", "referrer"]) if (a[k]) out[k] = a[k];
  return out;
}

/* ---------- телефон: та же логика, что на сервере (kvarta/phone.py) ---------- */
const MOBILE = ["25","29","33","44"];
const LANDLINE = ["15","16","17","21","22","23"];

function nationalDigits(raw) {
  const d = raw.replace(/\D/g, "");
  if (d.startsWith("375")) return d.slice(3);
  if (d.startsWith("80")) return d.slice(2);
  if (d.startsWith("0")) return d.slice(1);
  return d;
}
function isValidPhone(raw) {
  const n = nationalDigits(raw);
  if (n.length !== 9) return false;
  const p = n.slice(0, 2);
  if (MOBILE.includes(p)) return n[2] !== "0";
  return LANDLINE.includes(p);
}
function formatPhone(raw) {
  const digits = raw.replace(/\D/g, "");
  // Номер другой страны (+7…, +48…) не переделываем — пусть человек видит, что ввёл.
  if (raw.trim().startsWith("+") && digits && !"375".startsWith(digits.slice(0, 3)) ) return raw;
  const n = nationalDigits(raw).slice(0, 9);
  if (!n) return "";
  let s = "+375 (" + n.slice(0, 2);
  if (n.length >= 2) s += ")";
  if (n.length > 2) s += " " + n.slice(2, 5);
  if (n.length > 5) s += "-" + n.slice(5, 7);
  if (n.length > 7) s += "-" + n.slice(7, 9);
  return s;
}

/* ---------- форма ---------- */
const form = document.getElementById("lead-form");
const submit = document.getElementById("f-submit");
const statusBox = document.getElementById("f-status");
const phoneInput = form.elements.phone;
// Запасной путь, если форма не отправилась. Телефона в брифе нет, поэтому — мастерская.
const MAP_URL = document.querySelector(".ways .link-arrow")?.getAttribute("href") || "#delivery";

const MESSAGES = {
  name: "Напишите, как к вам обращаться.",
  phone: "Нужен белорусский номер: +375 и 9 цифр, например +375 29 123-45-67.",
};

phoneInput.addEventListener("input", (e) => {
  if (e.inputType && e.inputType.startsWith("delete")) return; // не мешаем стирать
  phoneInput.value = formatPhone(phoneInput.value);
});
phoneInput.addEventListener("blur", () => {
  if (phoneInput.value) phoneInput.value = formatPhone(phoneInput.value) || phoneInput.value;
  if (phoneInput.value && !isValidPhone(phoneInput.value)) setError("phone", MESSAGES.phone);
});
form.addEventListener("input", (e) => { if (e.target.name) setError(e.target.name, ""); });

function setError(field, message) {
  const err = document.getElementById(`f-${field}-err`);
  if (err) err.textContent = message;
  const input = form.elements[field];
  if (input && input.setAttribute) input.setAttribute("aria-invalid", message ? "true" : "false");
}

function validate() {
  let first = null;
  const name = form.elements.name.value.trim();
  if (!name) { setError("name", MESSAGES.name); first ??= form.elements.name; }
  if (!isValidPhone(phoneInput.value)) { setError("phone", MESSAGES.phone); first ??= phoneInput; }
  if (first) first.focus();
  return !first;
}

function showStatus(kind, html) {
  statusBox.className = `form__status is-${kind}`;
  statusBox.innerHTML = html;
  statusBox.hidden = false;
  statusBox.focus({ preventScroll: kind === "error" });
  if (kind !== "error") form.classList.add("is-done");
  if (kind !== "error") form.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
}

const fallback = () =>
  `Если не выходит, приходите в мастерскую: <a href="${MAP_URL}" target="_blank" rel="noopener">ул. Короля, 9</a>, пн–пт 8:00–20:00, сб–вс 10:00–18:00.`;

let pending = false;
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (pending) return; // двойной клик: второй запрос даже не уходит
  statusBox.hidden = true;
  if (!validate()) return;

  pending = true;
  submit.disabled = true;
  submit.textContent = "Отправляем…";

  const payload = {
    name: form.elements.name.value.trim(),
    phone: phoneInput.value,
    interest: form.elements.interest.value,
    comment: form.elements.comment.value.trim(),
    website: form.elements.website.value,
    attribution: attributionPayload(),
  };

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  try {
    const res = await fetch("/api/lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    const data = await res.json().catch(() => ({}));

    if (res.status === 201) {
      showStatus("ok", `<h3>Заявка принята</h3><p>Спасибо, ${escapeHtml(payload.name)}! Менеджер перезвонит на ${formatPhone(payload.phone)} в рабочие часы: пн–пт 8:00–20:00, сб–вс 10:00–18:00.</p>`);
    } else if (res.status === 200 && data.status === "duplicate") {
      showStatus("ok", `<h3>Заявка уже у нас</h3><p>${escapeHtml(data.message)} Если хотите что-то добавить, скажите об этом менеджеру по телефону.</p>`);
    } else if (res.status === 422 && data.errors) {
      for (const [field, msg] of Object.entries(data.errors)) setError(field, msg);
      const firstBad = Object.keys(data.errors).map((f) => form.elements[f]).find((el) => el && el.focus);
      firstBad?.focus();
    } else {
      showStatus("error", `<h3>Не получилось отправить</h3><p>${escapeHtml(data.message || "Сервер не ответил как надо.")}</p><p>Всё, что вы ввели, сохранилось. Нажмите «Отправить заявку» ещё раз через минуту.</p><p>${fallback()}</p>`);
    }
  } catch {
    showStatus("error", `<h3>Нет связи с сервером</h3><p>Похоже, пропал интернет или сервер долго не отвечает. Всё, что вы ввели, сохранилось: проверьте связь и нажмите «Отправить заявку» ещё раз.</p><p>${fallback()}</p>`);
  } finally {
    clearTimeout(timer);
    pending = false;
    submit.disabled = false;
    submit.textContent = "Отправить заявку";
  }
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- кнопки «Заказать» / «Подписка» заполняют форму ---------- */
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-interest]");
  if (!btn) return;
  const radio = form.querySelector(`input[name=interest][value=${btn.dataset.interest}]`);
  if (radio) radio.checked = true;
  const product = btn.dataset.product;
  const comment = form.elements.comment;
  if (product && !comment.value.includes(product)) {
    comment.value = comment.value ? `${comment.value.trim()}\n${product} — 1 шт.` : `${product} — 1 шт.`;
  }
  e.preventDefault();
  if (form.classList.contains("is-done")) return document.getElementById("order").scrollIntoView();
  document.getElementById("order").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  form.elements.name.focus({ preventScroll: true });
});
