import { api } from "../services/client.js";
import {
  QUESTION_BANK_SORT_FIELDS,
  QUESTION_BANK_VERSION_STATES,
  buildQuestionQueryParams,
} from "./questionBankQuery.js";

export {
  QUESTION_BANK_SORT_FIELDS,
  QUESTION_BANK_VERSION_STATES,
  buildQuestionQueryParams,
};

const QUESTION_BANK_PREFIX = "/api/v1/question-banks";

export async function fetchQuestionBanks(slug) {
  const response = await api.get(`${QUESTION_BANK_PREFIX}`, {
    params: slug ? { category_slug: slug } : {},
  });
  return response.data;
}

export async function fetchQuestionCategories({ tree = true } = {}) {
  const response = await api.get(`${QUESTION_BANK_PREFIX}/categories`, {
    params: { tree },
  });
  return response.data;
}

export async function createQuestionCategory(payload) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/categories`, payload);
  return response.data;
}

export async function updateQuestionCategory(categoryId, payload) {
  const response = await api.put(`${QUESTION_BANK_PREFIX}/categories/${categoryId}`, payload);
  return response.data;
}

export async function deleteQuestionCategory(categoryId) {
  const response = await api.delete(`${QUESTION_BANK_PREFIX}/categories/${categoryId}`);
  return response.data;
}

export async function fetchQuestionTags() {
  const response = await api.get(`${QUESTION_BANK_PREFIX}/tags`);
  return response.data;
}

export async function createQuestionTag(payload) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/tags`, payload);
  return response.data;
}

export async function updateQuestionTag(tagId, payload) {
  const response = await api.put(`${QUESTION_BANK_PREFIX}/tags/${tagId}`, payload);
  return response.data;
}

export async function deleteQuestionTag(tagId) {
  const response = await api.delete(`${QUESTION_BANK_PREFIX}/tags/${tagId}`);
  return response.data;
}

export async function createQuestionBank(slug, name) {
  const response = await api.post(
    `${QUESTION_BANK_PREFIX}`,
    { name },
    { params: slug ? { category_slug: slug } : {} }
  );
  return response.data;
}

export async function fetchQuestions(query = {}) {
  const response = await api.get(`${QUESTION_BANK_PREFIX}/questions`, {
    params: buildQuestionQueryParams(query),
  });
  return response.data;
}

export async function fetchBankQuestions(bankId, query = {}) {
  const response = await api.get(`${QUESTION_BANK_PREFIX}/${bankId}/questions`, {
    params: buildQuestionQueryParams({ ...query, bankId: undefined }),
  });
  return response.data;
}

export async function createQuestion(bankId, payload) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/${bankId}/questions`, payload);
  return response.data;
}

export async function updateDraftQuestion(bankId, questionId, payload) {
  const response = await api.put(
    `${QUESTION_BANK_PREFIX}/${bankId}/questions/${questionId}/draft`,
    payload
  );
  return response.data;
}

export async function publishQuestion(bankId, questionId) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/${bankId}/questions/${questionId}/publish`);
  return response.data;
}

export async function createNewDraft(bankId, questionId) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/${bankId}/questions/${questionId}/drafts`);
  return response.data;
}

export async function archiveDraftQuestion(bankId, questionId) {
  const response = await api.delete(`${QUESTION_BANK_PREFIX}/${bankId}/questions/${questionId}/draft`);
  return response.data;
}

export async function fetchQuestionVersions(bankId, questionId) {
  const response = await api.get(`${QUESTION_BANK_PREFIX}/${bankId}/questions/${questionId}/versions`);
  return response.data;
}

export async function createQuestionImportJob(payload) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/imports`, payload);
  return response.data;
}

export async function checkStaleQuestions(items) {
  const response = await api.post(`${QUESTION_BANK_PREFIX}/check-stale`, { items });
  return response.data;
}
