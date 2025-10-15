<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
      <div>
        <h2 class="text-center text-3xl font-bold text-gray-900">
          NutriCare
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Dietologist Login
        </p>
      </div>
      
      <form @submit.prevent="handleLogin" class="mt-8 space-y-6">
        <div class="space-y-4">
          <div>
            <label for="phone" class="block text-sm font-medium text-gray-700">
              Phone Number
            </label>
            <input
              id="phone"
              v-model="credentials.phone_number"
              type="tel"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="+998901234567"
            />
          </div>
          
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              v-model="credentials.password"
              type="password"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="••••••••"
            />
          </div>
        </div>

        <div v-if="errorMessage" class="text-red-600 text-sm">
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading">Logging in...</span>
          <span v-else>Sign in</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LoginRequest } from '~/types'

// This page does NOT need auth middleware
definePageMeta({
  layout: false, // No layout for login page
  middleware: undefined // Explicitly no middleware
})

const { login } = useAuth()

const credentials = ref<LoginRequest>({
  phone_number: '',
  password: '',
})

const loading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
  loading.value = true
  errorMessage.value = ''
  
  try {
    await login(credentials.value)
    
    // Success! Redirect to dashboard
    await navigateTo('/dashboard')
    
  } catch (error: any) {
    console.error('Login error:', error)
    
    // Show error message
    errorMessage.value = error.data?.message || 'Invalid phone number or password'
    
  } finally {
    loading.value = false
  }
}

// If already logged in, redirect to dashboard
const { checkAuth } = useAuth()
if (checkAuth()) {
  navigateTo('/dashboard')
}
</script>