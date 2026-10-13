from django.http import HttpResponse, JsonResponse


def health(request):
    """GET /api/health/ — the grader polls this until your app is ready."""
    return JsonResponse({"status": "ok"})


def portal_view(request):
    """GET / — Part E: DealerDesk Dealer Web Portal."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VIKMO DealerDesk — Dealer Ordering & AI Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #131b2e;
      --card-border: #1f2c47;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    header { background: #0f172a; border-bottom: 1px solid var(--card-border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
    .logo { font-size: 1.35rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 0.5rem; }
    .badge-live { background: rgba(16, 185, 129, 0.2); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; border: 1px solid var(--accent); }
    nav { display: flex; gap: 0.5rem; }
    nav button { background: transparent; border: none; color: var(--text-muted); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.9rem; transition: all 0.15s ease; }
    nav button:hover, nav button.active { background: #1e293b; color: #fff; }
    nav button.active { color: var(--primary); }
    main { max-width: 1300px; margin: 1.5rem auto; padding: 0 1rem; }
    .section { display: none; }
    .section.active { display: block; }
    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1.25rem; }
    .flex-between { display: flex; justify-content: space-between; align-items: center; }
    .filters { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
    input, select { background: #0f172a; border: 1px solid var(--card-border); color: #fff; padding: 0.6rem 0.9rem; border-radius: 6px; font-size: 0.9rem; outline: none; }
    input:focus, select:focus { border-color: var(--primary); }
    .btn { background: var(--primary); color: #fff; border: none; padding: 0.6rem 1.1rem; border-radius: 6px; font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
    .btn:hover { background: var(--primary-hover); }
    .btn-success { background: #059669; }
    .btn-success:hover { background: #047857; }
    .btn-danger { background: #dc2626; }
    .btn-danger:hover { background: #b91c1c; }
    .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text-muted); }
    .btn-outline:hover { background: #1e293b; color: #fff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 1.2rem; }
    .product-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; justify-content: space-between; }
    .product-sku { font-size: 0.8rem; font-weight: 600; color: #60a5fa; margin-bottom: 0.25rem; }
    .product-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem; line-height: 1.3; }
    .product-meta { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.8rem; }
    .product-price { font-size: 1.15rem; font-weight: 700; color: #10b981; }
    .stock-badge { padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .in-stock { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .out-stock { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.88rem; }
    th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-weight: 500; }
    .cart-drawer { position: fixed; right: 1.5rem; bottom: 1.5rem; background: #0f172a; border: 1px solid #2563eb; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border-radius: 12px; padding: 1.25rem; width: 340px; z-index: 99; }
    .chat-container { display: flex; flex-direction: column; height: 550px; background: #0f172a; border: 1px solid var(--card-border); border-radius: 10px; overflow: hidden; }
    .chat-messages { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .msg { max-width: 80%; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.9rem; line-height: 1.4; }
    .msg-user { align-self: flex-end; background: #1e3a8a; color: #fff; }
    .msg-bot { align-self: flex-start; background: var(--card-bg); border: 1px solid var(--card-border); color: #f3f4f6; }
    .msg-tool { font-size: 0.75rem; color: #93c5fd; background: rgba(59, 130, 246, 0.1); padding: 0.3rem 0.6rem; border-radius: 4px; margin-top: 0.3rem; display: inline-block; }
    .chat-input { display: flex; gap: 0.5rem; padding: 0.75rem; background: #1e293b; border-top: 1px solid var(--card-border); }
    .alert { padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.88rem; }
    .alert-error { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); color: #fca5a5; }
    .alert-success { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--accent); color: #6ee7b7; }
  </style>
</head>
<body>

  <header>
    <div class="logo">
      <span>⚡ VIKMO DealerDesk</span>
      <span class="badge-live">Online</span>
    </div>
    <nav>
      <button class="active" onclick="showTab('catalogue')">📦 Parts Catalogue</button>
      <button onclick="showTab('orders')">📋 Orders & GST</button>
      <button onclick="showTab('forecasting')">📊 Demand & Reorders</button>
      <button onclick="showTab('assistant')">🤖 Dealer Assistant</button>
      <button onclick="showTab('sync')">🔄 Supplier Sync</button>
    </nav>
  </header>

  <main>
    <div id="status-alert"></div>

    <!-- 1. CATALOGUE -->
    <div id="tab-catalogue" class="section active">
      <div class="card flex-between">
        <div>
          <h2>Product Catalogue</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted);">600 items with live stock and current wholesale pricing</p>
        </div>
        <div style="display:flex; gap: 0.5rem;">
          <select id="dealer-select" title="Active Dealer"></select>
        </div>
      </div>

      <div class="filters">
        <input type="text" id="search-input" placeholder="Search SKU, name, or brand..." style="flex: 1;" onkeyup="if(event.key==='Enter') loadProducts()">
        <input type="text" id="vehicle-input" placeholder="Vehicle model (e.g. Pulsar 150)..." style="flex: 1;" onkeyup="if(event.key==='Enter') loadProducts()">
        <button class="btn" onclick="loadProducts()">Search</button>
      </div>

      <div id="products-grid" class="grid"></div>
    </div>

    <!-- 2. ORDERS -->
    <div id="tab-orders" class="section">
      <div class="card flex-between">
        <div>
          <h2>Order Desk</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Draft creation, 18% GST calculation, status flow & stock locking</p>
        </div>
        <button class="btn btn-outline" onclick="loadOrders()">↻ Refresh Orders</button>
      </div>
      <div id="orders-list"></div>
    </div>

    <!-- 3. FORECASTING & REORDER -->
    <div id="tab-forecasting" class="section">
      <div class="card flex-between">
        <div>
          <h2>4-Week Demand Forecast & Safety Stock Reorders</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Formula: Reorder Point = Lead Demand + ceil(1.65 × σ × √L)</p>
        </div>
        <button class="btn btn-outline" onclick="loadReorders()">↻ Refresh Suggestions</button>
      </div>
      <div class="card" style="overflow-x: auto;">
        <table id="reorder-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Current Stock</th>
              <th>Lead Time</th>
              <th>Lead Demand</th>
              <th>Safety Stock</th>
              <th>Reorder Point</th>
              <th>Suggested Qty</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <!-- 4. ASSISTANT -->
    <div id="tab-assistant" class="section">
      <div class="card">
        <h2>AI Dealer Assistant (Tool Calling)</h2>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Grounds prices and stock dynamically with search_parts, check_stock & draft orders.</p>
      </div>
      <div class="chat-container">
        <div class="chat-messages" id="chat-messages">
          <div class="msg msg-bot">Hello! I am your DealerDesk Assistant. Ask me about parts compatibility, live stock, or placing a draft order!</div>
        </div>
        <div class="chat-input">
          <input type="text" id="chat-input" placeholder="e.g. Do you have brake pads for a Bajaj Pulsar 150?" style="flex:1;" onkeyup="if(event.key==='Enter') sendChat()">
          <button class="btn" onclick="sendChat()">Send</button>
        </div>
      </div>
    </div>

    <!-- 5. SUPPLIER SYNC -->
    <div id="tab-sync" class="section">
      <div class="card">
        <h2>Supplier Catalogue Sync</h2>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Pulls external feed, handles rate limits, deduplicates latest records, and preserves local stock.</p>
        <div style="margin-top: 1rem;">
          <button class="btn btn-success" onclick="triggerSync()">Trigger Supplier Sync Now</button>
        </div>
      </div>
      <div id="sync-result" class="card" style="display:none;"></div>
    </div>

  </main>

  <!-- CART DRAWER -->
  <div id="cart-drawer" class="cart-drawer" style="display:none;">
    <div class="flex-between" style="margin-bottom: 0.75rem;">
      <h3 style="font-size: 1rem;">🛒 Cart (<span id="cart-count">0</span> items)</h3>
      <button class="btn-outline" style="border:none; cursor:pointer;" onclick="clearCart()">Clear</button>
    </div>
    <div id="cart-items" style="max-height: 180px; overflow-y:auto; margin-bottom: 0.75rem; font-size: 0.85rem;"></div>
    <div style="border-top: 1px solid var(--card-border); padding-top: 0.5rem; font-size: 0.85rem;">
      <div class="flex-between"><span>Subtotal:</span><span id="cart-subtotal">₹0.00</span></div>
      <div class="flex-between" style="color:var(--text-muted);"><span>GST (18%):</span><span id="cart-tax">₹0.00</span></div>
      <div class="flex-between" style="font-weight:700; margin-top:0.25rem;"><span>Estimated Total:</span><span id="cart-total" style="color:#10b981;">₹0.00</span></div>
    </div>
    <button class="btn" style="width: 100%; margin-top: 0.75rem;" onclick="submitOrder()">Place Draft Order</button>
  </div>

  <script>
    let cart = {};
    let dealers = [];

    function showTab(tab) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + tab).classList.add('active');
      event.target.classList.add('active');
      if (tab === 'orders') loadOrders();
      if (tab === 'forecasting') loadReorders();
    }

    function showAlert(msg, isError = false) {
      const el = document.getElementById('status-alert');
      el.innerHTML = `<div class="alert ${isError ? 'alert-error' : 'alert-success'}">${msg}</div>`;
      setTimeout(() => { el.innerHTML = ''; }, 6000);
    }

    async function init() {
      // Load dealers
      const dRes = await fetch('/api/dealers/');
      const dData = await dRes.json();
      dealers = dData.results || [];
      const dSelect = document.getElementById('dealer-select');
      dealers.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        opt.innerText = `${d.dealer_code} - ${d.name}`;
        dSelect.appendChild(opt);
      });
      loadProducts();
    }

    async function loadProducts() {
      const search = document.getElementById('search-input').value;
      const vehicle = document.getElementById('vehicle-input').value;
      let url = '/api/products/?page_size=24';
      if (search) url += '&search=' + encodeURIComponent(search);
      if (vehicle) url += '&vehicle=' + encodeURIComponent(vehicle);
      const res = await fetch(url);
      const data = await res.json();
      const grid = document.getElementById('products-grid');
      grid.innerHTML = '';
      (data.results || []).forEach(p => {
        const inStock = p.stock > 0;
        grid.innerHTML += `
          <div class="product-card">
            <div>
              <div class="product-sku">${p.sku} • ${p.brand}</div>
              <div class="product-title">${p.name}</div>
              <div class="product-meta">Fit: ${p.vehicle_fitment}</div>
            </div>
            <div>
              <div class="flex-between" style="margin-bottom: 0.75rem;">
                <span class="product-price">₹${p.price}</span>
                <span class="stock-badge ${inStock ? 'in-stock' : 'out-stock'}">${p.stock} in stock</span>
              </div>
              <button class="btn btn-outline" style="width: 100%;" onclick="addToCart('${p.sku}', '${p.name.replace(/'/g, "")}', ${p.price})">+ Add to Cart</button>
            </div>
          </div>
        `;
      });
    }

    function addToCart(sku, name, price) {
      if (!cart[sku]) cart[sku] = { sku, name, price, qty: 1 };
      else cart[sku].qty += 1;
      updateCartUI();
    }

    function updateCartUI() {
      const itemsDiv = document.getElementById('cart-items');
      const drawer = document.getElementById('cart-drawer');
      const keys = Object.keys(cart);
      if (keys.length === 0) {
        drawer.style.display = 'none';
        return;
      }
      drawer.style.display = 'block';
      itemsDiv.innerHTML = '';
      let subtotal = 0;
      let count = 0;
      keys.forEach(k => {
        const item = cart[k];
        const line = item.price * item.qty;
        subtotal += line;
        count += item.qty;
        itemsDiv.innerHTML += `
          <div class="flex-between" style="margin-bottom:0.4rem;">
            <span>${item.sku} (x${item.qty})</span>
            <span>₹${line.toFixed(2)}</span>
          </div>
        `;
      });
      const tax = subtotal * 0.18;
      const total = subtotal + tax;
      document.getElementById('cart-count').innerText = count;
      document.getElementById('cart-subtotal').innerText = '₹' + subtotal.toFixed(2);
      document.getElementById('cart-tax').innerText = '₹' + tax.toFixed(2);
      document.getElementById('cart-total').innerText = '₹' + total.toFixed(2);
    }

    function clearCart() {
      cart = {};
      updateCartUI();
    }

    async function submitOrder() {
      const dealerId = document.getElementById('dealer-select').value;
      const items = Object.values(cart).map(i => ({ sku: i.sku, quantity: i.qty }));
      const res = await fetch('/api/orders/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dealer_id: parseInt(dealerId), items })
      });
      const data = await res.json();
      if (res.ok) {
        showAlert(`Order ${data.order_number} created as DRAFT! Subtotal: ₹${data.subtotal}, Tax: ₹${data.tax_total}, Grand Total: ₹${data.grand_total}`);
        clearCart();
        showTab('orders');
      } else {
        showAlert(data.error?.message || 'Failed to place order', true);
      }
    }

    async function loadOrders() {
      const res = await fetch('/api/orders/?page_size=20');
      const data = await res.json();
      const list = document.getElementById('orders-list');
      list.innerHTML = '';
      (data.results || []).forEach(o => {
        let badgeColor = '#94a3b8';
        if (o.status === 'CONFIRMED') badgeColor = '#3b82f6';
        if (o.status === 'DISPATCHED') badgeColor = '#f59e0b';
        if (o.status === 'DELIVERED') badgeColor = '#10b981';
        if (o.status === 'CANCELLED') badgeColor = '#ef4444';

        let actions = '';
        if (o.status === 'DRAFT') {
          actions = `
            <button class="btn btn-success" onclick="orderAction('${o.order_number}', 'confirm')">Confirm (Locks Stock)</button>
            <button class="btn btn-danger" onclick="orderAction('${o.order_number}', 'cancel')">Cancel</button>
          `;
        } else if (o.status === 'CONFIRMED') {
          actions = `
            <button class="btn" onclick="orderAction('${o.order_number}', 'dispatch')">Dispatch</button>
            <button class="btn btn-danger" onclick="orderAction('${o.order_number}', 'cancel')">Cancel & Restore Stock</button>
          `;
        } else if (o.status === 'DISPATCHED') {
          actions = `<button class="btn btn-success" onclick="orderAction('${o.order_number}', 'deliver')">Mark Delivered</button>`;
        }

        let itemsRows = o.items.map(i => `
          <tr>
            <td>${i.sku}</td>
            <td>${i.name}</td>
            <td>${i.quantity}</td>
            <td>₹${i.unit_price}</td>
            <td>₹${i.line_tax}</td>
            <td>₹${i.line_total}</td>
          </tr>
        `).join('');

        list.innerHTML += `
          <div class="card">
            <div class="flex-between" style="margin-bottom: 0.75rem;">
              <div>
                <span style="font-weight:700; font-size:1.1rem;">${o.order_number}</span>
                <span class="stock-badge" style="background:${badgeColor}22; color:${badgeColor}; margin-left:0.5rem;">${o.status}</span>
              </div>
              <div style="font-size:0.85rem; color:var(--text-muted);">${new Date(o.created_at).toLocaleString()}</div>
            </div>
            <table>
              <thead>
                <tr><th>SKU</th><th>Name</th><th>Qty</th><th>Unit Price</th><th>GST (18%)</th><th>Line Total</th></tr>
              </thead>
              <tbody>${itemsRows}</tbody>
            </table>
            <div class="flex-between" style="margin-top: 1rem; border-top: 1px solid var(--card-border); padding-top: 0.75rem;">
              <div>
                <span>Subtotal: <b>₹${o.subtotal}</b></span> • 
                <span>Tax: <b>₹${o.tax_total}</b></span> • 
                <span style="color:#10b981;">Grand Total: <b>₹${o.grand_total}</b></span>
              </div>
              <div style="display:flex; gap:0.5rem;">${actions}</div>
            </div>
          </div>
        `;
      });
    }

    async function orderAction(orderNumber, action) {
      const res = await fetch(`/api/orders/${orderNumber}/${action}/`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showAlert(`Order ${orderNumber} transitioned to ${data.status}!`);
        loadOrders();
      } else {
        showAlert(data.error?.message || 'Action failed', true);
      }
    }

    async function loadReorders() {
      const res = await fetch('/api/reorder-suggestions/');
      const data = await res.json();
      const tbody = document.querySelector('#reorder-table tbody');
      tbody.innerHTML = '';
      (data.results || []).forEach(r => {
        const reorderNeeded = r.reorder_qty > 0;
        tbody.innerHTML += `
          <tr>
            <td><b>${r.sku}</b></td>
            <td>${r.current_stock}</td>
            <td>${r.lead_time_weeks} wks</td>
            <td>${r.lead_time_demand}</td>
            <td>${r.safety_stock}</td>
            <td>${r.reorder_point}</td>
            <td><span class="stock-badge ${reorderNeeded ? 'out-stock' : 'in-stock'}">${r.reorder_qty} units</span></td>
          </tr>
        `;
      });
    }

    async function sendChat() {
      const input = document.getElementById('chat-input');
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';
      const box = document.getElementById('chat-messages');
      box.innerHTML += `<div class="msg msg-user">${msg}</div>`;
      box.scrollTop = box.scrollHeight;

      const dealerId = document.getElementById('dealer-select').value || 1;
      const res = await fetch('/api/assistant/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: 'web-session', dealer_id: parseInt(dealerId), message: msg })
      });
      const data = await res.json();
      let toolsHtml = '';
      if (data.tool_calls && data.tool_calls.length) {
        toolsHtml = data.tool_calls.map(t => `<div class="msg-tool">🛠️ Tool called: ${t.name}(${JSON.stringify(t.arguments)})</div>`).join('');
      }
      box.innerHTML += `
        <div class="msg msg-bot">
          ${data.reply}
          ${toolsHtml}
        </div>
      `;
      box.scrollTop = box.scrollHeight;
    }

    async function triggerSync() {
      const div = document.getElementById('sync-result');
      div.style.display = 'block';
      div.innerHTML = 'Syncing catalogue from supplier API...';
      const res = await fetch('/api/sync/supplier/', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        div.innerHTML = `
          <h3 style="color:#10b981; margin-bottom:0.5rem;">Sync Completed Successfully!</h3>
          <p>Created: <b>${data.created}</b> • Updated: <b>${data.updated}</b> • Unchanged: <b>${data.unchanged}</b> • Rejected: <b>${data.rejected.length}</b></p>
          <p style="font-size:0.85rem; color:var(--text-muted); margin-top:0.3rem;">Pages fetched: ${data.pages_fetched} • Requests made: ${data.requests_made}</p>
        `;
      } else {
        div.innerHTML = `<h3 style="color:#ef4444;">Sync Failed (${res.status}): ${data.error?.message}</h3>`;
      }
    }

    window.onload = init;
  </script>
</body>
</html>
"""
    return HttpResponse(html_content, content_type="text/html")
