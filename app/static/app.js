const API_BASE = "";

const state = {
  products: [],
  category: "",
  occasion: "",
  color: "",
  query: "",
  token: localStorage.getItem("flower_token") || "",
  user: JSON.parse(localStorage.getItem("flower_user") || "null"),
  localCart: JSON.parse(localStorage.getItem("flower_local_cart") || "[]"),
  remoteCart: { items: [], total: 0 },
  authMode: "login",
  view: "catalog",
  orders: [],
  adminOrders: [],
  adminProducts: [],
  adminUsers: [],
  reviewSummaries: {},
  reviewProduct: null,
};

const fallbackImages = [
  "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1520763185298-1b434c919102?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1459411621453-7b03977f4bfc?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1470509037663-253afd7f0f51?auto=format&fit=crop&w=900&q=80",
];

const colorMap = {
  red: "#c94f5d",
  white: "#f7f7f2",
  pink: "#eaa3b3",
  yellow: "#e4b743",
  green: "#4e8a5f",
  purple: "#8660a8",
  orange: "#d9823b",
};

const els = {
  appShell: document.querySelector(".app-shell"),
  grid: document.querySelector("#productGrid"),
  catalogView: document.querySelector("#catalogView"),
  ordersView: document.querySelector("#ordersView"),
  adminView: document.querySelector("#adminView"),
  clientOrdersView: document.querySelector("#clientOrdersView"),
  pageEyebrow: document.querySelector("#pageEyebrow"),
  pageTitle: document.querySelector("#pageTitle"),
  status: document.querySelector("#statusLine"),
  search: document.querySelector("#searchInput"),
  occasion: document.querySelector("#occasionFilter"),
  color: document.querySelector("#colorFilter"),
  cartPanel: document.querySelector("#cartPanel"),
  cartItems: document.querySelector("#cartItems"),
  cartTotal: document.querySelector("#cartTotal"),
  cartCount: document.querySelector("#cartCount"),
  checkoutForm: document.querySelector("#checkoutForm"),
  address: document.querySelector("#addressInput"),
  authOpen: document.querySelector("#authOpenBtn"),
  logout: document.querySelector("#logoutBtn"),
  categoryNav: document.querySelector(".category-nav"),
  categoryToggle: document.querySelector("#categoryToggle"),
  authModal: document.querySelector("#authModal"),
  authForm: document.querySelector("#authForm"),
  authClose: document.querySelector("#authClose"),
  authSubmit: document.querySelector("#authSubmit"),
  authToggle: document.querySelector("#authModeToggle"),
  modalTitle: document.querySelector("#modalTitle"),
  productModal: document.querySelector("#productModal"),
  productModalClose: document.querySelector("#productModalClose"),
  productModalImage: document.querySelector("#productModalImage"),
  productModalTitle: document.querySelector("#productModalTitle"),
  productModalMeta: document.querySelector("#productModalMeta"),
  productModalDescription: document.querySelector("#productModalDescription"),
  productModalReviewSummary: document.querySelector("#productModalReviewSummary"),
  productModalSoldCount: document.querySelector("#productModalSoldCount"),
  productModalReviewList: document.querySelector("#productModalReviewList"),
  productModalPrice: document.querySelector("#productModalPrice"),
  productModalAdd: document.querySelector("#productModalAdd"),
  reviewModal: document.querySelector("#reviewModal"),
  reviewForm: document.querySelector("#reviewForm"),
  reviewModalClose: document.querySelector("#reviewModalClose"),
  reviewModalTitle: document.querySelector("#reviewModalTitle"),
  reviewRating: document.querySelector("#reviewRatingInput"),
  reviewComment: document.querySelector("#reviewCommentInput"),
  name: document.querySelector("#nameInput"),
  email: document.querySelector("#emailInput"),
  password: document.querySelector("#passwordInput"),
  phone: document.querySelector("#phoneInput"),
  adminNav: document.querySelector("#adminNavBtn"),
  clientOrdersNav: document.querySelector("#clientOrdersNavBtn"),
  ordersList: document.querySelector("#ordersList"),
  adminStats: document.querySelector("#adminStats"),
  adminOrdersBody: document.querySelector("#adminOrdersBody"),
  adminUsersBody: document.querySelector("#adminUsersBody"),
  refreshOrders: document.querySelector("#refreshOrdersBtn"),
  refreshAdmin: document.querySelector("#refreshAdminBtn"),
  refreshClientOrders: document.querySelector("#refreshClientOrdersBtn"),
  productForm: document.querySelector("#productForm"),
  productEditingId: document.querySelector("#productEditingId"),
  adminProductGrid: document.querySelector("#adminProductGrid"),
  productName: document.querySelector("#productNameInput"),
  productPrice: document.querySelector("#productPriceInput"),
  productStock: document.querySelector("#productStockInput"),
  productCategory: document.querySelector("#productCategoryInput"),
  productOccasion: document.querySelector("#productOccasionInput"),
  productColor: document.querySelector("#productColorInput"),
  productImage: document.querySelector("#productImageInput"),
  productDescription: document.querySelector("#productDescriptionInput"),
  productSubmit: document.querySelector("#productSubmitBtn"),
  productCancelEdit: document.querySelector("#productCancelEditBtn"),
  toast: document.querySelector("#toast"),
};

