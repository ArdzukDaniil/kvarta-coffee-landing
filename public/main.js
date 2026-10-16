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
  interest: "Выберите: подписка, разовый заказ или вопрос.",
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
  if (!form.elements.interest.value) { setError("interest", MESSAGES.interest); first ??= form.querySelector("input[name=interest]"); }
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
    items: isQuestion() ? {} : { ...current() },
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
      const list = Object.entries(payload.items).map(([sku, q]) => `${CATALOG[sku].name} × ${q}`).join(", ");
      showStatus("ok", `<h3>Заявка принята</h3><p>Спасибо, ${escapeHtml(payload.name)}! Менеджер перезвонит на ${formatPhone(payload.phone)} в рабочие часы: пн–пт 8:00–20:00, сб–вс 10:00–18:00.</p>${list ? `<p>В заявке: ${list}.</p>` : ""}`);
      if (!isQuestion()) baskets[mode()] = {};
      try { sessionStorage.setItem(ORDER_KEY, JSON.stringify(baskets)); } catch { /* не страшно */ }
      renderOrder();
    } else if (res.status === 200 && data.status === "updated") {
      showStatus("ok", `<h3>Добавили к вашей заявке</h3><p>${escapeHtml(data.message)}</p>`);
      if (!isQuestion()) baskets[mode()] = {};
      try { sessionStorage.setItem(ORDER_KEY, JSON.stringify(baskets)); } catch { /* не страшно */ }
      renderOrder();
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
    submit.textContent = submitLabel();
  }
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- выбор кофе: счётчики в карточках и «листок заказа» в форме ----------
   Два отдельных выбора: для разового заказа и для подписки, — переключение
   «Что вас интересует» ничего не теряет и не смешивает. Карточки, листок и нижняя
   полоска только рисуют текущий выбор, поэтому всё всегда совпадает.
   Цены здесь — для подсказки, сервер считает по своему прайсу (kvarta/catalog.py). */
const CATALOG = Object.fromEntries([...document.querySelectorAll("[data-sku]")].map((el) => [
  el.dataset.sku, { name: el.dataset.name, price: Number(el.dataset.price), inSub: el.dataset.sub === "1" },
]));
const ORDER_KEY = "kvarta_order";
const MAX_QTY = 20;
const SUB_PACKS = 2;          // подписка из брифа: 2 пачки по 250 г в месяц
const SUB_PRICE = 54;
const FREE_DELIVERY_FROM = 50;

const baskets = { one_time: {}, subscription: {} };
try {
  const saved = JSON.parse(sessionStorage.getItem(ORDER_KEY) || "{}");
  for (const m of Object.keys(baskets)) Object.assign(baskets[m], saved[m] || {});
} catch { /* приватный режим или битые данные */ }
for (const [m, basket] of Object.entries(baskets)) {
  for (const sku of Object.keys(basket)) {
    if (!CATALOG[sku] || !(basket[sku] > 0) || (m === "subscription" && !CATALOG[sku].inSub)) delete basket[sku];
  }
}

const interest = () => form.elements.interest.value;              // "" — пока не выбрано
const mode = () => (interest() === "subscription" ? "subscription" : "one_time");
const current = () => baskets[mode()];
const isQuestion = () => interest() === "question";
const submitLabel = () => (isQuestion() ? "Задать вопрос" : "Отправить заявку");
const COMMENT_HINT = {
  question: "Например: какой сорт подойдёт для турки?",
  other: "Например: смолоть под турку, привезти после 18:00",
};
const countOf = (basket) => Object.values(basket).reduce((n, q) => n + q, 0);
const pickInterest = (value) => { form.querySelector(`input[name=interest][value=${value}]`).checked = true; };

form.addEventListener("change", (e) => {
  if (e.target.name === "interest") { setError("interest", ""); renderOrder(); }
});

function setQty(sku, qty) {
  // Кофе из каталога без выбранного интереса или при «Вопросе» — это разовый заказ.
  if (!interest() || isQuestion()) pickInterest("one_time");
  const basket = current();
  if (mode() === "subscription") {
    if (!CATALOG[sku].inSub) return;
    qty = Math.min(qty, (basket[sku] || 0) + SUB_PACKS - countOf(basket)); // не больше 2 пачек всего
  }
  qty = Math.max(0, Math.min(MAX_QTY, qty));
  if (qty) basket[sku] = qty; else delete basket[sku];
  try { sessionStorage.setItem(ORDER_KEY, JSON.stringify(baskets)); } catch { /* не страшно */ }
  setError("items", "");
  renderOrder(sku);
}

