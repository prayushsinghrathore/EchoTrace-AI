"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/contexts/auth-context";
import { updateProfile, changePassword } from "@/lib/auth-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

export default function ProfilePage() {
  const { user, isLoading } = useAuth();
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState("");
  const [nameEdited, setNameEdited] = useState(false);
  const [savingName, setSavingName] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPw, setChangingPw] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-2xl">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!user) return <p>Not authenticated</p>;

  const handleSaveName = async () => {
    if (!displayName.trim() || displayName === user.display_name) {
      setNameEdited(false);
      return;
    }
    setSavingName(true);
    try {
      await updateProfile({ display_name: displayName.trim() });
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
      setNameEdited(false);
      toast.success("Profile updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSavingName(false);
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPwError("");
    setPwSuccess(false);

    if (!currentPassword) { setPwError("Current password is required"); return; }
    if (newPassword.length < 8) { setPwError("New password must be at least 8 characters"); return; }
    if (newPassword !== confirmPassword) { setPwError("Passwords do not match"); return; }

    setChangingPw(true);
    try {
      await changePassword(currentPassword, newPassword);
      setPwSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Password changed");
    } catch (err) {
      setPwError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setChangingPw(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">Manage your account settings</p>
      </div>

      {/* Account Info */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your EchoTrace AI account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs text-muted-foreground">Email</label>
              <p className="font-medium">{user.email}</p>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Role</label>
              <p className="font-medium capitalize">{user.role}</p>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Status</label>
              <Badge variant={user.status === "active" ? "success" : "secondary"}>{user.status}</Badge>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Verified</label>
              <p className="font-medium">{user.is_verified ? "Yes" : "No"}</p>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Member since</label>
              <p className="font-medium">{new Date(user.created_at).toLocaleDateString()}</p>
            </div>
            {user.last_login_at && (
              <div>
                <label className="text-xs text-muted-foreground">Last login</label>
                <p className="font-medium">{new Date(user.last_login_at).toLocaleString()}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit Profile */}
      <Card>
        <CardHeader>
          <CardTitle>Display Name</CardTitle>
          <CardDescription>How your name appears across EchoTrace AI</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <input
              defaultValue={user.display_name || ""}
              onChange={(e) => { setDisplayName(e.target.value); setNameEdited(true); }}
              placeholder="Your display name"
              className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {nameEdited && (
              <Button onClick={handleSaveName} disabled={savingName}>
                {savingName ? "Saving..." : "Save"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Update your account password</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4">
            {pwError && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{pwError}</div>
            )}
            {pwSuccess && (
              <div className="rounded-md bg-green-50 p-3 text-sm text-green-700">Password changed successfully.</div>
            )}
            <div>
              <label htmlFor="current-pw" className="text-sm font-medium">Current Password</label>
              <input id="current-pw" type="password" value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                autoComplete="current-password"
              />
            </div>
            <div>
              <label htmlFor="new-pw" className="text-sm font-medium">New Password</label>
              <input id="new-pw" type="password" value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label htmlFor="confirm-pw" className="text-sm font-medium">Confirm New Password</label>
              <input id="confirm-pw" type="password" value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" disabled={changingPw}>
              {changingPw ? "Changing..." : "Change Password"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
