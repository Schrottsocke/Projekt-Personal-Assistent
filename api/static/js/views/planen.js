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
  let summaryLoaded = false;

  function renderSummary() {
    return `
      <div id="planen-summary" class="planen-summary" style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <div class="card planen-stat" style="flex:1;min-width:90px;cursor:pointer;text-align:center;padding:12px 8px" data-stat-tab="tasks">
          <div class="planen-stat-value skeleton" id="stat-tasks" style="font-size:1.3rem;font-weight:700;color:var(--accent)">–</div>
          <div class="card-subtitle" style="font-size:0.75rem">Aufgaben offen</div>
        </div>
        <div class="card planen-stat" style="flex:1;min-width:90px;cursor:pointer;text-align:center;padding:12px 8px" data-stat-tab="cooking" data-stat-cooking="mealplan">
          <div class="planen-stat-value skeleton" id="stat-meals" style="font-size:1.3rem;font-weight:700;color:var(--accent)">–</div>
          <div class="card-subtitle" style="font-size:0.75rem">Mahlzeiten geplant</div>
        </div>
        <div class="card planen-stat" style="flex:1;min-width:90px;cursor:pointer;text-align:center;padding:12px 8px" data-stat-tab="cooking" data-stat-cooking="shopping">
          <div class="planen-stat-value skeleton" id="stat-shopping" style="font-size:1.3rem;font-weight:700;color:var(--accent)">–</div>
          <div class="card-subtitle" style="font-size:0.75rem">Einkaeufe</div>
        </div>
      </div>
    `;
  }

  async function loadSummary() {
    if (summaryLoaded) return;
    summaryLoaded = true;

    const [tasksRes, mealsRes, shoppingRes] = await Promise.allSettled([
      Api.getTasks(),
      Api.getMealPlanWeek(),
      Api.getShoppingItems(),
    ]);

    const taskEl = document.getElementById('stat-tasks');
    const mealEl = document.getElementById('stat-meals');
    const shopEl = document.getElementById('stat-shopping');

    if (taskEl) {
      taskEl.classList.remove('skeleton');
      if (tasksRes.status === 'fulfilled') {
        const tasks = Array.isArray(tasksRes.value) ? tasksRes.value : (tasksRes.value.tasks || []);
        const open = tasks.filter(t => t.status !== 'done' && t.status !== 'completed').length;
        taskEl.textContent = open;
      } else {
        taskEl.textContent = '?';
      }
    }

    if (mealEl) {
      mealEl.classList.remove('skeleton');
      if (mealsRes.status === 'fulfilled') {
        const plans = Array.isArray(mealsRes.value) ? mealsRes.value : (mealsRes.value.plans || mealsRes.value.meals || []);
        mealEl.textContent = plans.length;
      } else {
        mealEl.textContent = '?';
      }
    }

    if (shopEl) {
      shopEl.classList.remove('skeleton');
      if (shoppingRes.status === 'fulfilled') {
        const items = Array.isArray(shoppingRes.value) ? shoppingRes.value : (shoppingRes.value.items || []);
        const unchecked = items.filter(i => !i.checked).length;
        shopEl.textContent = unchecked;
      } else {
        shopEl.textContent = '?';
      }
    }

    // Bind stat clicks
    if (container) {
      container.querySelectorAll('[data-stat-tab]').forEach(el => {
        el.addEventListener('click', () => {
          activeTab = el.dataset.statTab;
          if (el.dataset.statCooking) activeCookingTab = el.dataset.statCooking;
          update();
        });
      });
    }
  }

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
      ${renderSummary()}
      ${renderTabs()}
      <div id="planen-content"></div>
    `;
    bindTabs();
    renderContent();
  }

  async function render(el) {
    container = el;
    summaryLoaded = false;
    update();
    loadSummary();
  }

  // Erlaube direktes Navigieren zu einem Sub-Tab
  function setTab(tab, cookingTab) {
    activeTab = tab;
    if (cookingTab) activeCookingTab = cookingTab;
  }

  return { render, setTab };
})();
