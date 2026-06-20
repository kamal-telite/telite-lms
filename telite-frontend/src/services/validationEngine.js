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
      case "audio":
      case "pdf":
      case "scorm":
        if (!(block.media_asset_id || block.settings?.asset_id || block.settings?.url)) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `${block.block_type.toUpperCase()} block #${blockNum} is missing media.`,
          });
        } else if (!(block.media_asset_id || block.settings?.asset_id)) {
          warnings.push({
            blockId: block.id || `temp-${index}`,
            message: `${block.block_type.toUpperCase()} block #${blockNum} has an external or broken asset reference without a valid Media Library ID.`,
          });
        }
        break;

      case "h5p":
        if (!(block.media_asset_id || block.settings?.asset_id)) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `H5P block #${blockNum} must use an asset from the Media Library.`,
          });
        } else if (!block.settings?.metadata?.mainLibrary) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `H5P block #${blockNum} is missing valid metadata. Please ensure the uploaded file is a valid .h5p package.`,
          });
        }
        break;

      case "embed":
        if (!block.settings?.url || block.settings.url.trim() === "") {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Embed block #${blockNum} is missing a URL.`,
          });
        }
        break;

      case "assignment":
        if (!block.content || block.content.trim() === "") {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Assignment block #${blockNum} is missing a title.`,
          });
        }
        if (!block.settings?.instructions || block.settings.instructions.trim() === "") {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Assignment block #${blockNum} is missing instructions.`,
          });
        }
        break;

      case "quiz_reference":
        errors.push({
          blockId: block.id || `temp-${index}`,
          message: `Quiz Reference block #${blockNum} is deprecated. Use a Native Quiz block instead.`,
        });
        break;

      case "quiz": {
        const questions = block.settings?.questions || [];
        if (questions.length === 0) {
          errors.push({
            blockId: block.id || `temp-${index}`,
            message: `Quiz block #${blockNum} has no questions.`,
          });
          break;
        }

        questions.forEach((question, questionIndex) => {
          if (!question.text || question.text.trim() === "") {
            errors.push({
              blockId: block.id || `temp-${index}`,
              message: `Question ${questionIndex + 1} in Quiz block #${blockNum} is missing text.`,
            });
          }

          const options = question.options || [];
          if (options.length < 2) {
            errors.push({
              blockId: block.id || `temp-${index}`,
              message: `Question ${questionIndex + 1} in Quiz block #${blockNum} needs at least two options.`,
            });
          }

          options.forEach((option, optionIndex) => {
            if (!option.text || option.text.trim() === "") {
              errors.push({
                blockId: block.id || `temp-${index}`,
                message: `Option ${optionIndex + 1} for question ${questionIndex + 1} is empty.`,
              });
            }
          });

          if (!question.correct_option_id || !options.some((option) => option.id === question.correct_option_id)) {
            errors.push({
              blockId: block.id || `temp-${index}`,
              message: `Question ${questionIndex + 1} in Quiz block #${blockNum} has no valid correct option.`,
            });
          }
        });
        break;
      }

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
