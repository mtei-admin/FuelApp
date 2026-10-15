import {
  PERMISSION_GROUPS,
  ROLE_TEMPLATE_OPTIONS,
} from "../../types/permissions";
import { permissionsForTemplate, togglePermission } from "../../utils/permissions";

interface PermissionPickerProps {
  selected: string[];
  onChange: (next: string[]) => void;
}

export function PermissionPicker({ selected, onChange }: PermissionPickerProps) {
  function applyTemplate(templateId: string) {
    if (!templateId) {
      return;
    }
    onChange(permissionsForTemplate(templateId));
  }

  return (
    <div className="permission-picker">
      <label htmlFor="user-permission-template">Apply template</label>
      <select
        id="user-permission-template"
        defaultValue=""
        onChange={(event) => {
          applyTemplate(event.target.value);
          event.target.value = "";
        }}
      >
        <option value="">Choose a preset…</option>
        {ROLE_TEMPLATE_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>

      {PERMISSION_GROUPS.map((group) => (
        <fieldset key={group.id} className="permission-group">
          <legend>{group.label}</legend>
          <div className="permission-grid">
            {group.permissions.map((perm) => {
              const checked = perm.baseline || selected.includes(perm.code);
              return (
                <label
                  key={perm.code}
                  className={`checkbox-row permission-row${perm.baseline ? " permission-baseline" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={perm.baseline}
                    onChange={(event) =>
                      onChange(togglePermission(selected, perm.code, event.target.checked))
                    }
                  />
                  <span>{perm.label}</span>
                  {perm.baseline && <span className="muted permission-note">All users</span>}
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
