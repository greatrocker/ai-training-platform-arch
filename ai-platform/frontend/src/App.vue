<script setup>
import NavSidebar from "./components/NavSidebar.vue";
</script>

<template>
  <div class="layout">
    <NavSidebar />
    <main class="content">
      <div class="content-inner">
        <RouterView />
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}
.content {
  flex: 1;
  min-width: 0;
  padding: 28px 32px 60px;
}
.content-inner {
  max-width: 1180px;
  margin: 0 auto;
}
</style>