const orderStatuses = ["pending", "confirmed", "preparing", "delivering", "delivered", "cancelled"];
const userRoles = ["admin", "manager", "customer"];

function money(value) {
  return `$${Number(value || 0).toFixed(0)}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[char]);
}

function shortId(value) {
  return String(value || "").slice(0, 8);
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => els.toast.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }

  return data;
}

function imageFor(product) {
  if (product.image_url) return product.image_url;
  const source = `${product.id || product.name || ""}`;
  const index = [...source].reduce((sum, char) => sum + char.charCodeAt(0), 0) % fallbackImages.length;
  return fallbackImages[index];
}

function normalizeProduct(raw) {
  return {
    id: raw.id || raw.product_id,
    name: raw.name || "Untitled bouquet",
    price: Number(raw.price || 0),
    category: raw.category || "",
    color: raw.color || "",
    occasion: raw.occasion || "",
    stock: Number(raw.stock ?? raw.stock_quantity ?? 0),
    image_url: raw.image_url || "",
    description: raw.description || "",
    average_rating: raw.average_rating ?? null,
    review_count: Number(raw.review_count || 0),
    sold_count: Number(raw.sold_count || 0),
  };
}

async function loadProducts() {
  els.status.textContent = "Loading catalog...";
  const params = new URLSearchParams();
  if (state.category) params.set("category", state.category);
  if (state.occasion) params.set("occasion", state.occasion);
  if (state.color) params.set("color", state.color);

  try {
    if (state.query.trim()) {
      const data = await api(`/api/products/search?q=${encodeURIComponent(state.query.trim())}`);
      const detailed = await Promise.all((data.results || []).map(async (item) => {
        try {
          return await api(`/api/products/${encodeURIComponent(item.id)}`);
        } catch {
          return item;
        }
      }));
      state.products = detailed.map(normalizeProduct);
    } else {
      const data = await api(`/api/products/${params.toString() ? `?${params}` : ""}`);
      state.products = (data.products || []).map(normalizeProduct);
    }
    renderProducts();
    loadReviewSummaries();
  } catch (error) {
    els.status.textContent = "Could not load products. Check that API services are running.";
    els.grid.innerHTML = "";
  }
}

function reviewSummaryText(summary) {
  if (!summary || !summary.average_rating) return "";
  return `${Number(summary.average_rating).toFixed(1)}`;
}

function renderProducts() {
  els.status.textContent = state.products.length
    ? `${state.products.length} products available`
    : "No products match these filters.";

  els.grid.innerHTML = state.products.map((product) => {
    const stockLabel = product.stock <= 5 ? `${product.stock} left` : "In stock";
    const color = colorMap[product.color] || "#b9c3bd";
    const summary = state.reviewSummaries[product.id] || product;
    const rating = reviewSummaryText(summary);
    return `
      <article class="product-card" data-product-id="${escapeHtml(product.id)}" tabindex="0" role="button" aria-label="View ${escapeHtml(product.name)} details">
        <div class="product-image">
          <img src="${escapeHtml(imageFor(product))}" alt="${escapeHtml(product.name)}" loading="lazy">
          <span class="stock-pill ${product.stock <= 5 ? "low" : ""}">${escapeHtml(stockLabel)}</span>
          <span class="rating-badge ${rating ? "" : "hidden"}" data-rating-badge="${escapeHtml(product.id)}">${escapeHtml(rating)}</span>
          <span class="color-dot" style="background:${escapeHtml(color)}" title="${escapeHtml(product.color || "mixed")}"></span>
        </div>
        <div class="product-info">
          <div>
            <h3>${escapeHtml(product.name)}</h3>
            <div class="product-meta">
              ${product.occasion ? `<span class="chip">${escapeHtml(product.occasion)}</span>` : ""}
              ${product.color ? `<span class="chip">${escapeHtml(product.color)}</span>` : ""}
            </div>
          </div>
          <div class="product-bottom">
            <span class="price">${money(product.price)}</span>
            <button class="primary-btn" type="button" data-add="${escapeHtml(product.id)}" ${product.stock < 1 ? "disabled" : ""}>Add</button>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

async function loadReviewSummaries() {
  const products = [...state.products];
  await Promise.all(products.map(async (product) => {
    try {
      const data = await api(`/api/products/${encodeURIComponent(product.id)}/reviews`);
      state.reviewSummaries[product.id] = data;
      updateRatingBadge(product.id);
    } catch {
      state.reviewSummaries[product.id] = { average_rating: null, review_count: 0, sold_count: 0, reviews: [] };
      updateRatingBadge(product.id);
    }
  }));
}

function updateRatingBadge(productId) {
  const badge = [...document.querySelectorAll("[data-rating-badge]")]
    .find((item) => item.dataset.ratingBadge === productId);
  if (!badge) return;
  const text = reviewSummaryText(state.reviewSummaries[productId]);
  badge.textContent = text;
  badge.classList.toggle("hidden", !text);
}

function renderProductReviews(productId, data) {
  const reviewCount = Number(data?.review_count || data?.reviews?.length || 0);
  const average = data?.average_rating ? Number(data.average_rating).toFixed(1) : "No ratings yet";
  const soldCount = Number(data?.sold_count || 0);
  els.productModalReviewSummary.textContent = reviewCount
    ? `${average} average from ${reviewCount} review${reviewCount === 1 ? "" : "s"}`
    : "No reviews yet";
  els.productModalSoldCount.textContent = soldCount
    ? `${soldCount} delivered`
    : "";

  const reviews = data?.reviews || [];
  els.productModalReviewList.innerHTML = reviews.length
    ? reviews.map((review) => `
        <article class="review-item">
          <div>
            <strong>${escapeHtml(Number(review.rating).toFixed(1))}</strong>
            <span>${escapeHtml(formatDate(review.created_at))}</span>
          </div>
          <p>${escapeHtml(review.comment || "No comment")}</p>
        </article>
      `).join("")
    : `<div class="empty-state compact">No one has reviewed this product yet.</div>`;
}

async function loadProductReviews(productId) {
  els.productModalReviewSummary.textContent = "Loading reviews...";
  els.productModalSoldCount.textContent = "";
  els.productModalReviewList.innerHTML = "";
  try {
    const data = await api(`/api/products/${encodeURIComponent(productId)}/reviews`);
    state.reviewSummaries[productId] = data;
    updateRatingBadge(productId);
    renderProductReviews(productId, data);
  } catch (error) {
    els.productModalReviewSummary.textContent = "Could not load reviews";
    els.productModalReviewList.innerHTML = `<div class="empty-state compact">${escapeHtml(error.message)}</div>`;
  }
}

function openProductModal(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;

  const stockText = product.stock > 0 ? `${product.stock} in stock` : "Out of stock";
  const meta = [
    product.category,
    product.occasion,
    product.color,
    stockText,
  ].filter(Boolean);

  els.productModalImage.src = imageFor(product);
  els.productModalImage.alt = product.name;
  els.productModalTitle.textContent = product.name;
  els.productModalMeta.innerHTML = meta.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  els.productModalDescription.textContent = product.description || "No description has been added for this product yet.";
  els.productModalPrice.textContent = money(product.price);
  els.productModalAdd.dataset.add = product.id;
  els.productModalAdd.disabled = product.stock < 1;
  renderProductReviews(productId, state.reviewSummaries[productId] || { reviews: [] });
  els.productModal.classList.remove("hidden");
  loadProductReviews(productId);
  els.productModalClose.focus();
}

function closeProductModal() {
  els.productModal.classList.add("hidden");
  els.productModalAdd.removeAttribute("data-add");
}

function isAdmin() {
  return state.user?.role === "admin";
}

function isStaff() {
  return ["admin", "manager"].includes(state.user?.role);
}

function setView(view) {
  if (view === "admin" && !isAdmin()) {
    toast("Admin access required");
    return;
  }
  if (view === "clientOrders" && !isStaff()) {
    toast("Staff access required");
    return;
  }

  state.view = view;
  els.catalogView.classList.toggle("hidden", view !== "catalog");
  els.ordersView.classList.toggle("hidden", view !== "orders");
  els.adminView.classList.toggle("hidden", view !== "admin");
  els.clientOrdersView.classList.toggle("hidden", view !== "clientOrders");

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });

  if (view === "catalog") {
    els.pageEyebrow.textContent = "Fresh catalog";
    els.pageTitle.textContent = "Order flowers without calling the shop";
  }
  if (view === "orders") {
    els.pageEyebrow.textContent = "Order history";
    els.pageTitle.textContent = "Track your flower deliveries";
    loadOrders();
  }
  if (view === "admin") {
    els.pageEyebrow.textContent = "Operations";
    els.pageTitle.textContent = "Manage product cards and user roles";
    loadAdminProducts();
    loadAdminUsers();
  }
  if (view === "clientOrders") {
    els.pageEyebrow.textContent = "Client orders";
    els.pageTitle.textContent = "Manage incoming deliveries";
    loadAdminOrders();
  }
}

