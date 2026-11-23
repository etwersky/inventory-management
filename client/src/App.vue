<template>
  <div class="app">
    <header class="top-nav">
      <div class="nav-container">
        <div class="logo">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </header>
    <div class="app-body">
      <div class="sidebar-slot" :class="{ collapsed: collapsed }">
        <aside class="sidebar" :class="{ collapsed: collapsed }">
          <nav class="sidebar-nav" :aria-label="t('nav.mainNavigation')">
            <router-link
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="sidebar-link"
              :aria-label="t(item.label)"
              :title="t(item.label)"
              @click="onNavigate"
            >
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="1.75" stroke-linecap="round"
                stroke-linejoin="round" aria-hidden="true" focusable="false">
                <path v-for="d in item.icon" :key="d" :d="d" />
              </svg>
              <span class="sidebar-label">{{ t(item.label) }}</span>
            </router-link>
          </nav>
          <button
            type="button"
            class="sidebar-toggle"
            :aria-expanded="String(!collapsed)"
            :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
            :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
            @click="toggleSidebar"
          >
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="1.75" stroke-linecap="round"
              stroke-linejoin="round" aria-hidden="true" focusable="false">
              <path d="M3 5h18v14H3z" />
              <path d="M9 5v14" />
              <path :d="collapsed ? 'M14 9l3 3-3 3' : 'M17 9l-3 3 3 3'" />
            </svg>
            <span class="sidebar-label">{{ collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar') }}</span>
          </button>
        </aside>
        <div v-if="overlayOpen" class="sidebar-backdrop" @click="onNavigate"></div>
      </div>
      <div class="app-column">
        <FilterBar />
        <main class="main-content">
          <router-view />
        </main>
      </div>
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
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
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
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

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

    // Sidebar
    const navItems = [
      { path: '/', label: 'nav.overview', icon: ['M3 12l9-8 9 8', 'M5 10v10h5v-6h4v6h5V10'] },
      { path: '/inventory', label: 'nav.inventory', icon: ['M21 8l-9-5-9 5 9 5 9-5z', 'M3 8v8l9 5 9-5V8', 'M12 13v8'] },
      { path: '/orders', label: 'nav.orders', icon: ['M9 3h6v3H9z', 'M7 5H5v16h14V5h-2', 'M9 12h6', 'M9 16h6'] },
      { path: '/spending', label: 'nav.finance', icon: ['M12 2v20', 'M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6'] },
      { path: '/demand', label: 'nav.demandForecast', icon: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'] },
      { path: '/restocking', label: 'nav.restocking', icon: ['M21 12a9 9 0 01-15.5 6.2', 'M3 12A9 9 0 018.5 5.8', 'M3 4v5h5', 'M21 20v-5h-5'] },
      { path: '/reports', label: 'nav.reports', icon: ['M14 3H6v18h12V7z', 'M14 3v4h4', 'M9 13h6', 'M9 17h6'] }
    ]

    const STORAGE_KEY = 'sidebarCollapsed'
    const MOBILE_QUERY = '(max-width: 767px)'
    let mql = null

    const readSaved = () => {
      try {
        const v = window.localStorage.getItem(STORAGE_KEY)
        if (v === '1') return true
        if (v === '0') return false
      } catch (e) { /* storage unavailable */ }
      return null
    }
    const saveCollapsed = (value) => {
      try {
        window.localStorage.setItem(STORAGE_KEY, value ? '1' : '0')
      } catch (e) { /* storage unavailable */ }
    }

    const isMobile = ref(false)
    try {
      mql = window.matchMedia(MOBILE_QUERY)
      isMobile.value = mql.matches
    } catch (e) { /* matchMedia unavailable */ }

    const saved = readSaved()
    // On small screens an expanded sidebar is an overlay, so never open it on load
    const collapsed = ref(isMobile.value ? true : (saved === null ? false : saved))
    let hasPreference = saved !== null

    const onMediaChange = (e) => {
      isMobile.value = e.matches
      if (!hasPreference) collapsed.value = e.matches
    }

    const toggleSidebar = () => {
      collapsed.value = !collapsed.value
      hasPreference = true
      saveCollapsed(collapsed.value)
    }

    // Expanded sidebar overlays content on small screens
    const overlayOpen = computed(() => isMobile.value && !collapsed.value)

    const onNavigate = () => {
      // Close the overlay after navigating on small screens (not saved as preference)
      if (overlayOpen.value) collapsed.value = true
    }

    const onKeydown = (e) => {
      if (e.key === 'Escape' && overlayOpen.value) collapsed.value = true
    }

    onMounted(() => {
      loadTasks()
      if (mql) {
        if (mql.addEventListener) mql.addEventListener('change', onMediaChange)
        else if (mql.addListener) mql.addListener(onMediaChange)
      }
      window.addEventListener('keydown', onKeydown)
    })
    onBeforeUnmount(() => {
      if (mql) {
        if (mql.removeEventListener) mql.removeEventListener('change', onMediaChange)
        else if (mql.removeListener) mql.removeListener(onMediaChange)
      }
      window.removeEventListener('keydown', onKeydown)
    })

    return {
      t,
      navItems,
      collapsed,
      overlayOpen,
      toggleSidebar,
      onNavigate,
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
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-nav {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 70px;
}

.nav-container > .language-switcher {
  margin-left: auto;
  margin-right: 1rem;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.logo h1 {
  font-size: 1.375rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.subtitle {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 400;
  padding-left: 0.75rem;
  border-left: 1px solid #e2e8f0;
}

.app-body {
  flex: 1;
  display: flex;
  align-items: stretch;
  min-width: 0;
}

.app-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-slot {
  position: relative;
  flex: 0 0 220px;
  width: 220px;
  transition: flex-basis 0.2s ease, width 0.2s ease;
}

.sidebar-slot.collapsed {
  flex-basis: 64px;
  width: 64px;
}

.sidebar {
  position: sticky;
  top: 70px;
  height: calc(100vh - 70px);
  width: 100%;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  padding: 0.75rem 0.5rem;
  overflow: hidden;
  z-index: 95;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  overflow-y: auto;
}

.sidebar-link,
.sidebar-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: 40px;
  padding: 0 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-family: inherit;
  font-weight: 500;
  font-size: 0.938rem;
  white-space: nowrap;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.sidebar-link:hover,
.sidebar-toggle:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.sidebar-link:focus-visible,
.sidebar-toggle:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: -2px;
}

.sidebar-link.router-link-exact-active {
  color: #2563eb;
  background: #eff6ff;
}

.nav-icon {
  flex: 0 0 20px;
}

.sidebar-toggle {
  margin-top: 0.5rem;
  border-top: 1px solid #e2e8f0;
  border-radius: 0 0 6px 6px;
  height: 48px;
}

.sidebar.collapsed .sidebar-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.sidebar-backdrop {
  display: none;
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

@media (max-width: 767px) {
  .nav-container {
    padding: 0 1rem;
  }

  .logo .subtitle {
    display: none;
  }

  .nav-container > .language-switcher {
    margin-right: 0.5rem;
  }

  /* Collapsed rail stays in flow; expanded sidebar overlays content */
  .sidebar-slot,
  .sidebar-slot.collapsed {
    flex: 0 0 56px;
    width: 56px;
  }

  .sidebar-slot:not(.collapsed) .sidebar {
    position: fixed;
    top: 70px;
    left: 0;
    width: 220px;
    box-shadow: 4px 0 16px rgba(15, 23, 42, 0.12);
    z-index: 110;
  }

  .sidebar-slot:not(.collapsed) .sidebar-backdrop {
    display: block;
    position: fixed;
    top: 70px;
    right: 0;
    bottom: 0;
    left: 0;
    background: rgba(15, 23, 42, 0.35);
    z-index: 105;
  }

  .sidebar {
    padding: 0.75rem 0.375rem;
  }

  .app .filters-bar .filters-container {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  .logo h1 {
    font-size: 1rem;
    line-height: 1.2;
  }

  .nav-container > .logo {
    min-width: 0;
  }

  .nav-container .profile-name {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  .app .filters-bar .filters-container,
  .app .filters-bar .filters-grid {
    flex-wrap: wrap;
  }

  .app .filters-bar {
    position: static;
  }

  /* Dashboard two-column chart grid must stack next to the sidebar rail */
  .app .main-content .charts-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .app .main-content .order-health-container {
    grid-template-columns: minmax(0, 1fr);
  }

  .app .filters-bar .filters-grid {
    gap: 0.5rem 0.75rem;
  }

  .app .filters-bar .filter-select {
    min-width: 0;
  }
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
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
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
