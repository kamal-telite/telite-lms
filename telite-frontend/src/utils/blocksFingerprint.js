/** Lightweight change fingerprint for block arrays — avoids JSON.stringify on every keystroke. */
export function blocksFingerprint(blocks) {
  if (!Array.isArray(blocks)) {
    return "";
  }
  return blocks
    .map((block) => {
      const settings = block.settings || {};
      return [
        block.id ?? "",
        block._tempId ?? "",
        block.is_deleted ? "1" : "0",
        block.sort_order ?? "",
        block.block_type ?? "",
        block.content?.length ?? 0,
        block.media_asset_id ?? "",
        settings.quiz_id ?? "",
        settings.asset_id ?? "",
        settings.locked ? "1" : "0",
      ].join("|");
    })
    .join(";");
}
