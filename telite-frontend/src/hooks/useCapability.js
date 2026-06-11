import { getSession } from "../context/session";

const SUPER_ADMIN_ROLE = "super_admin";

// Define the static capabilities matrix locally since we aren't fetching it from backend yet
// This mirrors the backend RolePermissions table.
const ROLE_CAPABILITIES = {
  author: [
    "block.create", "block.edit", "block.delete",
    "module.create", "module.edit", "module.delete",
    "section.create", "section.edit", "section.delete",
    "media.upload", "media.replace", "media.delete",
    "course.submit", "version.view", "version.create"
  ],
  reviewer: [
    "course.approve", "course.reject", "audit.view", "version.view"
  ],
  category_admin: [
    "block.create", "block.edit", "block.delete",
    "module.create", "module.edit", "module.delete",
    "section.create", "section.edit", "section.delete",
    "media.upload", "media.replace", "media.delete",
    "course.submit", "course.approve", "course.reject",
    "course.publish", "course.archive",
    "version.view", "version.create", "version.rollback",
    "audit.view", "audit.export"
  ],
  org_admin: [
    "block.create", "block.edit", "block.delete",
    "module.create", "module.edit", "module.delete",
    "section.create", "section.edit", "section.delete",
    "media.upload", "media.replace", "media.delete",
    "course.submit", "course.approve", "course.reject",
    "course.publish", "course.archive",
    "version.view", "version.create", "version.rollback",
    "audit.view", "audit.export", "permission.manage"
  ]
};

export function useCapability() {
  const session = getSession();
  const user = session?.user;
  
  const role = user?.role || "learner";

  const hasCapability = (permissionKey) => {
    if (role === SUPER_ADMIN_ROLE) return true;
    
    const capabilities = ROLE_CAPABILITIES[role] || [];
    return capabilities.includes(permissionKey);
  };

  return {
    hasCapability,
    // Convenience flags
    canEditStructure: hasCapability("module.edit") || hasCapability("section.edit"),
    canEditBlocks: hasCapability("block.edit"),
    canUploadMedia: hasCapability("media.upload"),
    canSubmit: hasCapability("course.submit"),
    canPublish: hasCapability("course.publish"),
    canApprove: hasCapability("course.approve"),
    canReject: hasCapability("course.reject"),
    canRollback: hasCapability("version.rollback"),
    canCreateVersion: hasCapability("version.create"),
    canViewVersions: hasCapability("version.view"),
    canViewAudit: hasCapability("audit.view"),
    canExportAudit: hasCapability("audit.export")
  };
}
