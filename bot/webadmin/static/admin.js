const createEmptyCategoryForm = () => ({
  id: "",
  title: "",
  description: "",
  premium_emoji_id: "",
  sort_order: "0",
});

const createEmptyProductForm = (categories = []) => ({
  id: "",
  category_id: categories[0] ? String(categories[0].id) : "",
  title: "",
  internal_name: "",
  price: "",
  warranty_label: "",
  sort_order: "0",
  description: "",
  important_info: "",
});

const createEmptyStockForm = (productId = "") => ({
  product_id: productId ? String(productId) : "",
  keys: "",
});

const state = {
  session: null,
  currentTab: "dashboard",
  catalogTab: "products",
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
    productsStatus: "all",
    productsStock: "all",
    usersSearch: "",
  },
  forms: {
    category: createEmptyCategoryForm(),
    product: createEmptyProductForm(),
    stock: createEmptyStockForm(),
    settings: {},
  },
  ui: {
    modal: null,
  },
  resources: {
    dashboard: { loading: false, error: "" },
    categories: { loading: false, error: "" },
    products: { loading: false, error: "" },
    users: { loading: false, error: "" },
    orders: { loading: false, error: "" },
    payments: { loading: false, error: "" },
    settings: { loading: false, error: "" },
  },
  loading: false,
  refreshing: false,
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
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_) {
      data = {};
    }
  }
  if (!response.ok) {
    throw new Error(data.error || data.message || text || "Request failed");
  }
  return data;
}

function setResourceState(name, patch) {
  state.resources[name] = { ...state.resources[name], ...patch };
}

async function loadResource(name, loader, { silent = false } = {}) {
  setResourceState(name, { loading: true, error: "" });
  if (!silent) render();
  try {
    await loader();
    setResourceState(name, { error: "" });
  } catch (error) {
    setResourceState(name, { error: error.message || "Не удалось загрузить данные" });
  } finally {
    setResourceState(name, { loading: false });
    render();
  }
}

async function bootstrap() {
  state.loading = true;
  render();
  try {
    const session = await fetchJson("/admin/api/session");
    state.session = session.session;
    if (state.session) {
      await loadAll({ silent: true });
    }
  } catch (_) {
    state.session = null;
  } finally {
    state.loading = false;
    render();
  }
}

async function loadAll({ silent = false } = {}) {
  await Promise.all([
    loadDashboard({ silent }),
    loadCategories({ silent }),
    loadProducts({ silent }),
    loadUsers({ silent }),
    loadOrders({ silent }),
    loadPayments({ silent }),
    loadSettings({ silent }),
  ]);
}

async function refreshAllData() {
  state.refreshing = true;
  render();
  await loadAll({ silent: true });
  state.refreshing = false;
  showToast("Данные обновлены");
  render();
}

async function loadDashboard({ silent = false } = {}) {
  await loadResource(
    "dashboard",
    async () => {
      const data = await fetchJson("/admin/api/dashboard");
      state.dashboard = data;
    },
    { silent }
  );
}

async function loadCategories({ silent = false } = {}) {
  await loadResource(
    "categories",
    async () => {
      const data = await fetchJson("/admin/api/categories");
      state.categories = data.items;
      if (!state.forms.product.category_id && data.items[0]) {
        state.forms.product.category_id = String(data.items[0].id);
      }
    },
    { silent }
  );
}

async function loadProducts({ silent = false } = {}) {
  await loadResource(
    "products",
    async () => {
      const data = await fetchJson("/admin/api/products");
      state.products = data.items;
    },
    { silent }
  );
}

async function loadUsers({ silent = false } = {}) {
  const params = new URLSearchParams();
  if (state.filters.usersSearch) params.set("search", state.filters.usersSearch);
  await loadResource(
    "users",
    async () => {
      const data = await fetchJson(`/admin/api/users?${params.toString()}`);
      state.users = data.items;
    },
    { silent }
  );
}

async function loadOrders({ silent = false } = {}) {
  await loadResource(
    "orders",
    async () => {
      const data = await fetchJson("/admin/api/orders?limit=30");
      state.orders = data.items;
    },
    { silent }
  );
}

async function loadPayments({ silent = false } = {}) {
  await loadResource(
    "payments",
    async () => {
      const data = await fetchJson("/admin/api/payments?limit=30");
      state.payments = data.items;
    },
    { silent }
  );
}

async function loadSettings({ silent = false } = {}) {
  await loadResource(
    "settings",
    async () => {
      const data = await fetchJson("/admin/api/settings");
      state.settings = data.item;
      state.forms.settings = { ...data.item };
    },
    { silent }
  );
}

function getResource(name) {
  return state.resources[name];
}

function openModal(type, payload = {}) {
  state.ui.modal = { type, ...payload };
  render();
}

