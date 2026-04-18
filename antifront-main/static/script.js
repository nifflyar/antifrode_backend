// ============================================================================
// Authentication Check
// ============================================================================

// Check if user is logged in on page load
if (localStorage.getItem('isLoggedIn') !== 'true') {
    window.location.href = '/login.html';
}

// Update user display
const userEmail = localStorage.getItem('userEmail') || 'Unknown user';
const userDisplay = document.querySelector('.absolute.bottom-6');
if (userDisplay) {
    userDisplay.innerHTML = `
        <div class="bg-gray-50 rounded-xl p-3 text-xs text-gray-500">
            <i class="fas fa-user-circle mr-1"></i> Аналитик · ${userEmail}
            <div class="flex mt-1 space-x-3">
                <span class="cursor-pointer hover:text-red-600 logout-btn"><i class="fas fa-sign-out-alt"></i> Выйти</span>
            </div>
        </div>
    `;

    // Add logout handler
    document.querySelector('.logout-btn').addEventListener('click', async () => {
        try {
            // Call logout API endpoint
            await apiClient.post('/api/auth/logout', {});
        } catch (error) {
            console.warn("Logout API error (continuing with local logout):", error);
        } finally {
            // Clear localStorage
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('userEmail');
            localStorage.removeItem('authToken');

            // Clear all cookies more reliably
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i];
                const eqPos = cookie.indexOf('=');
                const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();

                // Delete from current path and root
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/';
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=' + document.domain;
            }

            console.log(' Cookies cleared');

            // Redirect to login
            window.location.href = '/login.html';
        }
    });
}

// Global state (data fetched from API)
let passengersData = [];
let passengersOffset = 0;
let passengersIsLoading = false;
let passengersHasMore = true;
let passengersCurrentFilter = "all";
let passengersCurrentSearch = "";
let operationsData = [];
let operationsOffset = 0;
let operationsIsLoading = false;
let operationsHasMore = true;
let riskConcentrationData = {};
let currentDateFrom = null;
let currentDateTo = null;

// Note: API_BASE_URL is already defined in apiClient.js

// Форматирование даты и времени
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('ru-RU');
    } catch {
        return dateStr;
    }
}

// Форматирование суммы
function formatAmount(amount) {
    if (!amount && amount !== 0) return '-';
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'KZT' }).format(amount);
}

// Получение цвета риска
function getRiskColor(riskBand) {
    const riskColors = {
        'critical': 'bg-red-100 text-red-800',
        'high': 'bg-orange-100 text-orange-800',
        'medium': 'bg-yellow-100 text-yellow-800',
        'low': 'bg-green-100 text-green-800'
    };
    return riskColors[riskBand?.toLowerCase()] || 'bg-gray-100 text-gray-800';
}

// Рендер таблицы пассажиров
function renderPassengersTable() {
    let filtered = passengersData;

    // Фильтр по риску
    if (passengersCurrentFilter !== "all") {
        filtered = filtered.filter(p => p.risk_band?.toLowerCase() === passengersCurrentFilter.toLowerCase());
    }

    // Фильтр по поиску (ID или ФИО)
    if (passengersCurrentSearch.trim()) {
        const searchLower = passengersCurrentSearch.toLowerCase();
        filtered = filtered.filter(p =>
            p.id.toString().includes(searchLower) ||
            (p.fio_clean && p.fio_clean.toLowerCase().includes(searchLower))
        );
    }

    let html = "";
    filtered.forEach(p => {
        const topReasons = (p.top_reasons || []).join(', ') || '-';
        const seatBlocking = p.seat_blocking_flag ? ' Да' : '-';

        html += `<tr class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-sm">${p.id}</td>
            <td class="px-4 py-3 font-bold">${(p.final_score || 0).toFixed(2)}</td>
            <td class="px-4 py-3">
                <span class="px-2 py-1 rounded-full text-xs font-bold ${getRiskColor(p.risk_band)}">
                    ${p.risk_band || 'N/A'}
                </span>
            </td>
            <td class="px-4 py-3 text-xs">${topReasons}</td>
            <td class="px-4 py-3 text-sm">${p.refund_cnt || 0}</td>
            <td class="px-4 py-3 text-sm">${p.max_tickets_month || 0}</td>
            <td class="px-4 py-3 text-sm">${seatBlocking}</td>
        </tr>`;
    });

    const tbody = document.getElementById("passengersTableBody");
    if (html) {
        tbody.innerHTML = html;
    } else {
        tbody.innerHTML = "<tr><td colspan='7' class='p-4 text-center text-gray-500'>Нет данных</td></tr>";
    }
}

