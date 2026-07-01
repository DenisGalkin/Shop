const state = {
  session: null,
  currentTab: "dashboard",
  dashboard: null,
  categories: [],
  products: [],
  users: [],
  orders: [],
  payments: [],
  settings: {},
  filters: {
    productsSearch: "",
    productsCategoryId: "",
    usersSearch: "",
  },
  forms: {
    category: { title: "", description: "", sort_order: "0" },
    product: {
      id: "",
      category_id: "",
      title: "",
      internal_name: "",
      price: "",
      warranty_label: "",
      sort_order: "0",
      description: "",
      important_info: "",
    },
    stock: { product_id: "", keys: "" },
    settings: {},
  },
  loading: false,
  toasts: [],
};

const app = document.getElementById("app");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function showToast(message) {
  state.toasts = [...state.toasts, { id: crypto.randomUUID(), message }];
  render();
  setTimeout(() => {
    state.toasts = state.toasts.slice(1);
    render();
  }, 3200);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "same-origin",
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || data.message || text || "Request failed");
  }
  return data;
}

async function bootstrap() {
  state.loading = true;
  render();
  try {
    const session = await fetchJson("/admin/api/session");
    state.session = session.session;
    if (state.session) {
      await loadAll();
    }
  } catch (_) {
    state.session = null;
  } finally {
    state.loading = false;
    render();
  }
}

async function loadAll() {
  await Promise.all([
    loadDashboard(),
    loadCategories(),
    loadProducts(),
    loadUsers(),
    loadOrders(),
    loadPayments(),
    loadSettings(),
  ]);
}

async function loadDashboard() {
  const data = await fetchJson("/admin/api/dashboard");
  state.dashboard = data;
}

async function loadCategories() {
  const data = await fetchJson("/admin/api/categories");
  state.categories = data.items;
  if (!state.forms.product.category_id && data.items[0]) {
    state.forms.product.category_id = String(data.items[0].id);
  }
}

async function loadProducts() {
  const params = new URLSearchParams();
  if (state.filters.productsSearch) params.set("search", state.filters.productsSearch);
  if (state.filters.productsCategoryId) params.set("category_id", state.filters.productsCategoryId);
  const data = await fetchJson(`/admin/api/products?${params.toString()}`);
  state.products = data.items;
}

async function loadUsers() {
  const params = new URLSearchParams();
  if (state.filters.usersSearch) params.set("search", state.filters.usersSearch);
  const data = await fetchJson(`/admin/api/users?${params.toString()}`);
  state.users = data.items;
}

async function loadOrders() {
  const data = await fetchJson("/admin/api/orders?limit=30");
  state.orders = data.items;
}

async function loadPayments() {
  const data = await fetchJson("/admin/api/payments?limit=30");
  state.payments = data.items;
}

async function loadSettings() {
  const data = await fetchJson("/admin/api/settings");
  state.settings = data.item;
  state.forms.settings = { ...data.item };
}

async function handleLogin(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    state.loading = true;
    render();
    await fetchJson("/admin/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: form.get("username"),
        password: form.get("password"),
      }),
    });
    showToast("Вход выполнен");
    await bootstrap();
  } catch (error) {
    state.loading = false;
    render();
    showToast(error.message);
  }
}

async function handleLogout() {
  try {
    await fetchJson("/admin/api/logout", { method: "POST" });
  } catch (_) {}
  state.session = null;
  render();
}

