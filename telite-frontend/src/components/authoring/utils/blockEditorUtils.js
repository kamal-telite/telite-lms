/**
 * Utility functions for lesson block editor
 */

/**
 * Get the key for a block (uses id if available, falls back to _tempId)
 * @param {Object} block - The block object
 * @returns {string|number} The block key
 */
export function blockKey(block) {
  return block.id || block._tempId;
}

/**
 * Create a new native quiz question with default structure
 * @returns {Object} New question object with default values
 */
export function createNativeQuizQuestion() {
  const suffix = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const questionId = `q_${suffix}`;
  const optionA = `opt_${suffix}_1`;
  const optionB = `opt_${suffix}_2`;
  return {
    id: questionId,
    text: "",
    points: 10,
    options: [
      { id: optionA, text: "" },
      { id: optionB, text: "" },
    ],
    correct_option_id: optionA,
  };
}

/**
 * Create default settings for a new block based on type
 * @param {string} type - The block type
 * @returns {Object} Default settings object
 */
export function getDefaultBlockSettings(type) {
  const defaults = {
    poll: {
      question: "",
      allow_multiple: false,
      anonymous_voting: false,
      show_results: "after_vote",
      allow_vote_change: false,
      options: [{ id: `opt_${Date.now()}`, text: "" }]
    },
    flashcard: {
      completion_mode: "all_cards",
      randomize_order: false,
      cards: [{ id: `card_${Date.now()}`, front_text: "", back_text: "" }]
    },
    resource_collection: {
      completion_mode: "view",
      resources: []
    },
    quiz: {
      passing_score: 80,
      max_attempts: 3,
      questions: [createNativeQuizQuestion()]
    }
  };
  return defaults[type] || {};
}
