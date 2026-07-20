/**
 * Tiny DOM helper — creates elements without innerHTML, so all question text
 * (which may contain code snippets like `<T>` or `a < b`) renders safely.
 */

type Child = Node | string;

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: {
    className?: string;
    onClick?: (event: Event) => void;
    disabled?: boolean;
    href?: string;
    title?: string;
  } = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (attrs.className) node.className = attrs.className;
  if (attrs.title) node.title = attrs.title;
  if (attrs.onClick) node.addEventListener("click", attrs.onClick);
  if (attrs.disabled !== undefined && "disabled" in node) {
    (node as HTMLButtonElement).disabled = attrs.disabled;
  }
  if (attrs.href !== undefined && "href" in node) {
    (node as HTMLAnchorElement).href = attrs.href;
  }
  for (const child of children) {
    node.append(child instanceof Node ? child : document.createTextNode(child));
  }
  return node;
}

/** Replace the app container's content with the given nodes. */
export function render(...nodes: Child[]): void {
  const app = document.getElementById("app");
  if (!app) throw new Error("#app container missing");
  app.replaceChildren(...nodes.map((n) => (n instanceof Node ? n : document.createTextNode(n))));
}