// Рендер таблицы операций
function renderOperations() {
    let html = "";
    operationsData.forEach(op => {
        const opType = op.op_type === 'refund' ? 'Возврат' : op.op_type === 'sale' ? 'Продажа' : op.op_type;
        html += `<tr class="hover:bg-gray-50">
            <td class="p-3 text-sm">${formatDateTime(op.op_datetime)}</td>
            <td class="p-3 font-mono text-sm">${op.passenger_id}</td>
            <td class="p-3 text-sm">${op.train_no || '-'}</td>
            <td class="p-3 text-sm">${op.channel || '-'}</td>
            <td class="p-3 text-sm">${op.terminal || '-'}</td>
            <td class="p-3 text-sm">${op.cashdesk || '-'}</td>
            <td class="p-3 text-sm">${formatAmount(op.amount)}</td>
            <td class="p-3 text-sm ${op.op_type === 'refund' ? 'text-red-600 font-semibold' : ''}">${opType}</td>
        </tr>`;
    });
    document.getElementById("suspiciousOpsBody").innerHTML = html ||
        "<tr><td colspan='8' class='p-4 text-center text-gray-500'>Нет данных</td></tr>";
}

// ============================================================================
// API Data Loading Functions
// ============================================================================

/**
 * Load passengers from backend API with pagination
 */
async function loadPassengers(filterRisk = "all", search = "") {
    try {
        console.log(`Starting load passengers: filter=${filterRisk}, search="${search}"`);

        passengersCurrentFilter = filterRisk;
        passengersCurrentSearch = search;
        passengersOffset = 0;
        passengersData = [];
        passengersHasMore = true;

        document.getElementById("passengersTableBody").innerHTML =
            '<tr><td colspan="7" class="p-4 text-center text-gray-500">Загрузка...</td></tr>';

        await loadMorePassengers();

        // If no data was loaded, show empty state
        if (passengersData.length === 0) {
            renderPassengersTable();
        }
    } catch (error) {
        console.error("Failed to load passengers:", error);
        document.getElementById("passengersTableBody").innerHTML =
            '<tr><td colspan="7" class="p-4 text-center text-red-600">Ошибка загрузки</td></tr>';
    }
}

/**
 * Load more passengers (pagination)
 */
async function loadMorePassengers() {
    if (passengersIsLoading || !passengersHasMore) {
        console.log("Skipping load: isLoading=" + passengersIsLoading + ", hasMore=" + passengersHasMore);
        return;
    }

    try {
        passengersIsLoading = true;
        console.log(`Loading passengers: filter=${passengersCurrentFilter}, search="${passengersCurrentSearch}", offset=${passengersOffset}`);

        const response = await passengersApi.getList({
            riskBand: passengersCurrentFilter !== "all" ? passengersCurrentFilter.toLowerCase() : undefined,
            search: passengersCurrentSearch || undefined,
            limit: 50,
            offset: passengersOffset
        });

        const newPassengers = response.items || [];
        console.log(`Received ${newPassengers.length} passengers`);

        if (newPassengers.length === 0) {
            passengersHasMore = false;
            console.log("No more passengers to load");
        } else {
            passengersData = passengersData.concat(newPassengers);
            passengersOffset += newPassengers.length;
            renderPassengersTable();
            console.log(`Total passengers loaded: ${passengersData.length}`);
        }
    } catch (error) {
        console.error("Failed to load more passengers:", error);
        passengersHasMore = false; // Stop trying to load on error
    } finally {
        passengersIsLoading = false;
    }
}

/**
 * Load operations from backend API with pagination
 */
async function loadOperations() {
    try {
        console.log("Starting load operations");

        operationsOffset = 0;
        operationsData = [];
        operationsHasMore = true;

        document.getElementById("suspiciousOpsBody").innerHTML =
            '<tr><td colspan="8" class="p-4 text-center text-gray-500">Загрузка...</td></tr>';

        await loadMoreOperations();
    } catch (error) {
        console.error("Failed to load operations:", error);
        document.getElementById("suspiciousOpsBody").innerHTML =
            '<tr><td colspan="8" class="p-4 text-center text-red-600">Ошибка загрузки</td></tr>';
    }
}

/**
 * Load more operations (pagination)
 */
async function loadMoreOperations() {
    if (operationsIsLoading || !operationsHasMore) {
        console.log("Skipping load: isLoading=" + operationsIsLoading + ", hasMore=" + operationsHasMore);
        return;
    }

    try {
        operationsIsLoading = true;
        console.log(`Loading operations: offset=${operationsOffset}`);

        const response = await operationsApi.getList({
            limit: 50,
            offset: operationsOffset
        });

        const newOperations = response.items || [];
        console.log(`Received ${newOperations.length} operations`);

        if (newOperations.length === 0) {
            operationsHasMore = false;
            console.log("No more operations to load");

            // If no data at all, show empty state
            if (operationsData.length === 0) {
                renderOperations();
            }
        } else {
            operationsData = operationsData.concat(newOperations);
            operationsOffset += newOperations.length;
            renderOperations();
            console.log(`Total operations loaded: ${operationsData.length}`);
        }
    } catch (error) {
        console.error("Failed to load more operations:", error);
        operationsHasMore = false;
    } finally {
        operationsIsLoading = false;
    }
}

/**
 * Load dashboard metrics from backend API
 */