function closeModal() {
  state.ui.modal = null;
  render();
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

function resetCategoryForm() {
  state.forms.category = createEmptyCategoryForm();
}

function resetProductForm() {
  state.forms.product = createEmptyProductForm(state.categories);
}

function resetStockForm(productId = "") {
  state.forms.stock = createEmptyStockForm(productId);
}

function openCreateCategory() {
  resetCategoryForm();
  openModal("category", { mode: "create" });
}

function editCategory(categoryId) {
  const category = state.categories.find((item) => item.id === categoryId);
  if (!category) return;
  state.forms.category = {
    id: String(category.id),
    title: category.title,
    description: category.description,
    premium_emoji_id: category.premium_emoji_id || "",
    sort_order: String(category.sort_order),
  };
  openModal("category", { mode: "edit", entityId: categoryId });
}

async function submitCategory(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = {
    title: form.get("title"),
    description: form.get("description"),
    premium_emoji_id: form.get("premium_emoji_id"),
    sort_order: form.get("sort_order"),
  };
  try {
    if (state.forms.category.id) {
      await fetchJson(`/admin/api/categories/${state.forms.category.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showToast("Категория сохранена");
    } else {
      await fetchJson("/admin/api/categories", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Категория создана");
    }
    resetCategoryForm();
    closeModal();
    await Promise.all([loadCategories({ silent: true }), loadProducts({ silent: true }), loadDashboard({ silent: true })]);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleCategory(categoryId) {
  try {
    await fetchJson(`/admin/api/categories/${categoryId}/toggle`, { method: "POST" });
    await Promise.all([loadCategories({ silent: true }), loadProducts({ silent: true }), loadDashboard({ silent: true })]);
    showToast("Статус категории обновлен");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function openCreateProduct() {
  resetProductForm();
  openModal("product", { mode: "create" });
}

function editProduct(productId) {
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
  openModal("product", { mode: "edit", entityId: productId });
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
    if (state.forms.product.id) {
      await fetchJson(`/admin/api/products/${state.forms.product.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      showToast("Товар сохранен");
    } else {
      await fetchJson("/admin/api/products", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Товар создан");
    }
    resetProductForm();
    closeModal();
    await Promise.all([loadProducts({ silent: true }), loadCategories({ silent: true }), loadDashboard({ silent: true })]);
    render();
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleProduct(productId) {
  try {
    await fetchJson(`/admin/api/products/${productId}/toggle`, { method: "POST" });
    await Promise.all([loadProducts({ silent: true }), loadCategories({ silent: true }), loadDashboard({ silent: true })]);
    showToast("Статус товара обновлен");
    render();
  } catch (error) {
    showToast(error.message);
  }
}

function openStockDrawer(productId = "") {
  resetStockForm(productId);
  openModal("stock", { mode: "create", entityId: productId ? Number(productId) : null });
}

function updateStockDraft(value) {
  state.forms.stock.keys = value;
  render();
}

function countKeys(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean).length;
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
    resetStockForm();
    closeModal();
    await Promise.all([loadProducts({ silent: true }), loadCategories({ silent: true }), loadDashboard({ silent: true })]);
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
    await Promise.all([loadUsers({ silent: true }), loadDashboard({ silent: true })]);
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
    await Promise.all([loadSettings({ silent: true }), loadDashboard({ silent: true })]);
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

function setCatalogTab(tab) {
  state.catalogTab = tab;
  render();
}

function getFilteredProducts() {
  const search = state.filters.productsSearch.trim().toLowerCase();
  return state.products.filter((product) => {
    if (search) {
      const haystack = [product.title, product.internal_name, product.category_title].join(" ").toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    if (state.filters.productsCategoryId && String(product.category_id) !== state.filters.productsCategoryId) {
      return false;
    }
    if (state.filters.productsStatus === "active" && !product.is_active) return false;
    if (state.filters.productsStatus === "hidden" && product.is_active) return false;
    if (state.filters.productsStock === "in_stock" && product.stock_count <= 0) return false;
    if (state.filters.productsStock === "out_of_stock" && product.stock_count > 0) return false;
    return true;
  });
}

function getVisibleStockProducts() {
  return state.products.filter((product) => product.is_active);
}

function getArchiveData() {
  return {
    products: state.products.filter((product) => !product.is_active),
    categories: state.categories.filter((category) => !category.is_active),
  };
}

function getCatalogMetrics() {
  const total = state.products.length;
  const active = state.products.filter((item) => item.is_active).length;
  const hidden = state.products.filter((item) => !item.is_active).length;
  const outOfStock = state.products.filter((item) => item.is_active && item.stock_count === 0).length;
  return { total, active, hidden, outOfStock };
}

function renderLogin() {
  app.innerHTML = `
    <div class="auth-shell">
      <div class="auth-card">
        <h1>Shop Admin</h1>
        <p>Компактная операционная панель для каталога, склада, пользователей и платежей.</p>
        <form id="login-form">
          <div class="field">
            <label>Логин</label>
            <input name="username" placeholder="admin" autocomplete="username" required />
          </div>
          <div class="field">
            <label>Пароль</label>
            <input type="password" name="password" placeholder="Введите пароль" autocomplete="current-password" required />
          </div>
          <button class="primary-button" type="submit">Войти</button>
        </form>
      </div>
      ${renderToasts()}
    </div>
  `;
  document.getElementById("login-form")?.addEventListener("submit", handleLogin);
}

function renderMetricCard(title, value, footLeft, footRight, tone = "") {
  return `
    <section class="panel metric-card ${tone}">
      <strong>${escapeHtml(title)}</strong>
      <div class="value">${escapeHtml(value)}</div>
      <div class="metric-foot"><span>${escapeHtml(footLeft)}</span><span>${escapeHtml(footRight)}</span></div>
    </section>
  `;
}

function renderDashboard() {
  const resource = getResource("dashboard");
  const data = state.dashboard;
  if (resource.loading && !data) {
    return `<div class="panel"><div class="table-skeleton">${renderSkeletonRows(4, 3)}</div></div>`;
  }
  if (resource.error && !data) {
    return renderErrorPanel("Не удалось загрузить dashboard", "loadDashboard");
  }
  if (!data) {
    return `<div class="panel"><div class="empty-state"><strong>Нет данных</strong><p>Dashboard пока пуст.</p></div></div>`;
  }
  const maxRevenue = Math.max(...data.series.map((item) => item.revenue_cents), 1);
  return `
    <div class="grid">
      <div class="stats-grid">
        ${renderMetricCard("Выручка", data.stats.revenue_label, "Подтверждено", `${data.stats.orders_total} заказов`)}
        ${renderMetricCard("Пользователи", String(data.stats.users_total), "Всего в базе", `${data.stats.categories_total} категорий`)}
        ${renderMetricCard("Ключи на складе", String(data.stats.stock_total), "Доступно сейчас", `${data.low_stock.length} low stock`, "warn")}
        ${renderMetricCard("Ожидают оплаты", String(data.stats.payments_pending_total), "Последние счета", `${data.stats.products_total} товаров`)}
      </div>
      <div class="grid columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Продажи за 7 дней</h2>
              <p>Подтвержденные заказы и выручка.</p>
            </div>
          </div>
          <div class="chart">
            ${data.series
              .map(
                (item) => `
                  <div class="chart-bar">
                    <div class="chart-bar-fill" style="height:${Math.max(18, (item.revenue_cents / maxRevenue) * 160)}px"></div>
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
                <h3>Низкий остаток</h3>
                <p>Товары, которые требуют внимания.</p>
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
                  : `<div class="empty-state compact"><strong>Все стабильно</strong><p>Критичных остатков сейчас нет.</p></div>`
              }
            </div>
          </section>
          <section class="panel">
            <div class="panel-header">
              <div>
                <h3>Активные покупатели</h3>
                <p>Последние пользователи с заказами.</p>
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
              <p>Продажи по каталогу.</p>
            </div>
          </div>
          <div class="simple-list">${data.recent_orders.map(renderOrderRow).join("")}</div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>Последние платежи</h3>
              <p>Пополнения и покупки через CryptoBot.</p>
            </div>
          </div>
          <div class="simple-list">${data.recent_payments.map(renderPaymentRow).join("")}</div>
        </section>
      </div>
    </div>
  `;
}

function renderOrderRow(item) {
  return `
    <article class="list-row compact">
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
    <article class="list-row compact">
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

function renderSectionHeader(title, description, actionHtml = "") {
  return `
    <div class="panel-header">
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(description)}</p>
      </div>
      ${actionHtml}
    </div>
  `;
}

function renderSkeletonRows(columnCount, rowCount = 5) {
  return Array.from({ length: rowCount }, () => {
    return `
      <div class="skeleton-row" style="grid-template-columns: repeat(${columnCount}, minmax(0, 1fr));">
        ${Array.from({ length: columnCount }, () => `<span class="skeleton-block"></span>`).join("")}
      </div>
    `;
  }).join("");
}

function renderErrorPanel(message, retryAction) {
  return `
    <div class="error-state">
      <strong>${escapeHtml(message)}</strong>
      <p>Интерфейс продолжает работать, можно попробовать загрузить блок еще раз.</p>
      <button class="secondary-button" onclick="${retryAction}()">Повторить</button>
    </div>
  `;
}

function renderEmptyState(title, description, actionHtml = "") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(description)}</p>
      ${actionHtml}
    </div>
  `;
}

function renderDataTable({ columns, rows, loading, error, retryAction, emptyTitle, emptyDescription, colSpan }) {
  if (loading) {
    return `<div class="table-skeleton">${renderSkeletonRows(columns.length, 6)}</div>`;
  }
  if (error) {
    return renderErrorPanel(error, retryAction);
  }
  if (!rows.length) {
    return renderEmptyState(emptyTitle, emptyDescription);
  }
  return `
    <div class="data-table-shell">
      <table class="data-table">
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((row) => `<tr>${row}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderCatalogTabs() {
  const tabs = [
    ["products", "Товары"],
    ["categories", "Категории"],
    ["stock", "Склад ключей"],
    ["archive", "Архив"],
  ];
  return `
    <div class="subtabs">
      ${tabs
        .map(
          ([id, label]) =>
            `<button class="${state.catalogTab === id ? "active" : ""}" onclick="setCatalogTab('${id}')">${escapeHtml(label)}</button>`
        )
        .join("")}
    </div>
  `;
}

function renderProductStatus(product) {
  if (!product.is_active) {
    return `<span class="chip neutral">Скрыт</span>`;
  }
  if (product.stock_count === 0) {
    return `<span class="chip danger">Нет ключей</span>`;
  }
  return `<span class="chip success">Активен</span>`;
}

function renderProductsTab() {
  const metrics = getCatalogMetrics();
  const products = getFilteredProducts();
  const resource = getResource("products");
  return `
    <section class="panel">
      ${renderSectionHeader(
        "Товары",
        "Быстрый контроль каталога, остатков и видимости товаров.",
        `<button class="primary-button" onclick="openCreateProduct()">Новый товар</button>`
      )}
      <div class="stats-grid compact">
        ${renderMetricCard("Всего товаров", String(metrics.total), "Все позиции", "Каталог")}
        ${renderMetricCard("Активных", String(metrics.active), "Видимы на витрине", "Готовы к продаже", "success")}
        ${renderMetricCard("Без ключей", String(metrics.outOfStock), "Активные товары", "Требуют пополнения", "warn")}
        ${renderMetricCard("Скрытых", String(metrics.hidden), "Не видны клиенту", "Архив/паузa", "neutral")}
      </div>
      <form id="catalog-products-filters" class="toolbar dense">
        <div class="field grow-2">
          <label>Поиск</label>
          <input name="search" value="${escapeHtml(state.filters.productsSearch)}" placeholder="Название, внутреннее имя, категория" />
        </div>
        <div class="field">
          <label>Категория</label>
          <select name="category_id">
            <option value="">Все категории</option>
            ${state.categories
              .map((item) => `<option value="${item.id}" ${String(item.id) === state.filters.productsCategoryId ? "selected" : ""}>${escapeHtml(item.title)}</option>`)
              .join("")}
          </select>
        </div>
        <div class="field">
          <label>Статус</label>
          <select name="status">
            <option value="all" ${state.filters.productsStatus === "all" ? "selected" : ""}>Все</option>
            <option value="active" ${state.filters.productsStatus === "active" ? "selected" : ""}>Активные</option>
            <option value="hidden" ${state.filters.productsStatus === "hidden" ? "selected" : ""}>Скрытые</option>
          </select>
        </div>
        <div class="field">
          <label>Наличие ключей</label>
          <select name="stock">
            <option value="all" ${state.filters.productsStock === "all" ? "selected" : ""}>Все</option>
            <option value="in_stock" ${state.filters.productsStock === "in_stock" ? "selected" : ""}>Есть ключи</option>
            <option value="out_of_stock" ${state.filters.productsStock === "out_of_stock" ? "selected" : ""}>Нет ключей</option>
          </select>
        </div>
        <div class="toolbar-actions">
          <button class="secondary-button" type="button" onclick="resetProductFilters()">Сбросить</button>
          <button class="primary-button" type="submit">Применить</button>
        </div>
      </form>
      ${renderDataTable({
        columns: ["Товар", "Категория", "Цена", "Склад", "Продано", "Статус", "Действия"],
        rows: products.map(
          (product) => `
            <td>
              <div class="cell-primary">
                <strong>${escapeHtml(product.title)}</strong>
                <small>${escapeHtml(product.internal_name || "Без внутреннего имени")}</small>
              </div>
            </td>
            <td>${escapeHtml(product.category_title)}</td>
            <td class="mono">${escapeHtml(product.price_label)}</td>
            <td><span class="chip ${product.stock_count === 0 ? "danger" : product.stock_count <= 3 ? "warn" : "success"}">${product.stock_count}</span></td>
            <td>${product.sold_count}</td>
            <td>${renderProductStatus(product)}</td>
            <td>
              <div class="row-actions">
                <button class="secondary-button small" onclick="editProduct(${product.id})">Редактировать</button>
                <button class="secondary-button small" onclick="openStockDrawer(${product.id})">Загрузить ключи</button>
                <button class="secondary-button small" onclick="toggleProduct(${product.id})">${product.is_active ? "Скрыть" : "Активировать"}</button>
              </div>
            </td>
          `
        ),
        loading: resource.loading && !state.products.length,
        error: resource.error && !state.products.length ? resource.error : "",
        retryAction: "loadProducts",
        emptyTitle: "Товары не найдены",
        emptyDescription: "Измените фильтры или создайте новую позицию.",
        colSpan: 7,
      })}
    </section>
  `;
}

function renderCategoriesTab() {
  const resource = getResource("categories");
  return `
    <section class="panel">
      ${renderSectionHeader(
        "Категории",
        "Компактный список разделов каталога с остатками и статусами.",
        `<button class="primary-button" onclick="openCreateCategory()">Новая категория</button>`
      )}
      ${renderDataTable({
        columns: ["Название", "Emoji ID", "Товаров", "Активных", "Ключей", "Порядок", "Статус", "Действия"],
        rows: state.categories.map(
          (category) => `
            <td>
              <div class="cell-primary">
                <strong>${escapeHtml(category.title)}</strong>
                <small>${escapeHtml(category.description || "Без описания")}</small>
              </div>
            </td>
            <td class="mono">${escapeHtml(category.premium_emoji_id || "—")}</td>
            <td>${category.products_count}</td>
            <td>${category.active_products_count}</td>
            <td>${category.stock_total}</td>
            <td>${category.sort_order}</td>
            <td><span class="chip ${category.is_active ? "success" : "neutral"}">${category.is_active ? "Активна" : "Скрыта"}</span></td>
            <td>
              <div class="row-actions">
                <button class="secondary-button small" onclick="editCategory(${category.id})">Редактировать</button>
                <button class="secondary-button small" onclick="toggleCategory(${category.id})">${category.is_active ? "Скрыть" : "Активировать"}</button>
              </div>
            </td>
          `
        ),
        loading: resource.loading && !state.categories.length,
        error: resource.error && !state.categories.length ? resource.error : "",
        retryAction: "loadCategories",
        emptyTitle: "Категорий пока нет",
        emptyDescription: "Создайте первую категорию для каталога.",
        colSpan: 8,
      })}
    </section>
  `;
}

function renderStockTab() {
  const resource = getResource("products");
  const items = getVisibleStockProducts();
  return `
    <section class="panel">
      ${renderSectionHeader(
        "Склад ключей",
        "Остатки по товарам и быстрая загрузка новых ключей.",
        `<button class="primary-button" onclick="openStockDrawer()">Загрузить ключи</button>`
      )}
      ${renderDataTable({
        columns: ["Товар", "Категория", "Остаток", "Продано", "Действия"],
        rows: items.map(
          (product) => `
            <td>
              <div class="cell-primary">
                <strong>${escapeHtml(product.title)}</strong>
                <small>${escapeHtml(product.internal_name || "Без внутреннего имени")}</small>
              </div>
            </td>
            <td>${escapeHtml(product.category_title)}</td>
            <td><span class="chip ${product.stock_count === 0 ? "danger" : product.stock_count <= 3 ? "warn" : "success"}">${product.stock_count}</span></td>
            <td>${product.sold_count}</td>
            <td>
              <div class="row-actions">
                <button class="secondary-button small" onclick="openStockDrawer(${product.id})">Загрузить ключи</button>
                <button class="secondary-button small" onclick="editProduct(${product.id})">Открыть товар</button>
              </div>
            </td>
          `
        ),
        loading: resource.loading && !state.products.length,
        error: resource.error && !state.products.length ? resource.error : "",
        retryAction: "loadProducts",
        emptyTitle: "Нет активных товаров",
        emptyDescription: "Активируйте или создайте товар, чтобы пополнять склад.",
        colSpan: 5,
      })}
    </section>
  `;
}

function renderArchiveTab() {
  const archive = getArchiveData();
  const productsHtml = renderDataTable({
    columns: ["Товар", "Категория", "Цена", "Склад", "Действия"],
    rows: archive.products.map(
      (product) => `
        <td>
          <div class="cell-primary">
            <strong>${escapeHtml(product.title)}</strong>
            <small>${escapeHtml(product.internal_name || "Без внутреннего имени")}</small>
          </div>
        </td>
        <td>${escapeHtml(product.category_title)}</td>
        <td class="mono">${escapeHtml(product.price_label)}</td>
        <td>${product.stock_count}</td>
        <td>
          <div class="row-actions">
            <button class="secondary-button small" onclick="editProduct(${product.id})">Редактировать</button>
            <button class="secondary-button small" onclick="toggleProduct(${product.id})">Активировать</button>
          </div>
        </td>
      `
    ),
    loading: false,
    error: "",
    retryAction: "loadProducts",
    emptyTitle: "Скрытых товаров нет",
    emptyDescription: "Здесь появятся товары, снятые с витрины.",
    colSpan: 5,
  });
  const categoriesHtml = renderDataTable({
    columns: ["Категория", "Товаров", "Ключей", "Действия"],
    rows: archive.categories.map(
      (category) => `
        <td>
          <div class="cell-primary">
            <strong>${escapeHtml(category.title)}</strong>
            <small>${escapeHtml(category.description || "Без описания")}</small>
          </div>
        </td>
        <td>${category.products_count}</td>
        <td>${category.stock_total}</td>
        <td>
          <div class="row-actions">
            <button class="secondary-button small" onclick="editCategory(${category.id})">Редактировать</button>
            <button class="secondary-button small" onclick="toggleCategory(${category.id})">Активировать</button>
          </div>
        </td>
      `
    ),
    loading: false,
    error: "",
    retryAction: "loadCategories",
    emptyTitle: "Скрытых категорий нет",
    emptyDescription: "Здесь появятся отключенные разделы каталога.",
    colSpan: 4,
  });
  return `
    <div class="stack">
      <section class="panel">
        ${renderSectionHeader("Архив товаров", "Скрытые товары, которые можно вернуть на витрину.")}
        ${productsHtml}
      </section>
      <section class="panel">
        ${renderSectionHeader("Архив категорий", "Отключенные категории и их текущие остатки.")}
        ${categoriesHtml}
      </section>
    </div>
  `;
}

function renderCatalog() {
  const categoriesReady = !getResource("categories").loading && !getResource("categories").error;
  const productsReady = !getResource("products").loading && !getResource("products").error;
  const hasCriticalError = (!state.categories.length && getResource("categories").error) || (!state.products.length && getResource("products").error);
  let content = "";
  if (hasCriticalError && !categoriesReady && !productsReady) {
    content = `<section class="panel">${renderErrorPanel("Не удалось загрузить ассортимент", "refreshAllData")}</section>`;
  } else if (state.catalogTab === "categories") {
    content = renderCategoriesTab();
  } else if (state.catalogTab === "stock") {
    content = renderStockTab();
  } else if (state.catalogTab === "archive") {
    content = renderArchiveTab();
  } else {
    content = renderProductsTab();
  }
  return `
    <div class="stack">
      ${renderCatalogTabs()}
      ${content}
    </div>
  `;
}

function renderUsers() {
  const resource = getResource("users");
  return `
    <div class="grid">
      <section class="panel">
        ${renderSectionHeader("Пользователи", "Поиск по Telegram ID, username и имени. Баланс можно пополнять прямо из таблицы.")}
        <form id="users-search-form" class="toolbar dense">
          <div class="field grow-2">
            <label>Поиск</label>
            <input name="search" value="${escapeHtml(state.filters.usersSearch)}" placeholder="857..., @username, имя..." />
          </div>
          <div class="toolbar-actions">
            <button class="primary-button" type="submit">Найти</button>
          </div>
        </form>
        ${renderDataTable({
          columns: ["Пользователь", "Баланс", "Показатели", "Действия"],
          rows: state.users.map(
            (user) => `
              <td>
                <div class="cell-primary">
                  <strong>${escapeHtml(user.full_name)}</strong>
                  <small>@${escapeHtml(user.username || "no_username")} · <span class="mono">${user.tg_id}</span></small>
                </div>
              </td>
              <td>
                <div class="cell-primary">
                  <strong>${escapeHtml(user.balance_label)}</strong>
                  <small>Потрачено ${escapeHtml(user.total_spent_label)}</small>
                </div>
              </td>
              <td>
                <div class="chip-row">
                  <span class="chip">${user.orders_count} заказов</span>
                  <span class="chip success">${escapeHtml(user.total_deposited_label)}</span>
                  ${user.is_admin ? `<span class="chip warn">admin</span>` : ""}
                </div>
              </td>
              <td>
                <div class="row-actions">
                  <button class="primary-button small" onclick="topUpUser(${user.tg_id})">Пополнить</button>
                </div>
              </td>
            `
          ),
          loading: resource.loading && !state.users.length,
          error: resource.error && !state.users.length ? resource.error : "",
          retryAction: "loadUsers",
          emptyTitle: "Пользователи не найдены",
          emptyDescription: "Попробуйте изменить поисковый запрос.",
          colSpan: 4,
        })}
      </section>
    </div>
  `;
}

function renderOrders() {
  const resource = getResource("orders");
  return `
    <section class="panel">
      ${renderSectionHeader("Заказы", "Последние оформленные покупки с привязкой к пользователю и товару.")}
      ${
        resource.loading && !state.orders.length
          ? `<div class="table-skeleton">${renderSkeletonRows(3, 6)}</div>`
          : resource.error && !state.orders.length
            ? renderErrorPanel(resource.error, "loadOrders")
            : `<div class="simple-list">${state.orders.map(renderOrderRow).join("")}</div>`
      }
    </section>
  `;
}

function renderPayments() {
  const resource = getResource("payments");
  return `
    <section class="panel">
      ${renderSectionHeader("Платежи", "Статусы счетов CryptoBot, пополнений и покупок товара через платежный flow.")}
      ${
        resource.loading && !state.payments.length
          ? `<div class="table-skeleton">${renderSkeletonRows(3, 6)}</div>`
          : resource.error && !state.payments.length
            ? renderErrorPanel(resource.error, "loadPayments")
            : `<div class="simple-list">${state.payments.map(renderPaymentRow).join("")}</div>`
      }
    </section>
  `;
}

function renderSettings() {
  return `
    <div class="split">
      <section class="panel">
        ${renderSectionHeader("Настройки бота", "Быстрая правка параметров, которые хранятся в базе и используются приложением.")}
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
          ${renderSectionHeader("О панели", "Админка работает в том же приложении, что и бот.")}
          <div class="mini-list">
            <div class="mini-item">
              <div>
                <strong>Единый deploy</strong>
                <small>Бот, webhook и web-admin запускаются вместе.</small>
              </div>
            </div>
            <div class="mini-item">
              <div>
                <strong>Прямой доступ к данным</strong>
                <small>Каталог, склад, пользователи и платежи работают на текущей SQLite базе.</small>
              </div>
            </div>
            <div class="mini-item">
              <div>
                <strong>Без отдельного фронтенда</strong>
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

function renderModal() {
  const modal = state.ui.modal;
  if (!modal) return "";
  if (modal.type === "category") {
    return `
      <div class="modal-backdrop" data-close-modal="true">
        <aside class="drawer" role="dialog" aria-modal="true">
          <div class="drawer-header">
            <div>
              <h3>${state.forms.category.id ? "Редактирование категории" : "Новая категория"}</h3>
              <p>${state.forms.category.id ? "Измените параметры категории." : "Создайте новый раздел каталога."}</p>
            </div>
            <button class="icon-button" type="button" data-close-modal="true">×</button>
          </div>
          <form id="category-form" class="form-grid drawer-form">
            <div class="field full">
              <label>Название</label>
              <input name="title" value="${escapeHtml(state.forms.category.title)}" required />
            </div>
            <div class="field full">
              <label>Описание</label>
              <textarea name="description" rows="4">${escapeHtml(state.forms.category.description)}</textarea>
            </div>
            <div class="field">
              <label>Emoji ID</label>
              <input class="mono" name="premium_emoji_id" value="${escapeHtml(state.forms.category.premium_emoji_id)}" placeholder="Можно оставить пустым" />
            </div>
            <div class="field">
              <label>Порядок</label>
              <input name="sort_order" value="${escapeHtml(state.forms.category.sort_order)}" />
            </div>
            <div class="field full form-actions">
              <button class="secondary-button" type="button" data-close-modal="true">Отмена</button>
              <button class="primary-button" type="submit">${state.forms.category.id ? "Сохранить" : "Создать"}</button>
            </div>
          </form>
        </aside>
      </div>
    `;
  }
  if (modal.type === "product") {
    return `
      <div class="modal-backdrop" data-close-modal="true">
        <aside class="drawer wide" role="dialog" aria-modal="true">
          <div class="drawer-header">
            <div>
              <h3>${state.forms.product.id ? "Редактирование товара" : "Новый товар"}</h3>
              <p>${state.forms.product.id ? "Обновите карточку, цену и описание." : "Добавьте новую позицию в каталог."}</p>
            </div>
            <button class="icon-button" type="button" data-close-modal="true">×</button>
          </div>
          <form id="product-form" class="form-grid drawer-form">
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
              <button class="secondary-button" type="button" data-close-modal="true">Отмена</button>
              <button class="primary-button" type="submit">${state.forms.product.id ? "Сохранить" : "Создать"}</button>
            </div>
          </form>
        </aside>
      </div>
    `;
  }
  const selectedProduct = state.products.find((item) => String(item.id) === state.forms.stock.product_id);
  const keyCount = countKeys(state.forms.stock.keys);
  return `
    <div class="modal-backdrop" data-close-modal="true">
      <aside class="drawer" role="dialog" aria-modal="true">
        <div class="drawer-header">
          <div>
            <h3>Загрузка ключей</h3>
            <p>Добавляйте ключи пачкой, по одному ключу на строку.</p>
          </div>
          <button class="icon-button" type="button" data-close-modal="true">×</button>
        </div>
        <form id="stock-form" class="form-grid drawer-form">
          <div class="field full">
            <label>Товар</label>
            <select name="product_id" required>
              <option value="">Выберите товар</option>
              ${state.products
                .map((item) => `<option value="${item.id}" ${String(item.id) === state.forms.stock.product_id ? "selected" : ""}>${escapeHtml(item.title)} · ${escapeHtml(item.category_title)}</option>`)
                .join("")}
            </select>
          </div>
          ${
            selectedProduct
              ? `<div class="inline-note">Текущий остаток: <strong>${selectedProduct.stock_count}</strong> · Продано: <strong>${selectedProduct.sold_count}</strong></div>`
              : ""
          }
          <div class="field full">
            <label>Ключи</label>
            <textarea id="stock-keys-textarea" name="keys" rows="10" placeholder="По одному ключу на строку">${escapeHtml(state.forms.stock.keys)}</textarea>
          </div>
          <div class="drawer-footer-meta">
            <span class="muted">Подсказка: по одному ключу на строку</span>
            <span class="chip">${keyCount} найдено</span>
          </div>
          <div class="field full form-actions">
            <button class="secondary-button" type="button" data-close-modal="true">Отмена</button>
            <button class="primary-button" type="submit">Загрузить ключи</button>
          </div>
        </form>
      </aside>
    </div>
  `;
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
  const titleMap = {
    dashboard: "Операционный обзор",
    catalog: "Ассортимент",
    users: "Пользователи",
    orders: "Заказы",
    payments: "Платежи",
    settings: "Системные настройки",
  };
  const descriptionMap = {
    dashboard: "Ключевые метрики, продажи, остатки и последние оплаты в одном экране.",
    catalog: "Компактное управление товарами, категориями, складом ключей и архивом.",
    users: "Поиск клиентов, финансы и ручное пополнение баланса.",
    orders: "Последние оформленные продажи и выдачи товаров.",
    payments: "Проверка статусов счетов и подтверждений оплат.",
    settings: "Редактирование общих параметров магазина без перехода в Telegram.",
  };
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
            <h1>${escapeHtml(titleMap[state.currentTab])}</h1>
            <p>${escapeHtml(descriptionMap[state.currentTab])}</p>
          </div>
          <div class="topbar-actions">
            <button class="secondary-button" id="refresh-button">${state.refreshing ? "Обновляем..." : "Обновить"}</button>
            <button class="primary-button" id="goto-catalog-button">К ассортименту</button>
          </div>
        </div>
        ${renderCurrentTab()}
      </main>
      ${renderToasts()}
      ${renderModal()}
    </div>
  `;

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setTab(button.dataset.tab));
  });
  document.getElementById("refresh-button")?.addEventListener("click", refreshAllData);
  document.getElementById("goto-catalog-button")?.addEventListener("click", () => setTab("catalog"));
  document.getElementById("logout-button")?.addEventListener("click", handleLogout);
  document.getElementById("settings-form")?.addEventListener("submit", saveSettings);
  document.getElementById("users-search-form")?.addEventListener("submit", applyUserFilters);
  document.getElementById("catalog-products-filters")?.addEventListener("submit", applyProductFilters);
  document.getElementById("category-form")?.addEventListener("submit", submitCategory);
  document.getElementById("product-form")?.addEventListener("submit", submitProduct);
  document.getElementById("stock-form")?.addEventListener("submit", submitStock);
  document.getElementById("stock-keys-textarea")?.addEventListener("input", (event) => updateStockDraft(event.currentTarget.value));
  document.querySelectorAll("[data-close-modal]").forEach((node) => {
    node.addEventListener("click", (event) => {
      if (event.target === node || node.dataset.closeModal === "true") {
        closeModal();
      }
    });
  });
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

function applyProductFilters(event) {
  if (event) event.preventDefault();
  state.filters.productsSearch = document.querySelector('#catalog-products-filters [name="search"]')?.value || "";
  state.filters.productsCategoryId = document.querySelector('#catalog-products-filters [name="category_id"]')?.value || "";
  state.filters.productsStatus = document.querySelector('#catalog-products-filters [name="status"]')?.value || "all";
  state.filters.productsStock = document.querySelector('#catalog-products-filters [name="stock"]')?.value || "all";
  render();
}

function resetProductFilters() {
  state.filters.productsSearch = "";
  state.filters.productsCategoryId = "";
  state.filters.productsStatus = "all";
  state.filters.productsStock = "all";
  render();
}

function applyUserFilters(event) {
  event.preventDefault();
  state.filters.usersSearch = document.querySelector('#users-search-form [name="search"]')?.value || "";
  loadUsers({ silent: true }).catch((error) => showToast(error.message));
}

window.loadDashboard = loadDashboard;
window.loadCategories = loadCategories;
window.loadProducts = loadProducts;
window.loadUsers = loadUsers;
window.loadOrders = loadOrders;
window.loadPayments = loadPayments;
window.refreshAllData = refreshAllData;
window.toggleCategory = toggleCategory;
window.toggleProduct = toggleProduct;
window.topUpUser = topUpUser;
window.setCatalogTab = setCatalogTab;
window.openCreateCategory = openCreateCategory;
window.editCategory = editCategory;
window.openCreateProduct = openCreateProduct;
window.editProduct = editProduct;
window.openStockDrawer = openStockDrawer;
window.resetProductFilters = resetProductFilters;

bootstrap();
