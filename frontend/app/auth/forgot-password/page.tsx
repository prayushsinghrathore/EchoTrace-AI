"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="space-y-1 text-center">
        <div className="mx-auto mb-2 h-10 w-10 rounded-lg bg-primary" />
        <CardTitle className="text-2xl">Reset your password</CardTitle>
        <CardDescription>
          Enter your email and we&apos;ll send you a reset link
        </CardDescription>
      </CardHeader>
      <CardContent>
        {sent ? (
          <div className="space-y-4 text-center">
            <div className="text-4xl">✉️</div>
            <p className="text-sm text-muted-foreground">
              If an account with <strong>{email}</strong> exists, a reset link has been sent.
              Check your inbox (and spam folder).
            </p>
            <p className="text-xs text-muted-foreground">
              The link expires after 1 hour.
            </p>
            <div className="flex justify-center gap-3 pt-2">
              <Button variant="outline" onClick={() => setSent(false)}>
                Send again
              </Button>
              <Link href="/auth/login">
                <Button variant="default">Back to login</Button>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                autoComplete="email"
                autoFocus
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading || !email.trim()}>
              {loading ? "Sending..." : "Send Reset Link"}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Remember your password?{" "}
              <Link href="/auth/login" className="font-medium text-primary underline-offset-4 hover:underline">
                Sign in
              </Link>
            </p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
