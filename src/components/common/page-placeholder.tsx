interface PagePlaceholderProps {
  eyebrow: string;
  title: string;
  description: string;
}

export function PagePlaceholder({
  eyebrow,
  title,
  description,
}: PagePlaceholderProps) {
  return (
    <section
      aria-labelledby="page-title"
      className="flex min-h-[calc(100dvh-15rem)] items-center"
    >
      <div className="max-w-2xl">
        <p className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">
          {eyebrow}
        </p>
        <h1
          id="page-title"
          className="mt-4 font-literary text-4xl leading-tight font-semibold text-foreground sm:text-5xl"
        >
          {title}
        </h1>
        <p className="mt-5 max-w-xl font-nepali text-base leading-8 text-muted-foreground sm:text-lg">
          {description}
        </p>
      </div>
    </section>
  );
}
