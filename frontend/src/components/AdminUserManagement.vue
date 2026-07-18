<!-- Gestione utenti per admin: elenco utenti con ricerca, form di creazione e toggle di ruoli/attivazione.
     Props: nessuna. Eventi: nessuno (usa API admin). Stato interno: lista utenti, query di ricerca, form creazione.
     UI: toolbar con pulsante crea + input ricerca, tabella con toggle is_admin/is_client/is_active ed eliminazione. -->
<template>
  <div class="admin-users">
    <h2>{{ t("admin.users") }}</h2>
    <div class="toolbar">
      <button
class="btn-primary" @click="showCreateForm = true"
>
        {{ t("admin.createUser") }}
      </button>
      <input
        v-model="searchQuery"
        class="search-input"
        :placeholder="t('admin.searchUsers')"
      />
    </div>

    <div
v-if="showCreateForm" class="create-form"
>
      <h3>{{ t("admin.createUser") }}</h3>
      <div class="form-group">
        <label>{{ t("auth.username") }}</label>
        <input v-model="newUser.username">
      </div>
      <div class="form-group">
        <label>{{ t("auth.username") }}</label>
        <input
v-model="newUser.email" type="email" />
      </div>
      <div class="form-group">
        <label>{{ t("auth.password") }}</label>
        <input
v-model="newUser.password" type="password" />
      </div>
      <div class="form-actions">
        <button
class="btn-primary" @click="createUser"
:disabled="creating"
>
          {{ creating ? t("common.loading") : t("common.submit") }}
        </button>
        <button
class="btn-secondary" @click="showCreateForm = false"
>
          {{ t("common.cancel") }}
        </button>
      </div>
    </div>

    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>{{ t("auth.username") }}</th>
            <th>Email</th>
            <th>{{ t("admin.admin") }}</th>
            <th>{{ t("admin.client") }}</th>
            <th>{{ t("common.status") }}</th>
            <th>{{ t("common.actions") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
v-for="u in filteredUsers" :key="u.id"
>
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.email || "-" }}</td>
            <td>
              <button
class="btn-small" @click="toggleField(u, 'is_admin')"
>
                {{ u.is_admin ? t("common.yes") : t("common.no") }}
              </button>
            </td>
            <td>
              <button
class="btn-small" @click="toggleField(u, 'is_client')"
>
                {{ u.is_client ? t("common.yes") : t("common.no") }}
              </button>
            </td>
            <td>
              <button
class="btn-small" @click="toggleField(u, 'is_active')"
>
                {{ u.is_active ? t("common.yes") : t("common.no") }}
              </button>
            </td>
            <td>
              <button
class="btn-danger btn-small" @click="deleteUser(u.id)"
>
                {{ t("common.delete") }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "../composables/useI18n";
import { apiGet, apiPost, apiDelete } from "../utils/api";
import { useAuthStore } from "../stores/auth";

const { t } = useI18n();
const auth = useAuthStore();

const users = ref<
  Array<{
    id: number;
    username: string;
    email: string | null;
    is_admin: boolean;
    is_client: boolean;
    is_active: boolean;
    created_at: string | null;
  }>
>([]);

const searchQuery = ref("");
const showCreateForm = ref(false);
const creating = ref(false);

const newUser = ref({ username: "", email: "", password: "" });

const filteredUsers = computed(() => {
  const q = searchQuery.value.toLowerCase();
  if (!q) return users.value;
  return users.value.filter(
    (u) =>
      u.username.toLowerCase().includes(q) ||
      (u.email && u.email.toLowerCase().includes(q)),
  );
});

async function loadUsers() {
  try {
    const data = await apiGet<{
      users?: Array<{
        id: number;
        username: string;
        email: string | null;
        is_admin: boolean;
        is_client: boolean;
        is_active: boolean;
        created_at: string | null;
      }>;
    }>("/api/v1/admin/users", {}, { headers: auth.getAuthHeader() });
    users.value = data.users || [];
  } catch (e) {
    console.error("Failed to load users", e);
  }
}

async function createUser() {
  creating.value = true;
  try {
    await apiPost(
      "/api/v1/admin/users",
      {
        username: newUser.value.username,
        email: newUser.value.email,
        password: newUser.value.password,
      },
      { headers: auth.getAuthHeader() },
    );
    newUser.value = { username: "", email: "", password: "" };
    showCreateForm.value = false;
    await loadUsers();
  } catch (e) {
    console.error("Failed to create user", e);
  } finally {
    creating.value = false;
  }
}

async function toggleField(
  u: { id: number; is_admin: boolean; is_client: boolean; is_active: boolean },
  field: "is_admin" | "is_client" | "is_active",
) {
  try {
    await apiPost(
      `/api/v1/admin/users/${u.id}/toggle-${field === "is_admin" ? "admin" : field === "is_client" ? "client" : "active"}`,
      {},
      { headers: auth.getAuthHeader() },
    );
    u[field] = !u[field];
  } catch (e) {
    console.error(`Failed to toggle ${field}`, e);
  }
}

async function deleteUser(id: number) {
  if (!confirm("Eliminare questo utente?")) return;
  try {
    await apiDelete(`/api/v1/admin/users/${id}`, {
      headers: auth.getAuthHeader(),
    });
    users.value = users.value.filter((u) => u.id !== id);
  } catch (e) {
    console.error("Failed to delete user", e);
  }
}

onMounted(() => {
  loadUsers();
});
</script>

<style scoped>
.admin-users {
  padding: 20px;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.search-input {
  flex: 1;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.create-form {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  border: 1px solid var(--border);
}
.form-group {
  margin-bottom: 10px;
}
.form-group label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.85rem;
}
.form-group input {
  width: 100%;
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
}
.form-actions {
  display: flex;
  gap: 8px;
}
.table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 10px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}
.data-table th {
  background: var(--bg-secondary);
}
.btn-primary {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--accent);
  background: var(--accent-gradient);
  color: #000;
  cursor: pointer;
  font-weight: bold;
}
.btn-secondary {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
}
.btn-small {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
}
.btn-danger {
  border-color: var(--color-alert-border);
  color: var(--error);
}
</style>
