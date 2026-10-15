import type { User } from "../types/auth";
import {
  BASELINE_PERMISSIONS,
  COMPANY_SCOPED_PERMISSIONS,
  ROLE_TEMPLATE_PERMISSIONS,
} from "../types/permissions";

export type PermissionSubject =
  | string
  | Pick<User, "role" | "username" | "permissions">
  | null
  | undefined;

/** Return true when the subject holds a permission code. */
export function hasPermission(subject: PermissionSubject, code: string): boolean {
  if (subject && typeof subject === "object" && subject.permissions?.length) {
    return subject.permissions.includes(code);
  }
  return false;
}

/** Return true when the subject holds any listed permission. */
export function hasAnyPermission(subject: PermissionSubject, ...codes: string[]): boolean {
  return codes.some((code) => hasPermission(subject, code));
}

/** Apply a legacy role template to an explicit permission selection. */
export function permissionsForTemplate(templateId: string): string[] {
  return [...(ROLE_TEMPLATE_PERMISSIONS[templateId] ?? ROLE_TEMPLATE_PERMISSIONS.encoder)];
}

/** True when selected permissions require a company on the user account. */
export function permissionsRequireCompany(codes: string[]): boolean {
  return codes.some((code) => COMPANY_SCOPED_PERMISSIONS.has(code));
}

/** Toggle one permission in a selection (baseline codes are ignored). */
export function togglePermission(selected: string[], code: string, checked: boolean): string[] {
  if (BASELINE_PERMISSIONS.includes(code as (typeof BASELINE_PERMISSIONS)[number])) {
    return selected;
  }
  const set = new Set(selected);
  if (checked) {
    set.add(code);
  } else {
    set.delete(code);
  }
  return [...set].sort();
}
