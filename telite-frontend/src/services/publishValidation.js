import { api } from "./client";

function describeRequestError(err, fallback) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status && detail) return `${fallback} (${status}: ${detail})`;
  if (status) return `${fallback} (${status})`;
  return fallback;
}

export async function validateCourseForPublishing(courseId) {
  const errors = [];
  const warnings = [];

  try {
    // Fetch the full course structure
    const { data } = await api.get(`/authoring/courses/${courseId}/builder`);
    const sections = data.sections || [];

    if (sections.length === 0) {
      errors.push({ type: "course", message: "Course has no sections." });
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
        errors.push({ type: "section", message: `Section #${secNum} is missing a title.` });
      }
      if (!section.modules || section.modules.length === 0) {
        errors.push({ type: "section", message: `Section "${section.title || secNum}" has no modules.` });
      }
      (section.modules || []).forEach((mod, mIdx) => {
        if (!mod.title || mod.title.trim() === "") {
          errors.push({ type: "module", message: `Module #${mIdx + 1} in Section "${section.title}" is missing a title.` });
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
        errors.push({
          type: "system",
          message: describeRequestError(
            result.reason,
            `Failed to load blocks for module "${mod?.title || mod?.id || "unknown"}".`
          ),
        });
        continue;
      }
      const { mod, blocks } = result.value;
      if (blocks.length === 0) {
        warnings.push({ type: "module", message: `Module "${mod.title || mod.id}" is empty.` });
      }
      blocks.forEach((block, bIdx) => {
        const bNum = bIdx + 1;
        if (block.block_type === "heading" && (!block.content || block.content.trim() === "")) {
          errors.push({ type: "block", message: `Heading block #${bNum} in module "${mod.title}" is missing a title.` });
        }
        if (["image", "video", "pdf"].includes(block.block_type)) {
          if (!block.settings?.url) {
            errors.push({ type: "block", message: `${block.block_type.toUpperCase()} block #${bNum} in module "${mod.title}" is missing media.` });
          } else if (!block.settings?.asset_id) {
            warnings.push({ type: "block", message: `${block.block_type.toUpperCase()} block #${bNum} in module "${mod.title}" has an external/broken reference.` });
          }
        }
        if (block.block_type === "quiz_reference" && !block.settings?.quiz_id) {
          errors.push({ type: "block", message: `Quiz block #${bNum} in module "${mod.title}" has no selected quiz.` });
        }
      });
    }

  } catch (err) {
    errors.push({
      type: "system",
      message: describeRequestError(err, "Failed to load course structure for validation."),
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}
