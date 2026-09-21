import { defineStore } from "pinia";
import axios from "axios";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    userId: null,
    displayName: null,
    roles: [],
    dept: null,
    groups: [],
    loaded: false,
  }),
  getters: {
    isAuthenticated: (state) => !!state.userId,
    hasRole: (state) => (role) => state.roles.includes(role),
  },
  actions: {
    async fetchMe() {
      try {
        const { data } = await axios.get("/api/auth/me", { withCredentials: true });
        this.userId = data.user_id;
        this.displayName = data.display_name;
        this.roles = data.roles;
        this.dept = data.dept;
        this.groups = data.groups;
      } catch {
        this.userId = null;
      } finally {
        this.loaded = true;
      }
    },
    login() {
      window.location.href = "/api/auth/login";
    },
    async logout() {
      await axios.post("/api/auth/logout", {}, { withCredentials: true });
      this.$reset();
      window.location.href = "/";
    },
  },
});
