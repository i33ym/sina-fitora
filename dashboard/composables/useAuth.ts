import type { LoginRequest, LoginResponse } from '~/types'

export const useAuth = () => {
  // Get the API client we created earlier
  const { apiFetch } = useApi()
  
  // Cookie to store the authentication token
  // This persists across page refreshes
  const token = useCookie('auth_token', {
    maxAge: 60 * 60 * 24 * 7, // 7 days in seconds
    sameSite: 'lax', // CSRF protection
    secure: process.env.NODE_ENV === 'production', // HTTPS only in production
  })
  
  // Reactive state to track if user is logged in
  // useState is like ref() but shared across the app
  const isAuthenticated = useState<boolean>('isAuthenticated', () => {
    return !!token.value // Convert token to boolean (!! = not not)
  })

  /**
   * Login function
   * @param credentials - phone_number and password
   * @returns Promise<LoginResponse>
   */
  const login = async (credentials: LoginRequest): Promise<LoginResponse> => {
    try {
      // Call the login API endpoint
      const response = await apiFetch<LoginResponse>('/dietologist/auth/login', {
        method: 'POST',
        body: credentials, // Automatically converted to JSON
      })

      // Store the token in cookie
      token.value = response.token
      
      // Update authentication state
      isAuthenticated.value = true

      return response
      
    } catch (error: any) {
      // Clear any existing token on login failure
      token.value = null
      isAuthenticated.value = false
      
      // Re-throw error so component can handle it
      throw error
    }
  }

  /**
   * Logout function
   * Clears token and redirects to login page
   */
  const logout = () => {
    // Clear the token cookie
    token.value = null
    
    // Update authentication state
    isAuthenticated.value = false
    
    // Redirect to login page
    navigateTo('/login')
  }

  /**
   * Get the current auth token
   * @returns string | null
   */
  const getToken = (): string | null => {
    return token.value
  }

  /**
   * Check if user is currently authenticated
   * @returns boolean
   */
  const checkAuth = (): boolean => {
    return !!token.value
  }

  // Return all functions and state
  return {
    login,
    logout,
    getToken,
    checkAuth,
    isAuthenticated: readonly(isAuthenticated), // Make it read-only outside
  }
}