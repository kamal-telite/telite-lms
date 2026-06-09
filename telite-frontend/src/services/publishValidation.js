import { api } from "./client";

function describeRequestError(err, fallback) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status && detail) return `${fallback} (${status}: ${detail})`;
  if (status) return `${fallback} (${status})`;
  return fallback;
}

function validationError(type, message, context = {}) {
  return { type, message, ...context };
}

export async function validateCourseForPublishing(courseId) {
  const errors = [];
  const warnings = [];

  try {
    // Fetch the full course structure
    const { data } = await api.get(`/authoring/courses/${courseId}/builder`);
    const sections = data.sections || [];

    if (sections.length === 0) {
      errors.push(validationError("course", "Course has no sections."));
      return { isValid: false, errors, warnings };
    }

    // Collect all modules for a parallel block fetch (avoids N+1 serial calls)
    const allModules = sections.flatMap((s, sIdx) =>
      (s.modules || []).map(m => ({ ...m, _sectionTitle: s.title, _sectionIdx: sIdx + 1 }))
    );

    // Validate section/module structure first (no network needed)
    for (let sIdx = 0; sIdx < sections.length; sIdx++) {
      const section = sections[sIdx];
      const secNum = sIdx + 1;
      if (!section.title || section.title.trim() === "") {
        errors.push(validationError("section", `Section #${secNum} is missing a title.`, {
          sectionId: section.id,
          sectionTitle: section.title || `Section #${secNum}`,
        }));
      }
      if (!section.modules || section.modules.length === 0) {
        errors.push(validationError("section", `Section "${section.title || secNum}" has no modules.`, {
          sectionId: section.id,
          sectionTitle: section.title || `Section #${secNum}`,
        }));
      }
      (section.modules || []).forEach((mod, mIdx) => {
        if (!mod.title || mod.title.trim() === "") {
          errors.push(validationError("module", `Module #${mIdx + 1} in Section "${section.title}" is missing a title.`, {
            sectionId: section.id,
            sectionTitle: section.title,
            moduleId: mod.id,
            moduleTitle: mod.title || `Module #${mIdx + 1}`,
          }));
        }
      });
    }

    // Fetch all module blocks in parallel
    const blockResults = await Promise.allSettled(
      allModules.map(mod =>
        api.get(`/authoring/courses/${courseId}/modules/${mod.id}/blocks`)
          .then(r => ({ mod, blocks: r.data.blocks || [] }))
      )
    );

    for (const result of blockResults) {
      if (result.status === "rejected") {
        const mod = allModules[blockResults.indexOf(result)];
        errors.push(validationError(
          "system",
          describeRequestError(
            result.reason,
            `Failed to load blocks for module "${mod?.title || mod?.id || "unknown"}".`
          ),
          {
            moduleId: mod?.id,
            moduleTitle: mod?.title,
            sectionTitle: mod?._sectionTitle,
          }
        ));
        continue;
      }
      const { mod, blocks } = result.value;
      if (blocks.length === 0) {
        warnings.push(validationError("module", `Module "${mod.title || mod.id}" is empty.`, {
          moduleId: mod.id,
          moduleTitle: mod.title,
          sectionTitle: mod._sectionTitle,
        }));
      }
      blocks.forEach((block, bIdx) => {
        const bNum = bIdx + 1;
        if (block.block_type === "heading" && (!block.content || block.content.trim() === "")) {
          errors.push(validationError("block", `Heading block #${bNum} in module "${mod.title}" is missing a title.`, {
            moduleId: mod.id,
            moduleTitle: mod.title,
            sectionTitle: mod._sectionTitle,
            blockId: block.id,
            blockType: block.block_type,
          }));
        }
        if (["image", "video", "pdf"].includes(block.block_type)) {
          if (!(block.media_asset_id || block.settings?.asset_id || block.settings?.url)) {
            errors.push(validationError("block", `${block.block_type.toUpperCase()} block #${bNum} in module "${mod.title}" is missing media.`, {
              moduleId: mod.id,
              moduleTitle: mod.title,
              sectionTitle: mod._sectionTitle,
              blockId: block.id,
              blockType: block.block_type,
            }));
          } else if (!(block.media_asset_id || block.settings?.asset_id)) {
            warnings.push(validationError("block", `${block.block_type.toUpperCase()} block #${bNum} in module "${mod.title}" has an external/broken reference.`, {
              moduleId: mod.id,
              moduleTitle: mod.title,
              sectionTitle: mod._sectionTitle,
              blockId: block.id,
              blockType: block.block_type,
            }));
          }
        }
        if (block.block_type === "quiz_reference" && !block.settings?.quiz_id) {
          errors.push(validationError("block", `Quiz block #${bNum} in module "${mod.title}" has no selected quiz.`, {
            moduleId: mod.id,
            moduleTitle: mod.title,
            sectionTitle: mod._sectionTitle,
            blockId: block.id,
            blockType: block.block_type,
          }));
        }
      });
    }

  } catch (err) {
    errors.push(validationError("system", describeRequestError(err, "Failed to load course structure for validation.")));
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}
