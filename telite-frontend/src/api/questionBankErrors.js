export function getQuestionBankErrorMessage(error, fallback = "Question Bank request failed.") {
  const detail = error?.response?.data?.detail || error?.response?.data?.message;
  if (detail) {
    return detail;
  }

  if (error?.response?.status === 409) {
    return "This taxonomy item is in use and cannot be deleted.";
  }

  return error?.message || fallback;
}