async function loadDashboardMetrics() {
    try {
        const filters = {};

        // ALWAYS include date filters
        if (currentDateFrom && currentDateTo) {
            filters.dateFrom = currentDateFrom;
            filters.dateTo = currentDateTo;
            console.log(" Loading dashboard with date filter:", {
                from: currentDateFrom.split('T')[0],
                to: currentDateTo.split('T')[0]
            });
        } else {
            console.warn(" No date filters available, loading all data");
        }

        dashboardData = await dashboardApi.getSummary(filters);
        console.log(" Dashboard data loaded:", dashboardData);

        // Update KPI cards with real data
        document.getElementById('stat-total-passengers').textContent = dashboardData.total_passengers?.toLocaleString() || '—';
        document.getElementById('stat-high-risk').textContent = dashboardData.high_risk_count || '—';
        document.getElementById('stat-critical-risk').textContent = dashboardData.critical_risk_count || '—';
        document.getElementById('stat-suspicious-ops').textContent = (dashboardData.share_suspicious_ops?.toFixed(1) || '—') + '%';
        document.getElementById('stat-top-channel').textContent = dashboardData.top_risk_channel || '—';
        document.getElementById('stat-top-terminal').textContent = dashboardData.top_risk_terminal || '—';

        // Load charts with new data
        await loadCharts();

        return dashboardData;
    } catch (error) {
        console.error("Failed to load dashboard metrics:", error);
    }
}

/**
 * Load risk concentration data
 */
async function loadRiskConcentration() {
    try {
        const filters = {};
        if (currentDateFrom && currentDateTo) {
            filters.dateFrom = currentDateFrom;
            filters.dateTo = currentDateTo;
            console.log(" Loading risk concentration with date filter:", {
                from: currentDateFrom.split('T')[0],
                to: currentDateTo.split('T')[0]
            });
        } else {
            console.warn(" No date filters for risk concentration");
        }

        const [channels, terminals, cashdesks, aggregators] = await Promise.all([
            dashboardApi.getRiskConcentration("CHANNEL", filters),
            dashboardApi.getRiskConcentration("TERMINAL", filters),
            dashboardApi.getRiskConcentration("CASHDESK", filters),
            dashboardApi.getRiskConcentration("AGGREGATOR", filters)
        ]);

        riskConcentrationData = {
            channels: channels.items || [],
            terminals: terminals.items || [],
            cashdesks: cashdesks.items || [],
            aggregators: aggregators.items || []
        };

        console.log(" Risk concentration loaded");
        renderRiskConcentration();
    } catch (error) {
        console.error("Failed to load risk concentration:", error);
    }
}

/**
 * Load and display first high-risk passenger profile
 */
async function loadPassengerProfile() {
    try {
        const profileCard = document.getElementById('passengerProfileCard');

        // Try to find first critical risk passenger
        let passenger = null;
        let passengers = await passengersApi.getList({ riskBand: 'critical', limit: 1 });

        if (!passengers.items || passengers.items.length === 0) {
            // If no critical, try high risk
            passengers = await passengersApi.getList({ riskBand: 'high', limit: 1 });
        }

        if (!passengers.items || passengers.items.length === 0) {
            profileCard.innerHTML = '<p class="text-center text-gray-500 py-8">Нет пассажиров с риском для отображения</p>';
            return;
        }

        passenger = passengers.items[0];
        const passengerId = passenger.id; // Keep as string

        // Get full profile (transactions are optional)
        const profile = await passengersApi.getProfile(passengerId);

        let transactions = [];
        try {
            transactions = await passengersApi.getTransactions(passengerId, { limit: 5 });
        } catch (error) {
            console.warn("Could not load transactions:", error);
        }

        const riskColor = profile.score.risk_band === 'critical' ? 'red' : 'orange';

        const transactionRows = (transactions || [])
            .slice(0, 5)
            .map(tx => `<tr>
                <td class="border px-3 py-2">${new Date(tx.op_datetime).toLocaleString('ru-RU').split(',')[0]}</td>
                <td class="border px-3 py-2 ${tx.op_type === 'refund' ? 'text-red-600' : ''}">${tx.op_type === 'refund' ? 'Возврат' : 'Продажа'}</td>
                <td class="border px-3 py-2">${tx.train_no || '—'}</td>
                <td class="border px-3 py-2">${tx.amount || 0} KZT</td>
            </tr>`)
            .join('');

        const topReasons = (profile.score.top_reasons || []).join(', ') || '—';

        const transactionsSection = transactions && transactions.length > 0 ? `
            <div class="mt-6">
                <h4 class="font-semibold">Timeline операций (последние 5)</h4>
                <table class="min-w-full text-sm mt-2 border">
                    <tr class="bg-gray-50">
                        <th class="border px-3 py-2">Дата</th>
                        <th class="border px-3 py-2">Тип</th>
                        <th class="border px-3 py-2">Поезд</th>
                        <th class="border px-3 py-2">Сумма</th>
                    </tr>
                    ${transactionRows}
                </table>
            </div>
        ` : '';

        profileCard.innerHTML = `
            <div class="flex justify-between items-start border-b pb-4">
                <div>
                    <h2 class="text-2xl font-bold">Пассажир: ${profile.id}</h2>
                    <p class="text-gray-500">ФИО: ${profile.fio_clean || '—'}</p>
                </div>
                <div class="bg-${riskColor}-100 text-${riskColor}-800 px-4 py-1 rounded-full font-bold text-lg">
                    Risk: ${profile.score.risk_band.toUpperCase()} (${Math.round(profile.score.final_score)}/100)
                </div>
            </div>
            <div class="grid md:grid-cols-2 gap-5 mt-5">
                <div>
                    <p>
                        <i class="fas fa-flag-checkered"></i>
                        <strong>Топ причины:</strong> ${topReasons}
                    </p>
                    <p>
                        <i class="fas fa-ticket-alt"></i>
                        <strong>Билетов всего:</strong> ${profile.features.total_tickets || 0} |
                        Возвратов: ${profile.features.refund_cnt || 0} |
                        Доля возвратов: ${(profile.features.refund_share * 100 || 0).toFixed(0)}%
                    </p>
                    <p>
                        <i class="fas fa-calendar-week"></i>
                        <strong>Max билетов за месяц:</strong> ${profile.features.max_tickets_month || 0}
                    </p>
                </div>
                <div>
                    <p>
                        <i class="fas fa-train"></i>
                        <strong>Первый визит:</strong> ${new Date(profile.first_seen_at).toLocaleDateString('ru-RU')}
                    </p>
                    <p>
                        <i class="fas fa-clock"></i>
                        <strong>Последний визит:</strong> ${new Date(profile.last_seen_at).toLocaleDateString('ru-RU')}
                    </p>
                    <p>
                        <i class="fas fa-shield"></i>
                        <strong>Риск:</strong> ${profile.score.risk_band.toUpperCase()}
                    </p>
                </div>
            </div>
            ${transactionsSection}
        `;

        console.log(" Passenger profile loaded:", passenger.id);
    } catch (error) {
        console.error("Failed to load passenger profile:", error);
        document.getElementById('passengerProfileCard').innerHTML =
            '<p class="text-center text-gray-500 py-8">Нет доступных профилей пассажиров</p>';
    }
}