async function submitCategory(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await fetchJson("/admin/api/categories", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        description: form.get("description"),
        sort_order: form.get("sort_order"),
      }),
    });
    state.forms.category = { title: "", description: "", sort_order: "0" };
    await Promise.all([loadCategories(), loadDashboard()]);
    showToast("Категория создана");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleCategory(categoryId) {
  try {
    await fetchJson(`/admin/api/categories/${categoryId}/toggle`, { method: "POST" });
    await Promise.all([loadCategories(), loadDashboard()]);
    showToast("Статус категории обновлен");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveCategory(categoryId) {
  const title = document.querySelector(`[data-category-title="${categoryId}"]`)?.value || "";
  const description = document.querySelector(`[data-category-description="${categoryId}"]`)?.value || "";
  const sortOrder = document.querySelector(`[data-category-sort="${categoryId}"]`)?.value || "0";
  try {
    await fetchJson(`/admin/api/categories/${categoryId}`, {
      method: "PATCH",
      body: JSON.stringify({ title, description, sort_order: sortOrder }),
    });
    await Promise.all([loadCategories(), loadDashboard()]);
    showToast("Категория сохранена");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function submitProduct(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = {
    category_id: form.get("category_id"),
    title: form.get("title"),
    internal_name: form.get("internal_name"),
    price: form.get("price"),
    warranty_label: form.get("warranty_label"),
    sort_order: form.get("sort_order"),
    description: form.get("description"),
    important_info: form.get("important_info"),
  };
  try {
    await fetchJson("/admin/api/products", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.forms.product = {
      id: "",
      category_id: state.categories[0] ? String(state.categories[0].id) : "",
      title: "",
      internal_name: "",
      price: "",
      warranty_label: "",
      sort_order: "0",
      description: "",
      important_info: "",
    };
    await Promise.all([loadProducts(), loadDashboard()]);
    showToast("Товар создан");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function fillProductForm(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;
  state.forms.product = {
    id: String(product.id),
    category_id: String(product.category_id),
    title: product.title,
    internal_name: product.internal_name,
    price: (product.price_cents / 100).toFixed(2),
    warranty_label: product.warranty_label,
    sort_order: String(product.sort_order),
    description: product.description,
    important_info: product.important_info,
  };
  render();
}

async function updateProduct(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const productId = state.forms.product.id;
  if (!productId) {
    return submitProduct(event);
  }
  try {
    await fetchJson(`/admin/api/products/${productId}`, {
      method: "PATCH",
      body: JSON.stringify({
        category_id: form.get("category_id"),
        title: form.get("title"),
        internal_name: form.get("internal_name"),
        price: form.get("price"),
        warranty_label: form.get("warranty_label"),
        sort_order: form.get("sort_order"),
        description: form.get("description"),
        important_info: form.get("important_info"),
      }),
    });
    await Promise.all([loadProducts(), loadDashboard()]);
    showToast("Товар обновлен");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleProduct(productId) {
  try {
    await fetchJson(`/admin/api/products/${productId}/toggle`, { method: "POST" });
    await Promise.all([loadProducts(), loadDashboard()]);
    showToast("Статус товара обновлен");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function submitStock(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const productId = form.get("product_id");
  try {
    const result = await fetchJson(`/admin/api/products/${productId}/stock`, {
      method: "POST",
      body: JSON.stringify({ keys: form.get("keys") }),
    });
    state.forms.stock = { product_id: "", keys: "" };
    await Promise.all([loadProducts(), loadDashboard()]);
    showToast(`Добавлено ${result.added}, пропущено ${result.skipped}`);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function topUpUser(tgId) {
  const amount = window.prompt("Введите сумму пополнения в USD", "10");
  if (!amount) return;
  try {
    const result = await fetchJson(`/admin/api/users/${tgId}/balance`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    });
    await Promise.all([loadUsers(), loadDashboard()]);
    showToast(`Баланс пополнен на ${result.amount_label}`);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await fetchJson("/admin/api/settings", {
      method: "PATCH",
      body: JSON.stringify({
        support_username: form.get("support_username"),
        bot_username: form.get("bot_username"),
        referral_reward_percent: form.get("referral_reward_percent"),
        default_currency: form.get("default_currency"),
      }),
    });
    await Promise.all([loadSettings(), loadDashboard()]);
    showToast("Настройки сохранены");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function setTab(tab) {
  state.currentTab = tab;
  render();
}

function renderLogin() {
  app.innerHTML = `
    <div class="auth-shell">
      <div class="auth-card">
        <span class="eyebrow">Shop Control Center</span>
        <h1>Web-админка бота</h1>
        <p>Управляйте каталогом, ключами, пользователями, заказами и платежами из одного современного интерфейса.</p>
        <form id="login-form">
          <div class="field">
            <label>Логин</label>
            <input name="username" placeholder="admin" autocomplete="username" required />
          </div>
          <div class="field">
            <label>Пароль</label>
            <input type="password" name="password" placeholder="Введите пароль" autocomplete="current-password" required />
          </div>
          <button class="primary-button" type="submit">Войти в панель</button>
        </form>
      </div>
      ${renderToasts()}
    </div>
  `;
  document.getElementById("login-form")?.addEventListener("submit", handleLogin);
}

function renderMetricCard(title, value, footLeft, footRight) {
  return `
    <section class="panel metric-card">
      <strong>${escapeHtml(title)}</strong>
      <div class="value">${escapeHtml(value)}</div>
      <div class="metric-foot"><span>${escapeHtml(footLeft)}</span><span>${escapeHtml(footRight)}</span></div>
    </section>
  `;
}

function renderDashboard() {
  const data = state.dashboard;
  if (!data) return `<div class="loading">Загружаем dashboard...</div>`;
  const maxRevenue = Math.max(...data.series.map((item) => item.revenue_cents), 1);
  return `
    <div class="grid">
      <div class="grid stats-grid">
        ${renderMetricCard("Выручка", data.stats.revenue_label, "Все подтвержденные заказы", `${data.stats.orders_total} заказов`)}
        ${renderMetricCard("Пользователи", String(data.stats.users_total), "Всего зарегистрировано", `${data.stats.categories_total} категории`)}
        ${renderMetricCard("Ключи на складе", String(data.stats.stock_total), "Доступно к продаже", `${data.low_stock.length} low stock`)}
        ${renderMetricCard("Ожидают оплаты", String(data.stats.payments_pending_total), "По последним платежам", `${data.stats.products_total} товаров`)}
      </div>
      <div class="grid columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Динамика продаж за 7 дней</h2>
              <p>По выполненным заказам и подтвержденной выручке.</p>
            </div>
            <span class="chip success">Live sync</span>
          </div>
          <div class="chart">
            ${data.series
              .map(
                (item) => `
                  <div class="chart-bar">
                    <div class="chart-bar-fill" style="height:${Math.max(24, (item.revenue_cents / maxRevenue) * 180)}px"></div>
                    <strong>${escapeHtml(item.revenue_label)}</strong>
                    <label>${escapeHtml(item.day.slice(5))}</label>
                  </div>
                `
              )
              .join("")}
          </div>
        </section>
        <section class="stack">
          <section class="panel">
            <div class="panel-header">
              <div>
                <h3>Товары под контролем</h3>
                <p>Активные позиции с низким остатком.</p>
              </div>
            </div>
            <div class="mini-list">
              ${
                data.low_stock.length
                  ? data.low_stock
                      .map(
                        (item) => `
                          <div class="mini-item">
                            <div>
                              <strong>${escapeHtml(item.title)}</strong>
                              <small>${escapeHtml(item.category_title)} · ${escapeHtml(item.price_label)}</small>
                            </div>
                            <span class="chip ${item.stock_count === 0 ? "danger" : "warn"}">${item.stock_count} шт.</span>
                          </div>
                        `
                      )
                      .join("")
                  : `<div class="empty">Критичных остатков сейчас нет.</div>`
              }
            </div>
          </section>
          <section class="panel">
            <div class="panel-header">
              <div>
                <h3>Активные покупатели</h3>
                <p>Последние пользователи с заказами и балансом.</p>
              </div>
            </div>
            <div class="mini-list">
              ${data.top_users
                .map(
                  (user) => `
                    <div class="mini-item">
                      <div>
                        <strong>${escapeHtml(user.full_name)}</strong>
                        <small>@${escapeHtml(user.username || "no_username")} · ID ${user.tg_id}</small>
                      </div>
                      <span class="chip">${escapeHtml(user.balance_label)}</span>
                    </div>
                  `
                )
                .join("")}
            </div>
          </section>
        </section>
      </div>
      <div class="grid columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Последние заказы</h3>
              <p>Лента продаж по каталогу.</p>
            </div>
          </div>
          <div class="table">
            ${data.recent_orders.map(renderOrderRow).join("")}
          </div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Последние платежи</h3>
              <p>CryptoBot пополнения и покупка товаров.</p>
            </div>
          </div>
          <div class="table">
            ${data.recent_payments.map(renderPaymentRow).join("")}
          </div>
        </section>
      </div>
    </div>
  `;
}

function renderOrderRow(item) {
  return `
    <article class="table-row compact">
      <div>
        <strong>#${item.id} · ${escapeHtml(item.product_title)}</strong>
        <small>${escapeHtml(item.buyer_name)} · ${item.buyer_tg_id}</small>
      </div>
      <div>
        <strong>${escapeHtml(item.amount_label)}</strong>
        <small>${escapeHtml(item.created_label)}</small>
      </div>
      <div class="chip-row">
        <span class="chip success">${escapeHtml(item.payment_method)}</span>
      </div>
    </article>
  `;
}

function renderPaymentRow(item) {
  const statusClass = item.status === "completed" ? "success" : item.status === "pending" ? "warn" : "danger";
  return `
    <article class="table-row compact">
      <div>
        <strong>#${item.id} · ${escapeHtml(item.buyer_name)}</strong>
        <small>${escapeHtml(item.product_title || item.purpose)} · ${item.buyer_tg_id}</small>
      </div>
      <div>
        <strong>${escapeHtml(item.amount_label)}</strong>
        <small>${escapeHtml(item.created_label)}</small>
      </div>
      <div class="chip-row">
        <span class="chip ${statusClass}">${escapeHtml(item.status)}</span>
      </div>
    </article>
  `;
}

function renderCatalog() {
  return `
    <div class="split">
      <div class="stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Категории</h2>
              <p>Управляйте разделами каталога и видимостью на витрине.</p>
            </div>
          </div>
          <div class="table">
            ${state.categories
              .map(
                (category) => `
                  <article class="category-card">
                    <div class="category-grid">
                      <div class="field">
                        <label>Название</label>
                        <input data-category-title="${category.id}" value="${escapeHtml(category.title)}" />
                      </div>
                      <div class="field">
                        <label>Порядок</label>
                        <input class="mono" data-category-sort="${category.id}" value="${category.sort_order}" />
                      </div>
                      <div class="category-actions">
                        <span class="chip ${category.is_active ? "success" : "danger"}">${category.is_active ? "Активна" : "Выключена"}</span>
                        <button class="secondary-button" onclick="saveCategory(${category.id})">Сохранить</button>
                        <button class="action-button" onclick="toggleCategory(${category.id})">${category.is_active ? "Отключить" : "Включить"}</button>
                      </div>
                    </div>
                    <div class="field">
                      <label>Описание</label>
                      <input data-category-description="${category.id}" value="${escapeHtml(category.description)}" />
                    </div>
                    <div class="chip-row">
                      <span class="chip">${category.products_count} товаров</span>
                      <span class="chip success">${category.stock_total} ключей</span>
                      <span class="chip">${category.active_products_count} активных</span>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Товары и склад</h2>
              <p>Фильтруйте ассортимент, редактируйте карточки и следите за остатками.</p>
            </div>
          </div>
          <div class="toolbar">
            <div class="field">
              <label>Поиск товара</label>
              <input id="products-search" value="${escapeHtml(state.filters.productsSearch)}" placeholder="ChatGPT, Claude, Grok..." />
            </div>
            <div class="field">
              <label>Категория</label>
              <select id="products-category-filter">
                <option value="">Все категории</option>
                ${state.categories
                  .map((item) => `<option value="${item.id}" ${String(item.id) === state.filters.productsCategoryId ? "selected" : ""}>${escapeHtml(item.title)}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="field" style="align-self:end;">
              <button class="primary-button" onclick="applyProductFilters()">Применить</button>
            </div>
          </div>
          <div class="table">
            ${state.products
              .map(
                (product) => `
                  <article class="table-row">
                    <div>
                      <strong>${escapeHtml(product.title)}</strong>
                      <small>${escapeHtml(product.internal_name)} · ${escapeHtml(product.category_title)}</small>
                    </div>
                    <div>
                      <strong>${escapeHtml(product.price_label)}</strong>
                      <small>${escapeHtml(product.warranty_label || "Без подписи гарантии")}</small>
                    </div>
                    <div class="chip-row">
                      <span class="chip ${product.stock_count === 0 ? "danger" : product.stock_count <= 3 ? "warn" : "success"}">${product.stock_count} на складе</span>
                      <span class="chip">${product.sold_count} продано</span>
                    </div>
                    <div class="table-actions">
                      <button class="secondary-button" onclick="fillProductForm(${product.id})">Редактировать</button>
                      <button class="action-button" onclick="toggleProduct(${product.id})">${product.is_active ? "Скрыть" : "Активировать"}</button>
                    </div>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      </div>
      <aside class="stack sheet">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Новая категория</h3>
              <p>Добавьте новый раздел в витрину.</p>
            </div>
          </div>
          <form id="category-form" class="form-grid">
            <div class="field full">
              <label>Название</label>
              <input name="title" value="${escapeHtml(state.forms.category.title)}" required />
            </div>
            <div class="field full">
              <label>Описание</label>
              <textarea name="description" rows="4">${escapeHtml(state.forms.category.description)}</textarea>
            </div>
            <div class="field">
              <label>Порядок</label>
              <input name="sort_order" value="${escapeHtml(state.forms.category.sort_order)}" />
            </div>
            <div class="field full form-actions">
              <button class="primary-button" type="submit">Создать категорию</button>
            </div>
          </form>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>${state.forms.product.id ? "Редактирование товара" : "Новый товар"}</h3>
              <p>${state.forms.product.id ? "Обновите карточку и цену." : "Добавьте новую позицию в каталог."}</p>
            </div>
          </div>
          <form id="product-form" class="form-grid">
            <div class="field">
              <label>Категория</label>
              <select name="category_id" required>
                ${state.categories
                  .map((item) => `<option value="${item.id}" ${String(item.id) === state.forms.product.category_id ? "selected" : ""}>${escapeHtml(item.title)}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="field">
              <label>Порядок</label>
              <input name="sort_order" value="${escapeHtml(state.forms.product.sort_order)}" />
            </div>
            <div class="field full">
              <label>Название</label>
              <input name="title" value="${escapeHtml(state.forms.product.title)}" required />
            </div>
            <div class="field full">
              <label>Внутреннее название</label>
              <input name="internal_name" value="${escapeHtml(state.forms.product.internal_name)}" />
            </div>
            <div class="field">
              <label>Цена в USD</label>
              <input name="price" value="${escapeHtml(state.forms.product.price)}" placeholder="80.00" required />
            </div>
            <div class="field">
              <label>Гарантия</label>
              <input name="warranty_label" value="${escapeHtml(state.forms.product.warranty_label)}" />
            </div>
            <div class="field full">
              <label>Описание</label>
              <textarea name="description" rows="4">${escapeHtml(state.forms.product.description)}</textarea>
            </div>
            <div class="field full">
              <label>Важная информация</label>
              <textarea name="important_info" rows="4">${escapeHtml(state.forms.product.important_info)}</textarea>
            </div>
            <div class="field full form-actions">
              ${state.forms.product.id ? `<button class="secondary-button" type="button" onclick="resetProductForm()">Сбросить</button>` : ""}
              <button class="primary-button" type="submit">${state.forms.product.id ? "Сохранить товар" : "Создать товар"}</button>
            </div>
          </form>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Пополнение склада</h3>
              <p>Добавляйте ключи пачкой, по одному в строке.</p>
            </div>
          </div>
          <form id="stock-form" class="form-grid">
            <div class="field full">
              <label>Товар</label>
              <select name="product_id" required>
                <option value="">Выберите товар</option>
                ${state.products.map((item) => `<option value="${item.id}">${escapeHtml(item.title)}</option>`).join("")}
              </select>
            </div>
            <div class="field full">
              <label>Ключи</label>
              <textarea name="keys" rows="6" placeholder="По одному ключу на строку"></textarea>
            </div>
            <div class="field full form-actions">
              <button class="primary-button" type="submit">Загрузить ключи</button>
            </div>
          </form>
        </section>
      </aside>
    </div>
  `;
}

function renderUsers() {
  return `
    <div class="grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Пользователи</h2>
            <p>Поиск по Telegram ID, username и имени. Баланс можно пополнять прямо из таблицы.</p>
          </div>
        </div>
        <div class="toolbar">
          <div class="field">
            <label>Поиск</label>
            <input id="users-search" value="${escapeHtml(state.filters.usersSearch)}" placeholder="857..., @username, имя..." />
          </div>
          <div class="field" style="align-self:end;">
            <button class="primary-button" onclick="applyUserFilters()">Найти</button>
          </div>
        </div>
        <div class="table">
          ${state.users
            .map(
              (user) => `
                <article class="table-row">
                  <div>
                    <strong>${escapeHtml(user.full_name)}</strong>
                    <small>@${escapeHtml(user.username || "no_username")} · <span class="mono">${user.tg_id}</span></small>
                  </div>
                  <div>
                    <strong>${escapeHtml(user.balance_label)}</strong>
                    <small>Потрачено ${escapeHtml(user.total_spent_label)}</small>
                  </div>
                  <div class="chip-row">
                    <span class="chip">${user.orders_count} заказов</span>
                    <span class="chip success">${escapeHtml(user.total_deposited_label)}</span>
                    ${user.is_admin ? `<span class="chip warn">admin</span>` : ""}
                  </div>
                  <div class="table-actions">
                    <button class="primary-button" onclick="topUpUser(${user.tg_id})">Пополнить</button>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
      </section>
    </div>
  `;
}

function renderOrders() {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Заказы</h2>
          <p>Последние оформленные покупки с привязкой к пользователю и товару.</p>
        </div>
      </div>
      <div class="table">${state.orders.map(renderOrderRow).join("")}</div>
    </section>
  `;
}

function renderPayments() {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Платежи</h2>
          <p>Статусы счетов CryptoBot, пополнений и покупок товара через платежный flow.</p>
        </div>
      </div>
      <div class="table">${state.payments.map(renderPaymentRow).join("")}</div>
    </section>
  `;
}

function renderSettings() {
  return `
    <div class="split">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Настройки бота</h2>
            <p>Быстрая правка параметров, которые уже хранятся в базе и используются приложением.</p>
          </div>
        </div>
        <form id="settings-form" class="form-grid">
          <div class="field">
            <label>Username поддержки</label>
            <input name="support_username" value="${escapeHtml(state.forms.settings.support_username || "")}" />
          </div>
          <div class="field">
            <label>Username бота</label>
            <input name="bot_username" value="${escapeHtml(state.forms.settings.bot_username || "")}" />
          </div>
          <div class="field">
            <label>Реферальный процент</label>
            <input name="referral_reward_percent" value="${escapeHtml(state.forms.settings.referral_reward_percent || "")}" />
          </div>
          <div class="field">
            <label>Валюта по умолчанию</label>
            <input name="default_currency" value="${escapeHtml(state.forms.settings.default_currency || "USD")}" />
          </div>
          <div class="field full form-actions">
            <button class="primary-button" type="submit">Сохранить настройки</button>
          </div>
        </form>
      </section>
      <aside class="stack">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>О панели</h3>
              <p>Web-админка живет внутри того же контейнера и процесса, что и бот.</p>
            </div>
          </div>
          <div class="mini-list">
            <div class="mini-item">
              <div>
                <strong>Единый deploy</strong>
                <small>Docker запускает bot polling, webhook и web-admin вместе.</small>
              </div>
            </div>
            <div class="mini-item">
              <div>
                <strong>Прямой доступ к данным</strong>
                <small>Каталог, склад, пользователи, заказы и платежи работают на текущей SQLite базе.</small>
              </div>
            </div>
            <div class="mini-item">
              <div>
                <strong>Без отдельного фронтенд-билда</strong>
                <small>Статика встроена в репозиторий и отдается напрямую через aiohttp.</small>
              </div>
            </div>
          </div>
        </section>
      </aside>
    </div>
  `;
}

function renderCurrentTab() {
  switch (state.currentTab) {
    case "catalog":
      return renderCatalog();
    case "users":
      return renderUsers();
    case "orders":
      return renderOrders();
    case "payments":
      return renderPayments();
    case "settings":
      return renderSettings();
    default:
      return renderDashboard();
  }
}

function renderApp() {
  const tabs = [
    ["dashboard", "Dashboard"],
    ["catalog", "Ассортимент"],
    ["users", "Пользователи"],
    ["orders", "Заказы"],
    ["payments", "Платежи"],
    ["settings", "Настройки"],
  ];
  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <small>Shop Bot Admin</small>
          <strong>Control Center</strong>
        </div>
        <nav class="nav">
          ${tabs
            .map(
              ([id, label]) =>
                `<button class="${state.currentTab === id ? "active" : ""}" data-tab="${id}">${escapeHtml(label)}</button>`
            )
            .join("")}
        </nav>
        <div class="sidebar-footer">
          <div class="sidebar-card">
            <small>Авторизован как</small>
            <strong>${escapeHtml(state.session.username)}</strong>
            <div class="muted">Сессия активна в браузере</div>
          </div>
          <button class="ghost-button" id="logout-button">Выйти</button>
        </div>
      </aside>
      <main class="content">
        <div class="topbar">
          <div class="page-title">
            <span class="eyebrow">Telegram commerce operations</span>
            <h1>${state.currentTab === "dashboard" ? "Операционный обзор" : state.currentTab === "catalog" ? "Каталог и склад" : state.currentTab === "users" ? "Пользователи" : state.currentTab === "orders" ? "Заказы" : state.currentTab === "payments" ? "Платежи" : "Системные настройки"}</h1>
            <p>${state.currentTab === "dashboard" ? "Ключевые метрики, продажи, low-stock сигналы и последние оплаты в одном экране." : state.currentTab === "catalog" ? "Добавляйте категории, собирайте товарные карточки и загружайте ключи прямо из web-панели." : state.currentTab === "users" ? "Ищите клиентов, проверяйте финансы и быстро пополняйте баланс вручную." : state.currentTab === "orders" ? "Смотрите ленту последних продаж и выданных товаров." : state.currentTab === "payments" ? "Отслеживайте статусы счетов и подтверждение оплат через CryptoBot." : "Редактируйте общие настройки магазина без похода в Telegram-админку."}</p>
          </div>
          <div class="topbar-actions">
            <button class="secondary-button" id="refresh-button">Обновить данные</button>
            <button class="primary-button" id="goto-catalog-button">Быстро к ассортименту</button>
          </div>
        </div>
        ${renderCurrentTab()}
      </main>
      ${renderToasts()}
    </div>
  `;

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setTab(button.dataset.tab));
  });
  document.getElementById("refresh-button")?.addEventListener("click", async () => {
    await loadAll();
    showToast("Данные обновлены");
    render();
  });
  document.getElementById("goto-catalog-button")?.addEventListener("click", () => setTab("catalog"));
  document.getElementById("logout-button")?.addEventListener("click", handleLogout);
  document.getElementById("category-form")?.addEventListener("submit", submitCategory);
  document.getElementById("product-form")?.addEventListener("submit", updateProduct);
  document.getElementById("stock-form")?.addEventListener("submit", submitStock);
  document.getElementById("settings-form")?.addEventListener("submit", saveSettings);
}

function renderToasts() {
  return `
    <div class="toast-stack">
      ${state.toasts.map((toast) => `<div class="toast">${escapeHtml(toast.message)}</div>`).join("")}
    </div>
  `;
}

function render() {
  if (state.loading && !state.session) {
    app.innerHTML = `<div class="loading">Подключаемся к admin API...</div>`;
    return;
  }
  if (!state.session) {
    renderLogin();
    return;
  }
  renderApp();
}

function applyProductFilters() {
  state.filters.productsSearch = document.getElementById("products-search")?.value || "";
  state.filters.productsCategoryId = document.getElementById("products-category-filter")?.value || "";
  loadProducts().then(render).catch((error) => showToast(error.message));
}

function applyUserFilters() {
  state.filters.usersSearch = document.getElementById("users-search")?.value || "";
  loadUsers().then(render).catch((error) => showToast(error.message));
}

function resetProductForm() {
  state.forms.product = {
    id: "",
    category_id: state.categories[0] ? String(state.categories[0].id) : "",
    title: "",
    internal_name: "",
    price: "",
    warranty_label: "",
    sort_order: "0",
    description: "",
    important_info: "",
  };
  render();
}

window.saveCategory = saveCategory;
window.toggleCategory = toggleCategory;
window.toggleProduct = toggleProduct;
window.fillProductForm = fillProductForm;
window.topUpUser = topUpUser;
window.applyProductFilters = applyProductFilters;
window.applyUserFilters = applyUserFilters;
window.resetProductForm = resetProductForm;

bootstrap();
