class WealthWatchApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.token = localStorage.getItem('wealthwatch_token');
        this.currentUser = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        if (this.token) {
            this.showDashboard();
            this.loadUserProfile();
        } else {
            this.showLogin();
        }
    }

    async loadExpenseCategories() {
        const select = document.getElementById('expenseCategory');
        if (!select) return;

        try {
            const categories = await this.apiCall('/budget/categories?type=expense');

            select.innerHTML = '<option value="">Select a category</option>';
            if (Array.isArray(categories)) {
                categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat.name;
                    opt.textContent = cat.name;
                    select.appendChild(opt);
                });
            }
        } catch (error) {
            // Error already handled by apiCall
        }
    }

    setupEventListeners() {
        // Navigation
        document.getElementById('dashboardBtn').addEventListener('click', () => this.showDashboard());
        document.getElementById('expensesBtn').addEventListener('click', () => this.showExpenses());
        document.getElementById('groupsBtn').addEventListener('click', () => this.showGroups());
        document.getElementById('balancesBtn').addEventListener('click', () => this.showBalances());
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());

        // Auth forms
        document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('registerForm').addEventListener('submit', (e) => this.handleRegister(e));
        document.getElementById('showRegisterBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.showRegister();
        });
        document.getElementById('showLoginBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.showLogin();
        });

        // Expense modal
        document.getElementById('addExpenseBtn').addEventListener('click', () => this.showExpenseModal());
        document.getElementById('cancelExpenseBtn').addEventListener('click', () => this.hideExpenseModal());
        document.getElementById('expenseForm').addEventListener('submit', (e) => this.handleAddExpense(e));

        // Group button
        document.getElementById('addGroupBtn').addEventListener('click', () => this.handleAddGroup());
    }

    // API Methods
    async apiCall(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (this.token) {
            config.headers.Authorization = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            this.showNotification(error.message, 'error');
            throw error;
        }
    }

    // Authentication
    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const data = await this.apiCall('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });

            this.token = data.token;
            this.currentUser = data.user;
            localStorage.setItem('wealthwatch_token', this.token);
            
            this.showNotification('Login successful!', 'success');
            this.showDashboard();
            this.loadUserProfile();
        } catch (error) {
            // Error already handled by apiCall
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        const firstName = document.getElementById('registerFirstName').value;
        const lastName = document.getElementById('registerLastName').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;

        try {
            const data = await this.apiCall('/auth/register', {
                method: 'POST',
                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName,
                    email,
                    password
                })
            });

            this.token = data.token;
            this.currentUser = data.user;
            localStorage.setItem('wealthwatch_token', this.token);
            
            this.showNotification('Registration successful!', 'success');
            this.showDashboard();
            this.loadUserProfile();
        } catch (error) {
            // Error already handled by apiCall
        }
    }

    logout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('wealthwatch_token');
        this.showLogin();
    }

    // User Profile
    async loadUserProfile() {
        try {
            this.currentUser = await this.apiCall('/profile');
            document.getElementById('userName').textContent = this.currentUser.first_name;
            this.loadDashboardData();
        } catch (error) {
            console.error('Failed to load user profile:', error);
        }
    }

    // Dashboard
    async loadDashboardData() {
        this.loadBalances();
        this.loadRecentExpenses();
    }

    async loadBalances() {
        try {
            const balances = await this.apiCall('/balances');
            let totalOwed = 0;
            let totalOwe = 0;

            const balanceList = document.getElementById('balanceList');
            balanceList.innerHTML = '';

            if (balances.balances && balances.balances.length > 0) {
                balances.balances.forEach(balance => {
                    const amount = Math.abs(balance.amount);
                    if (balance.amount > 0) {
                        totalOwed += amount;
                    } else {
                        totalOwe += amount;
                    }

                    const balanceItem = document.createElement('div');
                    balanceItem.className = 'flex justify-between items-center p-3 border rounded-lg';
                    balanceItem.innerHTML = `
                        <div>
                            <p class="font-medium">User ${balance.user_id}</p>
                            <p class="text-sm text-gray-500">user${balance.user_id}@example.com</p>
                        </div>
                        <div class="text-right">
                            <p class="font-semibold ${balance.amount > 0 ? 'balance-positive' : 'balance-negative'}">
                                ${balance.amount > 0 ? '+' : ''}$${amount.toFixed(2)}
                            </p>
                            <p class="text-xs text-gray-500">
                                ${balance.amount > 0 ? 'owes you' : 'you owe'}
                            </p>
                        </div>
                    `;
                    balanceList.appendChild(balanceItem);
                });
            } else {
                balanceList.innerHTML = '<p class="text-gray-500 text-center py-4">No balances to show</p>';
            }

            document.getElementById('totalOwed').textContent = totalOwed.toFixed(2);
            document.getElementById('totalOwe').textContent = Math.abs(totalOwe).toFixed(2);
            document.getElementById('totalBalance').textContent = (totalOwed + totalOwe).toFixed(2);
        } catch (error) {
            console.error('Failed to load balances:', error);
        }
    }

    async loadRecentExpenses() {
        try {
            const expenses = await this.apiCall('/expenses?limit=5');
            const recentExpenses = document.getElementById('recentExpenses');
            recentExpenses.innerHTML = '';

            if (expenses && expenses.length > 0) {
                expenses.forEach(expense => {
                    const expenseItem = document.createElement('div');
                    expenseItem.className = 'flex justify-between items-center p-3 border rounded-lg';
                    expenseItem.innerHTML = `
                        <div>
                            <p class="font-medium">${expense.title}</p>
                            <p class="text-sm text-gray-500">${new Date(expense.date).toLocaleDateString()}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-semibold">$${expense.amount.toFixed(2)}</p>
                            <p class="text-xs text-gray-500">Paid by ${expense.payer.first_name}</p>
                        </div>
                    `;
                    recentExpenses.appendChild(expenseItem);
                });
            } else {
                recentExpenses.innerHTML = '<p class="text-gray-500 text-center py-4">No recent expenses</p>';
            }
        } catch (error) {
            console.error('Failed to load expenses:', error);
        }
    }

    // Expenses
    async loadExpenses() {
        try {
            const expenses = await this.apiCall('/expenses');
            const expensesList = document.getElementById('expensesList');
            expensesList.innerHTML = '';

            if (expenses && expenses.length > 0) {
                expenses.forEach(expense => {
                    const expenseItem = document.createElement('div');
                    expenseItem.className = 'p-4 border-b last:border-b-0';
                    expenseItem.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div>
                                <h4 class="font-semibold text-lg">${expense.title}</h4>
                                <p class="text-gray-600">${expense.description || 'No description'}</p>
                                <p class="text-sm text-gray-500 mt-1">
                                    Paid by ${expense.payer.first_name} ${expense.payer.last_name} • 
                                    ${new Date(expense.date).toLocaleDateString()}
                                </p>
                                <div class="mt-2">
                                    <span class="text-sm font-medium">Split between: </span>
                                    ${expense.splits.map(split => 
                                        `<span class="text-sm">${split.user.first_name} ($${split.amount.toFixed(2)})</span>`
                                    ).join(', ')}
                                </div>
                            </div>
                            <div class="text-right">
                                <p class="text-2xl font-bold">$${expense.amount.toFixed(2)}</p>
                                ${expense.group ? `<p class="text-sm text-gray-500">${expense.group.name}</p>` : ''}
                            </div>
                        </div>
                    `;
                    expensesList.appendChild(expenseItem);
                });
            } else {
                expensesList.innerHTML = '<p class="text-gray-500 text-center py-8">No expenses to show</p>';
            }
        } catch (error) {
            console.error('Failed to load expenses:', error);
        }
    }

    showExpenseModal() {
        this.loadExpenseCategories();
        document.getElementById('expenseModal').classList.remove('hidden');
        document.getElementById('expenseModal').classList.add('flex');
    }

    hideExpenseModal() {
        document.getElementById('expenseModal').classList.add('hidden');
        document.getElementById('expenseModal').classList.remove('flex');
        document.getElementById('expenseForm').reset();
    }

    async handleAddExpense(e) {
        e.preventDefault();
        
        const title = document.getElementById('expenseTitle').value;
        const amount = parseFloat(document.getElementById('expenseAmount').value);
        const description = document.getElementById('expenseDescription').value;
        const category = document.getElementById('expenseCategory').value;
        const splitWithText = document.getElementById('expenseSplitWith').value;

        // For demo purposes, split equally with specified users
        const splitWith = splitWithText ? splitWithText.split(',').map(id => parseInt(id.trim())) : [];
        const splitAmount = amount / (splitWith.length + 1); // +1 for current user

        const splits = [{ user_id: this.currentUser.id, amount: splitAmount }];
        splitWith.forEach(userId => {
            splits.push({ user_id: userId, amount: splitAmount });
        });

        try {
            await this.apiCall('/expenses', {
                method: 'POST',
                body: JSON.stringify({
                    title,
                    amount,
                    description,
                    category,
                    date: new Date().toISOString(),
                    splits
                })
            });

            this.showNotification('Expense added successfully!', 'success');
            this.hideExpenseModal();
            this.loadExpenses();
            this.loadDashboardData();
        } catch (error) {
            // Error already handled by apiCall
        }
    }

    // Groups
    async loadGroups() {
        try {
            const groups = await this.apiCall('/groups');
            const groupsList = document.getElementById('groupsList');
            groupsList.innerHTML = '';

            if (groups && groups.length > 0) {
                groups.forEach(group => {
                    const groupItem = document.createElement('div');
                    groupItem.className = 'bg-white shadow rounded-lg p-6';
                    groupItem.innerHTML = `
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-semibold">${group.name}</h3>
                            <div class="flex-shrink-0 bg-gray-100 rounded-full p-2">
                                <i class="fas fa-users text-gray-600"></i>
                            </div>
                        </div>
                        <p class="text-gray-600 mb-4">${group.description || 'No description'}</p>
                        <div class="flex items-center justify-between">
                            <div class="flex -space-x-2">
                                ${group.members.slice(0, 4).map(member => 
                                    `<div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium border-2 border-white">
                                        ${member.first_name[0]}${member.last_name[0]}
                                    </div>`
                                ).join('')}
                                ${group.members.length > 4 ? 
                                    `<div class="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-gray-600 text-sm font-medium border-2 border-white">
                                        +${group.members.length - 4}
                                    </div>` : ''}
                            </div>
                            <span class="text-sm text-gray-500">${group.members.length} members</span>
                        </div>
                    `;
                    groupsList.appendChild(groupItem);
                });
            } else {
                groupsList.innerHTML = '<p class="text-gray-500 text-center py-8">No groups to show</p>';
            }
        } catch (error) {
            console.error('Failed to load groups:', error);
        }
    }

    async handleAddGroup() {
        const name = prompt('Enter group name:');
        if (!name) return;

        const description = prompt('Enter group description (optional):') || '';

        try {
            await this.apiCall('/groups', {
                method: 'POST',
                body: JSON.stringify({ name, description })
            });

            this.showNotification('Group created successfully!', 'success');
            this.loadGroups();
        } catch (error) {
            // Error already handled by apiCall
        }
    }

    // Detailed Balances
    async loadDetailedBalances() {
        try {
            const balances = await this.apiCall('/balances');
            const balancesList = document.getElementById('balancesList');
            balancesList.innerHTML = '';

            if (balances.balances && balances.balances.length > 0) {
                balances.balances.forEach(balance => {
                    const balanceItem = document.createElement('div');
                    balanceItem.className = 'p-4 border-b last:border-b-0';
                    balanceItem.innerHTML = `
                        <div class="flex justify-between items-center">
                            <div>
                                <h4 class="font-semibold">User ${balance.user_id}</h4>
                                <p class="text-gray-600">user${balance.user_id}@example.com</p>
                            </div>
                            <div class="text-right">
                                <p class="text-xl font-bold ${balance.amount > 0 ? 'balance-positive' : 'balance-negative'}">
                                    ${balance.amount > 0 ? '+' : ''}$${Math.abs(balance.amount).toFixed(2)}
                                </p>
                                <p class="text-sm text-gray-500">
                                    ${balance.amount > 0 ? 'owes you' : 'you owe'}
                                </p>
                            </div>
                        </div>
                    `;
                    balancesList.appendChild(balanceItem);
                });
            } else {
                balancesList.innerHTML = '<p class="text-gray-500 text-center py-8">No balances to show</p>';
            }
        } catch (error) {
            console.error('Failed to load balances:', error);
        }
    }

    // UI Methods
    showLogin() {
        this.hideAllSections();
        document.getElementById('loginSection').classList.remove('hidden');
    }

    showRegister() {
        this.hideAllSections();
        document.getElementById('registerSection').classList.remove('hidden');
    }

    showDashboard() {
        this.hideAllSections();
        document.getElementById('dashboardSection').classList.remove('hidden');
        document.getElementById('dashboardBtn').classList.add('bg-blue-100', 'text-blue-700');
    }

    showExpenses() {
        this.hideAllSections();
        document.getElementById('expensesSection').classList.remove('hidden');
        document.getElementById('expensesBtn').classList.add('bg-blue-100', 'text-blue-700');
        this.loadExpenses();
    }

    showGroups() {
        this.hideAllSections();
        document.getElementById('groupsSection').classList.remove('hidden');
        document.getElementById('groupsBtn').classList.add('bg-blue-100', 'text-blue-700');
        this.loadGroups();
    }

    showBalances() {
        this.hideAllSections();
        document.getElementById('balancesSection').classList.remove('hidden');
        document.getElementById('balancesBtn').classList.add('bg-blue-100', 'text-blue-700');
        this.loadDetailedBalances();
    }

    hideAllSections() {
        const sections = ['loginSection', 'registerSection', 'dashboardSection', 'expensesSection', 'groupsSection', 'balancesSection'];
        sections.forEach(section => {
            document.getElementById(section).classList.add('hidden');
        });

        // Remove active state from all nav buttons
        const navButtons = ['dashboardBtn', 'expensesBtn', 'groupsBtn', 'balancesBtn'];
        navButtons.forEach(btn => {
            document.getElementById(btn).classList.remove('bg-blue-100', 'text-blue-700');
        });
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' : 
            type === 'error' ? 'bg-red-500 text-white' : 
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize the app
const app = new WealthWatchApp();
