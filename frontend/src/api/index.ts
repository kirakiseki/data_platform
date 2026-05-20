import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0) {
      console.error('API Error:', res.message)
      throw new Error(res.message || 'Request failed')
    }
    return res.data
  },
  (error) => {
    console.error('Request Error:', error)
    throw error
  }
)

export default api
