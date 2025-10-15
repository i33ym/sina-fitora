<template>
  <div>
    <!-- Your layout with sidebar, header, etc -->
    <slot />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})
</script>