class WealthWatchApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.token = localStorage.getItem('wealthwatch_token');
        this.currentUser = null;
        this.charts = {};
        this.categoriesCache = [];
        this.subCategoriesCache = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        if (this.token) {
            this.enterApp();
        } else {
            this.showAuth();
        }
    }

    // ── Helpers ──────────────────────────────────────────────
    $(id) { return document.getElementById(id); }
    money(n) { return '$' + Number(n||0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }
    pct(n) { return Number(n||0).toFixed(1) + '%'; }
    fmtDate(d) { return d ? new Date(d).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) : ''; }
    monthNames() { return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; }
    typeLabel(t) {
        const m = {checking:'Checking',savings:'Savings',credit_card:'Credit Card',investment:'Investment',loan:'Loan',mortgage:'Mortgage',real_estate:'Real Estate',other:'Other'};
        return m[t]||t;
    }

    // ── API ─────────────────────────────────────────────────
    async api(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const config = { headers: {}, ...options };
        if (!(config.body instanceof FormData)) {
            config.headers['Content-Type'] = 'application/json';
        }
        if (this.token) config.headers.Authorization = `Bearer ${this.token}`;
        try {
            const res = await fetch(url, config);
            if (res.status === 204) return null;
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Request failed');
            return data;
        } catch (e) {
            console.error('API Error:', e);
            this.notify(e.message, 'error');
            throw e;
        }
    }

    // ── Auth ────────────────────────────────────────────────
    setupEventListeners() {
        this.$('loginForm').addEventListener('submit', e => this.handleLogin(e));
        this.$('registerForm').addEventListener('submit', e => this.handleRegister(e));
        this.$('showRegisterBtn').addEventListener('click', e => { e.preventDefault(); this.$('loginSection').classList.add('hidden'); this.$('registerSection').classList.remove('hidden'); });
        this.$('showLoginBtn').addEventListener('click', e => { e.preventDefault(); this.$('registerSection').classList.add('hidden'); this.$('loginSection').classList.remove('hidden'); });
        this.$('logoutBtn').addEventListener('click', () => this.logout());
        this.$('modalClose').addEventListener('click', () => this.closeModal());

        document.querySelectorAll('.sidebar-link[data-page]').forEach(btn => {
            btn.addEventListener('click', () => this.navigate(btn.dataset.page));
        });

        this.$('addAccountBtn').addEventListener('click', () => this.showAccountForm());
        this.$('addHoldingBtn').addEventListener('click', () => this.showHoldingForm());
        this.$('addBudgetExpenseBtn').addEventListener('click', () => this.showBudgetExpenseForm());
        this.$('addBudgetBtn').addEventListener('click', () => this.showBudgetForm());
        this.$('addRecurringBtn').addEventListener('click', () => this.showRecurringForm());
        this.$('addRuleBtn').addEventListener('click', () => this.showRuleForm());
        this.$('addExpenseBtn').addEventListener('click', () => this.showSplitExpenseForm());
        this.$('addGroupBtn').addEventListener('click', () => this.handleAddGroup());
        this.$('addReceiptBtn').addEventListener('click', () => this.showReceiptForm());
        this.$('invitePartnerBtn').addEventListener('click', () => this.showInviteForm());
        this.$('nwSnapshotBtn').addEventListener('click', () => this.takeNetWorthSnapshot());
        this.$('loadSankeyBtn').addEventListener('click', () => this.loadCashFlow());
        this.$('accountFilterOwnership').addEventListener('change', () => this.loadAccounts());
        this.$('txFilterCategory').addEventListener('change', () => this.loadBudgetExpenses());
        this.$('txFilterMonth').addEventListener('change', () => this.loadBudgetExpenses());

        const importInfoBtn = this.$('importInfoCsvBtn');
        if (importInfoBtn) importInfoBtn.addEventListener('click', () => this.importInfoCsv());
        const importMonthlyBtn = this.$('importMonthlyCsvBtn');
        if (importMonthlyBtn) importMonthlyBtn.addEventListener('click', () => this.importMonthlyCsvs());
    }

    async importInfoCsv() {
        const input = this.$('importInfoCsvFile');
        if (!input || !input.files || input.files.length === 0) {
            this.notify('Choose an Info CSV file first', 'error');
            return;
        }

        const fd = new FormData();
        fd.append('file', input.files[0]);
        try {
            const res = await this.api('/budget/import/categories-csv', { method: 'POST', body: fd, headers: {} });
            await this.loadCategoriesCache();
            this.notify(`Imported categories: ${res.created_categories || 0}, sub-categories: ${res.created_sub_categories || 0}`, 'success');
            input.value = '';
        } catch (e) {
            console.error(e);
        }
    }

    async importMonthlyCsvs() {
        const input = this.$('importMonthlyCsvFiles');
        if (!input || !input.files || input.files.length === 0) {
            this.notify('Choose one or more monthly CSV files first', 'error');
            return;
        }

        const fd = new FormData();
        for (const f of input.files) fd.append('files', f);
        try {
            const res = await this.api('/budget/import/monthly-csv', { method: 'POST', body: fd, headers: {} });
            await this.loadCategoriesCache();
            await this.loadBudgetExpenses();
            this.notify(`Imported transactions: ${res.created_budget_expenses || 0}`, 'success');
            input.value = '';
        } catch (e) {
            console.error(e);
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        try {
            const data = await this.api('/auth/login', { method:'POST', body: JSON.stringify({ email: this.$('loginEmail').value, password: this.$('loginPassword').value }) });
            this.token = data.token; this.currentUser = data.user;
            localStorage.setItem('wealthwatch_token', this.token);
            this.enterApp();
        } catch(err){ console.error(err); }
    }

    async handleRegister(e) {
        e.preventDefault();
        try {
            const data = await this.api('/auth/register', { method:'POST', body: JSON.stringify({
                first_name: this.$('registerFirstName').value, last_name: this.$('registerLastName').value,
                email: this.$('registerEmail').value, password: this.$('registerPassword').value
            })});
            this.token = data.token; this.currentUser = data.user;
            localStorage.setItem('wealthwatch_token', this.token);
            this.enterApp();
        } catch(err){ console.error(err); }
    }

    logout() {
        this.token = null; this.currentUser = null;
        localStorage.removeItem('wealthwatch_token');
        Object.values(this.charts).forEach(c => c.destroy());
        this.charts = {};
        this.showAuth();
    }

    // ── Navigation ──────────────────────────────────────────
    showAuth() {
        this.$('authWrapper').classList.remove('hidden');
        this.$('appShell').classList.add('hidden');
        this.$('appShell').classList.remove('flex');
        this.$('loginSection').classList.remove('hidden');
        this.$('registerSection').classList.add('hidden');
    }

    async enterApp() {
        this.$('authWrapper').classList.add('hidden');
        this.$('appShell').classList.remove('hidden');
        this.$('appShell').classList.add('flex');
        try {
            this.currentUser = await this.api('/profile');
            this.$('userName').textContent = this.currentUser.first_name;
            this.$('userAvatar').textContent = (this.currentUser.first_name[0]||'')+(this.currentUser.last_name[0]||'');
        } catch(err){ this.logout(); return; }
        await this.loadCategoriesCache();
        this.navigate('dashboard');
    }

    async loadCategoriesCache() {
        try {
            this.categoriesCache = await this.api('/budget/categories') || [];
            this.subCategoriesCache = await this.api('/budget/subcategories') || [];
        } catch(err){ console.error(err); }
    }

    pageTitles = {
        dashboard:'Dashboard', networth:'Net Worth', accounts:'Accounts', investments:'Investments',
        budgetExpenses:'Transactions', budgets:'Budgets', recurring:'Recurring Bills', rules:'Auto Rules',
        reports:'Spending Trends', cashflow:'Cash Flow', expenses:'Split Expenses', groups:'Groups',
        balances:'Balances', receipts:'Receipts', family:'Family / Partner'
    };

    navigate(page) {
        document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.sidebar-link').forEach(el => el.classList.remove('active'));
        const pageEl = this.$('page-'+page);
        if (pageEl) pageEl.classList.remove('hidden');
        const btn = document.querySelector(`.sidebar-link[data-page="${page}"]`);
        if (btn) btn.classList.add('active');
        this.$('pageTitle').textContent = this.pageTitles[page] || page;

        const loaders = {
            dashboard: () => this.loadDashboard(),
            networth: () => this.loadNetWorth(),
            accounts: () => this.loadAccounts(),
            investments: () => this.loadInvestments(),
            budgetExpenses: () => this.loadBudgetExpenses(),
            budgets: () => this.loadBudgets(),
            recurring: () => this.loadRecurring(),
            rules: () => this.loadRules(),
            reports: () => this.loadReports(),
            cashflow: () => this.initCashFlow(),
            expenses: () => this.loadSplitExpenses(),
            groups: () => this.loadGroups(),
            balances: () => this.loadBalances(),
            receipts: () => this.loadReceipts(),
            family: () => this.loadFamily(),
        };
        if (loaders[page]) loaders[page]();
    }

    // ── Modal ───────────────────────────────────────────────
    openModal(title, bodyHtml) {
        this.$('modalTitle').textContent = title;
        this.$('modalBody').innerHTML = bodyHtml;
        this.$('modal').classList.remove('hidden');
        this.$('modal').classList.add('flex');
    }
    closeModal() {
        this.$('modal').classList.add('hidden');
        this.$('modal').classList.remove('flex');
    }

    // ── Notification ────────────────────────────────────────
    notify(message, type = 'info') {
        const el = document.createElement('div');
        el.className = `fixed top-4 right-4 px-4 py-3 rounded-xl shadow-lg z-[100] text-sm font-medium ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-brand-500 text-white'}`;
        el.textContent = message;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    }

    // ── Dashboard ───────────────────────────────────────────
    async loadDashboard() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        try {
            const [nw, savings, trends, upcoming, txs] = await Promise.all([
                this.api('/networth/summary').catch(()=>({})),
                this.api(`/reports/savings-rate?year=${year}&month=${month}`).catch(()=>({})),
                this.api('/reports/spending-trends?months=6').catch(()=>[]),
                this.api('/recurring/upcoming').catch(()=>[]),
                this.api('/budget/expenses').catch(()=>[]),
            ]);

            this.$('dashNetWorth').textContent = this.money(nw.net_worth);
            this.$('dashAssets').textContent = this.money(nw.total_assets);
            this.$('dashLiabilities').textContent = this.money(nw.total_liabilities);
            this.$('dashSavingsRate').textContent = this.pct(savings.savings_rate);

            this.renderBarChart('dashSpendingChart', Array.isArray(trends) ? trends : []);
            this.renderDoughnutChart('dashAllocationChart', nw.assets_by_type || {});

            const upEl = this.$('dashUpcoming');
            const upArr = Array.isArray(upcoming) ? upcoming : [];
            upEl.innerHTML = upArr.length ? upArr.slice(0,5).map(r => `
                <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div><p class="font-medium text-sm">${r.merchant}</p><p class="text-xs text-gray-500">${this.fmtDate(r.next_due_date)}</p></div>
                    <span class="font-semibold text-sm">${this.money(r.amount)}</span>
                </div>`).join('') : '<p class="text-gray-400 text-sm text-center py-4">No upcoming bills</p>';

            const txEl = this.$('dashRecentTx');
            const txArr = Array.isArray(txs) ? txs : [];
            txEl.innerHTML = txArr.length ? txArr.slice(0,5).map(t => `
                <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div><p class="font-medium text-sm">${t.title}</p><p class="text-xs text-gray-500">${this.fmtDate(t.date)}${t.merchant?' - '+t.merchant:''}</p></div>
                    <span class="font-semibold text-sm text-red-600">-${this.money(t.amount)}</span>
                </div>`).join('') : '<p class="text-gray-400 text-sm text-center py-4">No recent transactions</p>';
        } catch(e) { console.error(e); }
    }

    renderBarChart(canvasId, data) {
        if (this.charts[canvasId]) this.charts[canvasId].destroy();
        const ctx = this.$(canvasId).getContext('2d');
        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => this.monthNames()[(d.month||1)-1] + ' ' + (d.year||'')),
                datasets: [{ label: 'Spending', data: data.map(d => d.total_spent), backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 6 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => '$' + v } } } }
        });
    }

    renderDoughnutChart(canvasId, byType) {
        if (this.charts[canvasId]) this.charts[canvasId].destroy();
        const labels = Object.keys(byType).map(k => this.typeLabel(k));
        const values = Object.values(byType);
        const colors = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#ec4899'];
        if (!labels.length) { labels.push('No data'); values.push(1); }
        const ctx = this.$(canvasId).getContext('2d');
        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: { labels, datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length) }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 12, padding: 8, font: { size: 11 } } } } }
        });
    }

    // ── Net Worth ───────────────────────────────────────────
    async loadNetWorth() {
        try {
            const [summary, history] = await Promise.all([
                this.api('/networth/summary'),
                this.api('/networth/history'),
            ]);
            this.$('nwTotal').textContent = this.money(summary.net_worth);
            this.$('nwAssets').textContent = this.money(summary.total_assets);
            this.$('nwLiabilities').textContent = this.money(summary.total_liabilities);

            if (this.charts['nwChart']) this.charts['nwChart'].destroy();
            const hist = Array.isArray(history) ? history : [];
            const ctx = this.$('nwChart').getContext('2d');
            this.charts['nwChart'] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: hist.map(h => this.fmtDate(h.date)),
                    datasets: [
                        { label: 'Net Worth', data: hist.map(h => h.net_worth), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', fill: true, tension: 0.3 },
                        { label: 'Assets', data: hist.map(h => h.total_assets), borderColor: '#10b981', borderDash: [5,5], tension: 0.3 },
                        { label: 'Liabilities', data: hist.map(h => h.total_liabilities), borderColor: '#ef4444', borderDash: [5,5], tension: 0.3 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: v => '$' + v } } } }
            });

            const assetsEl = this.$('nwAssetsList');
            const liabEl = this.$('nwLiabilitiesList');
            assetsEl.innerHTML = ''; liabEl.innerHTML = '';
            for (const [type, amount] of Object.entries(summary.assets_by_type || {})) {
                assetsEl.innerHTML += `<div class="flex justify-between p-2 bg-green-50 rounded"><span class="text-sm">${this.typeLabel(type)}</span><span class="font-medium text-sm">${this.money(amount)}</span></div>`;
            }
            for (const [type, amount] of Object.entries(summary.liabilities_by_type || {})) {
                liabEl.innerHTML += `<div class="flex justify-between p-2 bg-red-50 rounded"><span class="text-sm">${this.typeLabel(type)}</span><span class="font-medium text-sm">${this.money(amount)}</span></div>`;
            }
            if (!assetsEl.innerHTML) assetsEl.innerHTML = '<p class="text-gray-400 text-sm text-center py-2">No assets yet</p>';
            if (!liabEl.innerHTML) liabEl.innerHTML = '<p class="text-gray-400 text-sm text-center py-2">No liabilities yet</p>';
        } catch(e) { console.error(e); }
    }

    async takeNetWorthSnapshot() {
        try {
            await this.api('/networth/snapshot', { method: 'POST' });
            this.notify('Snapshot saved', 'success');
            this.loadNetWorth();
        } catch(err) { console.error(err); }
    }

    // ── Accounts ────────────────────────────────────────────
    async loadAccounts() {
        const ownership = this.$('accountFilterOwnership').value;
        let url = '/accounts';
        if (ownership) url += '?ownership=' + ownership;
        try {
            const accounts = await this.api(url);
            const el = this.$('accountsList');
            const arr = Array.isArray(accounts) ? accounts : [];
            el.innerHTML = arr.length ? arr.map(a => `
                <div class="bg-white rounded-xl shadow-sm border p-5 ownership-${a.ownership}">
                    <div class="flex items-center justify-between mb-3">
                        <span class="text-xs font-medium px-2 py-1 rounded-full ${a.is_asset ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">${a.is_asset ? 'Asset' : 'Liability'}</span>
                        <span class="text-xs text-gray-400 uppercase">${a.ownership}</span>
                    </div>
                    <h4 class="font-semibold">${a.account_name}</h4>
                    <p class="text-sm text-gray-500">${a.institution_name} &middot; ${this.typeLabel(a.account_type)}</p>
                    <p class="text-2xl font-bold mt-3 ${a.is_asset ? 'text-green-600' : 'text-red-600'}">${this.money(a.balance)}</p>
                    <div class="flex space-x-2 mt-3">
                        <button onclick="app.showEditAccountForm(${a.id})" class="text-xs text-brand-600 hover:underline">Edit</button>
                        <button onclick="app.deleteAccount(${a.id})" class="text-xs text-red-500 hover:underline">Delete</button>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8 col-span-full">No accounts yet. Add your first account to get started.</p>';
        } catch(e) { console.error(e); }
    }

    showAccountForm() {
        this.openModal('Add Account', `
            <form id="accountForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Institution Name</label><input name="institution_name" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div><label class="block text-sm font-medium mb-1">Account Name</label><input name="account_name" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Type</label><select name="account_type" required class="w-full border rounded-lg px-3 py-2 text-sm">
                        <option value="checking">Checking</option><option value="savings">Savings</option><option value="credit_card">Credit Card</option>
                        <option value="investment">Investment</option><option value="loan">Loan</option><option value="mortgage">Mortgage</option>
                        <option value="real_estate">Real Estate</option><option value="other">Other</option>
                    </select></div>
                    <div><label class="block text-sm font-medium mb-1">Ownership</label><select name="ownership" class="w-full border rounded-lg px-3 py-2 text-sm">
                        <option value="ours">Ours (Joint)</option><option value="yours">Yours</option><option value="mine">Mine</option>
                    </select></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Balance</label><input name="balance" type="number" step="0.01" value="0" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Account</button>
            </form>`);
        this.$('accountForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = Object.fromEntries(fd);
            body.balance = parseFloat(body.balance);
            try { await this.api('/accounts', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Account added', 'success'); this.loadAccounts(); } catch(err) { console.error(err); }
        });
    }

    async showEditAccountForm(id) {
        try {
            const a = await this.api('/accounts/' + id);
            this.openModal('Edit Account', `
                <form id="editAccountForm" class="space-y-4">
                    <div><label class="block text-sm font-medium mb-1">Account Name</label><input name="account_name" value="${a.account_name}" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Balance</label><input name="balance" type="number" step="0.01" value="${a.balance}" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Ownership</label><select name="ownership" class="w-full border rounded-lg px-3 py-2 text-sm">
                        <option value="ours" ${a.ownership==='ours'?'selected':''}>Ours</option><option value="yours" ${a.ownership==='yours'?'selected':''}>Yours</option><option value="mine" ${a.ownership==='mine'?'selected':''}>Mine</option>
                    </select></div>
                    <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save</button>
                </form>`);
            this.$('editAccountForm').addEventListener('submit', async ev => {
                ev.preventDefault();
                const fd = new FormData(ev.target);
                const body = {};
                for (const [k,v] of fd) body[k] = k === 'balance' ? parseFloat(v) : v;
                try { await this.api('/accounts/' + id, { method: 'PUT', body: JSON.stringify(body) }); this.closeModal(); this.notify('Updated', 'success'); this.loadAccounts(); } catch(err) { console.error(err); }
            });
        } catch(err) { console.error(err); }
    }

    async deleteAccount(id) {
        if (!confirm('Delete this account?')) return;
        try { await this.api('/accounts/' + id, { method: 'DELETE' }); this.notify('Deleted', 'success'); this.loadAccounts(); } catch(err) { console.error(err); }
    }

    // ── Investments ─────────────────────────────────────────
    async loadInvestments() {
        try {
            const [portfolio, holdings] = await Promise.all([
                this.api('/investments/portfolio'),
                this.api('/investments'),
            ]);
            this.$('invTotalValue').textContent = this.money(portfolio.total_value);
            this.$('invCostBasis').textContent = this.money(portfolio.total_cost_basis);
            const gl = portfolio.total_gain_loss || 0;
            this.$('invGainLoss').textContent = (gl >= 0 ? '+' : '') + this.money(gl);
            this.$('invGainLoss').className = 'text-2xl font-bold mt-1 ' + (gl >= 0 ? 'text-green-600' : 'text-red-600');
            const pctVal = portfolio.total_gain_loss_pct || 0;
            this.$('invReturn').textContent = (pctVal >= 0 ? '+' : '') + this.pct(pctVal);
            this.$('invReturn').className = 'text-2xl font-bold mt-1 ' + (pctVal >= 0 ? 'text-green-600' : 'text-red-600');

            const arr = Array.isArray(holdings) ? holdings : [];
            const tb = this.$('holdingsTable');
            tb.innerHTML = arr.length ? arr.map(h => {
                const glc = h.gain_loss >= 0 ? 'text-green-600' : 'text-red-600';
                return `<tr>
                    <td class="px-4 py-3 font-semibold">${h.symbol}</td>
                    <td class="px-4 py-3">${h.name}</td>
                    <td class="px-4 py-3 text-right">${h.quantity}</td>
                    <td class="px-4 py-3 text-right">${this.money(h.current_price)}</td>
                    <td class="px-4 py-3 text-right font-medium">${this.money(h.current_value)}</td>
                    <td class="px-4 py-3 text-right ${glc}">${h.gain_loss >= 0 ? '+' : ''}${this.money(h.gain_loss)} (${this.pct(h.gain_loss_percent)})</td>
                    <td class="px-4 py-3 text-right"><button onclick="app.deleteHolding(${h.id})" class="text-red-500 hover:underline text-xs">Delete</button></td>
                </tr>`;
            }).join('') : '<tr><td colspan="7" class="px-4 py-8 text-center text-gray-400">No holdings yet</td></tr>';
        } catch(e) { console.error(e); }
    }

    showHoldingForm() {
        this.openModal('Add Holding', `
            <form id="holdingForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Account ID</label><input name="account_id" type="number" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Investment account ID"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Symbol</label><input name="symbol" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="AAPL"></div>
                    <div><label class="block text-sm font-medium mb-1">Type</label><select name="investment_type" class="w-full border rounded-lg px-3 py-2 text-sm">
                        <option value="stock">Stock</option><option value="etf">ETF</option><option value="mutual_fund">Mutual Fund</option>
                        <option value="bond">Bond</option><option value="crypto">Crypto</option><option value="other">Other</option>
                    </select></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Name</label><input name="name" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-3 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Quantity</label><input name="quantity" type="number" step="0.0001" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Cost Basis</label><input name="cost_basis" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Current Price</label><input name="current_price" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                </div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Holding</button>
            </form>`);
        this.$('holdingForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = {};
            for (const [k,v] of fd) body[k] = ['account_id'].includes(k) ? parseInt(v) : (['quantity','cost_basis','current_price'].includes(k) ? parseFloat(v) : v);
            try { await this.api('/investments', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Holding added', 'success'); this.loadInvestments(); } catch(err) { console.error(err); }
        });
    }

    async deleteHolding(id) {
        if (!confirm('Delete this holding?')) return;
        try { await this.api('/investments/' + id, { method: 'DELETE' }); this.notify('Deleted', 'success'); this.loadInvestments(); } catch(err) { console.error(err); }
    }

    // ── Transactions (Budget Expenses) ──────────────────────
    async loadBudgetExpenses() {
        const catSel = this.$('txFilterCategory');
        if (catSel.options.length <= 1) {
            this.categoriesCache.filter(c => c.type === 'expense').forEach(c => {
                const o = document.createElement('option'); o.value = c.id; o.textContent = c.name; catSel.appendChild(o);
            });
        }
        let url = '/budget/expenses';
        const params = [];
        if (catSel.value) params.push('category_id=' + catSel.value);
        const monthVal = this.$('txFilterMonth').value;
        if (monthVal) { const [y,m] = monthVal.split('-'); params.push('year=' + y, 'month=' + parseInt(m)); }
        if (params.length) url += '?' + params.join('&');

        try {
            const txs = await this.api(url);
            const arr = Array.isArray(txs) ? txs : [];
            this.$('txTable').innerHTML = arr.length ? arr.map(t => `
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3 text-gray-500">${this.fmtDate(t.date)}</td>
                    <td class="px-4 py-3 font-medium">${t.title}</td>
                    <td class="px-4 py-3 text-gray-500">${t.merchant || '-'}</td>
                    <td class="px-4 py-3"><span class="text-xs bg-gray-100 px-2 py-1 rounded-full">${t.category?.name || ''} ${t.sub_category?.name ? '/ ' + t.sub_category.name : ''}</span></td>
                    <td class="px-4 py-3 text-right font-semibold text-red-600">-${this.money(t.amount)}</td>
                </tr>`).join('') : '<tr><td colspan="5" class="px-4 py-8 text-center text-gray-400">No transactions found</td></tr>';
        } catch(e) { console.error(e); }
    }

    showBudgetExpenseForm() {
        const catOpts = this.categoriesCache.filter(c => c.type === 'expense').map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        const subOpts = this.subCategoriesCache.map(s => `<option value="${s.id}" data-cat="${s.category_id}">${s.name}</option>`).join('');
        this.openModal('Add Transaction', `
            <form id="txForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Title</label><input name="title" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Category</label><select name="category_id" required class="w-full border rounded-lg px-3 py-2 text-sm">${catOpts}</select></div>
                    <div><label class="block text-sm font-medium mb-1">Sub-Category</label><select name="sub_category_id" required class="w-full border rounded-lg px-3 py-2 text-sm">${subOpts}</select></div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Amount</label><input name="amount" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Date</label><input name="date" type="date" required value="${new Date().toISOString().split('T')[0]}" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Merchant</label><input name="merchant" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div><label class="block text-sm font-medium mb-1">Notes</label><textarea name="notes" rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Transaction</button>
            </form>`);
        this.$('txForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = {};
            for (const [k,v] of fd) body[k] = ['category_id','sub_category_id'].includes(k) ? parseInt(v) : (k === 'amount' ? parseFloat(v) : v);
            try { await this.api('/budget/expenses', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Transaction added', 'success'); this.loadBudgetExpenses(); } catch(err) { console.error(err); }
        });
    }

    // ── Budgets ─────────────────────────────────────────────
    async loadBudgets() {
        const now = new Date();
        try {
            const [budgets, summary] = await Promise.all([
                this.api(`/budget/budgets?year=${now.getFullYear()}&month=${now.getMonth()+1}`),
                this.api(`/budget/summary/monthly?year=${now.getFullYear()}&month=${now.getMonth()+1}`).catch(() => ({})),
            ]);
            const catSpending = {};
            (summary.by_category || []).forEach(c => { catSpending[c.category_id] = c.total_amount; });

            const arr = Array.isArray(budgets) ? budgets : [];
            this.$('budgetCards').innerHTML = arr.length ? arr.map(b => {
                const spent = catSpending[b.category_id] || 0;
                const pctVal = b.amount > 0 ? Math.min((spent / b.amount) * 100, 100) : 0;
                const over = spent > b.amount;
                return `<div class="bg-white rounded-xl shadow-sm border p-5">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-medium">${b.category?.name || 'Budget'} ${b.sub_category?.name ? '/ ' + b.sub_category.name : ''}</span>
                        <span class="text-xs ${over ? 'text-red-600' : 'text-gray-500'}">${this.money(spent)} / ${this.money(b.amount)}</span>
                    </div>
                    <div class="w-full bg-gray-100 rounded-full h-2.5">
                        <div class="h-2.5 rounded-full ${over ? 'bg-red-500' : 'bg-brand-500'}" style="width:${pctVal}%"></div>
                    </div>
                    <p class="text-xs text-gray-400 mt-2">${b.period} &middot; ${this.pct(pctVal)} used</p>
                </div>`;
            }).join('') : '<p class="text-gray-400 text-center py-8 col-span-full">No budgets set for this month.</p>';
        } catch(e) { console.error(e); }
    }

    showBudgetForm() {
        const catOpts = this.categoriesCache.filter(c => c.type === 'expense').map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        const now = new Date();
        this.openModal('Set Budget', `
            <form id="budgetForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Category</label><select name="category_id" required class="w-full border rounded-lg px-3 py-2 text-sm">${catOpts}</select></div>
                <div class="grid grid-cols-3 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Period</label><select name="period" class="w-full border rounded-lg px-3 py-2 text-sm"><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></div>
                    <div><label class="block text-sm font-medium mb-1">Year</label><input name="year" type="number" value="${now.getFullYear()}" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Month</label><input name="month" type="number" min="1" max="12" value="${now.getMonth()+1}" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Amount</label><input name="amount" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Budget</button>
            </form>`);
        this.$('budgetForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = {};
            for (const [k,v] of fd) body[k] = ['category_id','year','month'].includes(k) ? parseInt(v) : (k === 'amount' ? parseFloat(v) : v);
            try { await this.api('/budget/budgets', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Budget created', 'success'); this.loadBudgets(); } catch(err) { console.error(err); }
        });
    }

    // ── Recurring ───────────────────────────────────────────
    async loadRecurring() {
        try {
            const items = await this.api('/recurring');
            const arr = Array.isArray(items) ? items : [];
            this.$('recurringList').innerHTML = arr.length ? arr.map(r => `
                <div class="bg-white rounded-xl shadow-sm border p-5 flex items-center justify-between">
                    <div>
                        <h4 class="font-semibold">${r.merchant}</h4>
                        <p class="text-sm text-gray-500">${r.frequency} &middot; Next: ${this.fmtDate(r.next_due_date)}</p>
                        ${r.category ? `<span class="text-xs bg-gray-100 px-2 py-0.5 rounded-full">${r.category.name}</span>` : ''}
                    </div>
                    <div class="text-right">
                        <p class="text-lg font-bold">${this.money(r.amount)}</p>
                        <button onclick="app.deleteRecurring(${r.id})" class="text-xs text-red-500 hover:underline mt-1">Remove</button>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8">No recurring bills tracked.</p>';
        } catch(e) { console.error(e); }
    }

    showRecurringForm() {
        const catOpts = '<option value="">None</option>' + this.categoriesCache.filter(c => c.type === 'expense').map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        this.openModal('Add Recurring Bill', `
            <form id="recForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Merchant / Name</label><input name="merchant" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Amount</label><input name="amount" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Frequency</label><select name="frequency" class="w-full border rounded-lg px-3 py-2 text-sm">
                        <option value="monthly">Monthly</option><option value="weekly">Weekly</option><option value="yearly">Yearly</option><option value="quarterly">Quarterly</option>
                    </select></div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Next Due Date</label><input name="next_due_date" type="date" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Category</label><select name="category_id" class="w-full border rounded-lg px-3 py-2 text-sm">${catOpts}</select></div>
                </div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save</button>
            </form>`);
        this.$('recForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = {};
            for (const [k,v] of fd) {
                if (k === 'category_id') { if (v) body[k] = parseInt(v); }
                else if (k === 'amount') body[k] = parseFloat(v);
                else body[k] = v;
            }
            try { await this.api('/recurring', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Added', 'success'); this.loadRecurring(); } catch(err) { console.error(err); }
        });
    }

    async deleteRecurring(id) {
        if (!confirm('Remove this recurring bill?')) return;
        try { await this.api('/recurring/' + id, { method: 'DELETE' }); this.notify('Removed', 'success'); this.loadRecurring(); } catch(err) { console.error(err); }
    }

    // ── Auto Rules ──────────────────────────────────────────
    async loadRules() {
        try {
            const rules = await this.api('/rules');
            const arr = Array.isArray(rules) ? rules : [];
            this.$('rulesList').innerHTML = arr.length ? arr.map(r => `
                <div class="bg-white rounded-xl shadow-sm border p-5 flex items-center justify-between">
                    <div>
                        <p class="text-sm"><span class="font-medium">IF</span> merchant matches "<span class="text-brand-600 font-semibold">${r.merchant_pattern}</span>"
                        ${r.min_amount != null ? ' AND amount >= $' + r.min_amount : ''}${r.max_amount != null ? ' AND amount <= $' + r.max_amount : ''}</p>
                        <p class="text-sm mt-1"><span class="font-medium">THEN</span> categorize as <span class="bg-brand-100 text-brand-700 px-2 py-0.5 rounded text-xs font-medium">${r.category?.name || ''}${r.sub_category ? ' / ' + r.sub_category.name : ''}</span></p>
                    </div>
                    <button onclick="app.deleteRule(${r.id})" class="text-red-500 hover:underline text-xs">Delete</button>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8">No rules defined.</p>';
        } catch(e) { console.error(e); }
    }

    showRuleForm() {
        const catOpts = this.categoriesCache.filter(c => c.type === 'expense').map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        this.openModal('Add Auto-Categorization Rule', `
            <form id="ruleForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Merchant Pattern (contains)</label><input name="merchant_pattern" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. Starbucks"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Min Amount (optional)</label><input name="min_amount" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Max Amount (optional)</label><input name="max_amount" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Assign to Category</label><select name="category_id" required class="w-full border rounded-lg px-3 py-2 text-sm">${catOpts}</select></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Save Rule</button>
            </form>`);
        this.$('ruleForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const body = {};
            for (const [k,v] of fd) {
                if (!v) continue;
                if (k === 'category_id') body[k] = parseInt(v);
                else if (['min_amount','max_amount'].includes(k)) body[k] = parseFloat(v);
                else body[k] = v;
            }
            try { await this.api('/rules', { method: 'POST', body: JSON.stringify(body) }); this.closeModal(); this.notify('Rule created', 'success'); this.loadRules(); } catch(err) { console.error(err); }
        });
    }

    async deleteRule(id) {
        if (!confirm('Delete this rule?')) return;
        try { await this.api('/rules/' + id, { method: 'DELETE' }); this.notify('Deleted', 'success'); this.loadRules(); } catch(err) { console.error(err); }
    }

    // ── Reports ─────────────────────────────────────────────
    async loadReports() {
        try {
            const [trends, merchants] = await Promise.all([
                this.api('/reports/spending-trends?months=12').catch(() => []),
                this.api('/reports/spending-by-merchant?limit=10').catch(() => []),
            ]);
            this.renderBarChart('reportSpendingChart', Array.isArray(trends) ? trends : []);

            const mArr = Array.isArray(merchants) ? merchants : [];
            this.$('reportMerchants').innerHTML = mArr.length ? mArr.map((m,i) => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                        <span class="text-xs font-bold text-gray-400 w-5">#${i+1}</span>
                        <div><p class="font-medium text-sm">${m.merchant}</p><p class="text-xs text-gray-400">${m.count} transactions</p></div>
                    </div>
                    <span class="font-semibold text-sm">${this.money(m.total_spent)}</span>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8">No merchant data available.</p>';
        } catch(e) { console.error(e); }
    }

    // ── Cash Flow ───────────────────────────────────────────
    initCashFlow() {
        const now = new Date();
        this.$('sankeyMonth').value = now.getFullYear() + '-' + ('' + (now.getMonth()+1)).padStart(2, '0');
    }

    async loadCashFlow() {
        const val = this.$('sankeyMonth').value;
        if (!val) return;
        const [year, month] = val.split('-');
        try {
            const data = await this.api(`/reports/cashflow-sankey?year=${year}&month=${parseInt(month)}`);
            const container = this.$('sankeyContainer');
            const links = (data.links || []).filter(l => l.value > 0);
            if (!links.length) { container.innerHTML = '<p class="text-gray-400 text-center py-16">No cash flow data for this month.</p>'; return; }

            let html = '<div class="space-y-2">';
            const incLinks = links.filter(l => l.target === 'income');
            const expLinks = links.filter(l => l.source === 'expenses');
            const totalIn = incLinks.reduce((s,l) => s + l.value, 0);
            const totalOut = expLinks.reduce((s,l) => s + l.value, 0);

            html += `<div class="p-4 bg-green-50 rounded-xl mb-4"><p class="text-sm font-medium text-green-800 mb-2">Income Sources &rarr; Total: ${this.money(totalIn)}</p>`;
            incLinks.forEach(l => {
                const pctVal = totalIn > 0 ? (l.value / totalIn) * 100 : 0;
                html += `<div class="mb-2"><div class="flex justify-between text-sm mb-1"><span>${l.source.replace('inc_','')}</span><span class="font-medium">${this.money(l.value)}</span></div>
                    <div class="w-full bg-green-100 rounded-full h-2"><div class="bg-green-500 h-2 rounded-full" style="width:${pctVal}%"></div></div></div>`;
            });
            html += '</div>';
            html += '<div class="text-center py-2"><i class="fas fa-arrow-down text-gray-300 text-2xl"></i></div>';
            html += `<div class="p-4 bg-red-50 rounded-xl"><p class="text-sm font-medium text-red-800 mb-2">Expenses &rarr; Total: ${this.money(totalOut)}</p>`;
            expLinks.forEach(l => {
                const pctVal = totalOut > 0 ? (l.value / totalOut) * 100 : 0;
                html += `<div class="mb-2"><div class="flex justify-between text-sm mb-1"><span>${l.target.replace('exp_','')}</span><span class="font-medium">${this.money(l.value)}</span></div>
                    <div class="w-full bg-red-100 rounded-full h-2"><div class="bg-red-500 h-2 rounded-full" style="width:${pctVal}%"></div></div></div>`;
            });
            html += '</div>';
            const net = totalIn - totalOut;
            html += `<div class="p-4 bg-gray-50 rounded-xl mt-4 flex justify-between items-center">
                <span class="font-medium">Net Cash Flow</span>
                <span class="text-lg font-bold ${net >= 0 ? 'text-green-600' : 'text-red-600'}">${net >= 0 ? '+' : ''}${this.money(net)}</span></div>`;
            html += '</div>';
            container.innerHTML = html;
        } catch(e) { console.error(e); }
    }

    // ── Split Expenses ──────────────────────────────────────
    async loadSplitExpenses() {
        try {
            const expenses = await this.api('/expenses');
            const arr = Array.isArray(expenses) ? expenses : [];
            this.$('expensesList').innerHTML = arr.length ? arr.map(expense => `
                <div class="p-4 border-b last:border-b-0">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="font-semibold">${expense.title}</h4>
                            <p class="text-sm text-gray-500 mt-1">Paid by ${expense.payer?.first_name || '?'} ${expense.payer?.last_name || ''} &middot; ${this.fmtDate(expense.date)}</p>
                            <div class="mt-2 flex flex-wrap gap-1">
                                ${(expense.splits || []).map(s => `<span class="text-xs bg-gray-100 px-2 py-1 rounded-full">${s.user?.first_name || 'User ' + s.user_id}: ${this.money(s.amount)}</span>`).join('')}
                            </div>
                        </div>
                        <p class="text-xl font-bold">${this.money(expense.amount)}</p>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8">No split expenses.</p>';
        } catch(e) { console.error(e); }
    }

    showSplitExpenseForm() {
        const catOpts = '<option value="">None</option>' + this.categoriesCache.filter(c => c.type === 'expense').map(c => `<option value="${c.name}">${c.name}</option>`).join('');
        this.openModal('Add Split Expense', `
            <form id="splitExpForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Title</label><input name="title" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Amount</label><input name="amount" type="number" step="0.01" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Category</label><select name="category" class="w-full border rounded-lg px-3 py-2 text-sm">${catOpts}</select></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Description</label><textarea name="description" rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
                <div><label class="block text-sm font-medium mb-1">Split With (User IDs, comma-separated)</label><input name="split_with" placeholder="e.g. 2,3" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Add Expense</button>
            </form>`);
        this.$('splitExpForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const amount = parseFloat(fd.get('amount'));
            const splitWith = fd.get('split_with') ? fd.get('split_with').split(',').map(id => parseInt(id.trim())).filter(Boolean) : [];
            const splitAmount = amount / (splitWith.length + 1);
            const splits = [{ user_id: this.currentUser.id, amount: splitAmount }];
            splitWith.forEach(uid => splits.push({ user_id: uid, amount: splitAmount }));
            try {
                await this.api('/expenses', { method: 'POST', body: JSON.stringify({
                    title: fd.get('title'), amount, description: fd.get('description'), category: fd.get('category'),
                    date: new Date().toISOString(), splits
                })});
                this.closeModal(); this.notify('Expense added', 'success'); this.loadSplitExpenses();
            } catch(err) { console.error(err); }
        });
    }

    // ── Groups ──────────────────────────────────────────────
    async loadGroups() {
        try {
            const groups = await this.api('/groups');
            const arr = Array.isArray(groups) ? groups : [];
            this.$('groupsList').innerHTML = arr.length ? arr.map(g => `
                <div class="bg-white rounded-xl shadow-sm border p-5">
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="font-semibold">${g.name}</h3>
                        <div class="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center"><i class="fas fa-users text-brand-600 text-sm"></i></div>
                    </div>
                    <p class="text-sm text-gray-500 mb-3">${g.description || 'No description'}</p>
                    <div class="flex items-center justify-between">
                        <div class="flex -space-x-2">
                            ${(g.members || []).slice(0,4).map(m => `<div class="w-7 h-7 bg-brand-500 rounded-full flex items-center justify-center text-white text-xs font-medium border-2 border-white">${(m.first_name||'?')[0]}${(m.last_name||'?')[0]}</div>`).join('')}
                            ${(g.members||[]).length > 4 ? `<div class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 text-xs font-medium border-2 border-white">+${g.members.length-4}</div>` : ''}
                        </div>
                        <span class="text-xs text-gray-400">${(g.members||[]).length} members</span>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8 col-span-full">No groups yet.</p>';
        } catch(e) { console.error(e); }
    }

    handleAddGroup() {
        this.openModal('Create Group', `
            <form id="groupForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">Name</label><input name="name" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div><label class="block text-sm font-medium mb-1">Description</label><textarea name="description" rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Create Group</button>
            </form>`);
        this.$('groupForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            try { await this.api('/groups', { method: 'POST', body: JSON.stringify(Object.fromEntries(fd)) }); this.closeModal(); this.notify('Group created', 'success'); this.loadGroups(); } catch(err) { console.error(err); }
        });
    }

    // ── Balances ────────────────────────────────────────────
    async loadBalances() {
        try {
            const data = await this.api('/balances');
            const balances = data.balances || [];
            this.$('balancesList').innerHTML = balances.length ? balances.map(b => `
                <div class="p-4 border-b last:border-b-0 flex justify-between items-center">
                    <div><h4 class="font-medium">User ${b.user_id}</h4></div>
                    <div class="text-right">
                        <p class="text-lg font-bold ${b.amount > 0 ? 'text-green-600' : 'text-red-600'}">${b.amount > 0 ? '+' : ''}${this.money(Math.abs(b.amount))}</p>
                        <p class="text-xs text-gray-500">${b.amount > 0 ? 'owes you' : 'you owe'}</p>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8">No balances to show.</p>';
        } catch(e) { console.error(e); }
    }

    // ── Receipts ────────────────────────────────────────────
    async loadReceipts() {
        try {
            const receipts = await this.api('/receipts');
            const arr = Array.isArray(receipts) ? receipts : [];
            this.$('receiptsList').innerHTML = arr.length ? arr.map(r => `
                <div class="bg-white rounded-xl shadow-sm border p-5">
                    <div class="flex items-center space-x-3 mb-3">
                        <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center"><i class="fas fa-file-image text-gray-500"></i></div>
                        <div>
                            <p class="font-medium text-sm">${r.file_name}</p>
                            <p class="text-xs text-gray-400">${r.merchant || 'No merchant'} ${r.amount ? '&middot; ' + this.money(r.amount) : ''}</p>
                        </div>
                    </div>
                    ${r.notes ? `<p class="text-sm text-gray-500 mb-2">${r.notes}</p>` : ''}
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-gray-400">${this.fmtDate(r.created_at)}</span>
                        <button onclick="app.deleteReceipt(${r.id})" class="text-xs text-red-500 hover:underline">Delete</button>
                    </div>
                </div>`).join('') : '<p class="text-gray-400 text-center py-8 col-span-full">No receipts uploaded yet.</p>';
        } catch(e) { console.error(e); }
    }

    showReceiptForm() {
        this.openModal('Upload Receipt', `
            <form id="receiptForm" class="space-y-4">
                <div><label class="block text-sm font-medium mb-1">File</label><input name="file" type="file" accept="image/*,.pdf" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-sm font-medium mb-1">Merchant</label><input name="merchant" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                    <div><label class="block text-sm font-medium mb-1">Amount</label><input name="amount" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                </div>
                <div><label class="block text-sm font-medium mb-1">Date</label><input name="date" type="date" class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div><label class="block text-sm font-medium mb-1">Notes</label><textarea name="notes" rows="2" class="w-full border rounded-lg px-3 py-2 text-sm"></textarea></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Upload</button>
            </form>`);
        this.$('receiptForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            try {
                const headers = {};
                await this.api('/receipts', { method: 'POST', body: fd, headers });
                this.closeModal(); this.notify('Receipt uploaded', 'success'); this.loadReceipts();
            } catch(err) { console.error(err); }
        });
    }

    async deleteReceipt(id) {
        if (!confirm('Delete this receipt?')) return;
        try { await this.api('/receipts/' + id, { method: 'DELETE' }); this.notify('Deleted', 'success'); this.loadReceipts(); } catch(err) { console.error(err); }
    }

    // ── Family ──────────────────────────────────────────────
    async loadFamily() {
        try {
            const members = await this.api('/families/members');
            const arr = Array.isArray(members) ? members : [];
            this.$('familyMembersList').innerHTML = arr.length ? arr.map(m => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                        <div class="w-9 h-9 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 font-bold text-sm">${(m.user?.first_name||'?')[0]}${(m.user?.last_name||'?')[0]}</div>
                        <div>
                            <p class="font-medium text-sm">${m.user?.first_name || ''} ${m.user?.last_name || ''}</p>
                            <p class="text-xs text-gray-500">${m.user?.email || ''}</p>
                        </div>
                    </div>
                    <span class="text-xs font-medium px-2 py-1 rounded-full bg-brand-100 text-brand-700">${m.role}</span>
                </div>`).join('') : '<p class="text-gray-400 text-center py-4">No members yet</p>';
        } catch(e) { console.error(e); }
    }

    showInviteForm() {
        this.openModal('Invite Partner', `
            <form id="inviteForm" class="space-y-4">
                <p class="text-sm text-gray-500">Your partner must already have a WealthWatch account. Enter their email below to add them to your family.</p>
                <div><label class="block text-sm font-medium mb-1">Partner Email</label><input name="email" type="email" required class="w-full border rounded-lg px-3 py-2 text-sm"></div>
                <div><label class="block text-sm font-medium mb-1">Role</label><select name="role" class="w-full border rounded-lg px-3 py-2 text-sm">
                    <option value="admin">Admin</option><option value="member">Member</option>
                </select></div>
                <button type="submit" class="w-full bg-brand-600 text-white py-2.5 rounded-lg hover:bg-brand-700 font-medium">Send Invite</button>
            </form>`);
        this.$('inviteForm').addEventListener('submit', async e => {
            e.preventDefault();
            const fd = new FormData(e.target);
            try { await this.api('/families/members', { method: 'POST', body: JSON.stringify(Object.fromEntries(fd)) }); this.closeModal(); this.notify('Partner added!', 'success'); this.loadFamily(); } catch(err) { console.error(err); }
        });
    }
}

// Initialize the app
const app = new WealthWatchApp();
