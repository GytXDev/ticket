// static\src\js\dashboard.js
/** @odoo-module **/
import { registry } from '@web/core/registry';
import { Component, onMounted, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class Dashboard extends Component {
    static template = 'owl.Dashboard';

    setup() {
        this.action = useService("action");
        this.state = useState({
            totalTickets: 0,
            // Ajoutez d'autres états si nécessaire
        });
        this.lastBestDate = null;

        onMounted(async () => {
            // Chargement initial
            await this.loadTicketStats();

            // Rendu initial des composants
            await this._renderNumber();
            await this._emergencyCounts();
            await this._renderTickets();
            await this._renderChart();
            await this._renderAgents();
            this._eventListeners();

            // Mise à jour périodique des données
            setInterval(() => {
                this.updateDashboardData();
            }, 10000);
        });
    }

    async loadTicketStats() {
        try {
            const stats = await rpc('/api/tickets/stats', {});
            this.state.totalTickets = stats.unresolved_count;
        } catch (error) {
            console.error("Erreur lors de la récupération des statistiques :", error);
        }
    }

    async updateDashboardData() {
        try {
            const lastUpdate = await rpc('/api/tickets/last_update', {});
            if (!this.lastBestDate || lastUpdate !== this.lastBestDate) {
                // Il y a une mise à jour, rafraîchir les données
                await this._renderTickets();
                await this._renderChart();
                await this._renderNumber();
                await this._renderAgents();
                this.lastBestDate = lastUpdate;
            }
        } catch (error) {
            console.error("Erreur lors de la mise à jour des données :", error);
        }
    }


    _eventListeners() {
        // Style switcher
        document.querySelectorAll('.style-switcher-toggler').forEach(el => {
            el.addEventListener('click', () => {
                const styleSwitcher = document.querySelector('.style-switcher');
                if (styleSwitcher) {
                    styleSwitcher.classList.toggle('open');
                }
            });
        });

        // Sélecteur de période
        const chartSelection = document.querySelector('#chart-selection');
        if (chartSelection) {
            chartSelection.addEventListener('change', () => {
                this._renderChart();
                this._renderTickets();
                this._emergencyCounts();
            });
        }

        // Cartes principales des tickets
        document.querySelectorAll('.card').forEach(el => {
            el.addEventListener('click', (event) => {
                const state = el.dataset.state;
                console.log("Card clicked:", state);
                if (state) {
                    this._redirectToState(state);
                }
            });
        });


        // Cartes des urgences
        document.querySelectorAll('.card-one').forEach(el => {
            el.addEventListener('click', (event) => {
                const state = el.dataset.state;
                if (state) {
                    this._redirectToEmergencyList(state);
                }
            });
        });

        // Graphiques
        const pieChartCanvas = document.querySelector('#pie-chart');
        if (pieChartCanvas) {
            pieChartCanvas.addEventListener('click', (event) => {
                const elements = this.pieChart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true);
                if (elements.length > 0) {
                    const clickedIndex = elements[0].index;
                    const label = this.pieChart.data.labels[clickedIndex];
                    this._redirectToTicketList(label === 'Résolu' ? 'résolu' : 'non-résolu');
                }
            });
        }

        const lineChartCanvas = document.querySelector('#line-chart');
        if (lineChartCanvas) {
            lineChartCanvas.addEventListener('click', (event) => {
                const elements = this.lineChart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true);
                if (elements.length > 0) {
                    const clickedIndex = elements[0].index;
                    const step = this.lineChart.data.labels[clickedIndex];
                    this._redirectToStepList(step);
                }
            });
        }
    }


    async _emergencyCounts() {
        console.log("Starting _emergencyCounts...");

        const chartSelectionElem = document.querySelector('#chart-selection');
        const selectedOption = chartSelectionElem ? chartSelectionElem.value : 'all';
        console.log("Selected period for emergencies:", selectedOption);

        let endpoint = '/api/tickets/emergency'; // Default endpoint

        if (selectedOption === 'today') {
            endpoint = '/api/tickets/emergency/day';
        } else if (selectedOption === 'month') {
            endpoint = '/api/tickets/emergency/month';
        } else if (selectedOption === 'week') {
            endpoint = '/api/tickets/emergency/week';
        } else if (selectedOption === 'years') {
            endpoint = '/api/tickets/emergency/years';
        }

        console.log("Fetching emergency counts from endpoint:", endpoint);

        try {
            const result = await rpc(endpoint, {});
            console.log("Emergency counts fetched successfully:", result);

            // Updating UI
            const moyenElem = document.querySelector('.ticket_count_moyen');
            const urgentElem = document.querySelector('.ticket_count_urgent');
            const tresUrgentElem = document.querySelector('.ticket_count_tres_urgent');

            if (moyenElem) {
                moyenElem.textContent = result.moyen || 0;
                console.log("Updated moyen count:", result.moyen || 0);
            }
            if (urgentElem) {
                urgentElem.textContent = result.urgent || 0;
                console.log("Updated urgent count:", result.urgent || 0);
            }
            if (tresUrgentElem) {
                tresUrgentElem.textContent = result['très urgent'] || 0;
                console.log("Updated très urgent count:", result['très urgent'] || 0);
            }
        } catch (error) {
            console.error("Error while fetching emergency counts:", error);
        }
    }


    async _renderNumber() {
        try {
            const result = await rpc('/api/tickets/stats', {});
            const ticketCounts = result.ticket_counts;
            const totalTickets = ticketCounts.reduce((a, b) => a + b, 0);
            const ticketCountElem = document.querySelector('.ticket_count');
            if (ticketCountElem) ticketCountElem.textContent = totalTickets;
        } catch (error) {
            console.error("Erreur lors de la récupération des nombres :", error);
        }
    }

    async _renderTickets() {
        const chartSelectionElem = document.querySelector('#chart-selection');
        const selectedOption = chartSelectionElem ? chartSelectionElem.value : 'all';
        let endpoint = '/api/tickets/count/state';

        if (selectedOption === 'today') {
            endpoint = '/api/tickets/count/day';
        } else if (selectedOption === 'month') {
            endpoint = '/api/tickets/count/month';
        } else if (selectedOption === 'week') {
            endpoint = '/api/tickets/count/week';
        } else if (selectedOption === 'years') {
            endpoint = '/api/tickets/count/years';
        }

        try {
            const result = await rpc(endpoint, {});
            const selectors = [
                { selector: '.new_ticket_count', value: result.new_ticket_count },
                { selector: '.in_progress_ticket_count', value: result.in_progress_ticket_count },
                { selector: '.done_ticket_count', value: result.done_ticket_count },
                { selector: '.cancelled_ticket_count', value: result.cancelled_ticket_count },
            ];
            selectors.forEach(item => {
                const elem = document.querySelector(item.selector);
                if (elem) elem.textContent = item.value;
            });

            document.querySelectorAll('.card').forEach(el => {
                el.addEventListener('click', (event) => {
                    const state = el.dataset.state;
                    if (state) {
                        this._redirectToTicketList(state);
                    }
                });
            });


        } catch (error) {
            console.error("Erreur lors de la récupération des tickets :", error);
        }
    }

    async _renderChart() {
        console.log("Starting _renderChart...");

        const chartSelectionElem = document.querySelector('#chart-selection');
        const selectedOption = chartSelectionElem ? chartSelectionElem.value : 'all';
        console.log("Selected period for chart:", selectedOption);

        let endpoint = '/api/tickets/stats'; // Par défaut, récupérer toutes les données des statistiques

        // Vérifier la sélection de la période
        if (selectedOption === 'month') {
            endpoint = '/api/tickets/chart/month';
        } else if (selectedOption === 'week') {
            endpoint = '/api/tickets/chart/week';
        } else if (selectedOption === 'today') {
            endpoint = '/api/tickets/chart/today';
        } else if (selectedOption === 'year') {
            endpoint = '/api/tickets/chart/year';
        } else if (selectedOption === 'all') {
            endpoint = '/api/tickets/stats'; 
        }

        console.log("Fetching chart data from endpoint:", endpoint);

        if (this.pieChart) {
            this.pieChart.destroy();
        }
        if (this.lineChart) {
            this.lineChart.destroy();
        }

        try {
            const result = await rpc(endpoint, {});
            console.log("Chart data fetched successfully:", result);

            // Nettoyage des données
            const filteredSteps = result.steps.filter((step, index) => result.ticket_counts[index] > 0);
            const filteredCounts = result.ticket_counts.filter(count => count > 0);

            console.log("Filtered Steps:", filteredSteps);
            console.log("Filtered Counts:", filteredCounts);

            const pieData = {
                labels: ['Résolu', 'Non Résolu'],
                datasets: [{
                    data: [result.resolved_count, result.unresolved_count],
                    backgroundColor: ['#2ECC71', '#9B59B6']
                }]
            };

            const pieOptions = {
                responsive: true,
                maintainAspectRatio: true,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const clickedIndex = elements[0].index;
                        const label = pieData.labels[clickedIndex];
                        this._redirectToTicketList(label === 'Résolu' ? 'résolu' : 'non-résolu');
                    }
                }
            };

            const pieCtx = document.querySelector('#pie-chart').getContext('2d');
            this.pieChart = new Chart(pieCtx, {
                type: 'pie',
                data: pieData,
                options: pieOptions
            });

            const barData = {
                labels: filteredSteps,
                datasets: [{
                    label: 'Comptage des tickets',
                    data: filteredCounts,
                    backgroundColor: '#36A2EB',
                    borderColor: '#0366d6',
                    borderWidth: 1
                }]
            };

            const barOptions = {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 2 }
                    }
                }
            };

            const lineCtx = document.querySelector('#line-chart').getContext('2d');
            this.lineChart = new Chart(lineCtx, {
                type: 'bar',
                data: barData,
                options: barOptions
            });
        } catch (error) {
            console.error("Erreur lors de la récupération des données du graphique :", error);
        }
    }


    async _renderAgents() {
        try {
            const result = await rpc('/api/tickets/agents_stats', {});
            const userLabels = result.map(item => item.user_name);
            const userData = result.map(item => item.resolved_count);

            const barData = {
                labels: userLabels,
                datasets: [{
                    label: 'Tickets résolus',
                    data: userData,
                    backgroundColor: '#3498DB'
                }]
            };
            const barOptions = {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, precision: 0 }
                }
            };
            const barCtx = document.querySelector('#bar-chart').getContext('2d');

            // Détruire l'ancienne instance si elle existe
            if (this.agentsChart) {
                this.agentsChart.destroy();
            }
            // Créer et enregistrer la nouvelle instance
            this.agentsChart = new Chart(barCtx, {
                type: 'bar',
                data: barData,
                options: barOptions
            });
        } catch (error) {
            console.error("Erreur lors de la récupération des statistiques des agents :", error);
        }
    }

    _redirectToTicketList(status) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.ticket",
            views: [[false, "list"], [false, 'form'], [false, 'kanban']],
            domain: [["statut", "=", status]],
            name: `Tickets ${status}`,
        });
    }

    _redirectToEmergencyList(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.ticket",
            views: [[false, "list"], [false, 'form']],
            domain: [["niveau_urgence", "=", state]],
            name: `Tickets Urgence: ${state}`,
        });
    }


    _redirectToStepList(step) {
        let kanbanState = '';
        switch (step) {
            case 'Nouveaux tickets':
                kanbanState = 'new';
                break;
            case 'Tickets en cours':
                kanbanState = 'in_progress';
                break;
            case 'Tickets terminés':
                kanbanState = 'done';
                break;
            case 'Tickets annulés':
                kanbanState = 'cancelled';
                break;
        }
        if (kanbanState) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "ticket.ticket",
                views: [[false, "list"], [false, "form"]],
                domain: [["kanban_state", "=", kanbanState]],
                name: `Tickets: ${step}`,
            });
        }
    }

    _redirectToState(state) {
        console.log("Redirecting to state:", state);
        let stateLabel = '';
        switch (state) {
            case 'new':
                stateLabel = 'Nouveaux tickets';
                break;
            case 'in_progress':
                stateLabel = 'Tickets en cours';
                break;
            case 'done':
                stateLabel = 'Tickets terminés';
                break;
            case 'cancelled':
                stateLabel = 'Tickets annulés';
                break;
            default:
                console.error(`Unknown state: ${state}`);
                return;
        }

        console.log(`State label: ${stateLabel}`);
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.ticket",
            views: [[false, "list"], [false, "form"]],
            domain: [["kanban_state", "=", state]],
            name: `Tickets: ${stateLabel}`,
        });
    }

}

registry.category('actions').add('dashboard', Dashboard);
