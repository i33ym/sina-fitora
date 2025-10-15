export const useApi = () => {
    const config = useRuntimeConfig()

    const baseURL = config.public.apiBaseUrl

    const token = useCookies('authToken')

    const apiFetch = async <T>(
        endpoint: string,
        options: any = {}
    ) : Promise<T> => {
        try {
            const response = await $fetch<T>(endpoint, {
                baseURL,
                headers: {
                    'Content-Type': 'application/json',
                    ...(token.value ? {Authorization: `Bearer ${token.value}`} : {}),
                    ...options.headers
                },

                ...options,
            })

            return response
        } catch (error: any) {
            console.error('API Error: ', error)

            if (error.response?.status === 401) {
                token.value = null
                navigateTo('/login')
            }

            throw error
        }
    }

    return {
        apiFetch,
    }
}