// ============================================================================

function renderRiskConcentration() {
    let chHtml = "<table class='w-full text-sm'><tr class='bg-gray-100'><th>Канал</th><th>Всего опер.</th><th>High-risk</th><th>% High-risk</th><th>Lift</th></tr>";
    (riskConcentrationData.channels || []).forEach(c => { chHtml += `<tr><td class='p-2'>${c.dimension_value}</td><td>${c.total_ops}</td><td class='text-red-600'>${c.highrisk_ops}</td><td>${(c.share_highrisk_ops * 100).toFixed(1)}%</td><td>${c.lift_vs_base.toFixed(2)}</td></tr>`; });
    chHtml += "</table>"; document.getElementById("channelConcentrationTable").innerHTML = chHtml;

    let termHtml = "<table class='w-full text-sm'><tr class='bg-gray-100'><th>Терминал</th><th>Всего</th><th>High-risk</th><th>% High-risk</th><th>Lift</th></tr>";
    (riskConcentrationData.terminals || []).forEach(t => { termHtml += `<tr><td>${t.dimension_value}</td><td>${t.total_ops}</td><td class='text-red-600'>${t.highrisk_ops}</td><td>${(t.share_highrisk_ops * 100).toFixed(1)}%</td><td>${t.lift_vs_base.toFixed(2)}</td></tr>`; });
    document.getElementById("terminalRiskTable").innerHTML = termHtml;

    let cashHtml = "<table class='w-full text-sm'><tr class='bg-gray-100'><th>Касса</th><th>Операций</th><th>Рисковых</th><th>% риска</th><th>Lift</th></tr>";
    (riskConcentrationData.cashdesks || []).forEach(c => { cashHtml += `<tr><td>${c.dimension_value}</td><td>${c.total_ops}</td><td class='text-red-600'>${c.highrisk_ops}</td><td>${(c.share_highrisk_ops * 100).toFixed(1)}%</td><td>${c.lift_vs_base.toFixed(2)}</td></tr>`; });
    document.getElementById("cashdeskRiskTable").innerHTML = cashHtml;

    let aggHtml = "<table class='w-full text-sm'><tr class='bg-gray-100'><th>Агрегатор</th><th>Опер.</th><th>Риск</th><th>% риска</th><th>Lift</th></tr>";
    (riskConcentrationData.aggregators || []).forEach(a => { aggHtml += `<tr><td>${a.dimension_value}</td><td>${a.total_ops}</td><td class='text-red-600'>${a.highrisk_ops}</td><td>${(a.share_highrisk_ops * 100).toFixed(1)}%</td><td>${a.lift_vs_base.toFixed(2)}</td></tr>`; });
    document.getElementById("aggregatorTable").innerHTML = aggHtml;
}

// Инициализация графиков с реальными данными
let riskTrend, riskChannelChart, liftTerminalChart;

