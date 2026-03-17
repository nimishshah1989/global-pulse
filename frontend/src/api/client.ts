import axios from 'axios'
import type { ApiResponse } from '@/types/api'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse<unknown>
    if (data && typeof data === 'object' && 'data' in data && 'meta' in data) {
      response.data = data.data
    }
    return response
  },
  (error) => {
    return Promise.reject(error)
  },
)

export default apiClient
