<template>
  <div class="app-shell" :class="{ 'is-collapsed': sidebarCollapsed }">
    <aside
      id="app-sidebar"
      class="sidebar"
      :class="{ open: sidebarOpen, collapsed: sidebarCollapsed }"
    >
      <div class="sidebar-brand">
        <!-- .brand-text is visually hidden (not removed) in rail mode -->
        <div class="brand-text">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>

      <nav class="sidebar-nav" aria-label="Primary">
        <!-- title gives a native tooltip when the label is hidden in rail mode -->
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :title="item.label"
          @click="sidebarOpen = false"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <button
        type="button"
        class="sidebar-toggle"
        :aria-expanded="!sidebarCollapsed"
        aria-controls="app-sidebar"
        aria-label="Toggle sidebar width"
        :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <svg class="toggle-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M15 6l-6 6 6 6" />
        </svg>
      </button>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div v-if="sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false"></div>

    <div class="content-shell">
      <header class="topbar">
        <button
          type="button"
          class="menu-button"
          aria-label="Open navigation"
          aria-controls="app-sidebar"
          :aria-expanded="sidebarOpen"
          @click="sidebarOpen = true"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <span class="topbar-title">{{ t('nav.companyName') }}</span>
      </header>
      <div class="filter-bar-wrapper">
        <FilterBar />
      </div>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />
    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // sidebarOpen: mobile drawer visibility.
    const sidebarOpen = ref(false)

    // sidebarCollapsed: icons-only rail. A saved choice wins; otherwise start collapsed
    // below 1200px so the content column keeps enough room.
    const SIDEBAR_KEY = 'sidebar-collapsed'
    const readSavedSidebar = () => {
      try { return localStorage.getItem(SIDEBAR_KEY) } catch { return null } // storage can throw (private mode, blocked)
    }
    const savedSidebar = readSavedSidebar()
    const sidebarCollapsed = ref(
      savedSidebar !== null ? savedSidebar === 'true' : window.matchMedia('(max-width: 1199px)').matches
    )
    watch(sidebarCollapsed, (value) => {
      try { localStorage.setItem(SIDEBAR_KEY, String(value)) } catch { /* persistence is optional */ }
    })
    // Close the drawer after navigating
    watch(() => route.path, () => { sidebarOpen.value = false })

    const navItems = [
      { path: '/',           label: t('nav.overview'),       icon: '⊞' },
      { path: '/inventory',  label: t('nav.inventory'),      icon: '▤' },
      { path: '/orders',     label: t('nav.orders'),         icon: '◈' },
      { path: '/spending',   label: t('nav.finance'),        icon: '◎' },
      { path: '/demand',     label: t('nav.demandForecast'), icon: '↗' },
      { path: '/reports',    label: 'Reports',               icon: '≡' },
      { path: '/restocking', label: 'Restocking',            icon: '↺' },
    ]

    // Root path must be exact match; all others use startsWith
    const isActive = (path) => {
      if (path === '/') return route.path === '/'
      return route.path.startsWith(path)
    }

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      route,
      navItems,
      isActive,
      sidebarOpen,
      sidebarCollapsed,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 64px; /* 48px inner width (8px padding each side) fits the 32px avatar and 20px icons */
  --topbar-height: 56px;           /* mobile top bar; the sticky filter bar sits right below it */
  --focus-ring: 0 0 0 3px rgba(37, 99, 235, 0.35);
  --sidebar-transition: 0.2s ease;

  /* z-index scale. Existing values kept: filter bar 50, sidebar 100. Modals use 1000/2000 so they
     stay above everything here, including a drawer opened from the sidebar footer. */
  --z-filter-bar: 50;
  --z-topbar: 60;      /* above the filter bar, below the backdrop */
  --z-backdrop: 90;    /* covers topbar and content while the drawer is open */
  --z-sidebar: 100;
  --sidebar-bg: #ffffff;
  --sidebar-text: #64748b;
  --sidebar-text-active: #0f172a;
  --sidebar-hover-bg: #f1f5f9;
  --sidebar-active-bg: #eff6ff;
  --sidebar-active-text: #2563eb;
  --sidebar-border: #e2e8f0;

  --surface-bg: #f8fafc;
  --surface-card: #ffffff;
  --surface-border: #e2e8f0;
  --surface-border-hover: #cbd5e1;

  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;

  --brand: #2563eb;
  --brand-light: #eff6ff;
  --brand-border: #bfdbfe;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;

  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--surface-bg);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

