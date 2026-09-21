import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  { path: "/", redirect: "/dataset" },
  { path: "/dataset", name: "dataset", component: () => import("../pages/page2-dataset/DatasetList.vue") },
  { path: "/annotation", name: "annotation", component: () => import("../pages/page3-annotation/Annotation.vue") },
  { path: "/training", name: "training", component: () => import("../pages/page4-training/Training.vue") },
  { path: "/pipeline", name: "pipeline", component: () => import("../pages/page5-pipeline/Pipeline.vue") },
  { path: "/monitor", name: "monitor", component: () => import("../pages/page6-monitor/Monitor.vue") },
  { path: "/rbac", name: "rbac", component: () => import("../pages/page7-rbac/Rbac.vue") },
  { path: "/dashboard", name: "dashboard", component: () => import("../pages/page8-dashboard/Dashboard.vue") },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.loaded) {
    await auth.fetchMe();
  }
  if (!auth.isAuthenticated) {
    auth.login();
    return false;
  }
  return true;
});

export default router;
