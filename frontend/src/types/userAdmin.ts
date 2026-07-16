export type UserRole =
  | "encoder"
  | "approver"
  | "purchaser"
  | "accounting"
  | "superuser";

export const USER_ROLES: UserRole[] = [
  "encoder",
  "approver",
  "purchaser",
  "accounting",
  "superuser",
];

export interface AdminUser {
  id: number;
  username: string;
  role: string;
  full_name?: string | null;
  email?: string | null;
  company?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface UserCreateRequest {
  username: string;
  password: string;
  full_name: string;
  role: UserRole;
  email?: string;
  company?: string;
}

export interface UserUpdateRequest {
  username?: string;
  full_name?: string;
  role?: UserRole;
  email?: string;
  password?: string;
  company?: string;
}
