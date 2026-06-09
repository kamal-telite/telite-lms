/**
 * validationEngine.js
 * Real-time validation for Lesson Blocks in the Native Course Builder.
 */

export function validateBlocks(blocks) {
  const errors = [];
  const warnings = [];

  if (!blocks || blocks.length === 0) {
    warnings.push({ id: "empty-module", message: "This module has no content blocks." });
    return { isValid: true, errors, warnings };
  }

  blocks.forEach((block, index) => {
    const blockNum = index + 1;
    
    switch (block.block_type) {
      case "heading":
        if (!block.content || block.content.trim() === "") {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Heading block #${blockNum} is missing a title.`,
          });
        }
        break;

      case "text":
      case "paragraph":
        if (!block.content || block.content.trim() === "") {
          warnings.push({
            blockId: block.id || `temp-${index}`,
            message: `${block.block_type === "paragraph" ? "Paragraph" : "Text"} block #${blockNum} is empty.`,
          });
        }
        break;

      case "image":
      case "video":
      case "pdf":
        if (!block.settings?.url) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `${block.block_type.toUpperCase()} block #${blockNum} is missing media.`,
          });
        } else if (!block.settings?.asset_id) {
          warnings.push({
            blockId: block.id || `temp-${index}`,
            message: `${block.block_type.toUpperCase()} block #${blockNum} has an external or broken asset reference without a valid Media Library ID.`,
          });
        }
        break;

      case "quiz_reference":
        if (!block.settings?.quiz_id) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Quiz Reference block #${blockNum} has no quiz selected.`,
          });
        }
        break;

      default:
        // Unknown block types
        warnings.push({
          blockId: block.id || `temp-${index}`,
          message: `Block #${blockNum} has an unknown type: ${block.block_type}.`,
        });
        break;
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}
