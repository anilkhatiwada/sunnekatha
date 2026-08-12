"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useDeferredValue, useState } from "react";

import { AuthorCard } from "@/components/cards";
import { EmptyState } from "@/components/common/empty-state";
import { SectionError } from "@/components/common/section-error";
import { getAuthors, queryKeys } from "@/services";

export function AuthorsPageContent() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const deferredSearch = useDeferredValue(search);
  const authorsQuery = useQuery({
    queryKey: queryKeys.authors.list(deferredSearch, page),
    queryFn: () => getAuthors(deferredSearch, page),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-8 pb-10">
      <header className="max-w-3xl pt-2">
        <p className="font-nepali text-sm font-semibold text-primary">Creators</p>
        <h1 className="mt-2 font-literary text-4xl font-semibold text-foreground sm:text-5xl">
          Writers behind the words
        </h1>
        <p className="mt-4 font-nepali text-base leading-8 text-muted-foreground">
          Search authors and writers available on SunneKatha.
        </p>
      </header>

      <label className="flex min-h-12 max-w-xl items-center gap-3 rounded-xl border border-border bg-surface px-4 focus-within:border-primary">
        <Search className="size-5 text-muted-foreground" aria-hidden="true" />
        <span className="sr-only">Author Search</span>
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          placeholder="Search authors by name"
          className="min-w-0 flex-1 bg-transparent font-nepali text-foreground outline-none placeholder:text-muted-foreground"
        />
      </label>

      {authorsQuery.isError && (
        <SectionError
          onRetry={() => void authorsQuery.refetch()}
          isRetrying={authorsQuery.isFetching}
        />
      )}
      {authorsQuery.isSuccess && authorsQuery.data.results.length === 0 && (
        <EmptyState
          title="No authors found"
          description="Try another name or spelling."
        />
      )}
      <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        {authorsQuery.data?.results.map((author) => (
          <AuthorCard key={author.id} author={author} onPlay={() => undefined} />
        ))}
      </div>
      {authorsQuery.data && (authorsQuery.data.previous || authorsQuery.data.next) && (
        <nav aria-label="Author list pages" className="flex justify-center gap-3">
          <button
            type="button"
            disabled={!authorsQuery.data.previous}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            className="min-h-11 rounded-lg border border-border px-5 font-nepali text-sm font-semibold text-foreground disabled:opacity-40"
          >
            Previous
          </button>
          <span className="flex min-h-11 items-center font-nepali text-sm text-muted-foreground">
            Page {page}
          </span>
          <button
            type="button"
            disabled={!authorsQuery.data.next}
            onClick={() => setPage((value) => value + 1)}
            className="min-h-11 rounded-lg bg-primary px-5 font-nepali text-sm font-semibold text-primary-foreground disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
