export async function sharePage(input: {
  title: string;
  text?: string;
  url?: string;
}) {
  const url = input.url ?? window.location.href;
  if (navigator.share) {
    await navigator.share({ ...input, url });
    return "shared" as const;
  }
  await navigator.clipboard.writeText(url);
  return "copied" as const;
}