const pcs = (n) => `${n} шт`;
const stepper = (sku, qty, name, canAdd) => `
  <button type="button" class="qty__btn" data-dec="${sku}" aria-label="${qty === 1 ? "Убрать" : "Меньше"}: ${name}">−</button>
  <output class="qty__n" aria-live="polite" aria-label="${name}: ${pcs(qty)}">${qty}</output>
  <button type="button" class="qty__btn" data-inc="${sku}" aria-label="Больше: ${name}" ${canAdd ? "" : "disabled"}>+</button>`;

function renderOrder(changed) {
  const isSub = mode() === "subscription";
  const basket = current();
  const entries = Object.entries(basket);
  const count = countOf(basket);
  const total = entries.reduce((sum, [sku, q]) => sum + CATALOG[sku].price * q, 0);
  const subFull = isSub && count >= SUB_PACKS;
  const canAdd = (sku) => (isSub ? CATALOG[sku].inSub && !subFull : (basket[sku] || 0) < MAX_QTY);

  // карточки каталога
  for (const box of document.querySelectorAll("[data-qty]")) {
    const sku = box.dataset.qty, qty = basket[sku] || 0, name = CATALOG[sku].name;
    box.classList.toggle("is-on", qty > 0);
    if (qty) {
      box.innerHTML = `<span class="qty__label">${isSub ? "В подписке" : "В заявке"}</span>${stepper(sku, qty, name, canAdd(sku))}`;
    } else if (isSub && !CATALOG[sku].inSub) {
      box.innerHTML = `<span class="qty__note">В подписку не входит&nbsp;— только зерно</span>`;
    } else {
      const label = isSub ? "В подписку" : "Добавить в заявку";
      box.innerHTML = `<button type="button" class="btn btn--line qty__add" data-add="${sku}" aria-label="${label}: ${name}" ${canAdd(sku) ? "" : "disabled"}>${label}</button>`;
    }
    if (sku === changed && qty) box.querySelector(".qty__n").classList.add("is-bump");
  }

  // листок в форме: при «Вопросе» он не нужен — форма ровно как в ТЗ
  document.getElementById("sheet").hidden = isQuestion();
  form.elements.comment.placeholder = isQuestion() ? COMMENT_HINT.question : COMMENT_HINT.other;
  document.getElementById("question-note").hidden = !isQuestion();
  if (!pending) submit.textContent = submitLabel();
  document.getElementById("sheet-title").textContent = isSub ? `Выберите ${SUB_PACKS} пачки для подписки` : "Что привезти";
  const empty = document.getElementById("sheet-empty");
  empty.hidden = entries.length > 0;
  empty.innerHTML = isSub
    ? "Две пачки по&nbsp;250&nbsp;г в&nbsp;месяц&nbsp;— можно разные или две одинаковые. Не&nbsp;знаете, что выбрать,&nbsp;— менеджер предложит."
    : "Пока ничего не выбрано. Добавьте кофе прямо здесь или просто напишите в&nbsp;комментарии&nbsp;— менеджер всё уточнит.";
  document.getElementById("sheet-list").innerHTML = entries.map(([sku, q]) => {
    const { name, price } = CATALOG[sku];
    return `<li class="sheet__row${sku === changed ? " is-new" : ""}">
      <span class="sheet__name">${name}</span>
      <span class="qty is-on">${stepper(sku, q, name, canAdd(sku))}</span>
      <span class="sheet__sum">${isSub ? "" : `${price * q} BYN`}</span>
      <button type="button" class="sheet__x" data-remove="${sku}" aria-label="Убрать: ${name}">×</button>
    </li>`;
  }).join("");

  // «Добавить:» — то, чего ещё нет в выборе (для подписки — только зерно и пока есть место)
  const rest = Object.entries(CATALOG).filter(([sku]) => !basket[sku] && canAdd(sku));
  document.getElementById("sheet-add").hidden = !rest.length;
  document.getElementById("sheet-add-list").innerHTML = rest.map(([sku, { name, price }]) =>
    `<button type="button" class="sheet__chip" data-add="${sku}" aria-label="Добавить: ${name}${isSub ? "" : `, ${price} BYN`}">+ ${name.split(/[ ,]/)[0]}${isSub ? "" : ` <span>${price}</span>`}</button>`).join("");

  const totalEl = document.getElementById("sheet-total");
  if (isSub) {
    totalEl.hidden = false;
    totalEl.innerHTML = `<b>${count} из ${SUB_PACKS}${subFull ? " ✓" : ""}</b> · ${SUB_PRICE}&nbsp;BYN в&nbsp;месяц, доставка по&nbsp;Минску бесплатно.`
      + `<span class="sheet__more">Нужно больше&nbsp;— для офиса или кофейни? Напишите в&nbsp;комментарии, подберём объём.</span>`;
  } else {
    totalEl.hidden = !entries.length;
    const delivery = total >= FREE_DELIVERY_FROM
      ? "доставка по&nbsp;Минску бесплатно"
      : `до&nbsp;бесплатной доставки не&nbsp;хватает ${FREE_DELIVERY_FROM - total}&nbsp;BYN, самовывоз&nbsp;— бесплатно`;
    totalEl.innerHTML = `<b>≈ ${total}&nbsp;BYN</b> по&nbsp;прайсу, ${delivery}. Точную сумму подтвердит менеджер.`;
  }

  // нижняя полоска
  const bar = document.getElementById("order-bar");
  document.getElementById("order-bar-label").textContent = isSub ? "Подписка" : "В заявке";
  document.getElementById("order-bar-text").textContent = isSub
    ? `${count} из ${SUB_PACKS} пачек · ${SUB_PRICE} BYN/мес`
    : `${pcs(count)} · ≈ ${total} BYN`;
  bar.dataset.empty = entries.length && !isQuestion() ? "false" : "true";
  updateBar();
}