async function loadCharts() {
    try {
        // Fetch real data from API with date filters
        const filters = {
            dateFrom: currentDateFrom,
            dateTo: currentDateTo
        };

        console.log(" Loading charts with date filter:", {
            from: currentDateFrom?.split('T')[0],
            to: currentDateTo?.split('T')[0]
        });

        const [riskTrendData, channelData, terminalData] = await Promise.all([
            dashboardApi.getRiskTrend(filters),
            dashboardApi.getRiskConcentration("CHANNEL", filters),
            dashboardApi.getRiskConcentration("TERMINAL", filters)
        ]);

        // Process risk trend data
        const trendLabels = (riskTrendData.items || []).map(item => {
            const date = new Date(item.date);
            return `${date.getDate()}.${date.getMonth() + 1}`;
        });
        const trendData = (riskTrendData.items || []).map(item => item.highrisk_ops || 0);

        // Process channel data
        const channelLabels = (channelData.items || []).map(item => item.dimension_value);
        const channelValues = (channelData.items || []).map(item => parseFloat((item.share_highrisk_ops * 100).toFixed(1)));

        // Process terminal data
        const terminalLabels = (terminalData.items || []).map(item => item.dimension_value);
        const terminalValues = (terminalData.items || []).map(item => item.lift_vs_base || 0);

        // Initialize charts with real data
        if (riskTrend) riskTrend.destroy();
        if (riskChannelChart) riskChannelChart.destroy();
        if (liftTerminalChart) liftTerminalChart.destroy();

        const ctx1 = document.getElementById('riskTrendChart').getContext('2d');
        riskTrend = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: trendLabels.length > 0 ? trendLabels : ['—'],
                datasets: [{
                    label: 'Кол-во риск-операций',
                    data: trendData.length > 0 ? trendData : [0],
                    borderColor: '#f97316',
                    tension: 0.3,
                    fill: false
                }]
            }
        });

        const ctx2 = document.getElementById('riskChannelChart').getContext('2d');
        riskChannelChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: channelLabels.length > 0 ? channelLabels : ['—'],
                datasets: [{
                    label: 'Доля риск-операций, %',
                    data: channelValues.length > 0 ? channelValues : [0],
                    backgroundColor: '#3b82f6'
                }]
            }
        });

        const ctx3 = document.getElementById('liftTerminalChart').getContext('2d');
        liftTerminalChart = new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: terminalLabels.length > 0 ? terminalLabels : ['—'],
                datasets: [{
                    label: 'Risk Lift (vs средний)',
                    data: terminalValues.length > 0 ? terminalValues : [0],
                    backgroundColor: '#ef4444'
                }]
            }
        });

        console.log(" Charts loaded with real data");
    } catch (error) {
        console.error("Failed to load charts:", error);
    }
}

// Переключение вкладок
const tabs = document.querySelectorAll('.sidebar-item');
const contents = document.querySelectorAll('.tab-content');
const pageTitleElem = document.getElementById('pageTitle');
const titlesMap = { dashboard: "Дашборд аналитики", passengers: "Подозрительные пассажиры", operations: "Подозрительные операции", riskmap: "Risk-концентрация", profile: "Карточка пассажира", upload: "Загрузка данных", reports: "Отчёты и экспорт" };

tabs.forEach(tab => {
    tab.addEventListener('click', async () => {
        const target = tab.getAttribute('data-tab');
        contents.forEach(c => c.classList.remove('active-tab'));
        document.getElementById(target).classList.add('active-tab');
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        pageTitleElem.innerText = titlesMap[target] || "Аналитика";

        // Load data for this tab
        try {
            if (target === 'riskmap') {
                await loadRiskConcentration();
                renderRiskConcentration();
            } else if (target === 'passengers') {
                await loadPassengers();
                // Re-setup scroll handler for new tab
                setTimeout(() => setupPassengersScrollHandler(), 100);
            } else if (target === 'operations') {
                await loadOperations();
                // Re-setup scroll handler for new tab
                setTimeout(() => setupOperationsScrollHandler(), 100);
            } else if (target === 'profile') {
                await loadPassengerProfile();
            } else if (target === 'upload') {
                await loadRecentUploads();
            } else if (target === 'dashboard') {
                await loadDashboardMetrics();
            }
        } catch (error) {
            console.error(`Error loading ${target}:`, error);
        }
    });
});

// Фильтры таблицы пассажиров
document.getElementById('riskFilter').addEventListener('change', () => {
    const riskFilter = document.getElementById('riskFilter').value;
    const search = document.getElementById('passengersSearch').value;
    loadPassengers(riskFilter, search);
});

document.getElementById('channelFilter').addEventListener('change', () => {
    // Channel filter can be used for operations filtering if needed
    // For now, we'll reload all passengers
    const riskFilter = document.getElementById('riskFilter').value;
    const search = document.getElementById('passengersSearch').value;
    loadPassengers(riskFilter, search);
});

// Обработчик скролла для бесконечной загрузки пассажиров
function setupPassengersScrollHandler() {
    const container = document.querySelector('#passengers .overflow-y-auto');
    if (!container) return;

    let scrollTimeout;
    container.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            // Если прокрутка почти в конце - загружаем ещё
            if (!passengersIsLoading && passengersHasMore &&
                container.scrollHeight - container.scrollTop - container.clientHeight < 100) {
                console.log("Scroll detected, loading more passengers...");
                loadMorePassengers();
            }
        }, 200); // Debounce 200ms
    }, { passive: true });
}

