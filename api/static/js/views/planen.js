/**
 * Planen Hub – Zentrale Planungsansicht mit Sub-Tabs.
 * Buendelt Aufgaben, Kalender und Kochen (MealPlan + Rezepte + Einkauf).
 */
const PlanenView = (() => {
  let activeTab = 'tasks';
  let container = null;

  const TABS = [
    { id: 'tasks', label: 'Aufgaben', icon: 'check_circle' },
    { id: 'calendar', label: 'Kalender', icon: 'calendar_month' },
    { id: 'cooking', label: 'Kochen', icon: 'restaurant' },
  ];

  const COOKING_SUBTABS = [
    { id: 'mealplan', label: 'Wochenplan', icon: 'calendar_view_week' },
    { id: 'recipes', label: 'Rezepte', icon: 'menu_book' },
    { id: 'shopping', label: 'Einkauf', icon: 'shopping_cart' },
  ];

  let activeCookingTab = 'mealplan';

  function renderTabs() {
    return `
      <div class="planen-tabs">
        ${TABS.map(t => `
          <button class="planen-tab ${activeTab === t.id ? 'active' : ''}" data-tab="${t.id}">
            <span class="material-symbols-outlined" style="font-size:20px">${t.icon}</span>
            ${t.label}
          </button>
        `).join('')}
      </div>
    `;
  }

  function renderCookingSubtabs() {
    return `
      <div class="planen-subtabs">
        ${COOKING_SUBTABS.map(t => `
          <button class="planen-subtab ${activeCookingTab === t.id ? 'active' : ''}" data-cooking-tab="${t.id}">
            <span class="material-symbols-outlined" style="font-size:16px">${t.icon}</span>
            ${t.label}
          </button>
        `).join('')}
      </div>
    `;
  }

  function renderContent() {
    const contentEl = container.querySelector('#planen-content');
    if (!contentEl) return;

    if (activeTab === 'cooking') {
      contentEl.innerHTML = renderCookingSubtabs() + '<div id="cooking-content"></div>';
      bindCookingTabs();
      renderCookingContent();
    } else if (activeTab === 'tasks') {
      TasksView.render(contentEl);
    } else if (activeTab === 'calendar') {
      CalendarView.render(contentEl);
    }
  }

  function renderCookingContent() {
    const el = container.querySelector('#cooking-content');
    if (!el) return;

    if (activeCookingTab === 'mealplan') {
      MealPlanView.render(el);
    } else if (activeCookingTab === 'recipes') {
      RecipesView.render(el);
    } else if (activeCookingTab === 'shopping') {
      ShoppingView.render(el);
    }
  }

  function bindCookingTabs() {
    container.querySelectorAll('[data-cooking-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeCookingTab = btn.dataset.cookingTab;
        renderContent();
      });
    });
  }

  function bindTabs() {
    container.querySelectorAll('[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.tab;
        container.querySelector('#planen-content').innerHTML = '';
        update();
      });
    });
  }

  function update() {
    if (!container) return;
    container.innerHTML = `
      <div class="section-header">
        <h2><span class="material-symbols-outlined">event_note</span> Planen</h2>
      </div>
      ${renderTabs()}
      <div id="planen-content"></div>
    `;
    bindTabs();
    renderContent();
  }

  async function render(el) {
    container = el;
    update();
  }

  // Erlaube direktes Navigieren zu einem Sub-Tab
  function setTab(tab, cookingTab) {
    activeTab = tab;
    if (cookingTab) activeCookingTab = cookingTab;
  }

  return { render, setTab };
})();
