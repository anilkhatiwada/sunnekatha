"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, loginWithPassword, registerAccount } from "@/services";

const inputClassName =
  "mt-2 h-11 w-full rounded-lg border border-border bg-background/60 px-3 text-sm text-foreground focus:border-primary focus:outline-2 focus:outline-primary";

export function AccountAccessForm() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  return (
    <div className="mt-8 border-t border-border pt-7 text-left">
      <div className="grid grid-cols-2 rounded-full bg-background/60 p-1">
        {(["login", "register"] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={mode === value}
            onClick={() => {
              setMode(value);
              setError("");
            }}
            className={`rounded-full px-3 py-2.5 font-nepali text-sm transition-colors ${
              mode === value
                ? "bg-primary font-semibold text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {value === "login" ? "Sign in with email" : "New account"}
          </button>
        ))}
      </div>

      <form
        className="mt-5 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          setError("");
          setIsSubmitting(true);
          const form = new FormData(event.currentTarget);
          const request =
            mode === "login"
              ? loginWithPassword({
                  email: String(form.get("email") ?? "").trim(),
                  password: String(form.get("password") ?? ""),
                })
              : registerAccount({
                  email: String(form.get("email") ?? "").trim(),
                  username: String(form.get("username") ?? "").trim(),
                  displayName: String(form.get("displayName") ?? "").trim(),
                  password: String(form.get("password") ?? ""),
                  passwordConfirm: String(
                    form.get("passwordConfirm") ?? "",
                  ),
                });
          void request
            .then(() => window.location.assign("/profile"))
            .catch((requestError: unknown) => {
              setError(
                requestError instanceof ApiError
                  ? requestError.message
                  : "The account request failed. Please try again.",
              );
            })
            .finally(() => setIsSubmitting(false));
        }}
      >
        {mode === "register" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="font-nepali text-sm">
              Display name
              <input
                name="displayName"
                minLength={2}
                maxLength={100}
                required
                autoComplete="name"
                className={inputClassName}
              />
            </label>
            <label className="font-nepali text-sm">
              Username
              <input
                name="username"
                maxLength={150}
                required
                autoComplete="username"
                className={inputClassName}
              />
            </label>
          </div>
        ) : null}
        <label className="block font-nepali text-sm">
          Email
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className={inputClassName}
          />
        </label>
        <label className="block font-nepali text-sm">
          Password
          <input
            name="password"
            type="password"
            required
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            minLength={8}
            className={inputClassName}
          />
        </label>
        {mode === "register" ? (
          <label className="block font-nepali text-sm">
            Confirm password
            <input
              name="passwordConfirm"
              type="password"
              required
              autoComplete="new-password"
              minLength={8}
              className={inputClassName}
            />
          </label>
        ) : null}
        {error ? (
          <p role="alert" className="font-nepali text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-full font-nepali"
        >
          {isSubmitting
            ? "Please wait…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </Button>
      </form>
    </div>
  );
}