function renderOrderCard(order) {
  const items = order.items || [];
  const canReview = order.status === "delivered";
  return `
    <article class="order-card">
      <div class="order-card-head">
        <div>
          <strong>Order #${escapeHtml(shortId(order.id))}</strong>
          <p class="order-id">${escapeHtml(formatDate(order.created_at))}</p>
        </div>
        <span class="status-badge ${escapeHtml(order.status)}">${escapeHtml(order.status)}</span>
      </div>
      <div class="order-items">
        ${items.length ? items.map((item) => `
          <div class="order-item-row">
            <div>
              <strong>${escapeHtml(item.name)} x ${escapeHtml(item.quantity)}</strong>
              ${canReview ? `<button class="ghost-btn review-order-btn" type="button" data-review-product="${escapeHtml(item.product_id)}" data-review-order="${escapeHtml(order.id)}" data-review-name="${escapeHtml(item.name)}">Review</button>` : ""}
            </div>
            <span>${money(item.subtotal ?? Number(item.unit_price || 0) * Number(item.quantity || 0))}</span>
          </div>
        `).join("") : `<div class="empty-state">No item details stored for this order.</div>`}
      </div>
      <div class="order-card-foot">
        <p class="order-address">${escapeHtml(order.delivery_address || "No delivery address")}</p>
        <strong>${money(order.total)}</strong>
      </div>
    </article>
  `;
}

