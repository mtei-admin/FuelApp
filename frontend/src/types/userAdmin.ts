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
  permissions: string[];
  permission_summary?: string | null;
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
  permissions: string[];
  email?: string;
  company?: string;
}

export interface UserUpdateRequest {
  username?: string;
  full_name?: string;
  permissions?: string[];
  email?: string;
  password?: string;
  company?: string;
}
