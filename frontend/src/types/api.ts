export interface ApiMeta {
  timestamp: string
  count: number | null
}

export interface ApiResponse<T> {
  data: T
  meta: ApiMeta
}
