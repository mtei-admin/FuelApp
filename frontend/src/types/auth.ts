export interface User {
  id: number;
  username: string;
  role: string;
  full_name?: string | null;
  email?: string | null;
  is_active: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}