function openReviewModal(productId, orderId, productName) {
  state.reviewProduct = { id: productId, orderId, name: productName };
  els.reviewModalTitle.textContent = `Review ${productName}`;
  els.reviewRating.value = "5";
  els.reviewComment.value = "";
  els.reviewModal.classList.remove("hidden");
  els.reviewRating.focus();
}

function closeReviewModal() {
  els.reviewModal.classList.add("hidden");
  state.reviewProduct = null;
}

async function submitReview(event) {
  event.preventDefault();
  if (!state.reviewProduct) return;

  const params = new URLSearchParams({ rating: els.reviewRating.value });
  if (state.reviewProduct.orderId) params.set("order_id", state.reviewProduct.orderId);
  const comment = els.reviewComment.value.trim();
  if (comment) params.set("comment", comment);

  try {
    await api(`/api/products/${encodeURIComponent(state.reviewProduct.id)}/reviews?${params}`, {
      method: "POST",
    });
    toast("Review added");
    const productId = state.reviewProduct.id;
    closeReviewModal();
    await loadProductReviews(productId);
    await loadReviewSummaries();
  } catch (error) {
    toast(error.message);
  }
}

async function loadOrders() {
  if (!state.token) {
    els.ordersList.innerHTML = `<div class="empty-state">Sign in to see your order history.</div>`;
    return;
  }

  try {
    const data = await api("/api/orders/");
    state.orders = data.orders || [];
    renderOrders();
  } catch (error) {
    els.ordersList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderOrders() {
  if (!state.orders.length) {
    els.ordersList.innerHTML = `<div class="empty-state">No orders yet.</div>`;
    return;
  }
  els.ordersList.innerHTML = state.orders.map(renderOrderCard).join("");
}

async function loadAdminOrders() {
  if (!isStaff()) {
    els.adminOrdersBody.innerHTML = `<tr><td colspan="5">Staff access required.</td></tr>`;
    els.adminStats.innerHTML = "";
    return;
  }

  try {
    const data = await api("/api/orders/admin");
    state.adminOrders = data.orders || [];
    renderAdminOrders();
  } catch (error) {
    els.adminOrdersBody.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
    els.adminStats.innerHTML = "";
  }
}

async function loadAdminProducts() {
  if (!isAdmin()) {
    els.adminProductGrid.innerHTML = `<div class="empty-state">Admin access required.</div>`;
    return;
  }

  try {
    const data = await api("/api/products/");
    state.adminProducts = (data.products || []).map(normalizeProduct);
    renderAdminProducts();
  } catch (error) {
    els.adminProductGrid.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

async function loadAdminUsers() {
  if (!isAdmin()) {
    els.adminUsersBody.innerHTML = `<tr><td colspan="4">Admin access required.</td></tr>`;
    return;
  }

  try {
    const data = await api("/api/users/");
    state.adminUsers = data.users || [];
    renderAdminUsers();
  } catch (error) {
    els.adminUsersBody.innerHTML = `<tr><td colspan="4">${escapeHtml(error.message)}</td></tr>`;
  }
}

function renderAdminUsers() {
  if (!state.adminUsers.length) {
    els.adminUsersBody.innerHTML = `<tr><td colspan="4">No users found.</td></tr>`;
    return;
  }

  els.adminUsersBody.innerHTML = state.adminUsers.map((user) => `
    <tr>
      <td>
        <strong>${escapeHtml(user.full_name || "Unnamed user")}</strong>
        <div class="muted">${escapeHtml(user.email)}</div>
      </td>
      <td>${escapeHtml(user.phone || "-")}</td>
      <td>${escapeHtml(formatDate(user.created_at))}</td>
      <td>
        <select data-user-role="${escapeHtml(user.id)}">
          ${userRoles.map((role) => `
            <option value="${role}" ${role === user.role ? "selected" : ""}>${role}</option>
          `).join("")}
        </select>
      </td>
    </tr>
  `).join("");
}

async function updateUserRole(userId, role) {
  if (!isAdmin()) {
    toast("Admin access required");
    return;
  }

  try {
    const updated = await api(`/api/users/${encodeURIComponent(userId)}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
    if (state.user?.id === updated.id) {
      state.user = updated;
      localStorage.setItem("flower_user", JSON.stringify(state.user));
      syncAuthUi();
    }
    toast("User role updated");
    await loadAdminUsers();
  } catch (error) {
    toast(error.message);
    await loadAdminUsers();
  }
}

function renderAdminProducts() {
  if (!state.adminProducts.length) {
    els.adminProductGrid.innerHTML = `<div class="empty-state">No active products.</div>`;
    return;
  }

  els.adminProductGrid.innerHTML = state.adminProducts.map((product) => `
    <article class="admin-product-card">
      <img src="${imageFor(product)}" alt="${escapeHtml(product.name)}">
      <div class="admin-product-body">
        <div>
          <h3>${escapeHtml(product.name)}</h3>
          <div class="product-meta">
            ${product.occasion ? `<span class="chip">${escapeHtml(product.occasion)}</span>` : ""}
            ${product.color ? `<span class="chip">${escapeHtml(product.color)}</span>` : ""}
            <span class="chip">${escapeHtml(product.stock)} in stock</span>
          </div>
        </div>
        <div class="admin-product-actions">
          <strong>${money(product.price)}</strong>
          <div class="button-row">
            <button class="ghost-btn compact-btn" type="button" data-edit-product="${escapeHtml(product.id)}">Edit</button>
            <button class="danger-btn" type="button" data-delete-product="${escapeHtml(product.id)}">Delete</button>
          </div>
        </div>
      </div>
    </article>
  `).join("");
}

async function startEditProduct(productId) {
  const product = state.adminProducts.find((item) => item.id === productId) || await api(`/api/products/${encodeURIComponent(productId)}`);
  els.productEditingId.value = product.id;
  els.productName.value = product.name || "";
  els.productPrice.value = product.price || "";
  els.productStock.value = product.stock ?? 0;
  els.productCategory.value = "";
  els.productOccasion.value = product.occasion || "any";
  els.productColor.value = product.color || "pink";
  els.productImage.value = product.image_url || "";
  els.productDescription.value = product.description || "";
  els.productSubmit.textContent = "Save changes";
  els.productCancelEdit.classList.remove("hidden");
  els.productName.focus();
}

function resetProductForm() {
  els.productForm.reset();
  els.productEditingId.value = "";
  els.productStock.value = "10";
  els.productSubmit.textContent = "Add product";
  els.productCancelEdit.classList.add("hidden");
}

async function createProduct(event) {
  event.preventDefault();
  if (!isAdmin()) {
    toast("Admin access required");
    return;
  }

  const editingId = els.productEditingId.value;
  const payload = {
    name: els.productName.value.trim(),
    price: Number(els.productPrice.value),
    stock: Number(els.productStock.value),
    category: els.productCategory.value || undefined,
    occasion: els.productOccasion.value,
    color: els.productColor.value,
    image_url: els.productImage.value.trim() || null,
    description: els.productDescription.value.trim() || null,
  };

  try {
    await api(editingId ? `/api/products/${encodeURIComponent(editingId)}` : "/api/products/", {
      method: editingId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    resetProductForm();
    toast(editingId ? "Product updated" : "Product added");
    await loadProducts();
    await loadAdminProducts();
  } catch (error) {
    toast(error.message);
  }
}

async function deleteProduct(productId) {
  if (!isAdmin()) {
    toast("Admin access required");
    return;
  }
  if (!window.confirm("Delete this product card from the catalog?")) return;

  try {
    await api(`/api/products/${encodeURIComponent(productId)}`, { method: "DELETE" });
    state.localCart = state.localCart.filter((item) => item.product_id !== productId);
    saveLocalCart();
    toast("Product deleted");
    await loadProducts();
    await loadAdminProducts();
    await loadCart();
  } catch (error) {
    toast(error.message);
  }
}

function renderAdminOrders() {
  const orders = state.adminOrders;
  const revenue = orders.reduce((sum, order) => sum + Number(order.total || 0), 0);
  const activeCount = orders.filter((order) => !["delivered", "cancelled"].includes(order.status)).length;
  const deliveredCount = orders.filter((order) => order.status === "delivered").length;

  els.adminStats.innerHTML = `
    <div class="stat-card"><span>Total orders</span><strong>${orders.length}</strong></div>
    <div class="stat-card"><span>Active</span><strong>${activeCount}</strong></div>
    <div class="stat-card"><span>Delivered</span><strong>${deliveredCount}</strong></div>
    <div class="stat-card"><span>Revenue</span><strong>${money(revenue)}</strong></div>
  `;

  if (!orders.length) {
    els.adminOrdersBody.innerHTML = `<tr><td colspan="5">No orders yet.</td></tr>`;
    return;
  }

  els.adminOrdersBody.innerHTML = orders.map((order) => {
    const customer = order.customer || {};
    const items = (order.items || []).map((item) => `${escapeHtml(item.name)} x ${escapeHtml(item.quantity)}`).join("<br>");
    return `
      <tr>
        <td>
          <strong>#${escapeHtml(shortId(order.id))}</strong>
          <div class="muted">${escapeHtml(formatDate(order.created_at))}</div>
          <div class="muted">${escapeHtml(order.delivery_address || "")}</div>
        </td>
        <td>
          <strong>${escapeHtml(customer.full_name || "Unknown")}</strong>
          <div class="muted">${escapeHtml(customer.email || "")}</div>
          <div class="muted">${escapeHtml(customer.phone || "")}</div>
        </td>
        <td>${items || "<span class=\"muted\">No items</span>"}</td>
        <td><strong>${money(order.total)}</strong></td>
        <td>
          <select data-status-order="${escapeHtml(order.id)}">
            ${orderStatuses.map((status) => `
              <option value="${status}" ${status === order.status ? "selected" : ""}>${status}</option>
            `).join("")}
          </select>
        </td>
      </tr>
    `;
  }).join("");
}

async function updateOrderStatus(orderId, status) {
  try {
    await api(`/api/orders/${encodeURIComponent(orderId)}/status?status=${encodeURIComponent(status)}`, { method: "PATCH" });
    toast("Order status updated");
    await loadAdminOrders();
    if (state.view === "orders") await loadOrders();
  } catch (error) {
    toast(error.message);
    await loadAdminOrders();
  }
}

function currentCartItems() {
  return state.token ? state.remoteCart.items : state.localCart;
}

function saveLocalCart() {
  localStorage.setItem("flower_local_cart", JSON.stringify(state.localCart));
}

function cartTotal(items = currentCartItems()) {
  return items.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0);
}

function cartCount(items = currentCartItems()) {
  return items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
}

async function loadCart() {
  if (!state.token) {
    renderCart();
    return;
  }

  try {
    state.remoteCart = await api("/api/cart/");
  } catch (error) {
    toast(error.message);
  }
  renderCart();
}

function renderCart() {
  const items = currentCartItems();
  els.cartCount.textContent = cartCount(items);
  els.cartTotal.textContent = money(state.token ? state.remoteCart.total : cartTotal(items));

  if (!items.length) {
    els.cartItems.innerHTML = `<div class="empty-state">Your cart is empty.</div>`;
    return;
  }

  els.cartItems.innerHTML = items.map((item) => `
    <article class="cart-item">
      <img src="${imageFor(item)}" alt="${item.name || "Product"}">
      <div>
        <h3>${item.name || "Product"}</h3>
        <p>${money(item.price)} each</p>
      </div>
      <div class="qty-controls" aria-label="Quantity controls">
        <button type="button" data-dec="${item.product_id}">-</button>
        <strong>${item.quantity}</strong>
        <button type="button" data-inc="${item.product_id}">+</button>
      </div>
    </article>
  `).join("");
}

async function addProduct(productId, quantity = 1) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;

  if (!state.token) {
    const existing = state.localCart.find((item) => item.product_id === productId);
    if (existing) {
      existing.quantity += quantity;
    } else {
      state.localCart.push({
        product_id: product.id,
        name: product.name,
        price: product.price,
        quantity,
        image_url: product.image_url,
      });
    }
    saveLocalCart();
    renderCart();
    toast("Added to local cart");
    return;
  }

  try {
    await api(`/api/cart/add?product_id=${encodeURIComponent(productId)}&quantity=${quantity}`, { method: "POST" });
    await loadCart();
    toast("Added to cart");
  } catch (error) {
    toast(error.message);
  }
}

async function removeRemote(productId) {
  await api(`/api/cart/remove/${encodeURIComponent(productId)}`, { method: "DELETE" });
  await loadCart();
}

async function changeQuantity(productId, delta) {
  if (!state.token) {
    const item = state.localCart.find((entry) => entry.product_id === productId);
    if (!item) return;
    item.quantity += delta;
    state.localCart = state.localCart.filter((entry) => entry.quantity > 0);
    saveLocalCart();
    renderCart();
    return;
  }

  if (delta > 0) {
    await addProduct(productId, 1);
    return;
  }

  const item = state.remoteCart.items.find((entry) => entry.product_id === productId);
  if (!item) return;
  if (item.quantity <= 1) {
    await removeRemote(productId);
  } else {
    await removeRemote(productId);
    await api(`/api/cart/add?product_id=${encodeURIComponent(productId)}&quantity=${item.quantity - 1}`, { method: "POST" });
    await loadCart();
  }
}

async function mergeLocalCart() {
  if (!state.token || !state.localCart.length) return;
  const items = [...state.localCart];
  state.localCart = [];
  saveLocalCart();

  for (const item of items) {
    await api(`/api/cart/add?product_id=${encodeURIComponent(item.product_id)}&quantity=${item.quantity}`, { method: "POST" });
  }
  await loadCart();
}

async function placeOrder(event) {
  event.preventDefault();

  if (!currentCartItems().length) {
    toast("Add products before checkout");
    return;
  }
  if (!state.token) {
    openAuth();
    toast("Sign in before placing an order");
    return;
  }

  try {
    const address = els.address.value.trim();
    const order = await api(`/api/orders/?delivery_address=${encodeURIComponent(address)}`, { method: "POST" });
    els.address.value = "";
    await loadCart();
    await loadOrders();
    toast(`Order ${order.order_id.slice(0, 8)} created`);
    subscribeOrder(order.order_id);
    setView("orders");
  } catch (error) {
    toast(error.message);
  }
}

function subscribeOrder(orderId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws/orders/${orderId}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "status_update") toast(`Order status: ${data.status}`);
  };
}

function syncAuthUi() {
  if (state.user) {
    els.authOpen.title = state.user.full_name || state.user.email;
    els.authOpen.setAttribute("aria-label", state.user.full_name || state.user.email);
    els.authOpen.classList.add("signed-in");
    els.authOpen.classList.add("hidden");
    els.logout.classList.remove("hidden");
    els.adminNav.classList.toggle("hidden", !isAdmin());
    els.clientOrdersNav.classList.toggle("hidden", !isStaff());
  } else {
    els.authOpen.title = "Sign in";
    els.authOpen.setAttribute("aria-label", "Sign in");
    els.authOpen.classList.remove("signed-in");
    els.authOpen.classList.remove("hidden");
    els.logout.classList.add("hidden");
    els.adminNav.classList.add("hidden");
    els.clientOrdersNav.classList.add("hidden");
  }
}

function openAuth(mode = "login") {
  state.authMode = mode;
  renderAuthMode();
  els.authModal.classList.remove("hidden");
  els.email.focus();
}

function closeAuth() {
  els.authModal.classList.add("hidden");
}

function renderAuthMode() {
  const isRegister = state.authMode === "register";
  els.modalTitle.textContent = isRegister ? "Create account" : "Sign in";
  els.authSubmit.textContent = isRegister ? "Create account" : "Sign in";
  els.authToggle.textContent = isRegister ? "I already have an account" : "Create account";
  document.querySelectorAll(".register-only").forEach((el) => el.classList.toggle("hidden", !isRegister));
  els.name.required = isRegister;
  els.password.autocomplete = isRegister ? "new-password" : "current-password";
}

async function submitAuth(event) {
  event.preventDefault();
  const payload = {
    email: els.email.value.trim(),
    password: els.password.value,
  };
  if (state.authMode === "register") {
    payload.full_name = els.name.value.trim();
    payload.phone = els.phone.value.trim() || null;
  }

  try {
    const data = await api(`/api/auth/${state.authMode}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem("flower_token", state.token);
    localStorage.setItem("flower_user", JSON.stringify(state.user));
    closeAuth();
    syncAuthUi();
    await mergeLocalCart();
    await loadCart();
    await loadOrders();
    if (isStaff()) await loadAdminOrders();
    if (isAdmin()) {
      await loadAdminProducts();
      await loadAdminUsers();
    }
    toast("Signed in");
  } catch (error) {
    toast(error.message);
  }
}

function logout() {
  state.token = "";
  state.user = null;
  state.remoteCart = { items: [], total: 0 };
  localStorage.removeItem("flower_token");
  localStorage.removeItem("flower_user");
  syncAuthUi();
  renderCart();
  state.orders = [];
  state.adminOrders = [];
  state.adminProducts = [];
  state.adminUsers = [];
  if (state.view === "admin") setView("catalog");
  if (state.view === "clientOrders") setView("catalog");
  if (state.view === "orders") renderOrders();
  toast("Logged out");
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  document.querySelectorAll(".category-item").forEach((button) => {
    button.addEventListener("click", () => {
      setView("catalog");
      document.querySelectorAll(".category-item").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.category = button.dataset.category;
      state.query = "";
      els.search.value = "";
      loadProducts();
    });
  });

  els.categoryToggle.addEventListener("click", () => {
    const isCollapsed = els.categoryNav.classList.toggle("collapsed");
    els.categoryToggle.setAttribute("aria-expanded", String(!isCollapsed));
  });

  els.search.addEventListener("input", () => {
    state.query = els.search.value;
    window.clearTimeout(bindEvents.searchTimer);
    bindEvents.searchTimer = window.setTimeout(loadProducts, 280);
  });
  els.occasion.addEventListener("change", () => {
    state.occasion = els.occasion.value;
    loadProducts();
  });
  els.color.addEventListener("change", () => {
    state.color = els.color.value;
    loadProducts();
  });

  els.grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-add]");
    if (button) {
      addProduct(button.dataset.add);
      return;
    }

    const card = event.target.closest("[data-product-id]");
    if (card) openProductModal(card.dataset.productId);
  });

  els.grid.addEventListener("keydown", (event) => {
    if (!["Enter", " "].includes(event.key)) return;
    const card = event.target.closest("[data-product-id]");
    if (!card || event.target.closest("button")) return;
    event.preventDefault();
    openProductModal(card.dataset.productId);
  });

  els.cartItems.addEventListener("click", (event) => {
    const inc = event.target.closest("[data-inc]");
    const dec = event.target.closest("[data-dec]");
    if (inc) changeQuantity(inc.dataset.inc, 1);
    if (dec) changeQuantity(dec.dataset.dec, -1);
  });

  document.querySelector("#cartToggle").addEventListener("click", () => {
    els.appShell.classList.remove("cart-closed");
    els.cartPanel.classList.remove("cart-closed");
    els.cartPanel.classList.add("open");
  });
  document.querySelector("#cartClose").addEventListener("click", () => {
    els.cartPanel.classList.remove("open");
    els.cartPanel.classList.add("cart-closed");
    els.appShell.classList.add("cart-closed");
  });
  els.checkoutForm.addEventListener("submit", placeOrder);
  els.refreshOrders.addEventListener("click", loadOrders);
  els.ordersList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-review-product]");
    if (!button) return;
    openReviewModal(
      button.dataset.reviewProduct,
      button.dataset.reviewOrder,
      button.dataset.reviewName || "Product",
    );
  });
  els.refreshAdmin.addEventListener("click", () => {
    loadAdminProducts();
    loadAdminUsers();
  });
  els.refreshClientOrders.addEventListener("click", loadAdminOrders);
  els.productForm.addEventListener("submit", createProduct);
  els.productCancelEdit.addEventListener("click", resetProductForm);
  els.adminProductGrid.addEventListener("click", (event) => {
    const deleteButton = event.target.closest("[data-delete-product]");
    const editButton = event.target.closest("[data-edit-product]");
    if (deleteButton) deleteProduct(deleteButton.dataset.deleteProduct);
    if (editButton) startEditProduct(editButton.dataset.editProduct);
  });
  els.adminOrdersBody.addEventListener("change", (event) => {
    const select = event.target.closest("[data-status-order]");
    if (select) updateOrderStatus(select.dataset.statusOrder, select.value);
  });
  els.adminUsersBody.addEventListener("change", (event) => {
    const select = event.target.closest("[data-user-role]");
    if (select) updateUserRole(select.dataset.userRole, select.value);
  });
  els.authOpen.addEventListener("click", () => openAuth());
  els.authClose.addEventListener("click", closeAuth);
  els.authModal.addEventListener("click", (event) => {
    if (event.target === els.authModal) closeAuth();
  });
  els.productModalClose.addEventListener("click", closeProductModal);
  els.productModal.addEventListener("click", (event) => {
    if (event.target === els.productModal) closeProductModal();
  });
  els.productModalAdd.addEventListener("click", () => {
    if (els.productModalAdd.dataset.add) addProduct(els.productModalAdd.dataset.add);
  });
  els.reviewModalClose.addEventListener("click", closeReviewModal);
  els.reviewModal.addEventListener("click", (event) => {
    if (event.target === els.reviewModal) closeReviewModal();
  });
  els.reviewForm.addEventListener("submit", submitReview);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!els.productModal.classList.contains("hidden")) closeProductModal();
    if (!els.reviewModal.classList.contains("hidden")) closeReviewModal();
    if (!els.authModal.classList.contains("hidden")) closeAuth();
  });
  els.authToggle.addEventListener("click", () => {
    state.authMode = state.authMode === "login" ? "register" : "login";
    renderAuthMode();
  });
  els.authForm.addEventListener("submit", submitAuth);
  els.logout.addEventListener("click", logout);
}

bindEvents();
syncAuthUi();
setView("catalog");
loadProducts();
loadCart();
loadOrders();
if (isAdmin()) {
  loadAdminProducts();
  loadAdminUsers();
}
if (isStaff()) {
  loadAdminOrders();
}
