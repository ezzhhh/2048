(function () {
  var PAINT = {
    13: 9600, 14: 9600, 15: 9800, 16: 10400, 17: 11600,
    18: 12800, 19: 14000, 20: 15400, 21: 16600, 22: 18200,
    23: 19600, 24: 21000
  };

  var burger = document.getElementById("burger");
  var nav = document.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll(".nav__item--sub > a").forEach(function (link) {
      link.addEventListener("click", function (event) {
        if (window.matchMedia("(max-width: 1100px)").matches) {
          event.preventDefault();
          link.parentElement.classList.toggle("is-open");
        }
      });
    });
  }

  function formatMoney(value) {
    return value.toLocaleString("ru-RU") + " ₽";
  }

  function digits(value) {
    return (value || "").replace(/\D/g, "");
  }

  function maskPhone(input) {
    var raw = digits(input.value);
    if (raw.startsWith("8")) raw = "7" + raw.slice(1);
    if (raw.startsWith("9")) raw = "7" + raw;
    if (!raw.startsWith("7")) raw = "7" + raw;
    raw = raw.slice(0, 11);
    var rest = raw.slice(1);
    var out = "+7";
    if (rest.length) out += " (" + rest.slice(0, 3);
    if (rest.length >= 3) out += ")";
    if (rest.length > 3) out += " " + rest.slice(3, 6);
    if (rest.length > 6) out += "-" + rest.slice(6, 8);
    if (rest.length > 8) out += "-" + rest.slice(8, 10);
    input.value = out;
  }

  document.querySelectorAll("[data-phone]").forEach(function (input) {
    input.addEventListener("input", function () { maskPhone(input); });
    input.addEventListener("focus", function () {
      if (!input.value) input.value = "+7";
    });
  });

  function updateCalc(root) {
    var size = root.querySelector("[data-size]");
    var discount = root.querySelector("[data-discount]");
    var baseEl = root.querySelector("[data-base]");
    var totalEl = root.querySelector("[data-total]");
    if (!size || !totalEl) return;
    var base = PAINT[size.value] || 0;
    var off = discount && discount.checked;
    var total = off ? Math.round(base * 0.9) : base;
    if (baseEl) baseEl.textContent = formatMoney(base);
    totalEl.textContent = formatMoney(total);
  }

  document.querySelectorAll("[data-calc]").forEach(function (root) {
    root.addEventListener("change", function () { updateCalc(root); });
    updateCalc(root);
  });

  function openModal(id) {
    var modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("is-open");
    document.body.style.overflow = "hidden";
    var focusable = modal.querySelector("input, select, textarea, button");
    if (focusable) focusable.focus();
  }

  function closeModals() {
    document.querySelectorAll(".modal.is-open").forEach(function (modal) {
      modal.classList.remove("is-open");
    });
    document.body.style.overflow = "";
  }

  document.querySelectorAll("[data-modal]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      openModal(btn.getAttribute("data-modal"));
    });
  });
  document.querySelectorAll("[data-close]").forEach(function (btn) {
    btn.addEventListener("click", closeModals);
  });
  document.querySelectorAll(".modal").forEach(function (modal) {
    modal.addEventListener("click", function (event) {
      if (event.target === modal) closeModals();
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeModals();
  });

  function validateForm(form) {
    var error = form.querySelector(".form-error");
    var name = form.querySelector("[name='name']");
    var phone = form.querySelector("[name='phone']");
    var agree = form.querySelector("[name='agree']");
    var message = "";
    if (name && name.value.trim().length < 2) message = "Укажите имя.";
    else if (phone && digits(phone.value).length < 11) message = "Введите телефон полностью.";
    else if (agree && !agree.checked) message = "Нужно согласие на обработку данных.";
    if (error) error.textContent = message;
    return !message;
  }

  document.querySelectorAll("form[data-lead]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!validateForm(form)) return;
      var ok = form.querySelector(".form-ok");
      if (ok) ok.classList.add("is-on");
      form.reset();
      var calc = form.closest("[data-calc]");
      if (calc) updateCalc(calc);
    });
  });

  var filters = document.querySelectorAll("[data-filter]");
  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var value = btn.getAttribute("data-filter");
      filters.forEach(function (item) { item.classList.remove("is-active"); });
      btn.classList.add("is-active");
      document.querySelectorAll(".work").forEach(function (card) {
        var show = value === "all" || card.getAttribute("data-cat") === value;
        card.hidden = !show;
      });
    });
  });

  var cookie = document.getElementById("cookie");
  if (cookie) {
    if (localStorage.getItem("obod-cookie") === "1") cookie.classList.add("is-hidden");
    var accept = document.getElementById("cookie-ok");
    if (accept) {
      accept.addEventListener("click", function () {
        localStorage.setItem("obod-cookie", "1");
        cookie.classList.add("is-hidden");
      });
    }
  }
})();
