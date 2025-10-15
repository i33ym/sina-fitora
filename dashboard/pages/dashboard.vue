<template>
  <div>
    <h1>Dashboard</h1>
    <!-- Your dashboard content -->
  </div>
</template>

<script setup lang="ts">
// This page requires authentication
definePageMeta({
  middleware: 'auth'
})
</script>