// Setup scroll handler for operations
function setupOperationsScrollHandler() {
    const container = document.querySelector('#operations .overflow-y-auto');
    if (!container) {
        console.warn(" Operations scroll container not found");
        return;
    }

    console.log(" Operations scroll handler attached to:", container);

    let scrollTimeout;
    container.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            const scrollPercentage = (container.scrollTop + container.clientHeight) / container.scrollHeight * 100;

            // Если прокрутка больше чем на 80% - загружаем ещё
            if (!operationsIsLoading && operationsHasMore && scrollPercentage > 80) {
                console.log(` Scroll detected (${scrollPercentage.toFixed(0)}%), loading more operations...`);
                loadMoreOperations();
            }
        }, 200); // Debounce 200ms
    }, { passive: true });
}

// Поиск по ID или ФИО
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log(" Starting app initialization...");

        // STEP 1: Initialize date range FIRST (restore from localStorage or use defaults)
        console.log(" Step 1: Initializing date range...");
        initializeDateRange();

        // STEP 2: Setup search handler
        console.log(" Step 2: Setting up search handler...");
        const searchInput = document.getElementById('passengersSearch');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                const search = e.target.value.trim();

                // Минимум 1 символ для поиска
                if (search.length === 0) {
                    // Очистить поиск
                    loadPassengers(document.getElementById('riskFilter').value, '');
                    return;
                }

                if (search.length < 1) {
                    return; // Не начинать поиск с одного символа
                }

                searchTimeout = setTimeout(() => {
                    console.log(`Search triggered: "${search}"`);
                    const riskFilter = document.getElementById('riskFilter').value;
                    loadPassengers(riskFilter, search);
                }, 500); // Debounce 500ms
            });
        }

        // STEP 3: Setup scroll handlers
        console.log(" Step 3: Setting up scroll handlers...");
        setupPassengersScrollHandler();
        setupOperationsScrollHandler();

        // STEP 4: Load all data from API with initialized dates
        console.log(" Step 4: Loading data from backend...");
        console.log(" Using dates:", {
            from: currentDateFrom?.split('T')[0] || 'NOT SET',
            to: currentDateTo?.split('T')[0] || 'NOT SET'
        });

        await Promise.all([
            loadDashboardMetrics(),
            loadPassengers(),
            loadOperations(),
            loadPassengerProfile(),
            loadRecentUploads()
        ]);

        // STEP 5: Set default active tab
        console.log(" Step 5: Setting active tab...");
        document.querySelector('.sidebar-item[data-tab="dashboard"]')?.classList.add('active');

        console.log(" App initialized successfully!");

    } catch (error) {
        console.error(" Initialization error:", error);
        alert("Failed to initialize app: " + error.message);
    }
});

// ============================================================================
// DATE RANGE MANAGEMENT
// ============================================================================

/**
 * Initialize or restore date range with guaranteed data load
 */
