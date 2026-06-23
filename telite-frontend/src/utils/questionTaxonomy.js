export function flattenCategoryOptions(categories = [], parentLabel = "", depth = 0) {
  return categories.flatMap((category) => {
    const label = parentLabel ? `${parentLabel} / ${category.name}` : category.name;
    return [
      {
        id: category.id,
        name: category.name,
        label,
        parent_id: category.parent_id ?? null,
        depth,
      },
      ...flattenCategoryOptions(category.children || [], label, depth + 1),
    ];
  });
}

export function toggleTagId(tagIds = [], tagId) {
  const normalized = Number(tagId);
  if (tagIds.includes(normalized)) {
    return tagIds.filter((id) => id !== normalized);
  }
  return [...tagIds, normalized].sort((a, b) => a - b);
}
