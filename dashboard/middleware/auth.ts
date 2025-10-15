export default defineNuxtRouteMiddleware((to, from) => {
  // Get auth composable
  const { checkAuth } = useAuth()
  
  // Check if user is authenticated
  const isAuthenticated = checkAuth()
  
  // If not authenticated and trying to access protected route
  if (!isAuthenticated) {
    // Redirect to login page
    return navigateTo('/login')
  }
})