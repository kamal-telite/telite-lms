export function buildBankReferenceItems(questions = []) {
  return questions.map((question) => ({
    id: `bank-ref-${question.id}-${question.active_version_id || question.current_published_version_id}`,
    type: "bank_reference",
    question_id: question.id,
    version_id: question.active_version_id || question.current_published_version_id,
  }));
}