// Полоску прячем, пока форма на экране или заявка уже отправлена.
let formInView = false;
function updateBar() {
  const bar = document.getElementById("order-bar");
  bar.hidden = bar.dataset.empty === "true" || formInView || form.classList.contains("is-done");
}
if ("IntersectionObserver" in window) {
  new IntersectionObserver(([e]) => { formInView = e.isIntersecting; updateBar(); }, { threshold: 0.15 })
    .observe(document.getElementById("order"));
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-add],[data-inc],[data-dec],[data-remove]");
  if (!t) return;
  const sku = t.dataset.add || t.dataset.inc || t.dataset.dec || t.dataset.remove;
  // Запоминаем, где нажали, ДО перерисовки: после неё кнопки t уже нет в документе.
  const scope = t.closest(".sheet") || t.closest("[data-qty]");
  const inSheet = scope?.classList.contains("sheet");
  const have = current()[sku] || 0;
  if (t.dataset.add || t.dataset.inc) setQty(sku, have + 1);
  else if (t.dataset.dec) setQty(sku, have - 1);
  else setQty(sku, 0);
  // Фокус возвращаем туда же, где нажимали, и без прокрутки — страница не должна прыгать.
  const area = inSheet ? document.getElementById("sheet") : document.querySelector(`[data-qty="${sku}"]`);
  const next = area.querySelector(`[data-inc="${sku}"]:not(:disabled)`) || area.querySelector(`[data-dec="${sku}"]`)
    || area.querySelector(`[data-add="${sku}"]`) || area.querySelector("[data-add]") || area;
  next.focus({ preventScroll: true });
});

/* ---------- кнопки «Оставить заявку на подписку» выбирают интерес ---------- */
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-interest]");
  if (!btn) return;
  pickInterest(btn.dataset.interest);
  setError("interest", "");
  renderOrder();
  e.preventDefault();
  if (form.classList.contains("is-done")) return document.getElementById("order").scrollIntoView();
  document.getElementById("order").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  form.elements.name.focus({ preventScroll: true });
});

// Вернулись на страницу с уже выбранным кофе — подхватываем, к чему он относился.
if (countOf(baskets.one_time)) pickInterest("one_time");
else if (countOf(baskets.subscription)) pickInterest("subscription");
renderOrder();