.app-shell {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ── */
.app-shell {
  --sidebar-pad: var(--space-4); /* sidebar inner padding; footer menus offset by it */
  --sidebar-current: var(--sidebar-width);
}

.app-shell.is-collapsed {
  --sidebar-current: var(--sidebar-width-collapsed);
}

.sidebar {
  width: var(--sidebar-current);
  flex-shrink: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  /* overflow stays visible so footer menus can open to the right of the sidebar;
     only the nav list scrolls (see .sidebar-nav) */
  z-index: var(--z-sidebar);
  transition: width var(--sidebar-transition);
}

.sidebar-brand {
  padding: var(--space-5) var(--sidebar-pad);
  border-bottom: 1px solid var(--sidebar-border);
}

.sidebar-brand h1 {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.brand-subtitle {
  font-size: 0.72rem;
  color: var(--text-muted);
  display: block;
  margin-top: 2px;
}

.sidebar-nav {
  flex: 1;
  min-height: 0; /* lets the flex child shrink so overflow-y scrolls instead of growing the sidebar */
  overflow-y: auto;
  padding: var(--space-3) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.nav-item:hover {
  background: var(--sidebar-hover-bg);
  color: var(--text-primary);
}

.nav-item:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.nav-item.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-active-text);
  font-weight: 600;
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  flex-shrink: 0;
  opacity: 0.7;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.nav-label {
  white-space: nowrap;
}

/* Collapse toggle */
.sidebar-toggle {
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  margin: var(--space-2) var(--space-2) 0;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-sm);
  color: var(--sidebar-text);
  cursor: pointer;
}

.sidebar-toggle:hover {
  background: var(--sidebar-hover-bg);
  color: var(--text-primary);
}

.sidebar-toggle:focus-visible {
  outline: none;
  border-color: var(--brand);
  box-shadow: var(--focus-ring);
}

.toggle-icon {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform var(--sidebar-transition);
}

/* Chevron points inward when expanded; flipped to point outward when collapsed */
.sidebar.collapsed .toggle-icon {
  transform: scaleX(-1);
}

.sidebar-footer {
  padding: var(--space-3) var(--sidebar-pad);
  margin-top: var(--space-2);
  border-top: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* Footer controls are child components with scoped CSS; these global selectors are more
   specific (3 classes) than their scoped ones (class + attribute), so they win. */
.sidebar-footer .language-button,
.sidebar-footer .profile-button {
  width: 100%;
}

.sidebar-footer .profile-name,
.sidebar-footer .language-label {
  flex: 1;
  min-width: 0;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer .chevron {
  margin-left: auto;
}

/* Menus open to the right of the sidebar, anchored to the bottom of their control */
.sidebar-footer .dropdown-menu {
  top: auto;
  bottom: 0;
  right: auto;
  left: calc(100% + var(--sidebar-pad) + var(--space-2));
}

/* ── Icons-only rail ── */
.sidebar.collapsed {
  --sidebar-pad: var(--space-2);
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding-inline: 0;
}

.sidebar.collapsed .sidebar-brand {
  padding-block: var(--space-5);
}

.sidebar.collapsed .sidebar-footer {
  align-items: center;
}

.sidebar.collapsed .sidebar-footer .language-button,
.sidebar.collapsed .sidebar-footer .profile-button {
  width: auto;
  padding: var(--space-1);
  justify-content: center;
}

.sidebar.collapsed .sidebar-footer .language-button {
  padding: var(--space-2);
}

/* Visually hidden, not display:none, so screen readers still announce each link/button name */
.sidebar.collapsed .nav-label,
.sidebar.collapsed .brand-text,
.sidebar.collapsed .sidebar-footer .profile-name,
.sidebar.collapsed .sidebar-footer .language-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.sidebar.collapsed .sidebar-footer .chevron {
  display: none; /* decorative only; the button still toggles its menu */
}

/* ── Content shell ── */
.content-shell {
  margin-left: var(--sidebar-current);
  flex: 1;
  min-width: 0; /* flex items default to min-width:auto, which let wide children widen the page */
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--sidebar-transition);
}

/* Topbar and backdrop only exist in drawer mode */
.topbar,
.sidebar-backdrop {
  display: none;
}

/* FilterBar sits sticky at top of content area */
.filter-bar-wrapper {
  position: sticky;
  top: 0;
  z-index: var(--z-filter-bar);
  background: var(--surface-bg);
  border-bottom: 1px solid var(--surface-border);
}

.main-content {
  flex: 1;
  min-width: 0;
  padding: var(--space-8);
  max-width: 1400px;
  width: 100%;
}

/* ── Drawer mode ──
   900px: below this a 240px sidebar leaves under ~660px for content, so it becomes an
   off-canvas drawer (the 901-1199px range uses the rail instead). */
@media (max-width: 900px) {
  .app-shell .content-shell,
  .app-shell.is-collapsed .content-shell {
    margin-left: 0; /* the sidebar no longer takes layout space */
  }

  .sidebar,
  .sidebar.collapsed {
    --sidebar-pad: var(--space-4);
    width: var(--sidebar-width);
    max-width: 85vw;
    transform: translateX(-100%);
    box-shadow: var(--shadow-md);
    /* hidden while closed so off-screen links are not reachable by Tab; delayed until the slide-out ends */
    visibility: hidden;
    transition: transform var(--sidebar-transition), visibility 0s linear 0.2s;
  }

  .sidebar.open {
    transform: translateX(0);
    visibility: visible;
    transition: transform var(--sidebar-transition), visibility 0s;
  }

  /* The drawer always shows labels: undo the rail styling */
  .sidebar.collapsed .nav-item {
    justify-content: flex-start;
    padding-inline: var(--space-3);
  }

  .sidebar.collapsed .nav-label,
  .sidebar.collapsed .brand-text,
  .sidebar.collapsed .sidebar-footer .profile-name,
  .sidebar.collapsed .sidebar-footer .language-label {
    position: static;
    width: auto;
    height: auto;
    overflow: hidden;
    clip-path: none;
  }

  .sidebar.collapsed .sidebar-footer {
    align-items: stretch;
  }

  .sidebar.collapsed .sidebar-footer .language-button,
  .sidebar.collapsed .sidebar-footer .profile-button {
    width: 100%;
    padding: 0.5rem 0.875rem; /* original padding from the components */
    justify-content: flex-start;
  }

  .sidebar.collapsed .sidebar-footer .chevron {
    display: block;
  }

  .sidebar-toggle {
    display: none;
  }

  /* No room beside the drawer on phones, so menus open upward inside it */
  .sidebar-footer .dropdown-menu {
    bottom: calc(100% + var(--space-2));
    left: 0;
    min-width: 0;
    width: calc(var(--sidebar-width) - 2 * var(--sidebar-pad));
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: var(--z-backdrop);
    background: rgba(15, 23, 42, 0.4);
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    height: var(--topbar-height);
    padding: 0 var(--space-4);
    position: sticky;
    top: 0;
    z-index: var(--z-topbar);
    background: var(--sidebar-bg);
    border-bottom: 1px solid var(--sidebar-border);
  }

  .menu-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--surface-card);
    border: 1px solid var(--surface-border);
    border-radius: var(--radius-sm);
    color: var(--sidebar-text);
    cursor: pointer;
  }

  .menu-button:hover {
    background: var(--sidebar-hover-bg);
    color: var(--text-primary);
  }

  .menu-button:focus-visible {
    outline: none;
    border-color: var(--brand);
    box-shadow: var(--focus-ring);
  }

  .menu-button svg {
    width: 20px;
    height: 20px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
  }

  .topbar-title {
    font-size: 0.9375rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }

  /* Stick the filter bar under the topbar */
  .filter-bar-wrapper {
    top: var(--topbar-height);
  }

  .main-content {
    padding: var(--space-4);
  }
}

