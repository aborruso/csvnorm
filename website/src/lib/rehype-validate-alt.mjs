export function rehypeValidateAlt() {
  return (tree, file) => {
    const visit = (node) => {
      if (!node || typeof node !== 'object') return;
      if (node.type === 'element' && node.tagName === 'img') {
        const alt = node.properties?.alt;
        if (alt === undefined || alt === null) {
          file.message('Image is missing alt text.', node);
        } else if (typeof alt === 'string') {
          const trimmed = alt.trim();
          if (trimmed.length > 0 && trimmed.length < 10) {
            file.message('Image alt text is too short (min 10 characters).', node);
          }
        }
      }
      const children = node.children;
      if (Array.isArray(children)) {
        for (const child of children) visit(child);
      }
    };

    visit(tree);
  };
}
