"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { cn } from "@/lib/utils";

interface SearchInputProps {
  className?: string;
}

export function SearchInput({ className }: SearchInputProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = query.trim();

    router.push(
      normalizedQuery
        ? `/search?q=${encodeURIComponent(normalizedQuery)}`
        : "/search",
    );
  }

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={cn("relative w-full", className)}
    >
      <label htmlFor="homepage-search" className="sr-only">
        कथा, कविता, लेखक वा वाचक खोज्नुहोस्
      </label>
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground"
      />
      <input
        id="homepage-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="कथा, कविता, लेखक वा वाचक खोज्नुहोस्"
        className="h-12 w-full rounded-full border border-border bg-surface/90 pr-24 pl-12 font-nepali text-sm text-foreground shadow-[0_10px_32px_rgb(0_0_0_/_0.16)] transition-colors placeholder:text-muted-foreground/75 hover:border-primary/25 focus:border-primary/50 focus:outline-2 focus:outline-primary sm:h-14 sm:text-base"
      />
      <button
        type="submit"
        className="absolute top-1/2 right-1.5 min-h-11 -translate-y-1/2 rounded-full bg-primary px-4 font-nepali text-sm font-semibold text-background transition-colors hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 sm:px-5"
      >
        खोज्नुहोस्
      </button>
    </form>
  );
}