/* 600px: the wrapped filter bar gets tall, so on phones it scrolls with the page instead of
   covering a large part of the screen. */
@media (max-width: 600px) {
  .filter-bar-wrapper {
    position: static;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .content-shell,
  .toggle-icon {
    transition: none;
  }
}

/* ── Global utility classes ── */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: var(--space-1);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.stat-card:hover {
  border-color: var(--surface-border-hover);
  box-shadow: var(--shadow-md);
}

/* Left accent bar for status indication */
.stat-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
}

.stat-card.success::before { background: #10b981; }
.stat-card.warning::before { background: #f59e0b; }
.stat-card.danger::before  { background: #ef4444; }
.stat-card.info::before    { background: var(--brand); }

.stat-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  line-height: 1;
}

.stat-card.warning .stat-value { color: #ea580c; }
.stat-card.success .stat-value { color: #059669; }
.stat-card.danger  .stat-value { color: #dc2626; }
.stat-card.info    .stat-value { color: var(--brand); }

.card {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  border: 1px solid var(--surface-border);
  margin-bottom: var(--space-5);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.card:hover {
  border-color: var(--surface-border-hover);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--surface-border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.015em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid var(--surface-border);
  border-bottom: 1px solid var(--surface-border);
}

th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-weight: 700;
  color: var(--text-secondary);
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

td {
  padding: var(--space-3);
  border-bottom: 1px solid #f1f5f9;
  color: var(--text-primary);
  font-size: 0.875rem;
}

tbody tr { transition: background-color 0.1s; }
tbody tr:hover { background: #fafbfc; }
tbody tr:last-child td { border-bottom: none; }

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.badge.success   { background: #d1fae5; color: #065f46; }
.badge.warning   { background: #fed7aa; color: #92400e; }
.badge.danger    { background: #fecaca; color: #991b1b; }
.badge.info      { background: #dbeafe; color: #1e40af; }
.badge.increasing { background: #d1fae5; color: #065f46; }
.badge.decreasing { background: #fecaca; color: #991b1b; }
.badge.stable    { background: #e0e7ff; color: #3730a3; }
.badge.high      { background: #fecaca; color: #991b1b; }
.badge.medium    { background: #fed7aa; color: #92400e; }
.badge.low       { background: #dbeafe; color: #1e40af; }

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: 0.875rem;
}
</style>
