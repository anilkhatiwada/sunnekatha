"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { type ReactNode, useId } from "react";

interface HorizontalSectionProps {
  title: string;
  eyebrow?: string;
  description?: string;
  children: ReactNode;
  viewAllHref?: string;
}

export function HorizontalSection({
  title,
  eyebrow,
  description,
  children,
  viewAllHref,
}: HorizontalSectionProps) {
  const shouldReduceMotion = useReducedMotion();
  const headingId = useId();

  return (
    <motion.section
      aria-labelledby={headingId}
      initial={shouldReduceMotion ? false : { opacity: 0, y: 14 }}
      whileInView={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.42, ease: "easeOut" }}
    >
      <div className="mb-4 flex items-end justify-between gap-4 sm:mb-5">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-xs font-semibold tracking-[0.16em] text-primary uppercase">
              {eyebrow}
            </p>
          )}
          <h2
            id={headingId}
            className="font-literary text-2xl font-semibold text-foreground sm:text-3xl"
          >
            {title}
          </h2>
          {description && (
            <p className="mt-2 max-w-2xl font-nepali leading-7 text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {viewAllHref && (
          <Link
            href={viewAllHref}
            className="inline-flex min-h-11 shrink-0 items-center rounded-sm font-nepali text-sm font-semibold text-primary transition-colors hover:text-primary/80 focus-visible:outline-2 focus-visible:outline-primary"
          >
            सबै हेर्नुहोस्
          </Link>
        )}
      </div>

      <div
        tabIndex={0}
        aria-label={`${title} सामग्री`}
        className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-3 [scrollbar-width:none] focus-visible:rounded-lg focus-visible:outline-2 focus-visible:outline-primary sm:-mx-6 sm:gap-4 sm:px-6 lg:-mx-8 lg:px-8 [&::-webkit-scrollbar]:hidden"
      >
        {children}
      </div>
    </motion.section>
  );
}
