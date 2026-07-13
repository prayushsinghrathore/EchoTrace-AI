"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { resetPassword } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function ResetForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  function validateForm(): boolean {
    const errors: Record<string, string> = {};
    if (!password) {
      errors.password = "Password is required";
    } else if (password.length < 8) {
      errors.password = "Must be at least 8 characters";
    } else if (!/[A-Z]/.test(password)) {
      errors.password = "Must contain an uppercase letter";
    } else if (!/[a-z]/.test(password)) {
      errors.password = "Must contain a lowercase letter";
    } else if (!/\d/.test(password)) {
      errors.password = "Must contain a digit";
    } else if (!/[!@#$%^&*(),.?":{}|<>_\-]/.test(password)) {
      errors.password = "Must contain a special character";
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!validateForm()) return;
    if (!token) {
      setError("Missing reset token. Use the link from your email.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Invalid reset link</CardTitle>
          <CardDescription>
            This link is missing the reset token. Request a new reset link.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <Link href="/auth/forgot-password">
            <Button>Request Reset Link</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (success) {
    return (
      <Card>
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-2 h-10 w-10 rounded-lg bg-primary" />
          <CardTitle className="text-2xl">Password reset</CardTitle>
          <CardDescription>
            Your password has been updated successfully.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <div className="text-4xl">✅</div>
          <Link href="/auth/login">
            <Button>Sign in with new password</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="space-y-1 text-center">
        <div className="mx-auto mb-2 h-10 w-10 rounded-lg bg-primary" />
        <CardTitle className="text-2xl">Set new password</CardTitle>
        <CardDescription>Enter your new password below</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
          )}
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">New Password</label>
            <input
              id="password" type="password" placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              autoComplete="new-password" autoFocus
            />
            {validationErrors.password && <p className="text-xs text-destructive">{validationErrors.password}</p>}
          </div>
          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium">Confirm Password</label>
            <input
              id="confirmPassword" type="password" placeholder="••••••••"
              value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              autoComplete="new-password"
            />
            {validationErrors.confirmPassword && <p className="text-xs text-destructive">{validationErrors.confirmPassword}</p>}
          </div>
          <p className="text-xs text-muted-foreground">
            Password must contain at least 8 characters, an uppercase letter, a lowercase letter, a digit, and a special character.
          </p>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Resetting..." : "Reset Password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="h-64 animate-pulse rounded-lg bg-muted" />}>
      <ResetForm />
    </Suspense>
  );
}