function initializeDateRange() {
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');

    if (!dateFromInput || !dateToInput) {
        console.error(" Date inputs not found - cannot initialize date range");
        // Set defaults even if inputs not found
        const today = new Date();
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        currentDateFrom = weekAgo.toISOString();
        currentDateTo = today.toISOString();
        return false;
    }

    // Try to restore saved dates from localStorage
    let savedDateFrom = localStorage.getItem('dateFrom');
    let savedDateTo = localStorage.getItem('dateTo');

    let dateFrom, dateTo;

    if (savedDateFrom && savedDateTo) {
        try {
            dateFrom = new Date(savedDateFrom);
            dateTo = new Date(savedDateTo);

            // Validate restored dates
            if (!isNaN(dateFrom.getTime()) && !isNaN(dateTo.getTime())) {
                console.log(" Restored dates from localStorage:", {
                    from: dateFrom.toISOString().split('T')[0],
                    to: dateTo.toISOString().split('T')[0]
                });
            } else {
                throw new Error("Invalid dates");
            }
        } catch (e) {
            console.warn(" Invalid saved dates in localStorage, using defaults:", e.message);
            savedDateFrom = null;
            savedDateTo = null;
        }
    }

    // Use defaults if no valid saved dates
    if (!savedDateFrom || !savedDateTo) {
        dateTo = new Date();
        dateTo.setHours(23, 59, 59, 999); // End of today
        dateFrom = new Date(dateTo.getTime() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
        dateFrom.setHours(0, 0, 0, 0); // Start of day
        console.log(" Using default dates (last 7 days)");
    }

    // Format for input elements (YYYY-MM-DD)
    const fromDateStr = dateFrom.toISOString().split('T')[0];
    const toDateStr = dateTo.toISOString().split('T')[0];

    // Set input values
    dateFromInput.value = fromDateStr;
    dateToInput.value = toDateStr;

    // Set constraints
    dateFromInput.max = toDateStr;
    dateToInput.min = fromDateStr;

    // Store ISO strings for API calls - use UTC midnight for precision
    const fromDateUTC = new Date(fromDateStr + 'T00:00:00Z');
    const toDateUTC = new Date(toDateStr + 'T23:59:59.999Z');
    currentDateFrom = fromDateUTC.toISOString();
    currentDateTo = toDateUTC.toISOString();

    console.log(" Date range initialized:", {
        display: { from: fromDateStr, to: toDateStr },
        api: { from: currentDateFrom, to: currentDateTo }
    });

    return true;
}

/**
 * Validate and normalize date range
 */
function validateDateRange() {
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');

    if (!dateFromInput.value || !dateToInput.value) {
        return false;
    }

    const dateFrom = new Date(dateFromInput.value);
    const dateTo = new Date(dateToInput.value);

    if (dateFrom > dateTo) {
        console.warn("Invalid date range: from > to, swapping");
        dateFromInput.value = dateToInput.value;
        return false;
    }

    return true;
}

/**
 * Update max/min date constraints in real-time
 */
function updateDateConstraints() {
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');

    if (dateFromInput.value) {
        dateToInput.min = dateFromInput.value;
    }

    if (dateToInput.value) {
        dateFromInput.max = dateToInput.value;
    }
}

// Date input change handlers with real-time validation
document.getElementById('dateFrom')?.addEventListener('change', () => {
    updateDateConstraints();
    if (!validateDateRange()) {
        updateDateConstraints();
    }
});

document.getElementById('dateTo')?.addEventListener('change', () => {
    updateDateConstraints();
    if (!validateDateRange()) {
        updateDateConstraints();
    }
});

// Also update constraints on input (while typing)
document.getElementById('dateFrom')?.addEventListener('input', updateDateConstraints);
document.getElementById('dateTo')?.addEventListener('input', updateDateConstraints);

// Date range filter application
document.getElementById('applyDateFilter')?.addEventListener('click', async () => {
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');

    if (!dateFromInput.value || !dateToInput.value) {
        alert(' Выберите обе даты');
        return;
    }

    if (!validateDateRange()) {
        alert(' Ошибка: Дата начала не может быть позже даты конца');
        return;
    }

    const dateFrom = new Date(dateFromInput.value);
    const dateTo = new Date(dateToInput.value);

    // Set proper time boundaries: start of day for 'from', end of day for 'to'
    const fromDateUTC = new Date(dateFromInput.value + 'T00:00:00Z');
    const toDateUTC = new Date(dateToInput.value + 'T23:59:59.999Z');

    currentDateFrom = fromDateUTC.toISOString();
    currentDateTo = toDateUTC.toISOString();

    // Save to localStorage for persistence
    localStorage.setItem('dateFrom', currentDateFrom);
    localStorage.setItem('dateTo', currentDateTo);

    console.log(" Applying date filter:", {
        from: dateFromInput.value,
        to: dateToInput.value
    });

    // Reload all dashboard data with new dates
    const btn = document.getElementById('applyDateFilter');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Применяю...';

    try {
        await Promise.all([
            loadDashboardMetrics(),
            loadCharts(),
            loadRiskConcentration()
        ]);
        alert(' Фильтр по датам применен');
    } catch (error) {
        console.error("Error applying date filter:", error);
        alert(' Ошибка при применении фильтра');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Risk recalculation button
document.getElementById('riskRecalcBtn').addEventListener('click', async () => {
    const btn = document.getElementById('riskRecalcBtn');
    const originalHtml = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Пересчёт...';

        // Call risk recalculation API
        const response = await apiClient.post('/api/scoring/recalculate', {});

        alert(' Пересчёт рисков запущен. Данные обновятся через несколько секунд.');

        // Reload all data after 2 seconds
        setTimeout(async () => {
            await Promise.all([
                loadDashboardMetrics(),
                loadPassengers(),
                loadOperations(),
                loadRiskConcentration(),
            ]);
        }, 2000);
    } catch (error) {
        console.error("Risk recalculation error:", error);
        alert(` Ошибка при пересчёте: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// Upload button and file handling
async function loadRecentUploads() {
    try {
        const uploads = await uploadsApi.listUploads({ limit: 5 });
        const uploadsContainer = document.getElementById('recentUploads');

        if (!uploads.items || uploads.items.length === 0) {
            uploadsContainer.innerHTML = '<li class="text-gray-400">Нет загруженных файлов</li>';
            return;
        }

        uploadsContainer.innerHTML = uploads.items
            .map(upload => {
                const date = new Date(upload.uploaded_at).toLocaleDateString('ru-RU');
                const status = {
                    'PENDING': ' На очереди',
                    'PROCESSING': ' Обработка',
                    'COMPLETED': ' Завершено',
                    'FAILED': ' Ошибка'
                }[upload.status] || upload.status;

                return `<li>${date} - ${upload.filename} (${status})</li>`;
            })
            .join('');
    } catch (error) {
        console.error("Failed to load recent uploads:", error);
    }
}

// Real file upload handler
const fileInput = document.getElementById('excelInput');

document.getElementById('uploadBtn').addEventListener('click', async () => {
    fileInput.click();
});

document.getElementById('excelInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx')) {
        alert('Пожалуйста, выберите файл .xlsx');
        return;
    }

    const uploadBtn = document.getElementById('uploadBtn');
    const originalText = uploadBtn.innerHTML;

    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';

        // Upload file
        const uploadResponse = await uploadsApi.uploadExcel(file);
        const uploadId = uploadResponse.id;

        uploadBtn.innerHTML = '<i class="fas fa-cog fa-spin"></i> Обработка...';

        // Poll for completion
        let isComplete = false;
        let attempts = 0;
        const maxAttempts = 120; // 2 minutes max

        while (!isComplete && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            const status = await uploadsApi.getUploadStatus(uploadId);

            if (status.status === 'COMPLETED') {
                isComplete = true;
                alert(` Файл успешно обработан: ${file.name}`);

                // Refresh all data
                await Promise.all([
                    loadDashboardMetrics(),
                    loadPassengers(),
                    loadOperations(),
                    loadRiskConcentration(),
                    loadRecentUploads()
                ]);
            } else if (status.status === 'FAILED') {
                throw new Error(`Обработка файла не удалась: ${status.error_message || 'неизвестная ошибка'}`);
            }

            attempts++;
        }

        if (!isComplete) {
            throw new Error('Время ожидания обработки файла истекло');
        }
    } catch (error) {
        console.error("Upload error:", error);
        alert(` Ошибка загрузки: ${error.message}`);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalText;
        fileInput.value = ''; // Reset file input
    }
});

// Add drag and drop support
const uploadContainer = document.querySelector('[id="upload"] .border-dashed');
if (uploadContainer) {
    uploadContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadContainer.style.backgroundColor = '#f3f4f6';
    });

    uploadContainer.addEventListener('dragleave', () => {
        uploadContainer.style.backgroundColor = '';
    });

    uploadContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadContainer.style.backgroundColor = '';
        const file = e.dataTransfer.files[0];
        if (file) {
            const fileInput = document.getElementById('excelInput');
            fileInput.files = e.dataTransfer.files;
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    });
}

// ============================================================================
// REPORTS EXPORT HANDLERS
// ============================================================================

/**
 * Helper function to download file from response
 */
async function downloadFileFromResponse(response, filename) {
    if (!response.ok) {
        const errorText = await response.text();
        console.error(`API Error ${response.status}:`, errorText);
        throw new Error(`HTTP ${response.status}: ${errorText || 'Unknown error'}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();

    // Cleanup
    setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(link);
    }, 100);
}

// Export risk list as Excel (suspicious operations)
document.getElementById('exportRiskListExcelBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('exportRiskListExcelBtn');
    const originalHtml = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Загрузка...';

        console.log(" Exporting risk list from:", API_BASE_URL + '/api/reports/operations/suspicious/excel');

        const response = await fetch(`${API_BASE_URL}/api/reports/operations/suspicious/excel`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        });

        await downloadFileFromResponse(
            response,
            `risk_list_${new Date().toISOString().split('T')[0]}.xlsx`
        );

        alert(' Список рисков успешно выгружен');
    } catch (error) {
        console.error(" Export risk list error:", error);
        alert(` Ошибка при выгрузке: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// Generate DOCX investigation report (currently exports as Excel)
document.getElementById('generateDocxReportBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('generateDocxReportBtn');
    const originalHtml = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Генерирую...';

        console.log(" Exporting investigation report from:", API_BASE_URL + '/api/reports/risk-concentration/excel');

        const response = await fetch(`${API_BASE_URL}/api/reports/risk-concentration/excel`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        });

        await downloadFileFromResponse(
            response,
            `investigation_report_${new Date().toISOString().split('T')[0]}.xlsx`
        );

        alert(' Отчёт расследования успешно сформирован');
    } catch (error) {
        console.error(" Generate investigation report error:", error);
        alert(` Ошибка при формировании отчёта: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// Export suspicious passengers as PDF
document.getElementById('exportPassengerPdfBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('exportPassengerPdfBtn');
    const originalHtml = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Генерирую...';

        // Get first critical risk passenger if available
        let passengerId = null;

        if (passengersData && passengersData.length > 0) {
            // Find first critical risk passenger
            const criticalPassenger = passengersData.find(p => p.risk_band?.toLowerCase() === 'critical');
            passengerId = criticalPassenger?.id || passengersData[0].id;
        } else {
            // Try to fetch critical passengers if not loaded
            try {
                const response = await passengersApi.getList({ riskBand: 'critical', limit: 1 });
                if (response.items && response.items.length > 0) {
                    passengerId = response.items[0].id;
                }
            } catch (e) {
                console.warn("Could not fetch critical passengers:", e);
            }
        }

        if (!passengerId) {
            alert(' Нет подозрительных пассажиров для экспорта');
            return;
        }

        console.log(" Exporting passenger PDF for ID:", passengerId, "from:", API_BASE_URL + `/api/reports/passengers/${passengerId}/pdf`);

        const response = await fetch(`${API_BASE_URL}/api/reports/passengers/${passengerId}/pdf`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/pdf'
            }
        });

        await downloadFileFromResponse(
            response,
            `passenger_${passengerId}_dossier_${new Date().toISOString().split('T')[0]}.pdf`
        );

        alert(' PDF карточка подозреваемого успешно экспортирована');
    } catch (error) {
        console.error(" Export passenger PDF error:", error);
        alert(` Ошибка при экспорте PDF: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

// App initialization
