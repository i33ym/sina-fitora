<template>
    <div>
        <button @click="testApi">Test API</button>
    </div>
</template>

<script setup lang="ts">
import { useApi } from '../composables/useApi';

const {apiFetch} = useApi()

const testApi = async () => {
    try {
        const result = await apiFetch('/dietologist/clients')
        console.log('Success: ', result)
    } catch (error) {
        console.log('Failed: ', error)
    }
}
</script>